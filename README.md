# MemoryPalace — EEG-triggered capture and retrieval

Detect moments of confusion, insight or surprise from EEG while a person works, capture
what they were looking at when it happened, and let them browse those moments later.

Hardware: an **EEG headset**, an **Android phone using its own camera**, and a laptop
running the detector and web experience. Ray-Ban Meta glasses are no longer required for
the working demo.

---

## The core idea: a model that learns from *your* brain, not a frozen one

**EEG is non-stationary. A statically trained model decays.** Signals drift between
sessions and within a single one as electrode impedance, fatigue, hair and headset
placement change. Spatial filters are tied to specific electrode positions, so weights do
not transfer between people or sessions — a model shipped pre-trained on someone else's
data is wrong for you on day one, and more wrong every week after.

**So we treat per-user adaptation as the product, not as a setup step.** The model trains
on your own recordings and keeps improving as you use it. Every moment you review —
confirming one mattered, or dismissing it — is a label, so ordinary use produces the
training signal. The system gets better the more you wear it.

This is a necessity before it is a pitch: the retraining is mandatory, so building around
it is the honest architecture rather than a feature bolted on. **The claim is evidenced by
a learning curve — detection quality against training-set size — not by assertion.** If
the curve is flat, we say so.

Adaptive BCI is an established research area; the novelty claimed here is *productising*
per-user adaptation, not inventing it.

---

## Sponsor integrations — part of the product, not a closing-slide add-on

Implementation evidence for every sponsor lives in
[`FULFILLMENT_SPONSORS.md`](FULFILLMENT_SPONSORS.md). Elastic is the first completed code
path; later sponsor sections will be added to that common record without replacing it.

| Sponsor / track | Role in MemoryPalace | Current state |
|---|---|---|
| **Meta — Bringing People Closer Together with AI** | Use **Muse Spark** as Memory Guard's reasoning provider to turn retrieved moments into concise, shareable recollections and future opted-in shared stories. This is the human-connection layer—not a dependency on Meta glasses. | Responses API adapter implemented; live use requires an eligible Model API account and `MODEL_API_KEY`. See [`DOCS_sponsor/meta`](DOCS_sponsor/meta). |
| **MongoDB** | Store the public-dataset catalog/manifests, derived feature and prediction records, moment metadata, consent/share relationships, annotations, and semantic-match outputs. Large raw EEG files and video should remain in file/object storage; MongoDB stores their URIs and queryable results rather than oversized blobs. | Planned cloud metadata layer; the backend now has a durable, atomic local catalog rather than an in-memory-only list. |
| **Elastic Vector Database** | Embed each short video directly with Jina v5 Omni, then fuse text-to-video dense kNN rank with BM25 using reciprocal rank fusion. Natural recall keeps date, session, and EEG-intensity filters. | Implemented behind `ELASTICSEARCH_URL` + `ELASTIC_API_KEY`; account credential still needs to be supplied. See [`DOCS_sponsor/elastic`](DOCS_sponsor/elastic). |
| **Meta Muse Spark / Grok** | Power **Memory Guard**, the homepage agent that explains and revisits retrieved moments. The provider is selected truthfully at launch; it is never silently swapped during a pitch. | Both Responses API adapters are implemented. A live provider requires its matching key. |
| **VoloRidge public-data challenge** | The detector work already uses public EEG datasets and reports reproducible predictions, controls, and electrode-ablation results. | Evidence exists in `eeg-neural-signal-processing/` and `xueqi-validation/`; sponsor-specific submission framing remains. See [`DOCS_sponsor/VoloRidge`](DOCS_sponsor/VoloRidge). |

The shared flow is **capture → durable moment → Elastic retrieval → Memory Guard answer**.
Only Memory Guard's reasoning provider changes between Meta and Grok
launches. Brain-signature matching remains an opt-in exploration, not an identity claim or an
automatic disclosure mechanism.

Launch the complete stack with one explicit provider choice:

```bash
# Meta pitch
MODEL_API_KEY=... ELASTIC_API_KEY=... \
  ./scripts/start-memorypalace.sh meta

# Grok pitch
XAI_API_KEY=... ELASTIC_API_KEY=... \
  ./scripts/start-memorypalace.sh grok
```

