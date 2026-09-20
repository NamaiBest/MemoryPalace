# Handoff — operational state and hard-won detail

Written for whoever picks this up next, human or agent. The project overview is in
[README.md](README.md); this file is operational detail: how to run it, what broke, and
why. Most entries here cost hours to find and minutes to fix once known.

> **Maintain this file.** Anyone working on this repo — including agents — updates it in
> the same change that alters behaviour. Add new failures to *Errors hit* with the symptom
> **and** the root cause, move items between *Working* and *Open issues* as they change,
> and date anything time-sensitive. A stale handoff is worse than none, because it is
> trusted. Commit it alongside the code it describes, never separately.

The active capture app is now `hardware-demo/phone-android/` and uses the phone camera
directly. `hardware-demo/meta-android/` is retained only as the previous Meta glasses
experiment; its generated `vendor/` tree is not needed for the current demo.

---

## Current state (2026-09-19)

| Piece | State |
|---|---|
| Detector | **Working.** Calibrates, fires at z ≈ +13 against a +0.6 baseline after 4 consecutive windows. |
| Backend ↔ phone | **Working.** Commands round-trip; the phone acknowledges. |
| EEG → stop → upload → carousel | **Working end to end.** Four clips captured this way. |
| Audio in clips | **Verified on the S23.** The uploaded 10.02s MP4 reports H.264 video plus MPEG-4 AAC audio (128 kbps). |
| Standalone phone-camera app | **Working on a physical Samsung S23.** Pair, camera-off idle, open/record, close, and upload were observed end to end. |
| Web app | **Working**, but only as a production build. See *next dev does not hydrate*. |
| Capture from the browser | `/live` has Demo surprise / Demo neural spike with 10s or 30s capture. The server-owned timer and 10s physical-phone path are verified. |
| Calibration learning curve | **Measured.** 108 subjects, Crown's exact electrodes. |
| Real Crown EEG | **Never connected.** All EEG so far is synthetic. |
| Meta glasses | **Removed from the active path.** Old client retained for reference only. |
| Meta Muse / MongoDB | **Planned, not implemented.** See the sponsor table in the root README. |

### On-demand capture update (2026-09-19)

- Pairing starts only backend polling; Android opens its camera on a recording command
  and releases it after finalization. Verified over wireless ADB on an SM-S911W / S23.
- 23 backend tests pass, including timed captures without EEG, start-ack timing,
  duplicate acknowledgements and stale timers. Frontend lint and production build pass.
- An isolated HTTP smoke test recorded an actual FFmpeg test-pattern MP4, issued stop
  after 10.11 seconds and uploaded it into the moment library with a matching recording
  ID. This tested the timer/upload plumbing, not the physical phone camera.
- A subsequent physical-phone run paired with the camera off, connected Camera2 only for
  a 10-second surprise moment, disconnected it on stop, and uploaded a 10.02-second,
  7.5 MB H.264/AAC MP4 with the matching recording ID.
- Live-page rendering and the 10s/30s selector were checked in Safari. The home hero and
  carousel were inspected with temporary test moments, separate from the real gallery.

---

## Running the whole thing

Four processes. The web app and the EEG stream are the two most often forgotten.

```bash
# 1. Backend (token must match the APK's)
export DEMO_TOKEN="<token>"
confusion-detector/.venv/bin/python hardware-demo/run.py serve \
  --source synthetic --recorder phone --host 0.0.0.0 --port 8771

# 2. Optional EEG stream for the legacy EEG-stop experiment.
#    The website's timed demo captures work without it.
confusion-detector/.venv/bin/python hardware-demo/feed_synthetic.py stream

# 3. Web app — BUILD, do not use next dev
cd app && npm run build
BACKEND_URL=http://127.0.0.1:8771 DEMO_TOKEN="<token>" npx next start -H 0.0.0.0

# 4. Optional: serve the APK for sideloading
cd <apk dir> && python3 -m http.server 8000 --bind 0.0.0.0
```

