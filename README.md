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

| Sponsor / track                                           | Role in MemoryPalace                                                                                                                                                                                                                                                                                                        | Current state                                                                                                                                                                        |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Meta — Bringing People Closer Together with AI** | Use**Muse Spark** to understand each captured clip, generate a grounded semantic title/description, and power Memory Guard's answers over retrieved moments. This is the human-connection layer—not a dependency on Meta glasses.                                                                                    | Video/image understanding and Responses API agent adapters are implemented and live behind`MODEL_API_KEY`. See [`DOCS_sponsor/meta`](DOCS_sponsor/meta).                          |
| **MongoDB**                                         | Store the public-dataset catalog/manifests, derived feature and prediction records, moment metadata, consent/share relationships, annotations, and semantic-match outputs. Large raw EEG files and video should remain in file/object storage; MongoDB stores their URIs and queryable results rather than oversized blobs. | Planned cloud metadata layer; the backend now has a durable, atomic local catalog rather than an in-memory-only list.                                                                |
| **Elastic Vector Database**                         | Index Meta-generated scene language and direct Jina v5 Omni video/text embeddings, then fuse dense kNN rank with BM25 using reciprocal rank fusion. Natural recall keeps date, session, and EEG-intensity filters.                                                                                                          | Implemented and verified on Elastic Cloud behind`ELASTICSEARCH_URL` + `ELASTIC_API_KEY`. See [`DOCS_sponsor/elastic`](DOCS_sponsor/elastic).                                    |
| **Meta Muse Spark / Grok**                          | Power**Memory Guard**, the homepage agent that explains and revisits retrieved moments. The provider is selected truthfully at launch; it is never silently swapped during a pitch.                                                                                                                                   | Both Responses API adapters are implemented. A live provider requires its matching key.                                                                                              |
| **VoloRidge public-data challenge**                 | The detector work already uses public EEG datasets and reports reproducible predictions, controls, and electrode-ablation results.                                                                                                                                                                                          | **Written up in [`eeg-state-detection/README.md`](eeg-state-detection/README.md)**, structured around VoloRidge's four stated criteria: data handling, signal extraction, elegance over complexity, and validation. The final model is 84 features and a logistic regression; seven more complex alternatives were tested as paired comparisons and every one lost. 8 of 15 sessions beat a circular time-shift null, and a random-flag null proved a promising brief-event detector was noise. Corroborating evidence in `eeg-neural-signal-processing/` and `xueqi-validation/`. See [`DOCS_sponsor/VoloRidge`](DOCS_sponsor/VoloRidge) and [`FULFILLMENT_SPONSORS.md`](FULFILLMENT_SPONSORS.md#voloridge--public-data-challenge-a-simple-signal-and-the-nulls-that-test-it). |

The shared flow is **capture → durable moment → Meta semantic description → Elastic retrieval → Memory Guard answer**.
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

| Stage                                                          | State                                                                                                                                                                                |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Detector on public + personal data                             | Validated — see`confusion-detector/`, `xueqi-validation/`, `my-dataset/`                                                                                                      |
| MemoryPalace web UI                                            | Runs with moments uploaded by the phone/backend                                                                                                                                      |
| Global Memory Guard + date navigation                          | **Working** — the assistant follows every page, answers from the local catalog when cloud models are unavailable, and shares the top-right Boston-date scope with the gallery |
| Standalone phone-camera Android app                            | **Verified on a physical Samsung S23 (2026-09-19).** Polished pairing UI, camera-off idle state, H.264/AAC capture, release, and upload all passed.                            |
| Phone ↔ backend commands                                      | Working over LAN                                                                                                                                                                     |
| **EEG → detector → phone stops and saves a recording** | **Working end to end, 2026-09-18**                                                                                                                                             |
| Captured media reaching the carousel                           | **Working** — upload, poster extraction and polling are implemented                                                                                                           |
| Real Crown EEG                                                 | Not connected                                                                                                                                                                        |
| Meta glasses                                                   | Removed from the active path; retained as an optional future/presentation path                                                                                                       |
| Muse Spark semantic video understanding + Memory Guard         | **Working live** — clips receive grounded titles/descriptions before Elastic indexing; large clips use their extracted poster frame                                           |
| Memory Guard provider switch                                   | **Implemented** — `meta` uses Muse Spark 1.3; `grok` uses Grok 4.6                                                                                                        |
| Elastic Jina v5 Omni text-to-video + hybrid RRF search         | **Working live** — all 12 preserved moments are indexed in Elastic Cloud                                                                                                      |
| Durable local persistence                                      | **Working** — atomic catalog + backup, stable media library, and idempotent migration of earlier run media                                                                    |
| MongoDB cloud persistence                                      | Planned; it can extend the durable local source of truth without making capture depend on the network                                                                                |

