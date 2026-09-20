# Would fewer channels help the burst branch? No: the aligned signal is weak in any channel set

Question from the user on 2026-09-19: would restricting the ERP classifier to significant
channels, such as the midline, help burst retrieval? This check answers the prerequisite:
does a small channel set carry a usable marker-aligned target signal at all? It uses the
four previously inspected participants, fits nothing on evaluation data, runs no continuous
scan and selects no threshold. Three runs, all reported:

- `channel_check_dev/`: ERP band 1–30 Hz (the pipeline default), two fixed features, three channel subsets.
- `channel_check_dev_descriptor_window/`: same, plus three fixed features at the 0.2–0.4 s window the data descriptor reports as the largest target/non-target difference (frontal, central, parietal).
- `channel_check_dev_highpass05/`: same as the second run with a 0.5 Hz high-pass, to test whether the default 1 Hz high-pass attenuates a P300-width deflection.

## Result

Known-onset AUROC on the held-out 2-/3-back blocks, mean over 12 sessions (4 participants × 3):

| Feature set | Fitted | 1–30 Hz | 0.5–30 Hz | Sessions ≥ 0.70 (1 Hz / 0.5 Hz) |
|---|---|---:|---:|---:|
| Pz mean amplitude 0.3–0.6 s | no | 0.533 | 0.532 | 0 / 1 |
| C4 − C3 mean amplitude 0.2–0.8 s | no | 0.511 | 0.535 | 1 / 1 |
| Pz 0.2–0.4 s (descriptor window) | no | 0.511 | 0.544 | 0 / 1 |
| Cz 0.2–0.4 s | no | 0.551 | 0.555 | 0 / 2 |
| F1 F2 FC1 FC2 Cz CP1 CP2 Pz cluster, 0.2–0.4 s | no | 0.556 | 0.569 | 0 / 2 |
| All 28 channels × 5 bins (current model) | yes | 0.586 | 0.600 | 4 / 3 |
| Midline AFz Cz Pz POz × 5 bins | yes | 0.627 | 0.623 | 3 / 3 |
| C3 C4 × 5 bins | yes | 0.577 | 0.570 | 2 / 2 |

Per participant, midline versus full at 1–30 Hz: VP001 0.75 vs 0.77, VP002 0.58 vs 0.57,
VP005 0.59 vs 0.53, VP006 0.59 vs 0.47.

The prespecified rule, midline or a fixed feature at or above 0.70 in at least 7 of 12
sessions, **was not met in any run**.

## Reading

- **Midline gives a small variance-reduction gain where the full set was at or below
  chance** (VP005, VP006), and nothing on VP001 where the full set already worked. The
  level it reaches on the three weak participants, about 0.59, is far below what
  marker-free retrieval needs: VP001 at 0.78 aligned still retrieved targets at chance.
- **No single-trial P300 amplitude separates targets in any participant.** Every fixed
  feature, including the descriptor's own 0.2–0.4 s window over the sites it names, is
  at 0.51–0.57. This holds on the 24-target calibration blocks as well as on evaluation.
  A grand-average difference across 26 participants does not imply single-trial
  separability at this effect size.
- **The 1 Hz high-pass is not the cause.** Widening the band to 0.5 Hz changed every
  mean by 0.03 or less.
- **VP001's discrimination is distributed and fitted, not a Pz amplitude.** Its fixed
  features are at chance while fitted 28-channel or midline bins reach 0.75–0.77. What
  the classifier uses there is not identified; it need not be a P300.
- **The response hand is not a confound.** The descriptor states that every trial was
  answered with the right hand, index finger for targets and middle finger for
  non-targets. The C4 − C3 feature at 0.51–0.54 agrees. Each stimulus also carried an
  auditory beep and a visual digit, so every trial evokes N100/P200 components; that is
  the stimulus-locked activity the background-negatives arm moved toward on VP006.

## Consequence for the burst plan

Channel selection is not the lever. The ceiling on aligned discrimination is set by the
effect size in single trials, which is near chance for three of four participants in any
channel set and either filter. Of the three options recorded in the handoff, this result
weakens option (a), pooling sessions: more trials sharpen the classifier's estimate but
do not enlarge an effect that a fixed physiological feature already shows to be near
zero. It leaves option (b), changing the endpoint to any stimulus-locked response, as
the only burst endpoint with visible signal, and option (c), stopping, as the honest
default for the hackathon.

All four participants were previously inspected; these are development numbers, not
validation. AUROC on 11–12 targets per session has a standard deviation near 0.1; read
means and session counts, not single cells. See `RESULTS.md` and `report.json` in each
of the three directories.
