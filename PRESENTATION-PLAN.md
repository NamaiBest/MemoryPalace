# HackMIT presentation plan — MemoryPalace

Deck: **MemoryPalace Pitch Deck** (published artifact, opens in a browser, works offline once loaded).
Written 2026-09-20. Every number below is sourced from this repository; the "source" column
says where, so anything that changes in the code can be corrected here in one pass.

---

## 1. The shape of the pitch, and why it is not a linear deck

A HackMIT expo slot is ~3 minutes plus questions, delivered **eight or nine times** to
different judges, each of whom probes somewhere different. A linear deck optimises for the
first delivery and fails every one after it.

So the deck is built as a **spine plus jump-to answers**:

- **Spine — exactly 3:00, 8 slides.** Identical every time. Rehearse this to the second.
- **Ten deep dives**, each reachable with one keypress. You do not walk through them.
  You land on one when a judge asks the question it answers.

The three Manim explainers (calibration, the trigger, the data) are **deep dives, not spine
slides**. The arithmetic forces it: the film is 45 s and the three animations total 60 s.
105 seconds of video in a 180-second slot leaves 75 seconds to say everything. Played as
*answers* they land harder anyway.

### Deck controls

| Key | Does |
|---|---|
| `→` `←` `Space` | Next / previous within the current route |
| `1` … `0` | Jump straight to a deep dive |
| `J` | Jump menu (all ten, with one-line descriptions) |
| `Esc` | Return to the spine, at the slide you left |
| `N` | Speaker notes |
| `T` | Rehearsal timer — counts against the 3:00 budget, turns red when over |
| `R` | Replay the video on the current slide |
| `F` | Full screen |

Clicking the right-hand two-thirds of the screen advances; the left third goes back.

---

## 2. The spine — 3:00, to the second

| # | Slide | Budget | The one thing to land |
|---|---|---|---|
| 1 | Title | 0:10 | "Your brain already flags the moments that mattered. We wired that flag to a camera." Then stop. |
| 2 | The problem | 0:20 | **30–45 minutes.** The measured battery life of continuous video on Ray-Ban-class hardware. |
| 3 | The film | 0:45 | Say nothing. Click, step back, watch the judges. |
| 4 | How it works | 0:35 | Trace the diagram, stop on the brass box: **four consecutive elevated windows.** |
| 5 | Evidence | 0:25 | Lead with the shuffled-label control at **34.79 %**, not the headline. |
| 6 | Sponsor tracks | 0:20 | Read the status column aloud. Ask which track they judge. |
| 7 | What we do not claim | 0:15 | "Every end-to-end run used synthetic EEG. It proves the plumbing, not the neuroscience." |
| 8 | What's next | 0:10 | End on the roadmap line, then stop talking. |

**Total 3:00.** Slide 3 is a fifth of your slot — protect it by cutting words elsewhere,
never by talking over the film.

### Beat-by-beat script

**1 · Title (0:10)**
> "MemoryPalace. Your brain already flags the moments that mattered — you have felt it,
> the jolt when something surprises you. Nobody has ever wired that flag to a camera."

Do not introduce the team, the stack, or the hardware here.

**2 · Problem (0:20)**
> "The obvious answer is record everything. We measured it: continuous video on
> Ray-Ban-class hardware gives you thirty to forty-five minutes. Dead before lunch. And
> even if the battery held, nobody scrubs ten hours of first-person footage, so nothing in
> it is ever recovered. The wearable-camera research that actually helped dementia patients
> — SenseCam — never recorded video at all. One still every thirty seconds.
> Capture is solved. Deciding what is worth capturing is the product."

**3 · Film (0:45)** — silence.

**4 · How it works (0:35)**
> "Every moment you just saw was chosen by a signal, not a button. Four-second windows of
> frontal theta-alpha, z-scored against *your* calibrated baseline. When four consecutive
> windows come back elevated, the phone wakes, records ten seconds, and closes again. That
> clip is written to a local catalog *before* anything touches the network, then described
> by Muse Spark, embedded by Jina, and indexed in Elastic."