The end-to-end run used synthetic EEG and a simulated device: baseline z ≈ +0.6 rising to
z ≈ +13 under scripted load, the stop firing after four consecutive elevated windows, and
the phone finalising an MP4. That validates the *machinery* end to end. It says nothing
about detecting confusion in a real person — the separation is a property of the fixture.
Operational detail and the full trace are in [HANDOFF.md](HANDOFF.md).

---

## Repository map

### Active — the build

| Folder                                                        | What it is                                                                                                                                                                                                                    | Runs today?                                                                                      |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| [hardware-demo/](hardware-demo/)                               | **Current build path.** EEG ingest, calibration, the EEG-triggered recording stop, the LAN backend, and the standalone phone-camera Android client. `feed_synthetic.py` drives a live backend for real-phone testing. | Phone camera path verified physically; Crown EEG remains unconnected                             |
| [app/](app/)                                                   | MemoryPalace frontend: the moment carousel, detail views, live monitor. Next.js 16 + React 19.                                                                                                                                | Yes — use`npm run build` then `npm start`; development mode currently has a hydration issue |
| [confusion-detector/](confusion-detector/)                     | The detector itself: feature extraction and the persistence filter that`hardware-demo/` imports. Also the measured answer to "how many electrodes and where" ([CHANNELS.md](confusion-detector/CHANNELS.md)).                | Yes — no hardware needed                                                                        |
| [eeg-neural-signal-processing/](eeg-neural-signal-processing/) | Signal-processing research and the hardware reality check that settled which headset to buy. Owns the shared`features.py` and venv.                                                                                         | Yes — on downloaded public data                                                                 |
| [xueqi-validation/](xueqi-validation/)                         | Independent validation: can surprise/transition signals be detected, and with how few channels.                                                                                                                               | Yes — results in[RESULTS.md](xueqi-validation/RESULTS.md)                                        |
| [my-dataset/](my-dataset/)                                     | Analysis of the team's own EPOC X recordings. 65.79% on a 3-class task against 33.3% chance, with a shuffled-label control.                                                                                                   | Yes                                                                                              |
| [eeg-state-detection/](eeg-state-detection/)                   | Session-calibrated task-vs-rest **state detector** on public 28-channel EEG (Shin 2018 n-back), evaluated walk-forward with models frozen before scoring, a circular time-shift null and eye-only controls. The VoloRidge "signal in noise" entry. Also records that brief-burst detection stayed at chance on four participants. | Yes — figures and numbers in [README.md](eeg-state-detection/README.md); `backtest` regenerates them from the saved models |

### [dataset/](dataset/) — all data

Every dataset, committed and local-only, indexed in [dataset/README.md](dataset/README.md).
The team's own recordings are committed at `dataset/epocx-imagery/`; large public datasets
are downloaded per-folder and gitignored.

### [other/](other/) — not in the current build

Superseded or exploratory work, kept for reference. Nothing here is on the critical path.

| Folder                                                  | Why it is here                                                                                                                                                                                              |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [other/glasses-software/](other/glasses-software/)       | Earlier glasses design. Its`CAPTURE_MODULE.md` argues for React Native and photo bursts; `hardware-demo/` shipped an HTTP bridge with video instead. **Superseded — prefer `hardware-demo/`.** |
| [other/meta-glasses-vision/](other/meta-glasses-vision/) | Feasibility research: can a glasses app be built without the hardware. Answered yes, via Meta's Mock Device Kit. Research only.                                                                             |
| [other/reserach/](other/reserach/)                       | A paper framing of the detection problem (IEEE Technical Correspondence). Not the hackathon build.                                                                                                          |
| [other/output/](other/output/)                           | A rendered PDF.                                                                                                                                                                                             |

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

# Neural Spike Calibration Pitch — Detailed Summary

## Executive Summary

The team aligned on presenting a **memory palace system that automatically captures meaningful moments when an EEG signal shows an unusual neural spike**. Because working EEG hardware and Meta smart glasses are unavailable, the prototype will demonstrate the complete concept through public EEG datasets, prerecorded footage, mock EEG animations, a phone camera, and explanatory Blender sequences.

