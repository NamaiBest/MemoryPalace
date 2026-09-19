"""Event-related analysis. Runs before any classifier.

Question answered here: does EEG change around annotated surprise onsets?
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.signal import stft

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.io_utils import ensure_dirs, setup_logging, write_json  # noqa: E402
from src.preprocess import iter_cached_epochs  # noqa: E402


def _stack() -> dict:
    data, labels, subjects, tasks = [], [], [], []
    times = None
    ch_names = None
    for pack in iter_cached_epochs():
        data.append(pack["data"])
        labels.append(pack["labels"])
        n = len(pack["labels"])
        subjects.extend([pack["subject"]] * n)
        tasks.extend([pack["task"]] * n)
        times = pack["times"]
        ch_names = pack["ch_names"]
    if not data:
        raise SystemExit("No cached epochs. Run preprocess.py first.")
    return {
        "data": np.concatenate(data, axis=0),
        "labels": np.concatenate(labels),
        "subject": np.array(subjects),
        "task": np.array(tasks),
        "times": times,
        "ch_names": ch_names,
    }


def grand_averages(stack: dict) -> dict:
    y = stack["labels"]
    x = stack["data"]
    ch = stack["ch_names"]
    t = stack["times"]
    erp_s = x[y == 1].mean(axis=0)
    erp_c = x[y == 0].mean(axis=0)
    diff = erp_s - erp_c
    # peak of |diff| at Cz if present else channel 0
    cz = ch.index("Cz") if "Cz" in ch else 0
    post = t >= 0
    peak_i = int(np.argmax(np.abs(diff[cz, post])))
    peak_lat = float(t[post][peak_i])
    peak_amp = float(diff[cz, post][peak_i])
    n_s = int((y == 1).sum())
    n_c = int((y == 0).sum())
    return {
        "times": t,
        "ch_names": ch,
        "erp_surprise": erp_s,
        "erp_control": erp_c,
        "erp_diff": diff,
        "n_surprise": n_s,
        "n_control": n_c,
        "cz_peak_latency_s": peak_lat,
        "cz_peak_diff_uv": peak_amp,
        "n_subjects": int(len(np.unique(stack["subject"]))),
    }


def channel_mean_window(stack: dict, t0: float = 0.25, t1: float = 0.55) -> dict:
    t = stack["times"]
    m = (t >= t0) & (t <= t1)
    x = stack["data"][:, :, m].mean(axis=2)
    y = stack["labels"]
    means_s = x[y == 1].mean(axis=0)
    means_c = x[y == 0].mean(axis=0)
    return {
        "window": [t0, t1],
        "ch_names": stack["ch_names"],
        "mean_surprise": means_s,
        "mean_control": means_c,
        "mean_diff": means_s - means_c,
    }


def tfr_midline(stack: dict, channels=("Fz", "Cz")) -> dict:
    """STFT of trial-averaged waveforms (phase-locked) plus mean |STFT| of trials.

    Epochs are short (1 s); this is a coarse time-frequency picture, not a
    high-resolution wavelet analysis.
    """
    ch = stack["ch_names"]
    t = stack["times"]
    sfreq = 1.0 / np.median(np.diff(t))
    idx = [ch.index(c) for c in channels if c in ch]
    names = [ch[i] for i in idx]
    out = {"channels": names, "sfreq": float(sfreq)}
    nperseg = int(max(16, round(sfreq * 0.32)))
    noverlap = nperseg // 2
    for lab, mask in (("surprise", stack["labels"] == 1), ("control", stack["labels"] == 0)):
        evoked = stack["data"][mask][:, idx, :].mean(axis=0)  # (ch, t)
        induced = []
        f, tt, z = stft(evoked, fs=sfreq, nperseg=nperseg, noverlap=noverlap, axis=-1)
        # subsample trials for induced TFR
        trials = stack["data"][mask][:, idx, :]
        rng = np.random.default_rng(C.RANDOM_SEED)
        take = min(400, trials.shape[0])
        sel = rng.choice(trials.shape[0], size=take, replace=False)
        mag = []
        for tr in trials[sel]:
            _, _, zi = stft(tr, fs=sfreq, nperseg=nperseg, noverlap=noverlap, axis=-1)
            mag.append(np.abs(zi))
        out[f"{lab}_evoked_abs"] = np.abs(z)
        out[f"{lab}_induced_abs"] = np.mean(mag, axis=0)
        out["freqs"] = f
        out["tfr_times"] = tt + t[0]
    out["diff_evoked"] = out["surprise_evoked_abs"] - out["control_evoked_abs"]
    out["diff_induced"] = out["surprise_induced_abs"] - out["control_induced_abs"]
    return out


def run() -> dict:
    log = setup_logging("event_analysis")
    ensure_dirs()
    stack = _stack()
    ga = grand_averages(stack)
    chm = channel_mean_window(stack)
    tfr = tfr_midline(stack)
    np.savez_compressed(
        C.CACHE_DIR / "erp_grand_average.npz",
        times=ga["times"],
        ch_names=np.array(ga["ch_names"]),
        erp_surprise=ga["erp_surprise"],
        erp_control=ga["erp_control"],
        erp_diff=ga["erp_diff"],
    )
    np.savez_compressed(
        C.CACHE_DIR / "tfr_midline.npz",
        freqs=tfr["freqs"],
        tfr_times=tfr["tfr_times"],
        channels=np.array(tfr["channels"]),
        surprise_evoked_abs=tfr["surprise_evoked_abs"],
        control_evoked_abs=tfr["control_evoked_abs"],
        surprise_induced_abs=tfr["surprise_induced_abs"],
        control_induced_abs=tfr["control_induced_abs"],
        diff_evoked=tfr["diff_evoked"],
        diff_induced=tfr["diff_induced"],
    )
    summary = {
        "n_surprise_epochs": ga["n_surprise"],
        "n_control_epochs": ga["n_control"],
        "n_subjects": ga["n_subjects"],
        "cz_peak_latency_s": ga["cz_peak_latency_s"],
        "cz_peak_diff_uv": ga["cz_peak_diff_uv"],
        "channel_window_diff_uv": {
            ch: float(d) for ch, d in zip(chm["ch_names"], chm["mean_diff"])
        },
        "note": (
            "These are surprise-related EEG responses time-locked to events.tsv "
            "trial_type==surprises versus dummy-surprises. Not 'aha' signatures."
        ),
    }
    write_json(C.RESULTS_DIR / "event_analysis.json", summary)
    log.info(
        "ERP Cz peak diff %.2f µV at %.3f s (n_s=%s n_c=%s)",
        ga["cz_peak_diff_uv"], ga["cz_peak_latency_s"], ga["n_surprise"], ga["n_control"],
    )
    return summary


def main() -> None:
    run()


if __name__ == "__main__":
    main()
