#!/usr/bin/env python
"""Validate the detector against synthetic EEG with KNOWN confusion episodes.

The point: "the code runs" is not "the detector works". BrainFlow's synthetic board is a
sine generator with no sustained states, so it can never tell us whether the persistence
filter actually catches a real episode or how often it fires spuriously.

Here we generate EEG where we control the ground truth: pink noise plus alpha and theta
oscillators, with theta raised and alpha suppressed during scripted "high load" episodes.
Then we run the SAME LoadExtractor / Calibrator / PersistenceDetector the live system
uses, and measure detection rate, false alarms per hour, and latency.

This is a fixture, not evidence about real brains. It tests the signal chain and the
operating point, and it lets us tune k and z before touching hardware.

    .venv/bin/python simulate.py
    .venv/bin/python simulate.py --sweep
"""
import argparse
import numpy as np

from src.config import DEFAULT
from src.cognitive_load import LoadExtractor
from src.detector import Calibrator, PersistenceDetector

FS = 256.0          # matches Muse
N_CH = 2            # matches a two-electrode glasses build (AF7/AF8)


def pink(n, rng):
    """1/f noise - EEG background is not white."""
    white = rng.standard_normal(n)
    f = np.fft.rfftfreq(n, 1 / FS)
    s = np.fft.rfft(white)
    scale = np.ones_like(f)
    scale[1:] = 1.0 / np.sqrt(f[1:])
    return np.fft.irfft(s * scale, n=n)


def slow_drift(n, rng, seconds_scale=45.0, strength=0.30):
    """Slow multiplicative wander of band amplitude.

    Real resting EEG is NOT stationary: attention fluctuates, electrode impedance
    drifts, posture shifts. Without this the simulated baseline has a standard
    deviation around 0.04 in load-index units, against roughly 0.2-0.5 for real
    frontal theta/alpha - which makes any threshold look far better than it is.
    """
    k = int(seconds_scale * FS)
    w = rng.standard_normal(n + 2 * k)
    ker = np.hanning(2 * k)
    ker /= ker.sum()
    smooth = np.convolve(w, ker, mode="same")[k:k + n]
    smooth /= (np.std(smooth) + 1e-12)
    return np.exp(strength * smooth)


def synth(duration_s, episodes, rng, theta_gain=1.9, alpha_drop=0.45, drift=True):
    """Generate (n_ch, n_samples) EEG plus a boolean ground-truth mask.

    episodes: list of (start_s, end_s) where cognitive load is elevated.
    During an episode theta amplitude rises and alpha falls, which is the direction
    the real effect goes (frontal midline theta up with effort, alpha desynchronises).
    """
    n = int(duration_s * FS)
    t = np.arange(n) / FS
    truth = np.zeros(n, bool)
    for a, b in episodes:
        truth[int(a * FS):int(b * FS)] = True

    th_amp = np.where(truth, theta_gain, 1.0) * 8.0
    al_amp = np.where(truth, alpha_drop, 1.0) * 14.0
    # smooth the transitions - real states ramp, they don't step
    k = int(FS * 2)
    ker = np.ones(k) / k
    th_amp = np.convolve(th_amp, ker, mode="same")
    al_amp = np.convolve(al_amp, ker, mode="same")

    if drift:
        # independent wander per band, so the RATIO drifts too - the hard case
        th_amp = th_amp * slow_drift(n, rng)
        al_amp = al_amp * slow_drift(n, rng)

    out = np.zeros((N_CH, n))
    for c in range(N_CH):
        ph1, ph2 = rng.uniform(0, 2 * np.pi, 2)
        theta = th_amp * np.sin(2 * np.pi * 6.0 * t + ph1)
        alpha = al_amp * np.sin(2 * np.pi * 10.5 * t + ph2)
        out[c] = theta + alpha + 12.0 * pink(n, rng)
    return out, truth


def needed_calib_s(cfg):
    """Calibration must yield enough INDEPENDENT windows, so it scales with hop."""
    n = cfg.calibration.min_clean_windows + 3
    return max(60.0, n * cfg.signal.hop_s + cfg.signal.window_s)


def run(cfg, eeg, truth, calib_s=None):
    if calib_s is None:
        calib_s = needed_calib_s(cfg)
    """Run the real pipeline offline. Returns (events, n_windows, monitored_s)."""
    ex = LoadExtractor(FS, cfg)
    cal = Calibrator(cfg)
    det = PersistenceDetector(cfg)

    win = int(cfg.signal.window_s * FS)
    hop = int(cfg.signal.hop_s * FS)

    # calibration must sit on clean baseline only
    for start in range(0, int(calib_s * FS) - win, hop):
        idx, _ = ex.load_index(eeg[:, start:start + win])
        cal.add(idx)
    cal.finish()

    events, n_win = [], 0
    for start in range(int(calib_s * FS), eeg.shape[1] - win, hop):
        t = (start + win) / FS
        idx, _ = ex.load_index(eeg[:, start:start + win])
        z = cal.z(idx)
        n_win += 1
        if det.update(z, t):
            events.append(t)
    monitored = (eeg.shape[1] - int(calib_s * FS)) / FS
    return events, n_win, monitored


