# Presentation handoff

**Read this before touching the deck.** Several Claude sessions have worked on this
presentation and none of them share context. This file is the shared state. Update it
when you change something structural.

Last updated: 2026-09-20, after the light-theme rebuild and the v2 revision.

---

## 1. Which file is live

```
presentation/revised-v2/FINAL Memorypalace-HackMIT.pptx     <- THE LIVE DECK
presentation/revised-v2/Memorypalace-HackMIT-updated.pptx   <- previous v2 build
presentation/revised-v2/Memorypalace-HackMIT-updated.pdf    <- static backup of that
presentation/MemoryPalace-HackMIT.pptx                      <- SUPERSEDED, earlier generation
presentation/MemoryPalace-HackMIT.pdf                       <- superseded
```

`FINAL Memorypalace-HackMIT.pptx` is 17 slides and is the one the user is editing by hand
in PowerPoint. **It contains hand edits that exist in no script.** Do not regenerate the
deck from a generator and overwrite it. Edit the file, or ask first.

Anything named `~$...` is a PowerPoint lock file. Ignore it.

---

## 2. How the deck has been built, and the trap in that

Two different build paths have been used, and they are not compatible.

**Path A, the generator.** `pptxgenjs` script producing the whole deck from code. That
approach built the superseded `presentation/MemoryPalace-HackMIT.pptx`. Its useful legacy
is a measured-layout discipline: because the deck has an 18pt floor and 18pt is physically
large on a 13.33in canvas, the generator measured every text block's height and threw at
build time rather than shipping clipped text. If you rebuild from a generator, keep that.

**Path B, direct OOXML editing.** The current v2 deck was made this way: unzip, edit
`ppt/slides/slideN.xml`, rezip. This is what allows native editable charts and preserved
hand edits. **This is the path to use now.**

The mechanics, from the pptx skill:

```bash
python3 -c "import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall('unpacked')" deck.pptx
# structural work FIRST: add/delete/reorder slides
#   add_slide.py unpacked/ slide2.xml --after slide5.xml
#   reorder or delete by editing <p:sldIdLst> in ppt/presentation.xml
#   clean.py unpacked/     (after deletions, removes orphans)
# THEN edit slide content in ppt/slides/slideN.xml
(cd unpacked && rm -f ../out.pptx && zip -Xr ../out.pptx .)
python scripts/office/validate.py out.pptx --original deck.pptx
```

Parse XML with `defusedxml.minidom`, never `xml.etree.ElementTree`, which rewrites
namespace prefixes and corrupts the package.

---

## 3. Design system

| Token | Value | Use |
|---|---|---|
| Page | `F3EFE5` | slide background, the app's ivory |
| Card | `FBF9F3` | panel fill |
| Edge | `DFD8C6` | panel border |
| Ink | `1A1917` | headings, 15:1 on page |
| Body | `4E4A42` | body text, 8.5:1 |
| Mute | `6E685C` | labels, 5.2:1 |
| Brass | `7A6430` | the single accent, 5.6:1 |
| Crit | `A44B3C` | negative or cautionary |
| OK | `46683F` | affirmative |

Light theme throughout. This was a deliberate reversal of an earlier dark deck; do not
invert it back.

**Typeface: Century Gothic, everything.** This is load bearing. An earlier version used
Geist and Instrument Serif from `video/memory-palace/fonts/`, they were never installed on
the presenting machine, PowerPoint substituted, and the deck looked broken. Century Gothic
ships with Microsoft Office on macOS and Windows, so there is nothing to install. If you
change the typeface you re-introduce that failure. Minimum size anywhere is 18pt.

Century Gothic is a wide geometric face: roughly 0.578 em average advance for body, 0.605
bold, 0.745 uppercase. Text that fitted in a grotesque will not fit here. Measure.

---

## 4. Slide inventory, current state

Twenty slides. Re-verified against the live file on 2026-09-20, second pass.

