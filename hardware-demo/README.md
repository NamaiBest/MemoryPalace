# EEG stops recording: runnable HackMIT demo

This is the current build path: **Crown → laptop Python detector → Android companion
→ stop and save the app's recording**. The detector reuses the existing feature
extractor and persistence filter in `confusion-detector/src/`.

## Run the demo now

From the repository root, using the Python environment already on this machine:

```bash
confusion-detector/.venv/bin/python hardware-demo/run.py demo --recorder phone
```

This starts the backend and a simulated phone, replays 120 seconds of synthetic
baseline EEG, starts an actual FFmpeg test-pattern MP4, and increases theta/alpha.
After four independent elevated windows, the backend sends a stop command. The
simulated phone finalizes the MP4 and acknowledges completion. The command exits
with an error if that complete chain fails.

The calibration is replayed quickly; monitoring defaults to 8× speed. Add `--speed 1`
for real-time monitoring. **The EEG and camera scene are synthetic. No human signal,
Crown connection, or Meta Bluetooth connection is validated by this demo.**

Each run creates `hardware-demo/runs/<timestamp>/` with:

- `demo-result.json`: result, signal-time trigger latency, and hardware-test flags.
- `mock-phone/*.mp4`: playable video that the trigger stopped.
- `events.jsonl`: calibration, every detector window, commands and acknowledgements.
- `eeg.jsonl`: raw input packets with original timestamps, for replay.
- `summary.json`: final backend state.

For a fresh machine, install Python 3.12+, Node 20.6+, and FFmpeg, then:

```bash
python3 -m venv hardware-demo/.venv
hardware-demo/.venv/bin/python -m pip install -r hardware-demo/requirements.txt
hardware-demo/.venv/bin/python hardware-demo/run.py demo --recorder phone
```

Use that interpreter in place of `confusion-detector/.venv/bin/python` below.
No BrainFlow, OpenCV, Meta account, or EEG device is needed for this demo.

## Connect the Crown when you get it

1. Ask the hardware desk how the loaned Crown is claimed/shared with your developer
   account. Obtain legitimate device access; credentials for an unrelated account
   cannot stream a claimed device. Charge it and set up its Wi-Fi in the Neurosity
   app/console. This publisher uses **Wi-Fi via Neurosity's cloud**, so it requires
   internet. It does not implement Node Bluetooth.
2. Fit the Crown while wearing the glasses. Check **F5 and F6 contact quality** in
   the Neurosity console/publisher output. They are the two frontal channels this
   prototype uses; they are not the midline Fz electrode.
3. Start the backend with a test camera first:

```bash
confusion-detector/.venv/bin/python hardware-demo/run.py serve --source crown
```

In another terminal:

```bash
cd hardware-demo/crown
npm ci
cp .env.example .env
# Edit .env locally: device ID, Neurosity email/password, backend URL and token.
npm start
```

The publisher subscribes to `brainwaves("rawUnfiltered")`. The backend applies its
own filters; data is eight channels × samples in microvolts, at 256 Hz. Choose
`serve --notch 50` where appropriate; use 60 at HackMIT.

4. Read easy material for two minutes. Check readiness:

```bash
confusion-detector/.venv/bin/python hardware-demo/run.py status
confusion-detector/.venv/bin/python hardware-demo/run.py start
confusion-detector/.venv/bin/python hardware-demo/run.py mark --label hard_start
```

Try a difficult reading/arithmetic task for 30–60 seconds. Record task markers
before easy and hard blocks. The supported labels are `easy_start`, `hard_start`,
`task_end`, `blink`, `jaw_clench`, and `head_movement`.

```bash
confusion-detector/.venv/bin/python hardware-demo/run.py mark --label task_end
confusion-detector/.venv/bin/python hardware-demo/run.py stop
```

The trigger is a **workload proxy**, not a calibrated probability of confusion.
The threshold may fail to distinguish your actual tasks. Measure this; do not label
an intentional blink or a scripted replay as detected cognitive load.