The project should remain focused on the memory palace and healthcare use case. Sponsor-specific features—especially a social connection concept for Meta—can be presented as extensions rather than pivots. Emotion classification was removed because it would be difficult to validate convincingly; the system will detect anomalies or spikes without claiming to know the associated emotion.

---

## 1. Core Product Concept

The product records a user’s day or work session and identifies moments associated with significant changes in neural activity.

The conceptual pipeline is:

1. The user completes an initial EEG calibration.
2. A camera records the user’s environment or work session.
3. EEG signals are synchronized with the video and audio.
4. A neural-processing model identifies activity that differs from the user’s baseline.
5. When a spike is found, the relevant video segment is extracted.
6. A vision-language model analyzes the captured video and audio.
7. Elastic indexes the moment and makes it searchable.
8. The moment appears in a memory palace interface for later review.

This is positioned as a way to preserve significant experiences without requiring the user to manually decide what to record.

---

## 2. Calibration Story

### Proposed audience demonstration

The pitch may open—or later return to—a short calming video featuring soothing visuals, such as a reversed waterfall, with peaceful background music. A jump scare at the end creates a noticeable surprise response.

The team would explain that, if the viewer had been wearing an EEG headset, the experience would establish:

- A baseline representing normal or calm activity
- A spike associated with the surprise
- A rough personal “neural spike signature”

The physical headset may still be worn during the pitch, but only as a **visual prop**. The team should not imply that it is capturing live data.

### P300-inspired calibration

A more defensible explanation would model calibration after a P300-style experiment:

- The user performs a repetitive task, such as counting numbers.
- Unexpected letters, flashing images, or other stimuli occasionally appear.
- The resulting event-related EEG responses help establish the user’s baseline and spike characteristics.

Calibration is intended to happen **once per user profile when the headset is first configured**, not before every recording session.

### Important limitation

The group acknowledged that a 10- or 30-second video would not be sufficient for scientifically robust personal calibration. It is mainly a simplified, audience-friendly story. The more rigorous validation should come from established datasets and supporting research.

---

## 3. Hardware Substitution Strategy

### EEG headset

There will be no genuine live EEG demo because functioning hardware is unavailable. Instead:

- The headset remains a presentation gimmick.
- Public EEG datasets provide the evidence supporting neural-spike detection.
- The application may show animated EEG channels.
- Blender animations will explain how electrodes would gather signals and feed the processing pipeline.
- A prerecorded session can be synchronized with mock brainwave data to demonstrate the intended experience.

The team distinguished between three things:

1. **Public raw EEG data** used for research and model validation
2. **Mock or animated EEG waves** displayed in the product demo
3. **A manually generated spike** inserted when demonstrating the interface

The public data should not be presented as though it is being captured live from the person wearing the headset.

### Smart glasses

Because Meta smart glasses are also unavailable:

- The phone’s back camera will stand in for the glasses.
- The application can include a mock “glasses connected” control.
- The team can state that the application is designed to integrate with the Meta Glasses ecosystem.
- During the prototype, clicking the relevant control will cause the phone camera to record the required clip.

This substitution was reportedly already functional at the time of the conversation.

---

## 4. Model Validation Plan

Albert was asked to validate the neural-spike model using several public datasets with different hardware configurations, ideally including:

- 8-electrode data
- 16-electrode data

The purpose is to quantify how electrode count affects detection accuracy and demonstrate that the concept can work across varying levels of hardware complexity.

### Preferred evaluation criteria

The model should be optimized for **high sensitivity**:

- False positives are considered tolerable.
- False negatives are more damaging.
- If a genuinely important or surprising moment happens, the system should capture it.
- Capturing an unimportant moment is preferable to permanently missing a meaningful one.

The analysis should report:

- Overall accuracy
- False positives
- False negatives
- Sensitivity or recall
- Differences across electrode counts
- Effects of tuning thresholds or hyperparameters

An example figure of roughly 89% accuracy was discussed, but not established as a final result.

### Research support

The web application should include a research or R&D tab containing:

- The datasets evaluated
- Electrode configurations
- Model results
- Accuracy and error metrics
- Relevant published papers
- An explanation of the threshold or sensitivity tradeoff

This will serve as the technical foundation for claims made during the pitch.

---

## 5. Removal of Emotion Classification

The earlier interface contained separate controls such as:

- Simulate anger
- Simulate wonder
- Simulate surprise

The team decided these are unnecessary and potentially risky. An EEG spike alone does not reliably establish a specific emotional category, and judges could ask how “anger,” “love,” or “wonder” was validated against video and audio.