Hand on the brass box for "four consecutive".

**5 · Evidence (0:25)**
> "Three questions, three datasets. Is there real signal in personal EEG — 65.8 % on a
> three-class task from our own recordings against 33.3 % chance, and the shuffled-label
> control lands at 34.79 %, which is the check that it is not a leak. How few electrodes —
> a Crown-like eight gets 0.763 against 0.778 for the full sixteen. Does it survive a
> stranger — 0.747 leave-one-participant-out, with shuffled and pre-event controls at
> chance. The fourth card is the electrode sensitivity sweep, still in progress, and it is
> labelled as such."

**6 · Sponsors (0:20)**
> "Each sponsor owns a different edge of the same pipeline. Elastic is the retrieval layer
> — running live, twelve of twelve moments indexed. Meta is understanding and the agent —
> also live. VoloRidge is the public-data work; the evidence exists, the submission framing
> does not yet, and I am not going to round that up. Which track are you judging?"

Then press `4`, `5` or `6`.

**7 · What we do not claim (0:15)** — flat delivery, no apology. Read three of the five.

**8 · Close (0:10)**
> "EEG is non-stationary, so a frozen model decays. Retraining on the wearer is mandatory
> — which is why per-user adaptation is the product and not a setup step. Every moment you
> confirm or dismiss is a label. We will show the learning curve, and if it is flat we will
> say so."

Stop. Let them ask.

---

## 3. The ten deep dives, and which question each answers

| Key | Deep dive | Reach for it when a judge asks |
|---|---|---|
| `1` | Why calibration is personal (Manim) | "Why calibrate at all?" · "Why can't you ship a pre-trained model?" |
| `2` | The trigger, and our own bug (Manim) | "How do you know it isn't noise?" · "What's your false-positive rate?" |
| `3` | Where the numbers come from (Manim) | "Which dataset?" · anything about peak-to-peak |
| `4` | Elastic — hybrid recall | Elastic judges · "why not just a vector database?" |
| `5` | Meta — understanding + agent | Meta judges · "what does the model actually do?" |
| `6` | VoloRidge — public data | VoloRidge judges · "is this reproducible?" |
| `7` | How many electrodes, and where | "Why the Crown?" · "Could you do this with two electrodes?" |
| `8` | Operating points | "What's your accuracy?" |
| `9` | What actually runs | "Is any of this real?" · "Show me the architecture" |
| `0` | The eight questions | Your own cheat sheet — rehearse, don't present |

---

## 4. One correction to make before you rehearse

The pitch has been described internally as: *train the brain to a minimum, flash something
unexpected, measure peak-to-peak amplitude, that value differs per person, therefore
calibration.* **The conclusion is right and the mechanism is wrong**, and a judge who opens
the repo will notice.

What `confusion-detector/` actually does (`src/config.py`, `README.md`):

- 4-second **non-overlapping** windows
- frontal **theta/alpha band power** — a state over seconds, explicitly *not* an ERP
- z-scored against the wearer's calibrated baseline
- fires after **k = 4** consecutive windows above **z = 2.0**

Peak-to-peak appears exactly once in the pipeline: as the **±150 µV artifact-rejection
threshold**, which throws an epoch away. It does not detect anything.

The correct calibration story is stronger, not weaker: **µ and σ are yours.** Two people can
show identical raw amplitude and score z = +4.1 and z = +0.8 — one fires the camera, one is
a Tuesday. That is exactly what deep dive `1` animates.

If you still want the P300 / oddball story in the pitch, it has to be labelled as the
**proposed calibration protocol**, never as what the detector runs.

---

## 5. Numbers you are allowed to say, and where they come from

