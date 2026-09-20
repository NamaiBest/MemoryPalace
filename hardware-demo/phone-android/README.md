# Standalone Android phone camera

This is the active capture client for MemoryPalace. It uses the Android phone's rear
camera and microphone directly; it has **no Meta glasses or Meta Wearables SDK
dependency**.

## Presentation flow

The launch screen contains one action: **Pair Meta glasses**. Tapping it opens the installed
Meta AI companion app. When the presenter returns to MemoryPalace, a short simulated pairing
sequence automatically:

1. connects to the real MemoryPalace backend;
2. leaves the camera and microphone off; and
3. displays `Session connected · camera off · ready for a moment`.

Only the pairing is simulated. Camera recording, backend commands, MP4 finalization and
upload use the real phone and backend. The screen explicitly says that the phone camera is
the demo capture source so the presentation does not claim unavailable glasses were
physically tested.

If Meta AI is not installed, the action opens its Play Store page. Returning to
MemoryPalace still permits the explicitly labelled phone-camera demo.

The app polls the Python backend every 250 ms. A backend `start` command opens the rear
camera and begins an H.264/AAC MP4. A `stop` command finalizes the MP4, releases the camera
and microphone, acknowledges completion, and uploads the bytes. Preview is visible only
during capture. This uses Android's [CameraDevice.close()](https://developer.android.com/reference/android/hardware/camera2/CameraDevice#close())
to release the device between moments.

Use **Demo surprise** or **Demo neural spike** in the website's Live tab. The duration
selector offers 10 or 30 seconds; the server times the recording after the phone confirms
start. Demo captures do not require EEG calibration. Keep the phone app in the foreground.

After pairing, the phone exposes two explicit paths:

- **Record live moment** records a real 10-second rear-camera clip without claiming that a
  neural event occurred. The saved event is labelled `Live Capture`.
- **Simulate neural spike** records the same real footage but attaches the clearly labelled
  excitement demo trigger. “Excitement” is not inferred from the wearer.

Meta analyzes either resulting MP4's visual frames and embedded audio, and Elastic indexes
the returned semantic metadata and Jina vector.

## Meta recording protocol

The hardware-free demo does **not** claim to command glasses through an invented endpoint.
Its working phone bridge uses authenticated JSON over HTTP:

1. `GET /commands` returns a short-lived `start` or `stop` action with a recording ID.
2. The Android client records only between those commands and calls
   `POST /commands/ack` with the same recording ID.
3. The finalized MP4 is uploaded to `/media`; Meta enrichment and Elastic indexing then run.

With physical glasses, Meta's public Android Device Access Toolkit v0.9 replaces the phone
camera layer. `Wearables.startRegistration(activity)` hands registration to Meta AI, camera
permission is requested through `Wearables.RequestPermissionContract()`,
`Wearables.createSession(AutoDeviceSelector())` starts a device session, and
`session.addCamera(config).stream.start()` provides video frames for the app to encode over
the 10-second moment window. This is a session and camera-stream API, not a generic REST
“record” request to the glasses.

Official references:

- https://wearables.developer.meta.com/docs/develop/dat/build-integration-android/
- https://github.com/facebook/meta-wearables-dat-android

## Build and install

The backend URL and token are compiled into the debug APK. Use the laptop's LAN IP—not
`127.0.0.1`—and the same token used by `run.py serve`.

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export DEMO_BACKEND_URL="http://<LAPTOP_LAN_IP>:8771"
export DEMO_TOKEN="<at-least-16-character-token>"

cd hardware-demo/phone-android
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n org.hackmit.memorypalace.phone/.MainActivity
```

Tap **Pair Meta glasses**, grant Camera and Microphone when Android asks, and keep the app
in the foreground. The banner should settle on
`Session connected · camera off · ready for a moment`.

The package name is `org.hackmit.memorypalace.phone`; useful diagnostics are:

```bash
adb logcat -s MemoryPalacePhone
adb shell pm grant org.hackmit.memorypalace.phone android.permission.CAMERA
adb shell pm grant org.hackmit.memorypalace.phone android.permission.RECORD_AUDIO
```

Wireless debugging assigns a new connection port whenever it is toggled. If `adb
devices` is empty, read the current IP and port from Android's **Wireless debugging**
screen and run `adb connect <phone-ip>:<connect-port>`.

### Physical verification

Verified on a Samsung SM-S911W (S23, Android 16) on 2026-09-19. Pairing left Camera2
closed; a 10-second surprise command opened the rear camera, acknowledged recording,
stopped after the backend timer, released the camera, and uploaded a matching 10.02-second
MP4. macOS metadata identified H.264 video and MPEG-4 AAC audio. This is one successful
cycle, not a soak test.

## Boundaries

- Captures are written into the app's external files directory before upload.
- The app allows cleartext HTTP only because the demo backend is a temporary LAN service
  protected by a shared bearer token. This is not a production security design.
- The old Meta glasses prototype remains under `../meta-android/` for reference and a
  possible presentation slide, but is no longer on the active path.