| # | Slide | Notes |
|---|---|---|
| 1 | Title, "Revisit & Reflect / Mental Health is Physical Wealth" | Full-bleed title card, `image1.png` |
| 2 | "Ever walked into a room..." | Semantic overload framing |
| 3 | The 36-second film | `media1.mp4` |
| 4 | "Sense it. Capture it. Come back to it." | Crown / glasses / app flowchart |
| 5 | "The field chased the hard problem." | SEED and Wang citations. **Says 30-90 s calibration; the ledger says 120 s. Reconcile.** |
| 6 | "Remember one detail. Get the whole moment back." | The app |
| 7 | **"Mental health reflection."** Everyday reflection and children | New. Office and child figures top right; WHAT WE DO NOT CLAIM strip |
| 8 | **Healthcare 2**, dementia and a trusted clinician | New. Elder figure top right; honest-limits card |
| 9 | Calibration animation | `media2.mp4` |
| 10 | "Start by learning your normal" | |
| 11 | "Removing signal noise" | `media3.mp4`, **trimmed to start 2 s in**; poster is the final frame |
| 12 | "Every check uses data it has never seen" | Retitled. Subtitle "Fresh samples reduce false alarms." Synthetic fixture |
| 13 | "Five datasets. One question." | BED removed; Shin card is now double width |
| 14 | "84 numbers. Eight electrodes." | Electrode ladder, **percentages on the n = 38 basis** |
| 15 | **"Two questions. Two datasets."** | New. Per-participant and per-electrode tables |
| 16 | Elastic | Workflows and Agent Builder labelled NEXT |
| 17 | Meta | Six surfaces. Muse Image keepsakes now LIVE; SEE and GROUND merged into one card |
| 18 | System architecture | A neural-network slide is still to be added here |
| 19 | **"Demo time."** | New |
| 20 | Close | Transparent wordmark, `image14.png`, hyperlink to localhost:3000 |

**Two number bases exist in this repo and they are not the same.**
`confusion-detector/CHANNELS.md` reports within-subject AUC over all 51 recordings
(16 ch 0.778, Crown-like 0.763, glasses brow 0.606). `Final Presentation/README.md`
reports the same analysis restricted to the 38 recordings where the full montage cleared
0.70 AUC (16 ch 84%, Crown-like 82%, glasses brow 63%). **Slides 5, 14 and 15 are all on
the n = 38 basis.** Do not mix them, and state the inclusion rule if anyone asks.

---

## 5. The claims ledger

This is the most important section. The deck's credibility rests on these lines, and
several have already had to be corrected once. **Check here before writing any number.**

### True, sourced, safe to say

| Claim | Value | Source |
|---|---|---|
| Detector method | frontal theta (4-8 Hz) over alpha (8-13 Hz) band power | `confusion-detector/src/cognitive_load.py` |
| Window | 4 s, non-overlapping (`hop_s == window_s`) | `confusion-detector/src/config.py` |
| Threshold | z = 2.0 against the wearer's own baseline | same |
| Persistence | k = 4 consecutive elevated windows | same |
| Calibration duration | **120 seconds** as run; default in code is 60 | `run_session.py --calibrate 120` |
| Overlap result | 75% overlap 30.3 false alarms/hr, 50% 18.9, none 1.3 | `confusion-detector/README.md` |
| Default operating point | 100% detection, 7.2 false alarms/hr, 15.7 s latency, drifting fixture | `config.py` comments |
| Within-subject AUC | 16 ch 0.778, Crown-like 8 ch 0.763, Fz+Cz 0.719, glasses F7+F8 0.601 | `confusion-detector/CHANNELS.md` |
| Cross-subject | 0.747 AUROC, 65.4% balanced accuracy, LOSO | `xueqi-validation/RESULTS.md` |
| Negative controls | majority 0.500, shuffled 0.477, pre-event 0.503 | `xueqi-validation/RESULTS.md` §13 |
| ds006394 | 33 participants, 56 usable recordings, 16 ch, 125 Hz, CC0 | `xueqi-validation/RESULTS.md` §1 |
| Epoch counts | 1,025 surprise, 5,865 time-matched control | same §3 |
| VoloRidge dataset | Shin et al. 2018 set A, 28 ch, 5 people, 15 sessions | `eeg-state-detection/README.md` |
| VoloRidge model | 84 features, logistic regression + one moving average | same |
| VoloRidge result | 8 of 15 sessions beat a circular time-shift null at p <= 0.05 | `outputs/backtest_state/report.json` |
| Personal EPOC X set | 65.79% 3-class vs 33.3% chance, shuffled control 34.79% | `my-dataset/results.json` |
| Elastic | 12 of 12 moments indexed, verified live 2026-09-19 | `FULFILLMENT_SPONSORS.md` |
| Phone client | verified on a physical Samsung S23, 2026-09-19 | root `README.md` |
| Public datasets opened | Shin 2018 set A; OpenNeuro ds006394; PhysioNet EEGMMIDB; PhysioNet Auditory EEG-Biometric; BED (restricted, not downloaded); own EPOC X | `dataset/README.md`, `eeg-neural-signal-processing/RESULTS.md` |
| Electrode ladder | 16 ch 0.778, Crown-like 8 ch 0.763, Ganglion 4 ch 0.719, midline Fz+Cz 0.719, glasses brow 0.606 | `confusion-detector/CHANNELS.md` |
| Best single pair | Cz+O1 at 0.745, beats the whole 4-channel Ganglion set | same |
| Top pairs | every one of the top 12 of 120 pairs contains Cz or Fz | same |
| Cross-context limit | visual-trained detector falls to 0.634 on the same person's auditory task | same, Result 3 |
| Elastic index | `memorypalace-multimodal-moments`, 1,024-dim cosine vector, RRF over BM25 + dense kNN | `hardware-demo/eegdemo/elastic_store.py` |
| Elastic inference id | `.jina-embeddings-v5-omni-small` | same |
| Meta vision model | `muse-spark-1.3` via `https://api.meta.ai/v1/responses`, `input_video` with an `input_image` fallback over 6 MB | `hardware-demo/eegdemo/vision.py` |
| Meta voice model | `muse-voice-transcribe-1.0`, 24 kHz mono, 30 s and 8 MB cap, never indexed | `hardware-demo/eegdemo/voice.py` |

