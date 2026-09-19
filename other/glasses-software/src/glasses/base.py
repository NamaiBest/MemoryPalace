"""Abstract glasses device. Everything the rest of the system is allowed to assume."""
from abc import ABC, abstractmethod
from ..contract import SpikeEvent, CaptureResult


class GlassesDevice(ABC):
    """Minimal surface: connect, capture on demand, disconnect.

    Kept deliberately small because Meta's toolkit exposes very little. Adding methods
    here that the real device cannot honour would make the mock lie, and a lying mock
    is worse than no mock.
    """

    name = "abstract"

    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def capture(self, event: SpikeEvent) -> CaptureResult:
        """Record for event.capture_seconds and return where the media landed."""
        ...

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()
