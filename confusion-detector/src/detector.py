"""Per-wearer calibration and the persistence filter that decides when to fire.

Two ideas do the work here, both taken from measurements in this repo rather than
guessed:

CALIBRATION. Absolute band-power values are meaningless across people - they depend on
skull thickness, hair, electrode contact, and time of day. What matters is where this
wearer is *relative to their own baseline*. Measured effect of calibrating within-subject
rather than across subjects: about +16 points of accuracy
(eeg-neural-signal-processing/RESULTS.md §11 A1 vs A2).

PERSISTENCE. A single window over threshold is noise. Requiring k consecutive elevated
windows collapses the false-alarm rate, because real states persist and noise does not.
Measured: k=1 gave ~19.5 false triggers/hour, k=4 gave ~1.5, with detection staying at
100% (RESULTS.md §10). The cost is latency, and latency is free here because we capture
forward rather than backward.
"""
import numpy as np


class Calibrator:
    """Learns this wearer's normal range of the load index."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.samples = []
        self.mean = None
        self.std = None

    def add(self, value):
        if value is not None:
            self.samples.append(value)

    def n(self):
        return len(self.samples)

    def enough(self):
        return len(self.samples) >= self.cfg.calibration.min_clean_windows

    def finish(self):
        if not self.enough():
            raise RuntimeError(
                f"calibration failed: only {len(self.samples)} clean windows, need "
                f"{self.cfg.calibration.min_clean_windows}. Usually this means the "
                f"electrodes are not making good contact, or the wearer was blinking a "
                f"lot. Re-seat the headband and try again."
            )
        a = np.asarray(self.samples)
        self.mean = float(a.mean())
        self.std = float(a.std())
        if self.std < 1e-6:
            self.std = 1e-6
        return self.mean, self.std

    def z(self, value):
        if value is None or self.mean is None:
            return None
        return (value - self.mean) / self.std

    def to_dict(self):
        return {"mean": self.mean, "std": self.std, "n_windows": len(self.samples)}


class PersistenceDetector:
    """Fires when the load index stays elevated for k consecutive windows.

    Deliberately simple and inspectable. On demo day you want to be able to explain
    exactly why it fired, and a threshold plus a counter is explainable in one sentence.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.run = 0
        self.last_fire_t = -1e9
        self.history = []

    def update(self, z, t):
        """Returns True on the window where a trigger fires.

        A dirty window (z is None) breaks the run rather than counting as low load -
        we genuinely do not know what was happening, so we should not accumulate
        evidence either way.
        """
        d = self.cfg.detector
        elevated = z is not None and z >= d.z_threshold
        self.run = self.run + 1 if elevated else 0
        self.history.append({"t": t, "z": z, "elevated": elevated, "run": self.run})

        if self.run < d.k_consecutive:
            return False
        if (t - self.last_fire_t) < d.cooldown_s:
            return False       # still inside the cooldown from the last bookmark
        self.last_fire_t = t
        self.run = 0
        return True

    def sustained_seconds(self):
        """How long the current elevated run has lasted, in seconds."""
        return self.run * self.cfg.signal.hop_s