| Meta keepsake images | `muse-image-1.0` via `https://api.meta.ai/v1/images/generations`, endpoint `/moments/keepsake`, UI in `app/components/moment/Keepsake.tsx` | `hardware-demo/eegdemo/imagery.py` |

### Not true. Do not put these on a slide.

| Claim that has come up | Reality |
|---|---|
| "Phase shift detection" | **Appears nowhere in the repository.** `grep -ri "phase.shift"` returns nothing. It is not a method this project implements. |
| "Burst detection" as a shipped technique | `burst` appears only as `burstId`, a React variable animating the EEG line in `app/components/live/EEGMonitor.tsx`, and in `app/README.md` as a *future* type. There is no burst detector. Slide 8 currently phrases the second check as "sustained burst confirmation", which is acceptable only because it describes the four-window rule, not a separate detector. |
| "20 minute configuration" | Calibration is **120 seconds**. The shorter number is the better claim; use it. Slide 5's notes already flag twenty minutes as an onboarding target, not a measured result. |
| "30 seconds of data" | Also not the implemented figure. 120 s is. |
| "7 days / 3 hours of conventional EEG training" | **No source found in this repository.** If it comes from a paper, cite the paper on the slide. If it cannot be cited, cut it. |
| "State of the art" | Unsupported comparative claim. Avoid. |
| Validated human detection | Every end-to-end run used synthetic EEG. The pass proves the plumbing, not the neuroscience. |
| Emotion recognition | Explicitly removed from the product. An EEG spike does not name a feeling. |
| Peak-to-peak as the detection mechanism | Peak-to-peak appears once, as the +/-150 uV artifact rejection threshold, which throws an epoch away. It does not fire anything. |
| Elastic Workflows or Agent Builder as built | **Not implemented.** `DOCS_sponsor/elastic` says so in its own words: "pitch direction, not implemented claims". Slide 14 labels them NEXT. Keep that label. |
| Meta generating the spoken answer | Meta's documented voice API covers transcription only. The answer audio is the device speech synthesizer. Say it that way. |
| Audio transcription of recorded moments | Voice transcription is for the user's spoken question only. Moment audio is not transcribed. |
| Physical Meta glasses | The team does not have them. The pairing handoff into Meta AI is real, the recorder is the phone camera, and the slide says DEMO. |

---

## 6. Change log, and what is still open

### Applied 2026-09-20

