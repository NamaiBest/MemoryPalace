# HackMIT presentation plan, MemoryPalace

Deliverable: **presentation/MemoryPalace-HackMIT.pptx**, 15 slides, 16:9.
A PDF copy sits beside it as a fallback. Rewritten 2026-09-20.

---

## 0. Before you open it once

**Fonts: nothing to install.** The deck is set entirely in **Century Gothic**, which ships
with Microsoft Office on both macOS and Windows. That is the whole reason it was chosen
over Poppins or the app's own Geist: the previous version needed three font installs, did
not get them, and PowerPoint substituted something ugly.

If you end up presenting on a machine with no Office at all, present the **PDF** instead.
It has the fonts embedded so it always renders correctly. The trade is that a PDF cannot
play the four embedded videos, so you would run those from Finder.

**Check the videos play.** Slides 3, 6, 7 and 8 carry embedded MP4s. Open the deck once on
the presenting machine and click each one.

**Theme.** Light throughout: the app's ivory (#F3EFE5) as the ground, near-black text, a
single brass accent. The three explainer animations were re-rendered light to match, so
nothing on screen is a dark rectangle except the film itself, which is meant to be.

## 1. Shape of the deck

| Slides | What they are |
|---|---|
| 1 to 8 | The pitch. Roughly three minutes if you do not linger. |
| 9 to 11 | One slide per sponsor track. Show the one that is judging you. |
| 12 to 13 | The honesty slide and the close. |
| 14 to 15 | Appendix. Architecture, and the demo run of show. |

You do not show all fifteen to anybody. The core run for a three minute slot is
**1, 2, 3, 4, 5, 12, 13**, then the sponsor slide for whoever is in front of you, then the
explainers only if asked.

### Slide list

| # | Slide | Budget | The one thing to land |
|---|---|---|---|
| 1 | Title | 0:10 | "Your brain already flags the moments that mattered. We wired that flag to a camera." Then stop. |
| 2 | The problem | 0:20 | **30 to 45 minutes.** Measured battery life of continuous wearable video. |
| 3 | The film, 36 s | 0:40 | Say nothing. Click, step back, watch the judges. |
| 4 | How a moment is chosen | 0:25 | Trace the row, stop on the brass box: **four consecutive elevated windows.** |
| 5 | What happens to the clip | 0:20 | The clip is committed locally **before** anything touches the network. |
| 6 | Calibration, animated | on request | "Same amplitude, opposite conclusion." |
| 7 | The trigger, animated | on request | Same code, same threshold, 24 times fewer false alarms. |
| 8 | The data, animated | on request | What is frozen before any model is fit. |
| 9 | Elastic | 0:30 | Built and not built, side by side. |
| 10 | Meta | 0:30 | Same. |
| 11 | VoloRidge | 0:30 | Same. |
| 12 | What we do not claim | 0:15 | "Every end to end run used synthetic EEG." |
| 13 | What is next | 0:10 | Per user adaptation is the product, not a setup step. |
| 14 | Appendix, what runs | on request | The phone never talks to the browser. |
| 15 | Appendix, run of show | for you | The demo order, and what to say when it breaks. |

Speaker notes are written into every slide. In PowerPoint use Presenter View, or
View then Notes Page to print them.

---

## 2. Beat by beat, slides 1 to 5

**1, Title.**
> "MemoryPalace. Your brain already flags the moments that mattered. You have felt it, the
> jolt when something surprises you. Nobody has ever wired that flag to a camera."

Do not introduce the team, the stack or the hardware here.

**2, The problem.**
> "The obvious answer is record everything. We measured it. Continuous video on Ray-Ban
> class hardware gives you thirty to forty five minutes. Dead before lunch. And even if the
> battery held, nobody scrubs ten hours of their own footage, so nothing in it is ever
> recovered. The wearable camera research that actually helped dementia patients, SenseCam,
> never recorded video at all. One still every thirty seconds.
> Capture is solved. Deciding what is worth capturing is the product."

**3, The film.** Silence. Thirty six seconds.

**4, How a moment is chosen.**
> "Every moment you just saw was chosen by a signal, not a button. Four second windows of
> frontal theta alpha power, z scored against your own calibrated baseline. When four
> consecutive windows come back elevated, and only then, the phone wakes up."

Hand on the brass box for "four consecutive".

**5, What happens to the clip.**
> "Ten seconds, then the camera closes again. The clip is written to a local atomic catalog
> before anything touches the network. Only then is it described, embedded and indexed. A
> sponsor service outage degrades search. It can never lose a memory."

**12, What we do not claim.** Flat delivery, no apology. Read three of the five rows.

**13, Close.**
> "EEG is non stationary, so a frozen model decays. Retraining on the wearer is mandatory,
> which is why per user adaptation is the product and not a setup step. Every moment you
> confirm or dismiss is a label."

Stop. Let them ask.

---

## 3. Why there are no accuracy numbers in this deck

Deliberate, and worth being able to explain if a judge asks.

The repository does contain measured results, but the strongest of them answer a
*different* question from the one this product asks. The 3 class mental imagery result was
recorded on an EPOC X, which is neither the product hardware nor the product task. Quoting
it invites exactly the question you do not want: "so what is your accuracy at detecting
confusion?" The honest answer is that no such number exists yet, because there has been no
validated human detection.

