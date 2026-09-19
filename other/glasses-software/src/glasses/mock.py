"""Mock glasses. Runs today, no hardware, no Meta account, no phone.

Uses the laptop webcam if OpenCV is available so the demo produces real media;
falls back to writing placeholder files so it still works headless (e.g. over SSH,
or on a machine with no camera permission).

The point is that every line of code outside this file behaves identically whether
you are running the mock or the real glasses.
"""
import os
import time
import json
from ..contract import SpikeEvent, CaptureResult
from .base import GlassesDevice


class MockGlasses(GlassesDevice):
    name = "mock"

    def __init__(self, out_dir="captures", use_webcam=True, fps=1.0):
        self.out_dir = out_dir
        self.use_webcam = use_webcam
        self.fps = fps            # stills per second, matching a SenseCam-style capture
        self._connected = False

    def connect(self) -> bool:
        os.makedirs(self.out_dir, exist_ok=True)
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def capture(self, event: SpikeEvent) -> CaptureResult:
        if not self._connected:
            return CaptureResult(event.event_id, False, error="not connected",
                                 device=self.name)
        ok, why = event.valid()
        if not ok:
            return CaptureResult(event.event_id, False, error=why, device=self.name)

        d = os.path.join(self.out_dir, event.event_id)
        os.makedirs(d, exist_ok=True)
        started = time.time()
        paths = []

        cap = None
        if self.use_webcam:
            try:
                import cv2
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    cap = None
            except Exception:
                cap = None

        n = max(1, int(event.capture_seconds * self.fps))
        interval = event.capture_seconds / n
        for i in range(n):
            p = os.path.join(d, f"frame_{i:03d}.jpg")
            wrote = False
            if cap is not None:
                okf, frame = cap.read()
                if okf:
                    try:
                        import cv2
                        cv2.imwrite(p, frame)
                        wrote = True
                    except Exception:
                        pass
            if not wrote:
                p = os.path.join(d, f"frame_{i:03d}.txt")
                with open(p, "w") as f:
                    f.write(f"placeholder frame {i} at {time.time():.3f}\n")
            paths.append(p)
            if i < n - 1:
                time.sleep(min(interval, 1.0))

        if cap is not None:
            cap.release()

        with open(os.path.join(d, "event.json"), "w") as f:
            f.write(event.to_json())

        return CaptureResult(
            event_id=event.event_id, ok=True, media_paths=paths,
            started_at=started, duration_s=time.time() - started, device=self.name)