Then open **MemoryPalace Camera** and tap **Pair Meta glasses**. The short pairing sequence
is deliberately simulated; it connects to the backend while leaving the camera off.
Grant Camera and Microphone when Android asks and wait for
`Session connected · camera off · ready for a moment`.

On `/live`, choose **10s** or **30s**, then **Demo surprise** or **Demo neural spike**.
`POST /recording/capture` accepts `seconds` and `demo_event` (`surprise` or `load`) and
does not require EEG calibration. Its timer begins after the phone's start acknowledgement
and stops the clip even if the browser closes. The phone releases its camera on stop.
The UI reports success only when the uploaded moment's `recordingId` matches the capture.

The older `feed_synthetic.py trigger` path still uses calibrated EEG to stop an open clip.

The paired Android screen also has **Simulate neural spike**, a manual presentation
trigger for the same 10-second backend-owned capture. The label records presenter intent;
it is not emotion recognition. The APK records at 720p/3 Mbps plus AAC so a typical
10-second clip stays small enough for Meta's full video-and-embedded-audio analysis.

### Driving a capture from the terminal

```bash
feed_synthetic.py calibrate   # backend only, never touches the phone
# confirm the phone app says Ready
feed_synthetic.py trigger     # start, raise theta/alpha, stop, verify
```

---

## Building the phone-camera APK

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export DEMO_BACKEND_URL="http://<LAPTOP_LAN_IP>:8771"
export DEMO_TOKEN="<same token the backend uses>"
cd hardware-demo/phone-android
./gradlew assembleDebug --no-daemon
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n org.hackmit.memorypalace.phone/.MainActivity
```

**`DEMO_BACKEND_URL` and `DEMO_TOKEN` are compiled in.** Changing network or token means
rebuilding *and reinstalling*. This is the most likely cause of a future "it just stopped
working". Verify what landed:

```bash
grep -E "DEMO_BACKEND_URL|DEMO_TOKEN" \
  app/build/generated/source/buildConfig/debug/org/hackmit/memorypalace/phone/BuildConfig.java
```

Environment that had to be installed (none of it existed):

| Need | Installed as | Note |
|---|---|---|
| JDK 17+ | `brew install openjdk@17` | Machine had Java 11. Keg-only, so set `JAVA_HOME`; `/usr/libexec/java_home` still reports only 11 and that is fine. |
| Android SDK | `brew install --cask android-commandlinetools` | Then `sdkmanager --install "platform-tools" "platforms;android-36" "build-tools;36.0.0"`. |
| pyriemann | `eeg-neural-signal-processing/.venv/bin/python -m pip install pyriemann` | For the learning curve. Note that venv's `pip` shim has a stale shebang — use `python -m pip`. |

---

## Controlling the phone over adb

This replaced hours of guessing with direct observation. Worth setting up first, not last.

```bash
export PATH=/opt/homebrew/share/android-commandlinetools/platform-tools:$PATH
adb pair <phone-ip>:<pairing-port>     # code from the pairing dialog, which must stay open
adb connect <phone-ip>:<connect-port>  # different port, on the main wireless-debugging screen

