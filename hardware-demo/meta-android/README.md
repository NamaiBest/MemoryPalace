# Prepared Android companion

`prepare.py` fetches Meta's official CameraAccess sample at commit
`81dfb51b9be26de5cd262bb1dcbb4b8d0d6bd2bc` (DAT 0.9.0), retains its license,
and injects our command client and recording methods. The generated project is in
`vendor/CameraAccess/` and is ignored by Git. Run from the repository root:

```bash
python3 hardware-demo/meta-android/prepare.py
```

Already prepared on this machine. Re-running intentionally preserves an existing
`vendor/`; move it aside to regenerate after changing the integration files.

What the integration does:

- Polls `/commands` every 250 ms, with one command executing at a time.
- Starts the sample's video-only recorder after you have manually opened preview.
- Waits for the recorder to actually receive video before acknowledging start.
- On stop, finalizes the MP4, closes the camera stream, then acknowledges completion.
- Returns the phone's `content://` URI; the media remains on the phone and can be
  shared using the sample UI. The backend does not copy that video to the laptop.
- Caches completed commands to avoid executing them again when an acknowledgement
  response is lost. The cache lives for the app process; do not restart the app in
  the middle of a demo recording. Backend command IDs are scoped to each clip.

## Build prerequisites

- Android Studio with JDK 17+ (the machine currently defaults to Java 11).
- Android SDK platform 36 and an Android 12+ phone (upstream minimum SDK 31).
- A GitHub token with `read:packages` for Meta's Maven artifacts, configured as
  `GITHUB_TOKEN` or `github_token` in the generated project's `local.properties`.
- Meta AI companion app, compatible glasses/firmware, and Developer Mode enabled
  for local development. The debug build uses Meta application/client IDs of `0`.

Before building, set `DEMO_BACKEND_URL` to the laptop's IP and port, and `DEMO_TOKEN`
to the backend's temporary token. These are embedded in the **debug APK**, so keep
that APK within your demo team. Use a generated hex token; avoid quotes/newlines in
these build variables. For an emulator, the laptop is `http://10.0.2.2:8771`.

```bash
export DEMO_BACKEND_URL=http://YOUR_LAPTOP_IP:8771
# Export the same DEMO_TOKEN used by the backend; do not commit it.
cd hardware-demo/meta-android/vendor/CameraAccess
./gradlew assembleDebug
./gradlew test lint
./gradlew installDebug
```

Choose a JDK 17+ Gradle runtime in Android Studio or set `JAVA_HOME` appropriately.
If building from Android Studio, configure the variables in the environment used
to launch Studio, or use the terminal commands above. Local HTTP is enabled only
for debug builds; release builds disable this backend integration.

## On the phone

Register/connect using the sample UI, allow camera access, open preview, and keep
the app in the foreground. Complete Crown calibration, then run backend `start`.
Use the backend's `stop` command for a dry run before trying EEG-triggered stops.
After a stop, reopen preview before starting another recording.

This controls **our app's stream and MP4**, not recordings started by the glasses'
hardware button or voice assistant. Avoid touching the sample's own record button
during a backend-controlled clip. If a device disconnects or the sample stops a
recording independently, backend state can remain `recording` until its next stop
command; check the phone UI as well as backend status.

Meta's sample includes Mock Device Kit controls and instrumentation tests. Use
those after a successful Android build, before testing physical glasses.

## Verification status

The pinned sample was downloaded and the integration applied successfully. The
Android build was attempted, but stopped at the Android Gradle plugin because this
machine's active JDK is Java 11. No APK or Mock Device Kit test result is claimed.
An Android SDK installation and package access must also be configured. Python's
simulated phone tests the HTTP protocol and MP4 stop, not Android SDK compatibility.

Upstream: [sample source and setup](https://github.com/facebook/meta-wearables-dat-android/tree/81dfb51b9be26de5cd262bb1dcbb4b8d0d6bd2bc/samples/CameraAccess).
