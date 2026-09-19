"""Configuration for the confusion detector.

Design decisions here are downstream of two pieces of measured evidence in this repo:

  1. eeg-neural-signal-processing/RESULTS.md §10 - a persistence filter (require k
     consecutive windows over threshold) turns a mediocre per-window detector into a
     usable event trigger, but ONLY for states that persist for tens of seconds.
  2. "Xueqi's Idea"/RESULTS.md §10-11 - the same persistence approach applied to a
     TRANSIENT event (a ~200 ms surprise ERP) fails badly: ~29 false triggers/hour.

Those are consistent, not contradictory. Sustained states work; transient events do not.
This system therefore targets SUSTAINED cognitive load, not an instantaneous "aha".
"""
from dataclasses import dataclass, field


@dataclass
class BandConfig:
    """Frequency bands, in Hz."""
    delta: tuple = (1.0, 4.0)
    theta: tuple = (4.0, 8.0)
    alpha: tuple = (8.0, 13.0)
    beta: tuple = (13.0, 30.0)


@dataclass
class SignalConfig:
    bandpass: tuple = (1.0, 40.0)
    notch_hz: float = 60.0          # 50.0 in Europe/most of Asia
    window_s: float = 4.0           # analysis window
    # Hop == window, i.e. NON-OVERLAPPING windows. This matters more than any other
    # parameter here. With 75% overlap (hop=1.0) consecutive windows share most of
    # their data, so "k in a row" is only ~2 independent looks and the persistence
    # filter barely works: measured 30.3 false alarms/hour. At 0% overlap the same k
    # gives 1.3/hour with identical detection. See simulate.py --sweep.
    hop_s: float = 4.0

    # Artifact rejection. Frontal electrodes sit right above the eyes, so blinks and
    # jaw clenches produce swings an order of magnitude larger than real EEG. Without
    # this the detector fires on every blink - which would kill the live demo.
    artifact_uv: float = 120.0
    # Fraction of a window that may be artifact before we discard the whole window.
    max_artifact_frac: float = 0.20


@dataclass
class DetectorConfig:
    """Persistence filter. See RESULTS.md §10 for where these numbers come from."""
    # How many standard deviations above the wearer's own calibrated baseline counts
    # as "elevated". Per-wearer calibration matters: measured worth ~16 points.
    z_threshold: float = 2.0
    # k=4 with non-overlapping 4 s windows = ~16 s of sustained load before a
    # bookmark. On the drifting-baseline fixture: 100% detection, 7.2 false
    # alarms/hour, 15.7 s latency. Trade-offs from simulate.py --sweep:
    #   k=3 z=2.0  100% detection   8.9/hr   11.7 s   (faster, noisier)
    #   k=4 z=2.0  100% detection   7.2/hr   15.7 s   <- default
    #   k=4 z=2.5   94% detection   3.0/hr   16.0 s   (quieter, misses some)
    #   k=5 z=2.5   91% detection   2.5/hr   19.7 s
    k_consecutive: int = 4
    # After firing, ignore new triggers for this long, so one long confusion episode
    # produces one bookmark rather than twenty.
    cooldown_s: float = 30.0


@dataclass
class CalibrationConfig:
    """Baseline the wearer against themselves before the session starts."""
    # Non-overlapping windows mean fewer baseline samples per second, so calibration
    # has to be longer than it would be with overlap: 120 s gives ~29 clean windows.
    duration_s: float = 120.0
    # Discard windows that are mostly artifact during calibration too.
    min_clean_windows: int = 20


@dataclass
class CaptureConfig:
    """Capture-forward, not retrospective buffering.

    This is the whole battery argument: a sustained state is still happening a second
    after we detect it, so we do not need to have been recording beforehand. We take a
    still image on trigger. Nothing is recorded between triggers.
    """
    camera_index: int = 0
    image_width: int = 1280
    warmup_frames: int = 3          # webcams need a few frames to auto-expose


@dataclass
class Config:
    bands: BandConfig = field(default_factory=BandConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)

    # Which electrodes carry the cognitive-load signal. Frontal midline theta is the
    # classic mental-effort marker; on Muse the usable frontal pair is AF7/AF8.
    preferred_frontal: tuple = ("AF7", "AF8", "Fp1", "Fp2", "F7", "F8", "Fz")

    session_dir: str = "sessions"


DEFAULT = Config()
