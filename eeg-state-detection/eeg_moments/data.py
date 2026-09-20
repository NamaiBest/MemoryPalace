from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

CHANNELS = ("Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4")
SOURCES = {"synthetic_eeg", "replayed_eeg", "recorded_eeg"}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


@dataclass
class Recording:
    samples: np.ndarray  # channels x samples, microvolts
    sample_rate: float
    channels: tuple[str, ...]
    session_id: str
    recording_id: str
    source: str
    units: str = "uV"
    processing_id: str = "raw"

    def validate(self):
        if self.samples.ndim != 2 or self.samples.shape[0] != len(self.channels):
            raise ValueError("Samples must be channels x time, matching channel names.")
        if not np.isfinite(self.samples).all():
            raise ValueError("Nonfinite EEG samples: split/repair documented gaps before import.")
        if not np.isfinite(self.sample_rate) or self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive and finite.")
        if len(set(self.channels)) != len(self.channels) or not self.channels:
            raise ValueError("Channel names must be nonempty and unique.")
        if self.units != "uV":
            raise ValueError("Input units must be uV; convert explicitly before import.")
        if self.source not in SOURCES:
            raise ValueError(f"Unknown EEG provenance: {self.source}")
        if not self.session_id or not self.recording_id:
            raise ValueError("Session and recording IDs are required.")
        if not isinstance(self.processing_id, str) or not self.processing_id:
            raise ValueError("A processing identity is required.")
        if self.samples.shape[1] < 10 * self.sample_rate:
            raise ValueError("At least 10 seconds of EEG is required.")
        return self

    @property
    def duration_s(self):
        return self.samples.shape[1] / self.sample_rate

    def save(self, path):
        self.validate()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # No labels, event schedules, or Python objects are stored in the EEG file.
        np.savez_compressed(path, samples=self.samples, sample_rate=self.sample_rate,
                            channels=np.asarray(self.channels), units=self.units,
                            session_id=self.session_id, recording_id=self.recording_id,
                            source=self.source, processing_id=self.processing_id)

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as obj:
            rec = cls(samples=obj["samples"], sample_rate=float(obj["sample_rate"]),
                      channels=tuple(str(c) for c in obj["channels"]),
                      units=str(obj["units"]), session_id=str(obj["session_id"]),
                      recording_id=str(obj["recording_id"]), source=str(obj["source"]),
                      processing_id=str(obj["processing_id"]) if "processing_id" in obj else "raw")
        return rec.validate()
