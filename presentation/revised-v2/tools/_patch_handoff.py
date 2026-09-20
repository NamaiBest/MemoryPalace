import re, io, os
p = os.path.expanduser("~/mnt/HackMIT/PRESENTATION-HANDOFF.md")
x = open(p, encoding="utf-8").read()

def replace_section(text, start_header, next_header, new_body):
    i = text.index(start_header)
    j = text.index(next_header, i)
    return text[:i] + new_body + text[j:]

S4 = """## 4. Slide inventory, current state

Seventeen slides. This table was re-verified against the live file on 2026-09-20.

| # | Slide | Notes |
|---|---|---|
| 1 | Title, logo, "Revisit & Reflect" | Logo is an image |
| 2 | "Ever walked into a room..." problem framing | Semantic overload framing, applied |
| 3 | The 36-second film, embedded | `media1.mp4`. Plays on click in desktop PowerPoint |
| 4 | "Sense it. Capture it. Come back to it." | Crown / glasses / app flowchart. Inserted slide |
| 5 | "The field chased the hard problem. We took the useful one." | Inserted slide, carries the SEED and Wang citations |
| 6 | "Remember one detail. Get the whole moment back." | The app search story |
| 7 | Calibration animation, full bleed | `media2.mp4` + poster `image7.png`. **Rebuilt 2026-09-20**, see §7 |
| 8 | "Start by learning your normal" | Per-wearer ranges |
| 9 | "Two checks before a moment is flagged" | |
| 10 | "Four fresh windows confirm one event" | `media3.mp4` persistence animation |
| 11 | "Fresh samples reduced false alarms" | Overlap chart, native |
| 12 | VoloRidge: "Six public datasets. One question." | **New 2026-09-20.** Dataset inventory, six cards |
| 13 | VoloRidge: "84 numbers. Eight electrodes." | **New 2026-09-20.** Replaced the backtest slide. Pipeline + electrode ladder |
| 14 | Elastic: "Elasticsearch is the memory." | **Rebuilt 2026-09-20.** Five-stage pipeline + four judged criteria |
| 15 | Meta: "Meta sees it, hears you, answers." | **Rebuilt 2026-09-20.** Six verticals with status pills |
| 16 | System architecture | Native editable diagram |
| 17 | Close | |

The backtest slide, "Does the signal survive a harder test?", was removed at the user's
request. Its content survives in `eeg-state-detection/README.md` and in the speaker notes
on slide 13.

---

"""

S6 = """## 6. Change log, and what is still open

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

"""

S7 = """## 7. The Manim animations

Sources: `presentation/manim/scenes.py` for the original three, and
`presentation/revised-v2/tools/baseline_scene.py` for the calibration scene that is
actually in the deck now.

Rendered with Manim Community 0.21 in a container.

```bash
pip install manim            # needs libcairo2-dev libpango1.0-dev dvisvgm texlive ffmpeg
python -m manim --resolution 1920,1080 --fps 30 baseline_scene.py Baseline
ffmpeg -i Baseline.mp4 -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p \\
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

"""

x = replace_section(x, "## 4. Slide inventory", "## 5. The claims ledger", S4)
x = replace_section(x, "## 6. Pending changes requested", "## 6b. Slides built", S6)
x = replace_section(x, "## 7. The two Manim videos", "## 8. Asset inventory", S7)

# claims ledger additions
anchor = "### Not true. Do not put these on a slide."
add_true = """| Public datasets opened | Shin 2018 set A; OpenNeuro ds006394; PhysioNet EEGMMIDB; PhysioNet Auditory EEG-Biometric; BED (restricted, not downloaded); own EPOC X | `dataset/README.md`, `eeg-neural-signal-processing/RESULTS.md` |
| Electrode ladder | 16 ch 0.778, Crown-like 8 ch 0.763, Ganglion 4 ch 0.719, midline Fz+Cz 0.719, glasses brow 0.606 | `confusion-detector/CHANNELS.md` |
| Best single pair | Cz+O1 at 0.745, beats the whole 4-channel Ganglion set | same |
| Top pairs | every one of the top 12 of 120 pairs contains Cz or Fz | same |
| Cross-context limit | visual-trained detector falls to 0.634 on the same person's auditory task | same, Result 3 |
| Elastic index | `memorypalace-multimodal-moments`, 1,024-dim cosine vector, RRF over BM25 + dense kNN | `hardware-demo/eegdemo/elastic_store.py` |
| Elastic inference id | `.jina-embeddings-v5-omni-small` | same |
| Meta vision model | `muse-spark-1.3` via `https://api.meta.ai/v1/responses`, `input_video` with an `input_image` fallback over 6 MB | `hardware-demo/eegdemo/vision.py` |
| Meta voice model | `muse-voice-transcribe-1.0`, 24 kHz mono, 30 s and 8 MB cap, never indexed | `hardware-demo/eegdemo/voice.py` |

"""
add_false = """| Elastic Workflows or Agent Builder as built | **Not implemented.** `DOCS_sponsor/elastic` says so in its own words: "pitch direction, not implemented claims". Slide 14 labels them NEXT. Keep that label. |
| Meta generating the spoken answer | Meta's documented voice API covers transcription only. The answer audio is the device speech synthesizer. Say it that way. |
| Muse Image in the build | Listed by Meta as available. This project does not use it. |
| Audio transcription of recorded moments | Voice transcription is for the user's spoken question only. Moment audio is not transcribed. |
| Physical Meta glasses | The team does not have them. The pairing handoff into Meta AI is real, the recorder is the phone camera, and the slide says DEMO. |
"""
i = x.index(anchor)
# insert true rows just before the "Not true" header, after the last table row
head = x[:i].rstrip()
x = head + "\n" + add_true + "\n" + x[i:]
j = x.index("| Peak-to-peak as the detection mechanism")
k = x.index("\n", x.index("throws an epoch away. It does not fire anything. |"))
x = x[:k+1] + add_false + x[k+1:]

# asset inventory additions
x = x.replace("| `presentation/SLIDES-VOLORIDGE.md` | The VoloRidge slide source text |",
 "| `presentation/revised-v2/tools/slidegen_lib.py` | Slide XML builders in the deck's own idiom: cards, pills, bars, measured text |\n"
 "| `presentation/revised-v2/tools/slidegen_build.py` | Generates slides 12 to 15. Run it, then copy `out/slideN.xml` into the unpacked deck |\n"
 "| `presentation/revised-v2/tools/baseline_scene.py` | The calibration Manim scene that is in the deck |\n"
 "| `DOCS_sponsor/VoloRidge`, `DOCS_sponsor/elastic`, `DOCS_sponsor/meta` | The sponsor briefs. **These are files, not folders.** Read them before touching a sponsor slide |\n"
 "| `presentation/SLIDES-VOLORIDGE.md` | The VoloRidge slide source text, now partly superseded |")

x = x.rstrip() + """
7. **`DOCS_sponsor/VoloRidge`, `elastic` and `meta` read as empty directories** in some
   listings. They are plain files with no extension. `cat` them.
8. **Text measured against the wrong typeface.** `slidegen_lib.py` carries a Poppins
   advance table and a `fits()` guard that raises at build time. It fired nine times
   during the sponsor-slide rebuild. Every throw was fixed by shortening copy, never by
   dropping below the 18pt floor.
"""

open(p, "w", encoding="utf-8").write(x)
print("handoff patched,", len(x), "chars")
