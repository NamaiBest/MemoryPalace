# Verification — September 10, 2026

- Python: **15/15 tests passed**, including HTTP ingestion → calibration → load
  detection → phone stop command → acknowledgement.
- Node: **3/3 publisher tests passed**; syntax checked and pinned Neurosity SDK
  imports/methods verified locally. No Neurosity login was attempted without credentials.
- Full demo: **passed with `demo --recorder phone`**. Synthetic baseline plus a
  scripted high-load episode passed through HTTP to the real feature extractor.
  One trigger fired after **16 seconds of elevated signal**, and the simulated phone
  finalized an MP4 before acknowledging `stopped`.
- Video: decoded the entire resulting MP4 with FFmpeg; exit code 0, no errors.
- Android: official sample downloaded at the pinned commit and integration applied.
  `assembleDebug` was attempted and stopped because the active runtime is Java 11;
  the Android Gradle plugin requires Java 17+. Android SDK setup and Meta package
  credentials are also outstanding. No APK, emulator, or physical-glasses result.
- No Crown or Meta hardware was connected. These results demonstrate software
  integration with synthetic EEG, not cognitive-load accuracy on people.

Successful local evidence:

`runs/20260910-231812-930790/demo-result.json`

`runs/20260910-231812-930790/mock-phone/simulated-camera-f4b793fd.mp4`

The raw EEG, window decisions, commands and acknowledgements are in that same run.
Earlier run directories retain failed attempts for debugging; use the successful
run above or generate a new one using the README command.