The script refuses to start if the selected agent key is missing.

---

## Architecture

The Android app owns the phone camera and polls the laptop backend. Everything else stays
web and Python:

```
┌─────────────────┐   HTTP    ┌──────────────────┐   polls 250ms   ┌──────────────────┐
│  app/           │ ────────► │  hardware-demo/  │ ◄────────────── │ phone-android/   │
│  MemoryPalace   │           │  Python backend  │                 │ rear camera +    │
│  (Next.js web)  │           │  (laptop, LAN)   │ ──────────────► │ microphone       │
└─────────────────┘           └────────┬─────────┘   start/stop    └──────────────────┘
                                      ▲
                                      │ EEG stream
                               ┌──────┴────────┐
                               │ EEG headset  │
                               │ or replay    │
                               └───────────────┘
```

The phone never talks to the web app directly. Both are clients of the same backend, which
is what lets the UI stay a plain web app.

For the presentation, the Android app opens with **Pair Meta glasses**. That button runs a
clearly labelled demo pairing sequence, then connects to the backend with the camera off.
This preserves the intended
wearable story without claiming that physical glasses were available or tested.

**Current demo: pair → camera off → simulate a neural spike → capture → camera off → moment.**
On `/live`, click **Simulate Neural Spike**, with 10 seconds (default)
or 30 seconds. The camera opens only when the capture command arrives, closes after saving,
and uploads the clip into the collection. No EEG calibration is needed for these explicitly
simulated triggers. The backend starts the stop timer only after the phone confirms
recording, so leaving the web page does not leave the camera running. This captures the
next interval; there is no footage from before the click.

The older continuous-recording / EEG-stop experiment remains available through the CLI.
It requires a calibrated EEG stream and is separate from the current on-demand demo.

---

## Progress

| Stage | State |
|---|---|
| Detector on public + personal data | Validated — see `confusion-detector/`, `xueqi-validation/`, `my-dataset/` |
| MemoryPalace web UI | Runs with moments uploaded by the phone/backend |
| Global Memory Guard + date navigation | **Working** — the assistant follows every page, answers from the local catalog when cloud models are unavailable, and shares the top-right Boston-date scope with the gallery |
| Standalone phone-camera Android app | **Verified on a physical Samsung S23 (2026-09-19).** Polished pairing UI, camera-off idle state, H.264/AAC capture, release, and upload all passed. |
| Phone ↔ backend commands | Working over LAN |
| **EEG → detector → phone stops and saves a recording** | **Working end to end, 2026-09-18** |
| Captured media reaching the carousel | **Working** — upload, poster extraction and polling are implemented |
| Real Crown EEG | Not connected |
| Meta glasses | Removed from the active path; retained as an optional future/presentation path |
| Muse Spark Memory Guard adapter | **Implemented**; live calls remain gated by Model API account availability |
| Memory Guard provider switch | **Implemented** — `meta` uses Muse Spark 1.3; `grok` uses Grok 4.6 |
| Elastic Jina v5 Omni text-to-video + hybrid RRF search | Implemented; awaiting a valid project API key for the live Cloud connection |
| Durable local persistence | **Working** — atomic catalog + backup, stable media library, and idempotent migration of earlier run media |
| MongoDB cloud persistence | Planned; it can extend the durable local source of truth without making capture depend on the network |

The end-to-end run used synthetic EEG and a simulated device: baseline z ≈ +0.6 rising to
z ≈ +13 under scripted load, the stop firing after four consecutive elevated windows, and
the phone finalising an MP4. That validates the *machinery* end to end. It says nothing
about detecting confusion in a real person — the separation is a property of the fixture.
Operational detail and the full trace are in [HANDOFF.md](HANDOFF.md).

---

## Repository map

### Active — the build

