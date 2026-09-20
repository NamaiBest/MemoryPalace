import os
p = os.path.expanduser("~/mnt/HackMIT/PRESENTATION-HANDOFF.md")
x = open(p, encoding="utf-8").read()
i = x.index("## 4. Slide inventory")
j = x.index("## 5. The claims ledger")
S4 = """## 4. Slide inventory, current state

Twenty slides. Re-verified against the live file on 2026-09-20, second pass.

| # | Slide | Notes |
|---|---|---|
| 1 | Title, "Revisit & Reflect / Mental Health is Physical Wealth" | Full-bleed title card, `image1.png` |
| 2 | "Ever walked into a room..." | Semantic overload framing |
| 3 | The 36-second film | `media1.mp4` |
| 4 | "Sense it. Capture it. Come back to it." | Crown / glasses / app flowchart |
| 5 | "The field chased the hard problem." | SEED and Wang citations. **Says 30-90 s calibration; the ledger says 120 s. Reconcile.** |
| 6 | "Remember one detail. Get the whole moment back." | The app |
| 7 | **Healthcare 1**, everyday reflection and children | New. Carries a WHAT WE DO NOT CLAIM strip |
| 8 | **Healthcare 2**, dementia and a trusted clinician | New. Carries the honest-limits card |
| 9 | Calibration animation | `media2.mp4` |
| 10 | "Start by learning your normal" | |
| 11 | "Removing signal noise" | `media3.mp4`, **trimmed to start 2 s in**; poster is the final frame |
| 12 | "Every check uses data it has never seen" | Retitled. Subtitle "Fresh samples reduce false alarms." Synthetic fixture |
| 13 | "Five datasets. One question." | BED removed; Shin card is now double width |
| 14 | "84 numbers. Eight electrodes." | Electrode ladder, **percentages on the n = 38 basis** |
| 15 | **"Two questions. Two datasets."** | New. Per-participant and per-electrode tables |
| 16 | Elastic | Workflows and Agent Builder labelled NEXT |
| 17 | Meta | Six verticals with status pills |
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

"""
x = x[:i] + S4 + x[j:]
open(p, "w", encoding="utf-8").write(x)
print("patched", len(x))