The simplified design should use one control:

> **Simulate neural spike**

The system will not claim to know the emotion. It will simply determine that an unusual or significant moment occurred and preserve the associated recording.

Well, that's only for the EEG. The EEG would not detect, but then, after that, once we have the video in place using the semantic understanding, definitely, once the META background runs on that, the emotion would be detected.

---

## 6. Demo Mechanics

The demo should represent a complete recorded session containing:

- Video
- Audio
- A synchronized EEG waveform
- Detected spikes along the timeline

A prerecorded video can be displayed with an animated EEG signal beneath it. When the system reaches a spike—or when the presenter manually triggers one—it extracts the associated section.

Different clip lengths were discussed:

- An initial concept captured the next 10 seconds.
- A later backend description used the next 30 seconds.

The team should standardize this before the final presentation.

### Backend flow

The intended backend is:

1. Record a work session.
2. Synchronize video, audio, and EEG.
3. Run the EEG through the neural-spike model.
4. Detect deviations from the calibrated baseline.
5. Extract the relevant video window.
6. Send the extracted segment to a vision-language model.
7. Generate metadata or a semantic description.
8. Index the moment with Elastic.
9. Add it to the memory palace.

Elastic’s role is primarily **video and metadata indexing**, not EEG analysis. The custom model analyzes EEG, while Elastic makes the resulting moments searchable and filterable.

---

## 7. Memory Palace Interface

The front end should stay visually simple and avoid adding too many concepts.

### Timeline view

The interface can display an entire session as a timeline, with markers wherever a neural spike occurred. Each marker represents a captured moment.

Users can:

- Scroll chronologically through moments
- Click a marker to open the associated clip
- See a small image or video preview
- Review the surrounding session context

### Carousel or streaming-style layout

A Netflix-like carousel was also discussed for browsing moments. This may already resemble the current interface and could be easier than creating an entirely new visualization.

A combined approach is possible:

- A session timeline shows when spikes occurred.
- A carousel displays the extracted clips.
- Clicking either representation opens the complete moment.

### Spike intensity

Each captured moment can include a simple color indicator:

- Red for a highly significant spike
- Orange for a moderately strong spike
- Yellow for a weaker spike
- Green for a low-intensity event retained because the model prioritizes sensitivity

The default organization should remain chronological. Users may then filter or sort moments by spike amplitude or intensity.

Possible interface elements include:

- Date navigation resembling GitHub’s activity calendar
- Session duration
- Clickable spike markers
- Thumbnail previews
- Intensity badges
- Filters for time and spike strength
- An Explore tab containing larger moment cards

---

## 8. Pitch Structure

The team discussed several possible orders. The cleanest structure would be:

1. **Introduce the problem:** meaningful experiences are easily forgotten.
2. **Present the memory palace:** a system that automatically saves neurologically significant moments.
3. **Show a short user story or Blender trailer:** demonstrate the product in everyday life.
4. **Explain calibration:** establish a personal baseline and spike signature.
5. **Show the processing pipeline:** EEG spike detection, video extraction, VLM analysis, and Elastic indexing.
6. **Demonstrate the interface:** timeline, moments, previews, and filters.
7. **Present research validation:** public datasets, electrode comparisons, and sensitivity metrics.
8. **Explain hardware substitutions honestly:** phone camera and simulated interface behavior.
9. **Tailor the closing section to the sponsor.**

A reusable three-minute Blender trailer was proposed as the common opening for multiple sponsor pitches. The spoken section could then be adjusted for Meta, MongoDB, Elastic, or other judges.

The animation could show:

- A person wearing the EEG device
- Electrodes collecting signals
- A calibration stimulus
- A full work session
- A spike being detected
- The corresponding video segment being extracted
- The captured moment entering the memory palace

---

## 9. Sponsor and Track Positioning

### Main track: Healthcare

The primary track remains healthcare. One healthcare-oriented example is supporting people with dementia by helping preserve important moments or allowing a trusted person to monitor captured experiences.

The removal of live hardware does not change the intended track. The team’s position is that the concept and processing architecture can still be validated without a live device.

### Meta-specific angle

For Meta, the team may add a connection-building or collaboration tab. Potential features include:

- Sharing captured moments with friends or family
- Comparing high-level patterns in two users’ neural activity
- Comparing the range between low and high activity over a day
- Estimating whether two users exhibit similar levels of excitement
- Letting someone monitor moments for a person with dementia

