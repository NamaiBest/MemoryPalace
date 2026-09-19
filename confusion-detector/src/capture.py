"""Camera capture, on trigger only.

This is the part that answers the battery objection. A retrospective "dash cam" design
has to hold a rolling video buffer, which means the camera runs continuously - roughly
30-45 minutes of battery on Ray-Ban-class hardware. Unusable.

Because we target a SUSTAINED state, we do not need the past: whatever confused you is
still in front of you a second later. So the camera stays off and we open it on trigger.

Worth knowing: SenseCam, the wearable-camera research that actually produced measurable
memory benefits in dementia patients, never recorded video either. It took a still every
~30 seconds. The evidence base was never doing the power-infeasible thing.

On real glasses this class is the seam: swap OpenCV for the Meta Wearables Device Access
Toolkit photo call and nothing else in the system changes.
"""
import os
import time
import cv2


class Camera:
    def __init__(self, cfg):
        self.cfg = cfg
        self.cap = None

    def _open(self):
        cap = cv2.VideoCapture(self.cfg.capture.camera_index)
        if not cap.isOpened():
            raise RuntimeError(
                f"could not open camera {self.cfg.capture.camera_index}. On macOS the "
                f"terminal needs Camera permission: System Settings > Privacy & "
                f"Security > Camera."
            )
        return cap

    def grab(self, path):
        """Open, capture one frame, close. Returns the path or None on failure."""
        cap = None
        try:
            cap = self._open()
            frame = None
            # Webcams return dark/garbage frames until auto-exposure settles.
            for _ in range(max(1, self.cfg.capture.warmup_frames)):
                ok, f = cap.read()
                if ok:
                    frame = f
            if frame is None:
                return None
            h, w = frame.shape[:2]
            target = self.cfg.capture.image_width
            if w > target:
                frame = cv2.resize(frame, (target, int(h * target / w)))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            cv2.imwrite(path, frame)
            return path
        except Exception as e:
            print(f"  [camera] capture failed: {e}")
            return None
        finally:
            if cap is not None:
                cap.release()


class NullCamera:
    """For headless testing, or rehearsing the pipeline with no camera attached."""

    def __init__(self, cfg=None):
        pass

    def grab(self, path):
        return None
