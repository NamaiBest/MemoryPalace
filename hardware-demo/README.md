# EEG stops recording: runnable HackMIT demo

This is the current build path: **EEG → laptop Python detector → Android phone camera
→ stop, save and upload the recording**. The detector reuses the existing feature
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
Crown connection, or physical phone camera is validated by this command.**

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
2. Fit the Crown. Check **F5 and F6 contact quality** in
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

## Connect the phone camera

### Durable memories across updates

`serve` uses `hardware-demo/library/` as its stable media and metadata store. Every moment
is appended to an atomically replaced `moments.json` catalog with a one-generation backup;
new backend run folders contain operational evidence only. At startup, older uncatalogued
media under `hardware-demo/runs/` is copied into the durable library idempotently—the
originals are never moved or deleted. Set `MEMORYPALACE_LIBRARY_DIR` or pass `--library`
to put that durable collection elsewhere.

The active Android app is [`phone-android/`](phone-android/). It uses the phone's rear
camera and microphone directly and has no Meta Wearables SDK, account, or glasses
dependency. It polls the same command queue, records H.264/AAC MP4, acknowledges the
actual start/stop state, releases the camera after each clip, and uploads the completed
moment. Pairing never opens the camera.

Start the backend on your own hotspot/LAN, using a temporary shared token:

```bash
export DEMO_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
confusion-detector/.venv/bin/python hardware-demo/run.py serve \
  --source crown --recorder phone --host 0.0.0.0
```

Use the same token in the Crown `.env`, phone build, and CLI terminal. Configure the
phone build with the laptop's reachable LAN IP; see
[`phone-android/README.md`](phone-android/README.md). Open the app and tap **Pair Meta
glasses**. The app simulates pairing, requests permissions and connects to the backend
with its camera off. For the current demo, use **Demo surprise** or **Demo neural spike**
on `/live` and select 10 or 30 seconds. Only `phone_connected` is required for these
timed demo captures. The legacy CLI `start` also requires calibrated EEG.

**Stop is confirmed only after the phone saves the recording and stops streaming.**
If the command expires or the phone reports failure, state becomes `error`, not
`stopped`. Check the phone, use `stop` to request recovery, and confirm the outcome
before starting another clip. Losing EEG alone does not stop a recording: it clears
partial evidence and marks the signal disconnected. Stop manually when needed.
Keep the app in the foreground for the demo; closing the backend while the phone is recording
requires stopping on the phone. This is a local prototype, not a hosted service.

## Connect Elastic Vector Database

The backend can index each completed moment into the sponsor project and expose hybrid
search at `GET /search?q=...`. It uses Elastic's preconfigured Jina v5 Omni endpoint and
provisions the `memorypalace-multimodal-moments` dense-vector index idempotently. Short MP4s
are embedded directly, text queries use the same shared vector space, and Elastic combines
BM25 with kNN using RRF. If media inference is unavailable, indexing falls back to the
moment's text without losing capture. Credentials never enter the browser, Android APK,
source tree, or request URLs.

```bash
export ELASTICSEARCH_URL="https://my-vectordb-project-bece59.es.us-east4.gcp.elastic.cloud"
export ELASTIC_API_KEY="<project API key>"
export DEMO_TOKEN="<the same temporary LAN token used by the phone>"
python3 hardware-demo/run.py serve --source synthetic --recorder phone --host 0.0.0.0
```

Optional overrides are `ELASTIC_INDEX`, `ELASTIC_INFERENCE_ID`, and
`ELASTIC_EMBEDDING_DIMS` (1024 by default for `jina-embeddings-v5-omni-small`). The `/status` response
reports only configuration/readiness/error state—never the API key. Elastic failures are
logged but do not fail local capture or erase the uploaded video.

The prior Meta glasses experiment is retained under [`meta-android/`](meta-android/) for
reference and a possible future/presentation path. It is not required by this build.

## Memory Guard

Every completed MP4 is committed to the durable library first, then indexed into Elastic
asynchronously when Elastic is configured. Historical text metadata is retained, but the
active build has no speech-to-text provider.

Memory Guard is the homepage agent. Its LLM is selected at process launch:

```bash
# Meta Muse Spark 1.3
export MEMORYPALACE_AGENT_PROVIDER=meta
export MODEL_API_KEY="<Meta Model API key>"

# Or Grok 4.6
export MEMORYPALACE_AGENT_PROVIDER=grok
export XAI_API_KEY="<xAI API key>"

```

Both adapters use their providers' Responses API. Memory Guard retrieves relevant moments
through Elastic when configured and falls back transparently to the newest durable local
moments otherwise. `/status` identifies the selected model and Elastic
readiness without returning credentials. For a one-command launch, use
`./scripts/start-memorypalace.sh meta` or `./scripts/start-memorypalace.sh grok` from the repo
root after exporting the matching keys.

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
| First 2 hours | EEG access/contact and live signal; phone app previews, records and uploads a clip |
| Hours 2–5 | Connect both to the backend; manually start/stop and verify saved MP4 |
| Hours 5–10 | Easy/hard trials on the actual wearer; record markers and artifact controls |
| Hours 10–16 | Tune only if supported by those recordings; rehearse on new trials |
| Remaining time | Demo explanation, presentation and clearly labelled replay fallback |

If EEG setup consumes the first two hours, use replay or synthetic EEG with the real
phone camera and say exactly which part is simulated. Do not postpone Android camera,
microphone, LAN, and upload checks until the final hours.

Sources checked September 10, 2026: [Crown raw EEG](https://docs.neurosity.co/docs/api/brainwaves/),
[authentication](https://docs.neurosity.co/docs/api/authentication/),
[Wi-Fi/Bluetooth](https://docs.neurosity.co/docs/api/streaming/).
