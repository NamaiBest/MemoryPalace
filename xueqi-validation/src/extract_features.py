"""A-priori feature extraction. Definitions are frozen in this file.

No feature is added or removed based on test-set performance.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.signal import welch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.io_utils import ensure_dirs, setup_logging, write_json  # noqa: E402
from src.preprocess import iter_cached_epochs  # noqa: E402

TIME_FEATURES = ("mean", "peak", "peak_lat", "rms", "var", "energy")
FREQ_FEATURES = tuple(f"{b}_pow" for b in C.BANDS) + ("theta_alpha", "beta_alpha", "spec_entropy")
ALL_LOCAL = TIME_FEATURES + FREQ_FEATURES


def _window_slice(times: np.ndarray, win: tuple[float, float]) -> slice:
    lo = int(np.searchsorted(times, win[0], side="left"))
    hi = int(np.searchsorted(times, win[1], side="right"))
    return slice(lo, max(hi, lo + 1))


def _bandpower(freqs: np.ndarray, psd: np.ndarray, band: tuple[float, float]) -> np.ndarray:
    mask = (freqs >= band[0]) & (freqs < band[1])
    if not mask.any():
        return np.zeros(psd.shape[0], dtype=np.float64)
    return np.trapezoid(psd[:, mask], freqs[mask], axis=1)


def _spectral_entropy(psd: np.ndarray) -> np.ndarray:
    p = psd / (psd.sum(axis=1, keepdims=True) + 1e-12)
    p = np.clip(p, 1e-12, 1.0)
    ent = -(p * np.log(p)).sum(axis=1)
    n = psd.shape[1]
    return ent / (np.log(n) + 1e-12)


def feature_names(ch_names: list[str] | None = None) -> list[str]:
    ch_names = ch_names or C.CHANNEL_NAMES
    names = []
    for ch in ch_names:
        for feat in ALL_LOCAL:
            names.append(f"{ch}_{feat}")
    return names


def extract_from_array(
    data: np.ndarray,
    times: np.ndarray,
    sfreq: float,
    ch_names: list[str],
    window: tuple[float, float] = C.FEATURE_WINDOW,
) -> np.ndarray:
    """data: (n_epochs, n_ch, n_times) in µV. Returns (n_epochs, n_features)."""
    sl = _window_slice(times, window)
    x = data[:, :, sl]  # (n, ch, t)
    n, nch, nt = x.shape
    t = times[sl]
    if nt < 4:
        raise ValueError(f"feature window too short: {nt} samples")

    mean = x.mean(axis=2)
    # peak = signed value at max |amp|
    peak_idx = np.argmax(np.abs(x), axis=2)
    peak = np.take_along_axis(x, peak_idx[:, :, None], axis=2)[:, :, 0]
    peak_lat = t[peak_idx]
    rms = np.sqrt((x ** 2).mean(axis=2))
    var = x.var(axis=2)
    energy = (x ** 2).sum(axis=2) / sfreq

    nperseg = min(nt, int(round(sfreq * 0.4)))
    nperseg = max(nperseg, 8)
    freqs, psd = welch(x, fs=sfreq, nperseg=nperseg, axis=2)
    # psd: (n, ch, f) — welch with axis=2 returns (n, ch, f)
    psd_2d = psd.reshape(n * nch, -1)
    band_pow = {}
    for name, band in C.BANDS.items():
        bp = _bandpower(freqs, psd_2d, band).reshape(n, nch)
        band_pow[name] = np.log10(bp + 1e-12)
    theta_alpha = band_pow["theta"] - band_pow["alpha"]
    beta_alpha = band_pow["beta"] - band_pow["alpha"]
    spec_ent = _spectral_entropy(psd_2d).reshape(n, nch)

    blocks = [mean, peak, peak_lat, rms, var, energy]
    for name in C.BANDS:
        blocks.append(band_pow[name])
    blocks.extend([theta_alpha, beta_alpha, spec_ent])

    # Interleave as channel-major matching feature_names().
    # blocks[f] is (n, ch). We want [ch0_f0, ch0_f1, ..., ch1_f0, ...]
    stacked = np.stack(blocks, axis=2)  # (n, ch, nfeat)
    X = stacked.reshape(n, nch * stacked.shape[2])
    expected = len(feature_names(ch_names))
    if X.shape[1] != expected:
        raise RuntimeError(f"feature width {X.shape[1]} != {expected}")
    return X.astype(np.float32)


def columns_for_channels(all_names: list[str], keep: list[str]) -> np.ndarray:
    keep_set = set(keep)
    idx = [i for i, n in enumerate(all_names) if n.split("_", 1)[0] in keep_set]
    return np.array(idx, dtype=int)


def build_table(window: tuple[float, float] = C.FEATURE_WINDOW) -> dict:
    log = setup_logging("features")
    Xs, ys, subjects, tasks, rec_ids = [], [], [], [], []
    ch_names = None
    times = None
    sfreq = None
    n_rec = 0
    for pack in iter_cached_epochs():
        ch_names = pack["ch_names"]
        times = pack["times"]
        sfreq = pack["sfreq"]
        X = extract_from_array(pack["data"], times, sfreq, ch_names, window=window)
        n = len(pack["labels"])
        Xs.append(X)
        ys.append(pack["labels"])
        subjects.extend([pack["subject"]] * n)
        tasks.extend([pack["task"]] * n)
        rec_ids.extend([f"{pack['subject']}_{pack['task']}"] * n)
        n_rec += 1
    if not Xs:
        raise SystemExit("No cached epochs. Run preprocess.py first.")
    X = np.vstack(Xs)
    y = np.concatenate(ys)
    names = feature_names(ch_names)
    log.info("features X=%s from %s recordings; positives=%s", X.shape, n_rec, int(y.sum()))
    return {
        "X": X,
        "y": y.astype(np.int8),
        "subject": np.array(subjects),
        "task": np.array(tasks),
        "recording": np.array(rec_ids),
        "feature_names": np.array(names),
        "ch_names": np.array(ch_names),
        "window": window,
        "sfreq": sfreq,
        "times": times,
    }


def save_table(table: dict, name: str = "features_event") -> Path:
    ensure_dirs()
    path = C.CACHE_DIR / f"{name}.npz"
    np.savez_compressed(
        path,
        X=table["X"],
        y=table["y"],
        subject=table["subject"],
        task=table["task"],
        recording=table["recording"],
        feature_names=table["feature_names"],
        ch_names=table["ch_names"],
        window=np.array(table["window"]),
        sfreq=table["sfreq"],
    )
    write_json(
        C.RESULTS_DIR / f"{name}_meta.json",
        {
            "n_epochs": int(table["X"].shape[0]),
            "n_features": int(table["X"].shape[1]),
            "n_positive": int(table["y"].sum()),
            "n_negative": int((table["y"] == 0).sum()),
            "n_subjects": int(len(np.unique(table["subject"]))),
            "feature_names": table["feature_names"].tolist(),
            "window": list(table["window"]),
            "definitions": {
                "mean": "mean amplitude in the feature window (µV)",
                "peak": "signed amplitude at max |amp| (µV)",
                "peak_lat": "latency of that peak (s)",
                "rms": "root-mean-square amplitude (µV)",
                "var": "variance (µV^2)",
                "energy": "sum of squares / sfreq",
                "band_pow": "log10 band power from Welch PSD",
                "theta_alpha": "log theta minus log alpha",
                "beta_alpha": "log beta minus log alpha",
                "spec_entropy": "normalized spectral entropy of the Welch PSD",
            },
        },
    )
    return path


def load_table(name: str = "features_event") -> dict:
    z = np.load(C.CACHE_DIR / f"{name}.npz", allow_pickle=False)
    return {
        "X": z["X"],
        "y": z["y"],
        "subject": z["subject"].astype(str),
        "task": z["task"].astype(str),
        "recording": z["recording"].astype(str),
        "feature_names": z["feature_names"].astype(str),
        "ch_names": z["ch_names"].astype(str),
        "window": tuple(z["window"].tolist()),
        "sfreq": float(z["sfreq"]),
    }


def run() -> None:
    event = build_table(C.FEATURE_WINDOW)
    save_table(event, "features_event")
    pre = build_table(C.PREEVENT_FEATURE_WINDOW)
    save_table(pre, "features_preevent")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