If calibration fails, adjust contact, stop any recording, and run `reset`.
Restarting the publisher creates a new stream ID and requires `reset` as well.
The standard-deviation floor of 0.1 is a prototype heuristic, not a validated
biological threshold. SDK contact quality is displayed to the operator; automatic
rejection currently checks flatlines, large excursions, and the existing artifact
filter, not the SDK's contact-quality score.

## Connect the Meta glasses

The Android code is prepared against an exact official CameraAccess sample commit;
see [meta-android/README.md](meta-android/README.md). The sample already implements
the SDK, permissions, HEVC video recording, MP4 finalization and preview/share.
Our additions poll this backend and acknowledge actual recording state.

Start the backend on your own hotspot/LAN, using a temporary shared token:

```bash
export DEMO_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
confusion-detector/.venv/bin/python hardware-demo/run.py serve \
  --source crown --recorder phone --host 0.0.0.0
```

Use the same token in the Crown `.env`, phone build, and CLI terminal. Configure the
phone with the laptop's reachable LAN IP. Check `status`: both `signal_connected`
and `phone_connected` should be true. On the phone, register the app, grant camera
access, connect the session and start preview before issuing backend `start`.
Recording is video-only in this integration.

**Stop is confirmed only after the phone saves the recording and stops streaming.**
If the command expires or the phone reports failure, state becomes `error`, not
`stopped`. Check the phone, use `stop` to request recovery, and confirm the outcome
before starting another clip. Losing EEG alone does not stop a recording: it clears
partial evidence and marks the signal disconnected. Stop manually when needed.
Keep the app open for the demo; closing the backend while the phone is recording
requires stopping on the phone. This is a local prototype, not a hosted service.

## Replay a saved session

Use a new backend session and a clearly labelled playback source. In one terminal:

```bash
confusion-detector/.venv/bin/python hardware-demo/run.py serve --source playback
```

In another:

```bash
confusion-detector/.venv/bin/python hardware-demo/run.py replay \
  --file hardware-demo/runs/YOUR_SESSION/eeg.jsonl --speed 1
```

Check `status` and manually `start` after calibration completes. Replay preserves
EEG sample timestamps and gaps for the detector; long gaps are capped at four
seconds of wall-clock waiting. Existing recordings with other channel layouts need
an explicit dataset adapter; do not relabel another headset's channels as Crown.

## Verification

```bash
confusion-detector/.venv/bin/python -m unittest discover -s hardware-demo/tests -v
cd hardware-demo/crown
npm run check
```

Tests cover sample-window equivalence across packet sizes, channel reordering,
duplicate packets, gaps and stale input, artifact/flatline rejection, calibration,
phone acknowledgements, expiry/retries, HTTP authentication and the full detector
to stop-command path. The demo additionally exercises an actual video encoder.

## Hardware-day sequence (24-hour budget)

| Time | Checkpoint |
| --- | --- |
| First 2 hours | Crown access/contact and live EEG; Meta sample pairs, previews, saves a clip |
| Hours 2–5 | Connect both to the backend; manually start/stop and verify saved MP4 |
| Hours 5–10 | Easy/hard trials on the actual wearer; record markers and artifact controls |
| Hours 10–16 | Tune only if supported by those recordings; rehearse on new trials |
| Remaining time | Demo explanation, presentation and clearly labelled replay fallback |

If pairing consumes the first two hours, fall back to Crown plus test camera, or
replay plus glasses, and say exactly which part is simulated. Check feasibility of
wearing both devices together immediately. Do not postpone the Meta permission and
recording check until the final hours.

Sources checked September 10, 2026: [Crown raw EEG](https://docs.neurosity.co/docs/api/brainwaves/),
[authentication](https://docs.neurosity.co/docs/api/authentication/),
[Wi-Fi/Bluetooth](https://docs.neurosity.co/docs/api/streaming/),
[Meta CameraAccess sample](https://github.com/facebook/meta-wearables-dat-android/tree/81dfb51b9be26de5cd262bb1dcbb4b8d0d6bd2bc/samples/CameraAccess).