So the deck claims the **method and the engineering**, and slide 12 says plainly what is
not yet true. When Albert's electrode sweep lands, an evidence slide goes back in between
slides 5 and 9, and the sweep is the thing it reports: detection rate, false positives and
false negatives at 4, 8 and 16 electrodes, tuned for recall.

If a judge presses for a number before then:

> "Accuracy is the wrong metric for a rare event trigger, and we do not have a validated
> human number yet. What we can show you is the false alarm engineering."

Then go to slide 7.

---

## 4. One correction to make before you rehearse

The pitch has been described internally as: train the brain to a minimum, flash something
unexpected, measure peak to peak amplitude, that value differs per person, therefore
calibration. **The conclusion is right and the mechanism is wrong**, and a judge who opens
the repo will notice.

What `confusion-detector/` actually does, per `src/config.py` and its README:

- 4 second **non overlapping** windows
- frontal **theta over alpha band power**, a state over seconds, explicitly not an ERP
- z scored against the wearer's calibrated baseline
- fires after **k = 4** consecutive windows above **z = 2.0**

Peak to peak appears exactly once in the pipeline, as the **plus or minus 150 microvolt
artifact rejection threshold**, which throws an epoch away. It does not detect anything.

The correct calibration story is stronger. **Mu and sigma are yours.** Two people can show
identical raw amplitude and score z = +4.1 and z = +0.8. One fires the camera, one is a
Tuesday. That is what slide 6 animates.

If you still want the P300 oddball story in the pitch, label it as the **proposed
calibration protocol**, never as what the detector runs.

---

## 5. Sponsor slides

Slides 9, 10 and 11 are each split into what we built and what we have not built. Read the
right hand column out loud. Most teams skip it, which is exactly why doing it works.

Current status, in one line each:

- **Elastic.** Implemented and verified live on Elastic Cloud. Workflows and Agent Builder
  are documented as future work, not presented as done.
- **Meta.** Muse Spark and Voice Transcribe implemented and verified live. Output speech is
  the browser voice, labelled as such, not a Meta TTS API. No physical glasses.
- **VoloRidge.** The evidence exists in `xueqi-validation/` and `confusion-detector/`. The
  sponsor specific submission framing does not. Do not round that up. If somebody writes it
  before Sunday, change the slide.

**Logos.** The slides use a typographic treatment: each sponsor's name set large in its own
brand colour. If you want real logo art, drop official files into
`presentation/logos/` and they can be placed on the matching slide. Do not approximate a
sponsor's logo by hand, it reads worse than no logo at all.

---

## 6. Assets built for this

| Path | What |
|---|---|
| `presentation/MemoryPalace-HackMIT.pptx` | The deck. Videos embedded. |
| `presentation/MemoryPalace-HackMIT.pdf` | Fonts embedded, no video. Fallback. |
| `presentation/manim/scenes.py` | The three animations, with every number sourced to a repo file. |
| `presentation/logo/` | Three logo concepts, lockup, horizontal and app icon, light and dark, transparent PNG and SVG. |
| `presentation/logo/thumbnail/` | Submission thumbnails at 1280x720, 1200x630 and 1080x1080. |
| `presentation/logo/review-all-three-light.png` | All three concepts side by side on the ivory ground, for picking. |

The film used in the deck is **MemoryPalace-36s.mp4**, the newer rebuild, not the 45 second
cut.

---

## 7. Open items before Sunday

1. **Albert's electrode sweep.** See section 3 for exactly what slide it becomes.
2. **Standardise the clip length.** The repo alternates between 10 s and 30 s. The deck says
   10 s throughout. Make the code, the README and the deck agree.
3. **Pick a logo.** Three concepts are in `presentation/logo/`. The submission thumbnail
   needs one of them.
4. **Confirm Century Gothic exists** on whatever machine presents, or present the PDF.
5. **The film's on screen graphics.** `../memorypalace-video/memory-palace/PRODUCTION-NOTES.md` says the
   signal values in the film are storytelling values, not measurements. If a judge freezes
   on them, say that first. Do not be caught defending a number the film's own
   documentation disowns.

---

## 8. Demo run of show

Slide 15 carries this, so you can put it on screen while you set up.

Order: pair the phone, open `/live`, simulate a neural spike, camera records ten seconds
and closes, the moment appears in the gallery, search `/explore` for a phrase from the clip,
click the timeline dot to replay it.

| If | Then |
|---|---|
| Page renders but nothing responds | You are on `next dev`, hydration never completes. Use `npm run build && npm start`. |
| Gallery is empty | That is the honest state, nothing is seeded. Capture one. |
| Elastic unreachable | Search falls back to local text matching and the label says so. Show it rather than hiding it. |
| No model key | Memory Guard answers from the local catalog with citations, clearly labelled. It never claims to be Meta or Grok. |
| No wifi at all | `confusion-detector/.venv/bin/python hardware-demo/run.py demo --recorder phone` runs the whole thing with no hardware. |

`/debug` names which link in the chain is down.

---

## 9. Rehearsal

- Run slides 1 to 5, then 12 and 13, on a timer. Target 2:50 to 3:00 without hurrying 12.
- Rehearse **jumping to a sponsor slide**. Practise asking "which track are you judging?"
  and landing on 9, 10 or 11 in under two seconds.
- Rehearse the film in silence at least once. The instinct to narrate over it is strong and
  it costs you the whole thirty six seconds.
