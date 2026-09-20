# Standalone Android phone camera

This is the active capture client for MemoryPalace. It uses the Android phone's rear
camera and microphone directly; it has **no Meta glasses or Meta Wearables SDK
dependency**.

## Presentation flow

The launch screen contains one action: **Pair Meta glasses**. Tapping it shows a short
simulated pairing sequence, then automatically:

1. connects to the real MemoryPalace backend;
2. leaves the camera and microphone off; and
3. displays `Session connected · camera off · ready for a moment`.

Only the pairing is simulated. Camera recording, backend commands, MP4 finalization and
upload use the real phone and backend. The screen explicitly says that the phone camera is
the demo capture source so the presentation does not claim unavailable glasses were
physically tested.

The app polls the Python backend every 250 ms. A backend `start` command opens the rear
camera and begins an H.264/AAC MP4. A `stop` command finalizes the MP4, releases the camera
and microphone, acknowledges completion, and uploads the bytes. Preview is visible only
during capture. This uses Android's [CameraDevice.close()](https://developer.android.com/reference/android/hardware/camera2/CameraDevice#close())
to release the device between moments.

Use **Demo surprise** or **Demo neural spike** in the website's Live tab. The duration
selector offers 10 or 30 seconds; the server times the recording after the phone confirms
start. Demo captures do not require EEG calibration. Keep the phone app in the foreground.

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