adb -s <device> install -r app-debug.apk
adb -s <device> exec-out screencap -p > screen.png   # read the screen directly
adb -s <device> shell pm grant org.hackmit.memorypalace.phone android.permission.CAMERA
adb -s <device> shell pm grant org.hackmit.memorypalace.phone android.permission.RECORD_AUDIO
adb -s <device> shell am start -n org.hackmit.memorypalace.phone/.MainActivity
adb -s <device> logcat -s MemoryPalacePhone
```

**Android assigns a new connect port every time wireless debugging is toggled**, so a
previously working port will be refused after a restart. Re-pairing is usually unnecessary;
just read the new port off the main screen.

Wireless debugging needs the phone **joined to** a Wi-Fi network. It is unavailable while
the phone is itself the hotspot.

---

## First end-to-end run (2026-09-18)

```
t=124s  z=+0.59  run=0  recording     <- baseline
t=128s  z=+1.65  run=0  recording     <- scripted load begins
t=132s  z=+12.76 run=1  recording
t=136s  z=+12.17 run=2  recording
t=140s  z=+13.19 run=3  recording
t=144s  z=+13.52 run=4  stopping      <- k_consecutive=4 reached
PASS: content://…/recordings/temp_recording_318951721.mp4
```

Latency 16 s from load onset — exactly four 4 s windows, which is what `k_consecutive = 4`
predicts. The large separation is a property of the **synthetic fixture**, not evidence
about human EEG.

## Calibration learning curve (2026-09-19)

`src/crown_learning_curve.py`, 108 subjects, EEGMMIDB restricted to the Crown's exact 8
electrodes with no substitution. Within-subject AUC against training-set size:

| Trials | CSP + LDA | Tangent space + logreg |
|---|---|---|
| 8 | 0.585 | 0.580 |
| 16 | 0.614 | 0.616 |
| 28 | 0.636 | **0.644** |

Three conclusions. The curve **rises monotonically**, which is the evidence behind the
per-user adaptation claim. Tangent space overtakes CSP+LDA from 12 trials and leads by
0.008 at 28 — real, consistent, but well inside the per-subject spread (sd ≈ 0.13). And it
**has not plateaued**: the ceiling is EEGMMIDB's ~45 trials per subject, not the model's,
so budget *more* calibration trials than feels necessary.

This is motor imagery, not confusion. **No public dataset pairs Crown hardware with a
labelled cognitive task** — confirmed from the Crown repo's README, its source, and a
fresh literature search across OpenAlex, Semantic Scholar, arXiv and Zenodo. Do not
re-search this; it does not exist.

---

## Errors hit, and what they actually were

### 1. `next dev` serves pages that never hydrate

**The single most expensive bug of the project.** Next's HMR WebSocket fails its
handshake:

```
ws://…/_next/hmr failed: Error during WebSocket handshake: net::ERR_INVALID_HTTP_RESPONSE
```

React begins loading, the socket retries forever, hydration never completes. Every page
**looks correct** because it is server-rendered, while nothing is interactive: capture
polling never runs so clips never appear, and buttons do nothing. It presents as "the app
is broken", not as an error.

**Use `next build` + `next start`.** No HMR socket, so it cannot occur. Remember the app is
then a static build — **code changes need a rebuild to appear**.

How it was finally caught, because the technique generalises: a probe page reporting
whether it had hydrated (it printed `NOT_HYDRATED`, identical to SSR), then attaching to
Chrome over the DevTools protocol to read the console. Reach for that early.

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --virtual-time-budget=25000 --screenshot=out.png http://127.0.0.1:3000/explore
```

A headless screenshot is a valid oracle — but validate the oracle itself first with a
trivial static page, because `--virtual-time-budget` can snapshot before a heavy React app
finishes hydrating.

### 2. `.gitignore` swallowed the web app's own source

The root `data/` rule, meant for EEG datasets, is unanchored and also matched `app/data/`.
`app/data/moments.ts` and `media.ts` were **never committed** and existed on no machine, so
every route 500'd on a clean checkout. Fixed with `!app/data/`.

### 3. Video would not play, "kept refreshing"

The media proxy answered with chunked `200`, no `Content-Length`, and ignored `Range`. A
`<video>` element cannot determine duration or seek against that, so it stalls and retries.
Now `206 Partial Content` with `Content-Range`, suffix ranges, and `416` out of bounds.

### 4. Captures never appeared, even when the API served them

Two separate causes, found in sequence. Seed moments were anchored to *today at 14:22*, so
a clip recorded at 08:47 sorted below invented data and never reached the hero. Seed data
is now gone entirely — an empty gallery is the honest state. Then the hydration bug above
meant nothing merged at all.

### 5. Phone never reached the backend — the long one

The remainder of this section through error 10 describes the now-archived Meta sample
client. Keep it as historical debugging context, but do not use its UI steps for the
standalone phone-camera app.

Four hypotheses, three wrong, recorded because the wrong ones cost the most:

| Hypothesis | Verdict |
|---|---|
| macOS firewall blocking the venv's python3.14 | **Wrong.** A second port under an allow-listed python was reachable too. |
| Mac's VPN breaking routing | **Wrong.** `route -n get` shows LAN traffic uses `en0` and bypasses `utun5`. |
| Phone's Surfshark VPN capturing LAN traffic | **Partly true** — Android VPNs do capture RFC1918. Bypasser exempted the app. Not the whole story. |
| **App sitting on the Home screen** | **Correct.** |

`CameraAccessScaffold.kt` gates `CameraScreen` on `isRegistered`, and `DemoBackend` polling
starts in `CameraViewModel.init`. On Home, **nothing polls**.

Later the same symptom had a completely different cause: **the app was not installed on
that phone at all.** Three devices were in play and earlier tests had run on a different
one. `adb install` settled in seconds what polling could not.

**The diagnostic that settles network-vs-app in one step** — open both in the phone's
browser: a port served by an allow-listed python, and `<laptop>:8771/commands`. A reply of
`error: invalid bearer token` is a **success**: the backend was reached and answered.

### 6. "Start the camera preview on the phone first"

`isStreaming` is strictly `streamState == STREAMING`, not "a stream exists". Causes, all
producing the identical message:

- No session started (controls are `alpha(0)` — **invisible, not disabled**)
- A paired mock device is **not** a session; *Start session* must still be tapped
- A single cap-touch tap in Mock Device Kit sets `PAUSED`
- CAMERA permission denied, so the mock device has no source

**If the app's own Record button is not tappable, the backend cannot start either** — both
read the same flag.

### 7. My own recovery step destroyed its precondition

When the recorder was in `error`, the driver sent `/recording/stop` to clear it — and the
phone's stop handler calls `stopStreaming()` unconditionally, tearing down the preview the
next start needs. Clear the error **before** starting preview, never after.

### 8. Web capture counted down against a rejected recording

`/recording/start` returns 200 as soon as the command is **queued**; the phone's refusal
arrives later by ack. Treating the 200 as success meant a 10 s countdown against a
recording already rejected, then a stop that could only fail with "Recording ID mismatch".
The hook now polls until the recorder reports `recording`.

### 9. Gradle, artifacts, downloads

JDK 17 required (see above). `maven.pkg.github.com` needs auth for all artifacts, public or
not — verify with a `curl -u "x:$(gh auth token)"` of the `mwdat-core` POM, expecting 200.
Downloads from `github.com` and `dl.google.com` failed intermittently; **an sdkmanager that
looks stalled will not recover — kill and retry.**

### 10. Kotlin declaration order in the injected fragment

`demoBackend` was declared in the fragment, which `prepare.py` injects *below* `init` —
and Kotlin refuses to let `init` assign a property declared later. It is now declared just
before `init`.

---

## Open issues

1. **No real EEG.** Every run used synthetic signal. This is the biggest gap between
   "the plumbing works" and "the system works".
2. **Repeat/open-close soak testing is still outstanding.** One physical S23 capture passed;
   longer runs and repeated 10s/30s cycles still need measurement.
3. **Build config is machine- and network-specific** — the laptop IP is compiled into the
   APK. Any network change invalidates the installed build.
4. **Recordings live in the app's external files directory** until uploaded. There is no
   retention cleanup yet.
5. **Audio remains inside the uploaded MP4.** The active build intentionally has no
   speech-to-text provider. Existing catalog text is preserved, and future visual description
   can enrich moments without changing or deleting the source videos.
6. **Elastic is implemented but not credentialled in the live project yet.** When Elastic is
   absent, moments remain available from `hardware-demo/library/moments.json` and its stable media
   directory. Writes are atomic, the previous catalog generation is retained as `.bak`, and older
   run media is imported idempotently without deleting its source. MongoDB and Muse remain planned.

## Secrets

`DEMO_TOKEN` is generated locally, is **not** in the repo, and is compiled into the debug
APK. That APK is therefore credential-bearing: keep it within the team, and do not serve it
over untrusted Wi-Fi. Release builds disable the backend integration entirely.