| Claim | Value | Source |
|---|---|---|
| Personal EEG, 3-class | 65.79 % ± 4.33 (chance 33.3 %) | `my-dataset/results.json` |
| Shuffled-label control | 34.79 % | same |
| Within-subject, all 16 ch | 0.778 AUC | `confusion-detector/CHANNELS.md` |
| Within-subject, Crown-like 8 | 0.763 AUC | same |
| Within-subject, Fz+Cz | 0.719 AUC | same |
| Within-subject, glasses F7+F8 | 0.601 AUC (worst-ranked region) | same |
| Cross-subject LOSO | 0.747 AUROC, 65.4 % balanced | `other/reserach/README.md`, `xueqi-validation/RESULTS.md` |
| Negative controls | majority 0.500 · shuffled 0.477 · pre-event 0.503 | `xueqi-validation/RESULTS.md` §13 |
| Overlap effect | 30.3 → 18.9 → 1.3 false alarms/hr | `confusion-detector/README.md` |
| Default operating point | 100 % detection, 7.2 false/hr, 15.7 s latency | same |
| First continuous detector | 1.5 % detection, ~29 false triggers/hr | `xueqi-validation/RESULTS.md` §10–11 |
| Dataset | ds006394, 33 participants, 16 ch, 125 Hz, CC0, 56 usable | `xueqi-validation/RESULTS.md` §1 |
| Elastic | 12 / 12 moments indexed, verified 2026-09-19 | `FULFILLMENT_SPONSORS.md` |
| Phone client | verified on a physical Samsung S23, 2026-09-19 | root `README.md` |

**Do not say**: a validated human detection, a calibrated probability, an accuracy figure
for the end-to-end system, or anything about emotion.

---

## 6. Open items before Sunday

1. **Albert's electrode sweep.** Slide 5 has a dashed placeholder card sized for it —
   detection rate, false positives, false negatives at 4 / 8 / 16 channels, tuned for
   recall. Replacing the placeholder is a five-line edit.
2. **Standardise the clip length.** The repo alternates between 10 s and 30 s. The deck
   says **10 s** throughout. Pick one and make the code, the README and the deck agree.
3. **MongoDB.** Deliberately cut from the deck — it is planned, not built, and a slide
   claiming it as the persistence layer is a Q&A trap. It appears once, on the roadmap
   pills, as a future cloud metadata layer.
4. **VoloRidge framing.** The status pill says "evidence exists · framing pending", which
   is accurate. If someone writes the submission framing before Sunday, change the pill to
   `live` and say so.
5. **The film's illustrative graphics.** `video/memory-palace/README.md` notes the on-screen
   signal values (surprise 98 %, frustration 68 %, curiosity 37 %) are storytelling values,
   not measurements. If a judge freezes on them, say that first — do not be caught
   defending a number the film's own documentation disowns.

---

## 7. Demo run-of-show and fallbacks

**If you demo live**, the order is: pair the phone → `/live` → Simulate Neural Spike →
camera opens, records, closes → the moment appears in the gallery → `/explore`, type
"laptop keyboard", show it returning first via `elastic-rrf-jina-v5-omni` → click the
timeline dot to replay the source clip.

Known failure modes and what to say:

| If | Then |
|---|---|
| The frontend looks right but nothing is interactive | You are on `next dev`. Hydration never completes. Use the production build: `npm run build && npm start`. |
| The gallery is empty | That is the honest state, not a bug — nothing is seeded. Say so and capture one. |
| Elastic is unreachable | Search falls back to local text matching and the label under the box says so. This is a designed degradation; show it rather than hiding it. |
| No model key | Memory Guard answers from the local catalog with citations, clearly labelled. It never claims to be Meta or Grok. |
| Wi-fi is gone entirely | The deck is self-contained once loaded. Run the whole backend with `hardware-demo/run.py demo --recorder phone` — no hardware needed. |

Open `/debug` if any link in the chain is in doubt; it names which one is down.

---

## 8. Rehearsal

- Press `T` and run the spine three times until you finish between 2:50 and 3:00 without
  hurrying slide 7.
- Then rehearse **deep-dive entry**: have someone read a question off slide `0`, and
  practise landing on the right key in under two seconds. That transition is what makes the
  format work.
- Rehearse the film in silence at least once. The instinct to narrate over it is strong and
  it costs you the whole 45 seconds.
