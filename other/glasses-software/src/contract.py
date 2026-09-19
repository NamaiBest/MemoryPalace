"""THE CONTRACT between the ML side and the glasses side.

This file is the whole point of the folder split. The ML pipeline
(confusion-detector/, or any future spike detector) knows nothing about Meta's SDK.
The glasses software knows nothing about EEG, band power, or classifiers. They agree
on exactly one thing: a SpikeEvent.

That means:
  - the ML team can improve the detector without touching glasses code
  - the glasses team can swap mock -> real hardware without touching ML code
  - either side can be tested alone

Anything that needs to cross the boundary goes in this file. Nothing else.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
import time
import uuid
import json


class SpikeKind(str, Enum):
    """What fired. Scope is deliberately narrow: semantic difficulty only.

      SEMANTIC - you hit something you did not understand. The N400: a negative
                 deflection ~400 ms after a word that does not fit, maximal over
                 centro-parietal scalp. This is the target.
      LOAD     - sustained effort in the seconds AFTER the semantic hit. Not a
                 separate detector and not a separate sensor - the same EEG stream,
                 a slower feature. A real reading struggle produces both: the N400
                 when you hit the word, then several seconds of elevated theta while
                 you re-read. Using both is what makes a single trial usable.
      MANUAL   - the wearer asked for it. Always trust this one.

    There is no startle/IMU kind. Physical flinches are out of scope by decision.
    """
    SEMANTIC = "semantic"
    LOAD = "load"
    MANUAL = "manual"


@dataclass
class SpikeEvent:
    """One detection, emitted by the ML side, consumed by the glasses side."""
    kind: SpikeKind
    confidence: float                    # 0..1, detector's own estimate
    detected_at: float = field(default_factory=time.time)   # unix seconds
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # How much to capture. Capture-forward: we record AFTER the trigger, because the
    # states worth catching persist. See confusion-detector/README.md for why this
    # removes the continuous-recording battery cost.
    capture_seconds: float = 30.0

    source: str = "unknown"              # e.g. "eeg:ganglion", "imu:phone"
    detail: dict = field(default_factory=dict)   # detector-specific, never required

    def to_json(self) -> str:
        d = asdict(self)
        d["kind"] = self.kind.value
        return json.dumps(d)

    @staticmethod
    def from_json(s: str) -> "SpikeEvent":
        d = json.loads(s)
        d["kind"] = SpikeKind(d["kind"])
        return SpikeEvent(**d)

    def valid(self) -> tuple[bool, str]:
        if not 0.0 <= self.confidence <= 1.0:
            return False, f"confidence {self.confidence} outside 0..1"
        if not 0 < self.capture_seconds <= 300:
            return False, f"capture_seconds {self.capture_seconds} outside (0, 300]"
        age = time.time() - self.detected_at
        if age > 60:
            return False, f"event is {age:.0f}s old; refusing to capture stale context"
        return True, ""


@dataclass
class CaptureResult:
    """What the glasses side reports back after acting on a SpikeEvent."""
    event_id: str
    ok: bool
    media_paths: list = field(default_factory=list)
    started_at: float = 0.0
    duration_s: float = 0.0
    device: str = "unknown"
    error: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self))