1. **Slide 7 video rebuilt.** One flat resting trace per wearer, no cognitive load, then a
   shared event band, then wearer A peaks small and wearer B peaks nearly three times
   larger on the same axis. Peak-to-peak 0.9 against 2.4. Ends on "So the threshold has to
   be yours." Source `presentation/revised-v2/tools/baseline_scene.py`.
2. **Slide 12 rebuilt** as the dataset inventory. Every public EEG corpus opened, including
   the one we could not get.
3. **Slide 13 replaced.** The backtest slide is gone; the slot now carries the winning
   pipeline and the 2 / 4 / 8 / 16 electrode ladder.
4. **Slide 14 rebuilt** against the full Elastic brief in `DOCS_sponsor/elastic`.
5. **Slide 15 rebuilt** against the full Meta brief in `DOCS_sponsor/meta`, including
   Muse Voice Transcribe.
6. **Background lifted** from `F3EFE6` to `F7F4EC` on all 17 slides. Slides 4 and 5 had no
   background element at all and were rendering white against the rest; they now carry one.
7. **Emphasis colours on slide 5** moved from pure red and the accent3 green to the deck
   palette, `A44B3C` and `46683F`.

### Still open

- The user has said more rounds of changes are coming. Ask before assuming anything below
  is wanted.
- VoloRidge's own logo is a navy plaque plus `image10.png`; it is the only sponsor logo
  that is not an official supplied file.
- Slide 16's architecture diagram has not been reviewed against the rebuilt sponsor slides.

---

## 6b. Slides built and waiting to be inserted

`presentation/revised-v2/Memorypalace-slides-to-insert.pptx`, 7 slides, built to the same
system as the live deck. Insert with PowerPoint's **Reuse Slides** (Home > New Slide >
Reuse Slides > Browse) and tick **Keep source formatting**. This preserves the hand edits
in the live deck, which regenerating it would destroy.

| In the insert file | Goes where | Action |
|---|---|---|
| 1, "Your day gives you more than you can hold" | slide 2 | replace |
| 2, "Come back to your day" | slide 4 | replace, drops the image for three cards |
| 3, "Sense it. Capture it. Come back to it." | slide 5 | replace, Crown / glasses / app flow |
| 4, "A neural signature belongs to one person" | after slide 5 | insert, new |
| 5, "The field chased the hard problem" | after the one above | insert, new |
| 6, "Small and simple held up" | after slide 11 | insert, new |
| 7, "Remember one detail" | slide 13 | replace, retitled |

Each carries speaker notes with its sources. Product images were extracted from the live
deck itself, so they match: Crown from `revised-v2/assets/crown.png` with its white ground
repainted to the card colour, glasses and app screenshot from the deck's own media.

### The citations now on the comparison slide

Both are real and were fetched, not recalled:

- **Zheng, W.-L. and Lu, B.-L.**, "Investigating Critical Frequency Bands and Channels for
  EEG-Based Emotion Recognition with Deep Neural Networks", *IEEE Transactions on
  Autonomous Mental Development* 7(3), 2015. The SEED protocol: 15 subjects, 2 sessions a
  week or more apart, 15 film clips of about 4 minutes each, 62 channels at 1000 Hz.
- **Wang, S. et al.**, "A Review on Signal Processing Approaches to Reduce Calibration
  Time in EEG-Based Brain-Computer Interface", *Frontiers in Neuroscience* 15, 2021,
  doi 10.3389/fnins.2021.733546. Tabulates 200 to 288 calibration trials per subject for
  motor imagery, and uses the phrase "long and tedious calibration time".

These replace the unsourced "7 days, minimum 3 hours" figure, which could not be found in
any paper and should not be said.

---

## 7. The Manim animations

Sources: `presentation/manim/scenes.py` for the original three, and
`presentation/revised-v2/tools/baseline_scene.py` for the calibration scene that is
actually in the deck now.

Rendered with Manim Community 0.21 in a container.

```bash
pip install manim            # needs libcairo2-dev libpango1.0-dev dvisvgm texlive ffmpeg
python -m manim --resolution 1920,1080 --fps 30 baseline_scene.py Baseline
ffmpeg -i Baseline.mp4 -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p \
       -movflags +faststart -an media2.mp4
ffmpeg -sseof -0.5 -i media2.mp4 -frames:v 1 image7.png     # the poster frame
```