| Folder | What it is | Runs today? |
|---|---|---|
| [hardware-demo/](hardware-demo/) | **Current build path.** EEG ingest, calibration, the EEG-triggered recording stop, the LAN backend, and the standalone phone-camera Android client. `feed_synthetic.py` drives a live backend for real-phone testing. | Phone camera path verified physically; Crown EEG remains unconnected |
| [app/](app/) | MemoryPalace frontend: the moment carousel, detail views, live monitor. Next.js 16 + React 19. | Yes — use `npm run build` then `npm start`; development mode currently has a hydration issue |
| [confusion-detector/](confusion-detector/) | The detector itself: feature extraction and the persistence filter that `hardware-demo/` imports. Also the measured answer to "how many electrodes and where" ([CHANNELS.md](confusion-detector/CHANNELS.md)). | Yes — no hardware needed |
| [eeg-neural-signal-processing/](eeg-neural-signal-processing/) | Signal-processing research and the hardware reality check that settled which headset to buy. Owns the shared `features.py` and venv. | Yes — on downloaded public data |
| [xueqi-validation/](xueqi-validation/) | Independent validation: can surprise/transition signals be detected, and with how few channels. | Yes — results in [RESULTS.md](xueqi-validation/RESULTS.md) |
| [my-dataset/](my-dataset/) | Analysis of the team's own EPOC X recordings. 65.79% on a 3-class task against 33.3% chance, with a shuffled-label control. | Yes |

### [dataset/](dataset/) — all data

Every dataset, committed and local-only, indexed in [dataset/README.md](dataset/README.md).
The team's own recordings are committed at `dataset/epocx-imagery/`; large public datasets
are downloaded per-folder and gitignored.

### [other/](other/) — not in the current build

Superseded or exploratory work, kept for reference. Nothing here is on the critical path.

| Folder | Why it is here |
|---|---|
| [other/glasses-software/](other/glasses-software/) | Earlier glasses design. Its `CAPTURE_MODULE.md` argues for React Native and photo bursts; `hardware-demo/` shipped an HTTP bridge with video instead. **Superseded — prefer `hardware-demo/`.** |
| [other/meta-glasses-vision/](other/meta-glasses-vision/) | Feasibility research: can a glasses app be built without the hardware. Answered yes, via Meta's Mock Device Kit. Research only. |
| [other/reserach/](other/reserach/) | A paper framing of the detection problem (IEEE Technical Correspondence). Not the hackathon build. |
| [other/output/](other/output/) | A rendered PDF. |

The previous Meta glasses Android client remains in
[`hardware-demo/meta-android/`](hardware-demo/meta-android/) as reference. It is not part
of the active demo and can be discussed later in the presentation as a future wearable
capture option.

---

## Start here

Reading cold, in this order:

1. This file — the architecture and the trigger direction.
2. [HANDOFF.md](HANDOFF.md) — current operational state, every error hit during Android
   bring-up and how it was resolved, and the open issues blocking an end-to-end test.
   **Read this before trying to run anything.**
3. [hardware-demo/README.md](hardware-demo/README.md) — what actually runs, and the
   hardware-day sequence.
4. [eeg-neural-signal-processing/HACKMIT-HARDWARE-REALITY-CHECK.md](eeg-neural-signal-processing/HACKMIT-HARDWARE-REALITY-CHECK.md)
   — why this hardware and not other hardware.
5. [confusion-detector/CHANNELS.md](confusion-detector/CHANNELS.md) — the measured
   electrode answer.
6. [dataset/README.md](dataset/README.md) — where the data is.

Run the demo with no hardware at all:

```bash
confusion-detector/.venv/bin/python hardware-demo/run.py demo --recorder phone
```

Run the frontend (production mode is required; see `HANDOFF.md`):

```bash
cd app && npm install && npm run build
BACKEND_URL=http://127.0.0.1:8771 DEMO_TOKEN="<token>" npm start
```

---

## Honest status

Things this repo does **not** claim:

- **No validated human detection.** Every end-to-end run so far used synthetic EEG. No
  Crown connection and no human signal has been exercised. The
  end-to-end pass proves the plumbing, not the neuroscience.
- **The trigger is a workload proxy**, not a calibrated probability of confusion.
- **Output is "moments worth reviewing," never "moments we detected."** Expect ~300
  candidates in a ten-minute session, almost all of them nothing. Ranking, not
  thresholding.
- **Elastic is the first implemented sponsor service**, but it is optional until project
  credentials are supplied. Muse and MongoDB remain planned; local capture first commits each
  moment to an atomic catalog and stable media library, so a sponsor-service outage cannot lose it.
- **Facial EMG is excluded from the claim**, but AF-site electrodes record ocular activity
  regardless, so suppression has to be verified rather than assumed.
