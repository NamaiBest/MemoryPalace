"""Sample-clock processing using the project's existing EEG implementation."""
import math
import time
from dataclasses import asdict

import numpy as np
from src.config import Config
from src.cognitive_load import LoadExtractor
from src.detector import Calibrator, PersistenceDetector

CROWN_CHANNELS = ["CP3", "C3", "F5", "PO3", "PO4", "F6", "C4", "CP4"]


class Pipeline:
    def __init__(self, emit, on_trigger, source="synthetic", notch=60):
        self.emit, self.on_trigger, self.source = emit, on_trigger, source
        self.cfg = Config()
        self.cfg.signal.notch_hz = notch
        self.cfg.preferred_frontal = ("F5", "F6")
        self.fs = 256
        self.window = int(self.cfg.signal.window_s * self.fs)
        self.extractor = LoadExtractor(self.fs, self.cfg)
        self.reset()

    def reset(self):
        self.calibrator = Calibrator(self.cfg)
        self.detector = PersistenceDetector(self.cfg)
        self.phase = "calibrating"
        self.buffer = np.empty((2, 0))
        self.expected_ms = None
        self.origin_ms = None
        self.stream_id = None
        self.last_arrival = None
        self.calibration_windows = 0
        self.windows = 0
        self.gaps = 0
        self.last_measurement = None
        self.emit("calibration_started", {"config": asdict(self.cfg), "source": self.source})

    def set_threshold(self, value):
        value = float(value)
        if not 0.5 <= value <= 6.0:
            raise ValueError("detection threshold must be between 0.5 and 6.0 z")
        self.cfg.detector.z_threshold = value
        self.detector.run = 0
        self.emit("detection_threshold_changed", {"z_threshold": value})
        return {"z_threshold": value}

    def break_continuity(self, reason):
        self.buffer = np.empty((2, 0))
        self.detector.run = 0
        self.gaps += 1
        self.emit("signal_gap", {"reason": reason})

    def watchdog(self):
        if self.last_arrival is not None and time.monotonic() - self.last_arrival > 5:
            self.break_continuity("no EEG received for five seconds")
            self.last_arrival = None
            self.expected_ms = None

    def ingest(self, body):
        if body.get("source") != self.source:
            raise ValueError(f"server expects source={self.source}")
        stream_id = body.get("stream_id")
        if not isinstance(stream_id, str) or not 1 <= len(stream_id) <= 128:
            raise ValueError("stream_id must be a nonempty string (max 128 characters)")
        epoch = body["epoch"]
        info = epoch["info"]
        names = info["channelNames"]
        if not isinstance(names, list) or len(names) != 8 or set(names) != set(CROWN_CHANNELS):
            raise ValueError("expected all eight Crown channel names, without duplicates")
        if info["samplingRate"] != self.fs:
            raise ValueError("expected Crown samplingRate=256")
        start = float(info["startTime"])
        data = np.asarray(epoch["data"], dtype=float)
        if (data.ndim != 2 or data.shape[0] != 8 or not 1 <= data.shape[1] <= 1024
                or not np.isfinite(data).all() or not math.isfinite(start)):
            raise ValueError("expected finite 8 x (1..1024) EEG samples and timestamp")
        end = start + data.shape[1] * 1000 / self.fs
        if self.source == "crown" and not -5000 <= time.time() * 1000 - end <= 5000:
            self.break_continuity("stale or future live EEG")
            raise ValueError("live EEG timestamp is more than five seconds from laptop time")
        if self.stream_id is not None and stream_id != self.stream_id:
            raise ValueError("publisher changed: stop recording and reset calibration first")
        if self.expected_ms is not None and start < self.expected_ms - 1:
            # Network retry: never count identical EEG twice.
            return {"accepted": False, "reason": "duplicate_or_out_of_order"}
        if self.expected_ms is not None and abs(start - self.expected_ms) > 1:
            self.break_continuity("missing samples or timestamp discontinuity")
        self.stream_id = stream_id
        if self.origin_ms is None:
            self.origin_ms = start
        self.expected_ms = end
        self.last_arrival = time.monotonic()
        self.emit("eeg", body)
        selected = data[[names.index("F5"), names.index("F6")]]
        self.buffer = np.concatenate((self.buffer, selected), axis=1)
        while self.buffer.shape[1] >= self.window:
            window = self.buffer[:, :self.window]
            self.buffer = self.buffer[:, self.window:]
            sample_end_ms = end - self.buffer.shape[1] * 1000 / self.fs
            self.measure(window, (sample_end_ms - self.origin_ms) / 1000)
        return {"accepted": True, "phase": self.phase}

    def measure(self, window, elapsed):
        # Flat contacts and clipping can otherwise look like a clean low-load baseline.
        std = np.std(window, axis=1)
        invalid = bool(np.any(std < 0.1) or np.any(np.abs(window) > 1000))
        if invalid:
            idx, frac = None, 1.0
        else:
            idx, frac = self.extractor.load_index(window)
        if idx is not None and not math.isfinite(idx):
            idx = None
        self.windows += 1
        fired, z = False, None
        if self.phase == "calibrating":
            self.calibration_windows += 1
            self.calibrator.add(idx)
            if self.calibration_windows >= 30:
                try:
                    self.calibrator.finish()
                    # A nearly constant baseline makes tiny changes enormous z-scores.
                    # Demo heuristic; must be tuned/validated with wearer recordings.
                    self.calibrator.std = max(self.calibrator.std, 0.1)
                    self.phase = "ready"
                    self.emit("calibration_complete", self.calibrator.to_dict())
                except RuntimeError as exc:
                    self.phase = "calibration_failed"
                    self.emit("calibration_failed", {"error": str(exc)})
        elif self.phase == "ready":
            z = self.calibrator.z(idx)
            fired = self.detector.update(z, elapsed)
        self.last_measurement = {"sample_time_s": elapsed, "load_index": idx,
                                 "z_score": z, "artifact_fraction": frac,
                                 "run": self.detector.run, "trigger": fired,
                                 "phase": self.phase}
        self.emit("window", self.last_measurement)
        if fired:
            self.on_trigger(dict(self.last_measurement))

    def status(self):
        self.watchdog()
        return {"source": self.source, "phase": self.phase,
                "channels_used": ["F5", "F6"], "sampling_rate": self.fs,
                "calibration_windows": self.calibration_windows,
                "clean_calibration_windows": self.calibrator.n(),
                "baseline": self.calibrator.to_dict(), "windows": self.windows,
                "signal_connected": self.last_arrival is not None,
                "signal_gaps": self.gaps, "last_window": self.last_measurement,
                "detection_threshold": self.cfg.detector.z_threshold}
