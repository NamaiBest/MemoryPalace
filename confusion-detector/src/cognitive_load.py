"""Turning a window of EEG into a single cognitive-load number.

The measure is frontal theta / alpha.

Why that: frontal midline theta (4-8 Hz) rises with mental effort and working-memory
load, and alpha (8-13 Hz) desynchronises (drops) when you engage with a task. The ratio
moves in the same direction for both, so it is more robust than either alone and it
partly cancels differences in electrode contact quality, which drift over a session.

This is deliberately NOT an ERP measure. ERPs are transient, need many averaged trials,
and "Xueqi's Idea" measured that a transient-event trigger produces ~29 false alarms per
hour. Band power over a multi-second window tracks a sustained state instead, which is
the regime that was measured to work.
"""
import numpy as np
from scipy import signal


class LoadExtractor:
    def __init__(self, fs, cfg):
        self.fs = fs
        self.cfg = cfg
        nyq = fs / 2.0
        lo, hi = cfg.signal.bandpass
        self.sos_bp = signal.butter(4, [lo / nyq, min(hi / nyq, 0.99)],
                                    btype="band", output="sos")
        f0 = cfg.signal.notch_hz
        if f0 and f0 < nyq:
            self.b_notch, self.a_notch = signal.iirnotch(f0 / nyq, Q=30.0)
        else:
            self.b_notch = self.a_notch = None

    def clean(self, x):
        """Filter, then report how much of the window is artifact.

        Returns (filtered, artifact_fraction). We do not try to *repair* blinks - with
        2-4 frontal channels there is no room for ICA. We detect and discard instead,
        which is honest and cheap.
        """
        y = signal.sosfiltfilt(self.sos_bp, x, axis=-1)
        if self.b_notch is not None:
            y = signal.filtfilt(self.b_notch, self.a_notch, y, axis=-1)
        bad = np.abs(y) > self.cfg.signal.artifact_uv
        frac = float(bad.any(axis=0).mean()) if y.size else 1.0
        return y, frac

    def band_power(self, x, band):
        """Welch PSD integrated over a band, averaged across channels."""
        nper = min(x.shape[-1], int(self.fs * 2))
        f, pxx = signal.welch(x, fs=self.fs, nperseg=nper, axis=-1)
        lo, hi = band
        m = (f >= lo) & (f < hi)
        if m.sum() < 2:
            return 0.0
        return float(np.mean(np.trapezoid(pxx[..., m], f[m], axis=-1)))

    def load_index(self, window):
        """window: (n_channels, n_samples) from the frontal electrodes only.

        Returns (index, artifact_fraction). index is None if the window is too dirty
        to trust - the caller must treat that as 'no reading', not as 'low load'.
        """
        y, frac = self.clean(window)
        if frac > self.cfg.signal.max_artifact_frac:
            return None, frac
        theta = self.band_power(y, self.cfg.bands.theta)
        alpha = self.band_power(y, self.cfg.bands.alpha)
        if alpha <= 0:
            return None, frac
        return float(np.log((theta + 1e-12) / (alpha + 1e-12))), frac


class RingBuffer:
    """Holds the most recent N samples of EEG. Small and fixed-size.

    Note this buffers *signal*, not video - a few seconds of 4-channel EEG is kilobytes.
    The battery-expensive thing (the camera) stays off until a trigger fires.
    """

    def __init__(self, n_channels, capacity):
        self.buf = np.zeros((n_channels, capacity))
        self.capacity = capacity
        self.filled = 0

    def push(self, chunk):
        n = chunk.shape[1]
        if n == 0:
            return
        if n >= self.capacity:
            self.buf[:] = chunk[:, -self.capacity:]
            self.filled = self.capacity
            return
        self.buf[:, :-n] = self.buf[:, n:]
        self.buf[:, -n:] = chunk
        self.filled = min(self.capacity, self.filled + n)

    def ready(self):
        return self.filled >= self.capacity

    def window(self):
        return self.buf