def score(events, episodes, monitored_s, tolerance_s=30.0):
    """Detection rate and false alarms per hour.

    An episode counts as detected if a trigger lands inside it (or within tolerance
    after its start - the persistence filter deliberately costs us latency).
    """
    hits, latencies = 0, []
    used = set()
    for a, b in episodes:
        for i, e in enumerate(events):
            if i in used:
                continue
            if a <= e <= b + tolerance_s:
                hits += 1
                latencies.append(e - a)
                used.add(i)
                break
    false = len(events) - len(used)
    return {
        "episodes": len(episodes),
        "detected": hits,
        "detection_rate": hits / max(1, len(episodes)),
        "false_alarms": false,
        "false_per_hour": false / (monitored_s / 3600.0),
        "mean_latency_s": float(np.mean(latencies)) if latencies else None,
    }


def scenario(seed=0, duration_s=1800.0, calib_s=None, cfg=None):
    """30 minutes: calibration, then confusion episodes of 25-40s."""
    if calib_s is None:
        calib_s = needed_calib_s(cfg) if cfg else 60.0
    rng = np.random.default_rng(seed)
    episodes, t = [], calib_s + 60.0
    while t < duration_s - 90:
        dur = rng.uniform(25, 40)
        episodes.append((t, t + dur))
        t += dur + rng.uniform(60, 110)
    eeg, truth = synth(duration_s, episodes, rng)
    return eeg, truth, episodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true", help="sweep k and z")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--save", metavar="PATH",
                    help="write a playback .npz with known episodes (demo fixture)")
    a = ap.parse_args()

    cfg = DEFAULT
    cfg.signal.artifact_uv = 400.0   # fixture amplitude, not real-EEG threshold

    if a.save:
        import os
        eeg, truth, eps = scenario(seed=0, cfg=cfg)
        os.makedirs(os.path.dirname(a.save) or ".", exist_ok=True)
        np.savez_compressed(
            a.save, eeg=eeg, fs=int(FS),
            ch_names=np.array(["AF7", "AF8"], dtype=object),
            episodes=np.array(eps),
        )
        mins = eeg.shape[1] / FS / 60
        print(f"wrote {a.save}: {mins:.1f} min, {len(eps)} known episodes")
        print("known episode start times (s):",
              ", ".join(f"{e[0]:.0f}" for e in eps))
        return

    if not a.sweep:
        print("=" * 76)
        print(f"  SIMULATION  k={cfg.detector.k_consecutive} "
              f"z>={cfg.detector.z_threshold} cooldown={cfg.detector.cooldown_s}s "
              f"({N_CH} channels @ {FS:.0f}Hz)")
        print("=" * 76)
        agg = []
        for s in range(a.seeds):
            eeg, truth, eps = scenario(seed=s, cfg=cfg)
            ev, nw, mon = run(cfg, eeg, truth)
            r = score(ev, eps, mon)
            agg.append(r)
            lat = f"{r['mean_latency_s']:5.1f}s" if r["mean_latency_s"] else "    -"
            print(f"  seed {s}: {r['detected']}/{r['episodes']} episodes  "
                  f"({r['detection_rate']*100:5.1f}%)  "
                  f"false={r['false_per_hour']:5.1f}/hr  latency={lat}")
        dr = np.mean([r["detection_rate"] for r in agg])
        fp = np.mean([r["false_per_hour"] for r in agg])
        la = [r["mean_latency_s"] for r in agg if r["mean_latency_s"]]
        print("-" * 76)
        print(f"  MEAN over {a.seeds} seeds: detection {dr*100:.1f}%   "
              f"false alarms {fp:.1f}/hour   latency {np.mean(la):.1f}s")
        print("=" * 76)
        return

    print("=" * 76)
    print("  OPERATING POINT SWEEP (mean over seeds)")
    print("=" * 76)
    print(f"  {'hop':>4s} {'ovl':>5s} {'k':>2s} {'z':>5s} | {'detect':>7s} "
          f"{'false/hr':>9s} {'latency':>8s}")
    print("  " + "-" * 62)
    # The signal does not depend on k or z, so generate once per seed and reuse.
    # Regenerating inside the loop made this ~30x slower for no reason.
    cache = {}

    def get(seed):
        if seed not in cache:
            cache[seed] = scenario(seed=seed, cfg=cfg)
        return cache[seed]

    for hop in (4.0, 6.0):
      for k in (3, 4, 5, 6, 8):
        for z in (1.5, 2.0, 2.5):
            cfg.signal.hop_s = hop
            cfg.detector.k_consecutive = k
            cfg.detector.z_threshold = z
            drs, fps, las = [], [], []
            for s in range(a.seeds):
                eeg, truth, eps = get(s)
                ev, nw, mon = run(cfg, eeg, truth)
                r = score(ev, eps, mon)
                drs.append(r["detection_rate"]); fps.append(r["false_per_hour"])
                if r["mean_latency_s"]:
                    las.append(r["mean_latency_s"])
            lat = f"{np.mean(las):6.1f}s" if las else "     -"
            ov = int(100 * (1 - hop / cfg.signal.window_s))
            print(f"  {hop:>4.1f} ({ov:>2d}%) {k:>2d} {z:>5.1f} | {np.mean(drs)*100:6.1f}% "
                  f"{np.mean(fps):8.1f} {lat:>8s}  sustained>={k*hop:.0f}s")
    print("=" * 76)


if __name__ == "__main__":
    main()