Then drop both into `ppt/media/` of the unpacked deck. `media2.mp4` and `image7.png` are
used by slide 7 and by nothing else, which was checked before the swap.

**The calibration scene, as it now reads.** Two panels on a shared y axis. Both wearers
hold a flat resting trace, labelled as no cognitive load. A single event band fades in
across both. The traces then complete through it: wearer A rises to a peak-to-peak of 0.9,
wearer B to 2.4 on the same stimulus. Double-headed arrows measure each from that person's
own resting level. The title swaps to "So the threshold has to be yours."

Two implementation traps that already cost a render each:

- Two `Create()` calls on the same mobject with offset `rate_func`s do **not** continue a
  partial draw. Split the trace into separate segments instead, one per animation.
- Add the event band to the scene *before* the traces, or it paints over them.

**Font trap:** small text in Poppins loses its word spacing in this renderer, producing
"twoof themindependent". Body and label text uses **URW Gothic**. Headings use Poppins
Medium, which is unaffected at large sizes. Do not switch the small text back to Poppins.

Scene background is `#f7f4ec`, matching the lifted deck background.

---

## 8. Asset inventory

| Path | What |
|---|---|
| `video/memory-palace/MemoryPalace-36s.mp4` | The current film. 36 s, 1920x1080. **Newer than the 45 s cut, use this one.** |
| `video/memory-palace/MemoryPalace-45s.mp4` | Superseded |
| `video/memory-palace/deck-assets/` | Web-compressed film and poster frames |
| `video/memory-palace/fonts/` | Geist, Geist Mono, Instrument Serif. Used by the film and the logo, **not** by the deck |
| `presentation/manim/scenes.py` | The three explainer animations |
| `presentation/logo/` | Three logo concepts, lockup / horizontal / icon, light and dark, transparent PNG and SVG |
| `presentation/logo/thumbnail/` | Submission thumbnails, 1280x720, 1200x630, 1080x1080 |
| `presentation/logos/` | Drop official sponsor logo files here |
| `presentation/revised-v2/assets/` | crown.png, person.png/svg, and the original and restored clips |
| `presentation/revised-v2/tools/slidegen_lib.py` | Slide XML builders in the deck's own idiom: cards, pills, bars, measured text |
| `presentation/revised-v2/tools/slidegen_build.py` | Generates slides 12 to 15. Run it, then copy `out/slideN.xml` into the unpacked deck |
| `presentation/revised-v2/tools/baseline_scene.py` | The calibration Manim scene that is in the deck |
| `DOCS_sponsor/VoloRidge`, `DOCS_sponsor/elastic`, `DOCS_sponsor/meta` | The sponsor briefs. **These are files, not folders.** Read them before touching a sponsor slide |
| `presentation/SLIDES-VOLORIDGE.md` | The VoloRidge slide source text, now partly superseded |
| `eeg-state-detection/` | The public-data research track: README, RESEARCH_LOG, outputs |

---

## 9. Things that have already gone wrong, so you do not repeat them

1. **Fonts not installed on the presenting machine.** Caused a full re-typeset. Century
   Gothic now, for that reason.
2. **Layout built for a narrower typeface.** At an 18pt floor with Century Gothic, cards
   overflow silently. Measure before you place.
3. **A dark deck.** Built, rejected, inverted. It is light now.
4. **Sponsor logos.** Claude cannot draw Elastic's, Meta's or VoloRidge's logo. Official
   files must be supplied. Slides 14 and 15 now carry real logo images; VoloRidge still
   needs one.
5. **Unsourced performance claims.** Corrected twice. §5 exists so it does not happen a
   third time.
6. **An HTML artifact version of this deck** was built early and is now stale and
   contradicts the current numbers. Do not revive it.
7. **`DOCS_sponsor/VoloRidge`, `elastic` and `meta` read as empty directories** in some
   listings. They are plain files with no extension. `cat` them.
8. **Text measured against the wrong typeface.** `slidegen_lib.py` carries a Poppins
   advance table and a `fits()` guard that raises at build time. It fired nine times
   during the sponsor-slide rebuild. Every throw was fixed by shortening copy, never by
   dropping below the 18pt floor.
