"""Adapter for real Meta Ray-Ban glasses via the Wearables Device Access Toolkit.

READ THIS BEFORE TRYING TO USE IT. See CAPTURE_MODULE.md for the real API, verified
against Meta's own CameraAccess sample (facebook/meta-wearables-dat-android) - this
docstring is the short version.

The Meta toolkit is a NATIVE MOBILE SDK (Kotlin for Android, Swift for iOS). There is
no Python binding. Your Python ML process cannot talk to the glasses directly - the
only path is:

    your app  ->  Meta AI companion app  ->  Bluetooth  ->  glasses

Real shape of the SDK (Session/Camera/Stream, not a single "record" call):

    session = Wearables.createSession(AutoDeviceSelector())
    session.start()                                    # cheap, keep this open
    camera = session.addCamera(StreamConfiguration(...))
    camera.stream.start()                               # THIS is the expensive part
    # wait for StreamState.STREAMING, then either:
    camera.stream.capturePhoto()                         # <- recommended: photo burst
    # or feed camera.stream.videoStream into an HEVC muxer for real video
    camera.stop()

CAPTURE_MODULE.md's recommendation: capturePhoto() in a loop (~every 2.5s), not full
video. One call per still versus muxer/audio-sync complexity for marginal benefit -
this is also what SenseCam did, the actual dementia-care research behind this feature.

Production architecture (see CAPTURE_MODULE.md §5): this is NOT a separate phone app
reached over HTTP. Crown's SDK is JavaScript-only (React Native), Meta's DAT SDK is
native-only, and neither has a binding into the other's language on Android today - so
the real app is React Native (Crown ingest + detector, all JS) with ONE small native
Kotlin module that does exactly the lifecycle above and nothing else. This Python class
still stands in for that native module during development, so the ML side can be
built and tested before the React Native app exists.

Testing without hardware: Meta ships a Mock Device Kit that simulates the whole SDK
stack (connection, permissions, camera) so the native module can be built and tested
with no glasses present. It does NOT yet cover the Display model or Neural Band
gestures.
"""
import json
import urllib.request
from ..contract import SpikeEvent, CaptureResult
from .base import GlassesDevice


class MetaDATGlasses(GlassesDevice):
    """Talks to a companion phone app that owns the actual DAT SDK calls."""

    name = "meta-dat"

    def __init__(self, phone_url="http://192.168.1.50:8080", timeout=45.0):
        self.phone_url = phone_url.rstrip("/")
        self.timeout = timeout
        self._connected = False

    def connect(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.phone_url}/health")
            with urllib.request.urlopen(req, timeout=5) as r:
                self._connected = r.status == 200
        except Exception:
            self._connected = False
        return self._connected

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def capture(self, event: SpikeEvent) -> CaptureResult:
        ok, why = event.valid()
        if not ok:
            return CaptureResult(event.event_id, False, error=why, device=self.name)
        try:
            req = urllib.request.Request(
                f"{self.phone_url}/spike",
                data=event.to_json().encode(),
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                d = json.loads(r.read().decode())
            return CaptureResult(**d)
        except Exception as e:
            return CaptureResult(event.event_id, False, device=self.name,
                                 error=f"phone app unreachable at {self.phone_url}: {e}")
