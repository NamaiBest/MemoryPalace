# Handoff — operational state and hard-won detail

Written for whoever picks this up next, human or agent. The project overview is in
[README.md](README.md); this file is operational detail: how to run it, what broke, and
why. Most entries here cost hours to find and minutes to fix once known.

> **Maintain this file.** Anyone working on this repo — including agents — updates it in
> the same change that alters behaviour. Add new failures to *Errors hit* with the symptom
> **and** the root cause, move items between *Working* and *Open issues* as they change,
> and date anything time-sensitive. A stale handoff is worse than none, because it is
> trusted. Commit it alongside the code it describes, never separately.

Links into `hardware-demo/meta-android/vendor/CameraAccess/` 404 on a fresh clone: that
tree is generated. Run `python3 hardware-demo/meta-android/prepare.py` first.

---

## Current state (2026-09-19)

| Piece | State |
|---|---|
| Detector | **Working.** Calibrates, fires at z ≈ +13 against a +0.6 baseline after 4 consecutive windows. |
| Backend ↔ phone | **Working.** Commands round-trip; the phone acknowledges. |
| EEG → stop → upload → carousel | **Working end to end.** Four clips captured this way. |
| Audio in clips | **Working** since 2026-09-19. AAC 44.1 kHz mono alongside HEVC video. |
| Web app | **Working**, but only as a production build. See *next dev does not hydrate*. |
| Capture from the browser | **Working.** `/live` records a fixed 10s clip on demand. |
| Calibration learning curve | **Measured.** 108 subjects, Crown's exact electrodes. |
| Real Crown EEG | **Never connected.** All EEG so far is synthetic. |
| Real Ray-Ban Meta glasses | **Never connected.** Mock Device Kit only. |

---

## Running the whole thing

Four processes. The web app and the EEG stream are the two most often forgotten.

```bash
# 1. Backend (token must match the APK's)
export DEMO_TOKEN="<token>"
confusion-detector/.venv/bin/python hardware-demo/run.py serve \
  --source synthetic --recorder phone --host 0.0.0.0 --port 8771

# 2. Continuous EEG. Without this, every capture is refused with
#    "complete calibration with a connected EEG source first".
confusion-detector/.venv/bin/python hardware-demo/feed_synthetic.py stream

# 3. Web app — BUILD, do not use next dev
cd app && npm run build
BACKEND_URL=http://127.0.0.1:8771 DEMO_TOKEN="<token>" npx next start -H 0.0.0.0

# 4. Optional: serve the APK for sideloading
cd <apk dir> && python3 -m http.server 8000 --bind 0.0.0.0
```

Then on the phone, **in this order** — each step gates the next:

1. Open the app. If on Home, tap **Register**. *Nothing polls from the Home screen.*
2. Debug menu → Mock Device Kit → pair → **Power, Donned, Unfolded** all on → camera
   source (grant CAMERA when asked).
3. Close the sheet → **Start session**. Until a session exists the Preview and Record
   controls are **invisible**, not greyed out.
4. **Preview** → wait for live video. Record becomes tappable; that flag is exactly what
   the backend needs.

Then either press **Capture the next 10 seconds** on `/live`, or run
`feed_synthetic.py trigger` for the EEG-triggered path.

### Driving a capture from the terminal

```bash
feed_synthetic.py calibrate   # backend only, never touches the phone
# start Preview on the phone HERE — not before
feed_synthetic.py trigger     # start, raise theta/alpha, stop, verify
```

The order is not arbitrary: the phone's stop handler calls `stopStreaming()`
unconditionally, so **every completed clip kills the preview**. It must be restarted
before each run.

---

## Rebuilding the APK

```bash
cd hardware-demo/meta-android/vendor/CameraAccess
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export GITHUB_TOKEN="$(gh auth token)"
export DEMO_BACKEND_URL="http://<LAPTOP_LAN_IP>:8771"
export DEMO_TOKEN="<same token the backend uses>"
./gradlew assembleDebug --no-daemon      # ~87 MB, ~6 min cold
```

**`DEMO_BACKEND_URL` and `DEMO_TOKEN` are compiled in.** Changing network or token means
rebuilding *and reinstalling*. This is the most likely cause of a future "it just stopped
working". Verify what landed:

```bash
grep -E "DEMO_BACKEND_URL|DEMO_TOKEN" \
  app/build/generated/source/buildConfig/debug/com/meta/wearable/dat/externalsampleapps/cameraaccess/BuildConfig.java
```

Environment that had to be installed (none of it existed):

| Need | Installed as | Note |
|---|---|---|
| JDK 17+ | `brew install openjdk@17` | Machine had Java 11. Keg-only, so set `JAVA_HOME`; `/usr/libexec/java_home` still reports only 11 and that is fine. |
| Android SDK | `brew install --cask android-commandlinetools` | Then `sdkmanager --install "platform-tools" "platforms;android-36" "build-tools;36.0.0"`. |
| `read:packages` | `gh auth refresh -h github.com -s read:packages` | Meta's SDK is on GitHub Packages, which needs auth **even for public artifacts**. |
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
adb -s <device> shell input tap <x> <y>              # Preview sits at ~(215, 1988) on an S23
adb -s <device> shell pm grant <pkg> android.permission.CAMERA
adb -s <device> logcat -s "CameraAccess:CameraViewModel" "HackMIT"
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
2. **No real glasses.** Mock Device Kit only. Bluetooth pairing, real latency and real
   battery behaviour are all unexercised.
3. **Each clip kills the preview**, so it must be restarted between captures. Automating a
   preview restart after stop would make repeated capture hands-free.
4. **Recordings land in `cacheDir`**, which Android may delete under storage pressure.
   Upload-on-stop mitigates this but does not remove it.
5. **Build config is machine- and network-specific** — the laptop IP is compiled into the
   APK. Any network change invalidates the installed build.
6. **Nothing is pushed.** All work is local commits on `main`. A teammate pulling now gets
   a version where the web app does not even start.
7. **Audio is the phone's mic** in mock mode. With real glasses it would be theirs;
   transcription has not been attempted on either.

## Secrets

`DEMO_TOKEN` is generated locally, is **not** in the repo, and is compiled into the debug
APK. That APK is therefore credential-bearing: keep it within the team, and do not serve it
over untrusted Wi-Fi. Release builds disable the backend integration entirely.
