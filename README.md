# MemoryPalace — EEG-triggered capture and retrieval

Detect moments of confusion, insight or surprise from EEG while a person works, capture
what they were looking at when it happened, and let them browse those moments later.

Hardware: a **Neurosity Crown** (EEG) worn with **Ray-Ban Meta glasses** (camera), with a
laptop running the detector between them.

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

## Architecture

A browser cannot talk to the glasses. Meta's Device Access Toolkit is native-only (Kotlin
on Android, Swift on iOS) with no JavaScript binding, so the phone is not optional. It is,
however, the only native piece — everything else is web and Python:

```
┌─────────────────┐   HTTP    ┌──────────────────┐   polls 250ms   ┌──────────────────┐
│  app/           │ ────────► │  hardware-demo/  │ ◄────────────── │  Android app     │
│  MemoryPalace   │           │  Python backend  │                 │  (Meta's sample  │
│  (Next.js web)  │           │  (laptop, LAN)   │ ──────────────► │   + our client)  │
└─────────────────┘           └──────────────────┘   start/stop    └────────┬─────────┘
                                       ▲                                    │ DAT SDK
                                       │ EEG stream                         ▼
                                ┌──────┴────────┐                  ┌──────────────────┐
                                │ Neurosity     │                  │ Ray-Ban Meta     │
                                │ Crown         │                  │ glasses          │
                                └───────────────┘                  └──────────────────┘
```

The phone never talks to the web app directly. Both are clients of the same backend, which
is what lets the UI stay a plain web app.

**Trigger direction: the glasses record continuously and EEG *stops and saves* the clip.**
This is deliberate and it is the opposite of an earlier design that started the camera on a
spike. Recording first means a detected moment cannot be missed during camera start-up
latency.

---

## Progress

| Stage | State |
|---|---|
| Detector on public + personal data | Validated — see `confusion-detector/`, `xueqi-validation/`, `my-dataset/` |
| MemoryPalace web UI | Runs, on simulated moments |
| Android app builds and installs | Done 2026-09-18, first ever build |
| Phone ↔ backend commands | Working over LAN |
| **EEG → detector → phone stops and saves a recording** | **Working end to end, 2026-09-18** |
| Captured media reaching the carousel | **Not built** — the largest remaining gap |
| Real Crown EEG | Not connected |
| Real Ray-Ban Meta glasses | Not connected — Mock Device Kit only |

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
| [hardware-demo/](hardware-demo/) | **Current build path.** Crown ingest, calibration, the EEG-triggered recording stop, the LAN backend, and the prepared Meta Android integration. `feed_synthetic.py` drives a live backend for real-phone testing. | Yes — and verified against a real Android phone |
| [app/](app/) | MemoryPalace frontend: the moment carousel, detail views, live monitor. Next.js 16 + React 19. | Yes — `npm run dev`, simulated data |
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

Run the frontend:

```bash
cd app && npm install && npm run dev
```

---

## Honest status

Things this repo does **not** claim:

- **No validated human detection.** Every run so far used synthetic EEG. No Crown
  connection, no Meta Bluetooth link, and no human signal has been exercised. The
  end-to-end pass proves the plumbing, not the neuroscience.
- **The trigger is a workload proxy**, not a calibrated probability of confusion.
- **Output is "moments worth reviewing," never "moments we detected."** Expect ~300
  candidates in a ten-minute session, almost all of them nothing. Ranking, not
  thresholding.
- **Media does not yet reach the UI.** The Android app returns a `content://` URI and the
  media stays on the phone; the backend does not copy it to the laptop. Wiring that to the
  carousel is the largest unbuilt piece.
- **Facial EMG is excluded from the claim**, but AF-site electrodes record ocular activity
  regardless, so suppression has to be verified rather than assumed.