The team specifically did **not** want to pivot the whole product into a Tinder-like matching system. Neural-signature matching can be mentioned as another possible application, but the memory palace remains the core product.

The group also noted a limitation: comparing two people’s neural activity without accounting for context may oversimplify what the measurements mean. Therefore, this feature is best framed as exploratory rather than scientifically definitive.

### Elastic

Elastic should be presented as the indexing and retrieval layer:

- Index extracted video moments
- Store generated descriptions and associated metadata
- Enable search and filtering
- Filter moments by spike intensity or amplitude
- Support chronological and semantic browsing

### MongoDB and other sponsors

The common product story should remain consistent, with the technical emphasis changed according to the sponsor. The team did not finalize a detailed MongoDB-specific narrative in this conversation.

---

## 10. Decisions Made

- Keep the **memory palace** as the central product.
- Remain in the **healthcare track**.
- Do not attempt a genuine live EEG demonstration.
- Keep the headset only as a visual prop.
- Use public EEG datasets for research and model validation.
- Use mock animations or prerecorded EEG waves in the interface.
- Replace Meta glasses with the phone’s back camera.
- Include a mock “glasses connected” experience.
- Remove specific emotion classification.
- Replace multiple emotion controls with one neural-spike trigger.
- Detect anomalous moments rather than labeling anger, love, surprise, or wonder.
- Calibrate once for each user profile during initial setup.
- Model the calibration explanation after a P300-style stimulus task.
- Prioritize low false-negative rates over minimizing false positives.
- Use Elastic to index and retrieve extracted moments.
- Organize moments primarily by time, with optional intensity filtering.
- Keep sponsor-specific applications as extensions rather than changing the core pitch.
- Add a Meta-focused connection-building concept when pitching to Meta.

---

## 11. Open Questions and Risks

### Scientific credibility

The short jump-scare calibration is easy to understand but not scientifically sufficient. The team must avoid overstating what can be learned from a few seconds of EEG.

### Public versus synthetic data

The terminology was inconsistent. Public dataset recordings are not necessarily synthetic data. The final pitch should clearly distinguish:

- Real EEG recordings from public studies
- Artificial or dummy waves used in the UI
- Manually triggered spikes used to demonstrate product behavior

### Clip duration

The team alternated between saving 10 seconds and 30 seconds after a spike. This should be resolved.

### Data timing

Saving only the period after a spike may miss the event that caused it. The final implementation may need a rolling buffer so that the extracted clip includes several seconds before the spike as well as after it.

### Cross-user comparison

Comparing neural signatures without considering context is potentially misleading. This should not be presented as a proven measure of interpersonal compatibility.

### Presentation complexity

The idea includes calibration, EEG processing, phone capture, VLM analysis, Elastic indexing, a memory palace, healthcare, and sponsor-specific features. The pitch risks becoming crowded. The core flow should be presented first, with research and sponsor extensions saved for later.

---

## 12. Action Items

### Albert

- Validate the spike-detection model on public EEG datasets.
- Compare datasets using 4, 8, and 16 electrodes.
- Report accuracy, false positives, and false negatives.
- Tune the system toward high sensitivity.
- Find research literature supporting the approach.
- Target an initial validation pass within approximately two to three hours.

### Astra / Animation Owner

Create a Blender animation that explains:

- EEG hardware and electrode placement
- Initial user calibration
- Neural-spike detection
- Synchronization of EEG with video
- Extraction of a significant moment
- Delivery of that moment into the memory palace

### Front-End Team

- Replace emotion-specific buttons with one spike trigger.
- Add mock EEG channel animations.
- Ensure the phone camera can act as the glasses substitute.
- Retain or add the mock glasses-connection control.
- Create timeline and/or carousel browsing.
- Add thumbnails or previews.
- Add intensity indicators and filtering.
- Add a research/R&D tab.
- Keep the interface simple.

### Backend Team

- Define the session structure for synchronized EEG, video, and audio.
- Standardize the clip extraction window.
- Detect anomalies relative to the calibrated baseline.
- Send clips to the VLM for analysis.
- Index clips and metadata with Elastic.
- Consider using a rolling video buffer to include context before each spike.

### Pitch Team

- Decide whether calibration appears at the beginning or after the product introduction.
- Produce a reusable three-minute introductory trailer.
- Create sponsor-specific closing sections.
- Clearly disclose the absence of live EEG hardware.
- Avoid claims of validated emotion recognition.
- Prepare concise answers about calibration time, generalizability, electrode count, model accuracy, and false negatives.
