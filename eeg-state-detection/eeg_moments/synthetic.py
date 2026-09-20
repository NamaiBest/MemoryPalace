"""A deliberately limited oscillatory simulator, not a biological insight model."""
import numpy as np
from scipy.signal import butter, sosfiltfilt

from .data import CHANNELS, Recording


def simulate(seed=100, session_seed=19, scenario="mixed", sample_rate=128.0):
    if scenario not in {"mixed", "independent", "negative", "baseline"}:
        raise ValueError("Scenario must be mixed, independent, negative, or baseline.")
    rng = np.random.default_rng(seed)
    # All calibration/evaluation blocks in a virtual session share sensor mixing.
    spatial_rng = np.random.default_rng(session_seed)
    mixing = np.eye(8) + spatial_rng.normal(0, 0.055, (8, 8))
    duration = 180.0
    n = round(duration * sample_rate)
    t = np.arange(n) / sample_rate
    freqs = np.fft.rfftfreq(n, 1 / sample_rate)
    spectrum = np.fft.rfft(rng.normal(size=(8, n)), axis=1)
    spectrum /= np.sqrt(np.maximum(freqs, 0.5))
    background = np.fft.irfft(spectrum, n=n, axis=1)
    background /= background.std(axis=1, keepdims=True)
    samples = background * rng.uniform(3.5, 5.0, (8, 1))
    phases = rng.uniform(0, 2 * np.pi, (8, 1))
    samples += 2 * np.sin(2 * np.pi * 10 * t + phases)
    samples += 1.5 * np.sin(2 * np.pi * 6 * t + phases)
    frontal = np.array([1.0, 0.9, 0.8, 0.85, 0.2, 0.2, 0.1, 0.1])
    posterior = np.array([0.15, 0.15, 0.3, 0.3, 0.75, 0.65, 1.0, 0.9])
    stretches = []
    for start, end in [(32, 55), (82, 108), (132, 156)]:
        shift = rng.uniform(-2, 2)
        start, end = start + shift, end + shift
        envelope = (np.tanh((t - start) / 0.9) - np.tanh((t - end) / 0.9)) / 2
        wave = rng.uniform(7, 11) * envelope * np.sin(
            2 * np.pi * rng.uniform(5, 7) * t + rng.uniform(0, 2 * np.pi))
        if scenario != "baseline":
            samples += frontal[:, None] * wave
            stretches.append({"start_s": float(start), "end_s": float(end)})

    if scenario == "mixed":
        # One leading-edge event, one late event, one event without a stretch.
        centers = [stretches[0]["start_s"] + rng.uniform(-1.5, 1.5),
                   stretches[1]["start_s"] + rng.uniform(11, 15),
                   rng.uniform(65, 69)]
        kinds = ["onset_adjacent", "late_in_stretch", "without_stretch"]
    elif scenario == "independent":
        centers = []
        while len(centers) < 3:
            c = rng.uniform(26, 160)
            if abs(c - 119) > 5 and all(abs(c - p) > 5 for p in centers):
                centers.append(c)
        kinds = ["independent_timing"] * 3
    else:
        centers, kinds = [], []
    bursts = []
    for center, kind in zip(centers, kinds):
        width = rng.uniform(0.65, 1.05)
        relative = (t - center) / width
        envelope = np.where(np.abs(relative) < 0.5, np.cos(np.pi * relative) ** 2, 0)
        wave = rng.uniform(13, 22) * envelope * np.sin(
            2 * np.pi * rng.uniform(18, 24) * t + rng.uniform(0, 2 * np.pi))
        samples += posterior[:, None] * wave
        bursts.append({"anchor_s": float(center), "start_s": float(center - width / 2),
                       "end_s": float(center + width / 2), "kind": kind})

    # Obvious high-amplitude blink-like artifact plus subthreshold muscle-like noise.
    samples += frontal[:, None] * 220 * np.exp(-0.5 * ((t - 119) / 0.18) ** 2)
    muscle = sosfiltfilt(butter(3, [15, 45], btype="bandpass", fs=sample_rate, output="sos"),
                        rng.normal(size=n))
    samples += frontal[:, None] * 22 * muscle * np.exp(-0.5 * ((t - 168) / 0.45) ** 2)
    samples = mixing @ samples
    rec = Recording(samples, sample_rate, CHANNELS, f"synthetic-session-{session_seed}",
                    f"synthetic-{scenario}-{seed}", "synthetic_eeg").validate()
    truth = {"recording_id": rec.recording_id, "scenario": scenario, "seed": seed,
             "session_seed": session_seed, "baseline_intervals_s": [[3.0, 20.0]],
             "bursts": sorted(bursts, key=lambda e: e["anchor_s"]), "stretches": stretches,
             "artifacts": [{"start_s": 118, "end_s": 120, "kind": "blink_like"},
                           {"start_s": 167, "end_s": 169, "kind": "muscle_like"}]}
    return rec, truth
