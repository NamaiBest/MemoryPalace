"""Feature extraction for EEG biometrics.

Deliberately classical: band power + Hjorth + spectral shape, fed to a linear model.
This is the baseline you should beat before reaching for a deep net -- and on small
subject pools it is often not far off.
"""
import numpy as np
from scipy import signal

# Bands capped at 40 Hz: the source data is already low-passed at 40 Hz, so anything
# above that is filter roll-off, not signal.
BANDS = {
    "delta": (1, 4),
    "theta": (4, 8),
    "alpha": (8, 13),
    "beta":  (13, 30),
    "gamma": (30, 40),
}


def hjorth(x):
    """Activity / mobility / complexity. Cheap time-domain shape descriptors."""
    dx = np.diff(x)
    ddx = np.diff(dx)
    var0 = np.var(x) + 1e-12
    var1 = np.var(dx) + 1e-12
    var2 = np.var(ddx) + 1e-12
    mobility = np.sqrt(var1 / var0)
    complexity = np.sqrt(var2 / var1) / (mobility + 1e-12)
    return np.log(var0), mobility, complexity


def epoch_features(epoch, fs):
    """epoch: (n_channels, n_samples) -> 1-D feature vector.

    Per channel: 5 log absolute band powers, 5 relative band powers,
    spectral edge frequency (95%), 3 Hjorth params = 14 features.
    """
    feats = []
    nper = min(epoch.shape[1], int(fs * 2))
    for ch in epoch:
        f, pxx = signal.welch(ch, fs=fs, nperseg=nper)
        abs_bp = []
        for lo, hi in BANDS.values():
            m = (f >= lo) & (f < hi)
            abs_bp.append(np.trapezoid(pxx[m], f[m]) if m.sum() > 1 else 0.0)
        abs_bp = np.asarray(abs_bp) + 1e-12
        total = abs_bp.sum()
        rel_bp = abs_bp / total

        # spectral edge frequency: where 95% of power below 40 Hz accumulates
        band = (f >= 1) & (f <= 40)
        c = np.cumsum(pxx[band])
        sef = f[band][np.searchsorted(c, 0.95 * c[-1])] if c[-1] > 0 else 0.0

        feats.extend(np.log(abs_bp))
        feats.extend(rel_bp)
        feats.append(sef)
        feats.extend(hjorth(ch))
    return np.asarray(feats, dtype=np.float64)


def feature_names(ch_names):
    names = []
    for c in ch_names:
        names += [f"{c}_logabs_{b}" for b in BANDS]
        names += [f"{c}_rel_{b}" for b in BANDS]
        names += [f"{c}_sef95", f"{c}_hjorth_act", f"{c}_hjorth_mob", f"{c}_hjorth_cplx"]
    return names


def epoch_signal(x, fs, epoch_s, overlap=0.0, max_uv=None):
    """Slice (n_channels, n_samples) into epochs. Optionally drop high-amplitude epochs."""
    n = int(epoch_s * fs)
    step = int(n * (1 - overlap))
    out = []
    for start in range(0, x.shape[1] - n + 1, step):
        e = x[:, start:start + n]
        if max_uv is not None and np.abs(e).max() > max_uv:
            continue  # artifact rejection
        out.append(e)
    return out
