# Bayesian stretch and zigzag burst comparison — VP005

One previously untested participant, three independently calibrated sessions, nine evaluation blocks. All 36 models were frozen before test scoring. All 28 EEG channels retained, with pre-task ocular correction.

## Stretches

Means of per-session metrics. All alternatives use identical accepted windows. Whole-task matches require IoU ≥ 0.5; counts are out of nine task blocks.

| Model | AUROC | Balanced accuracy | Intervals | Whole-task matches | Task covered | Rest included |
|---|---:|---:|---:|---:|---:|---:|
| power | 0.799 | 0.757 | 24 | 0/9 | 38.4% | 3.00/72.00 s |
| ema | 0.888 | 0.791 | 19 | 2/9 | 52.4% | 5.25/72.00 s |
| dlm | 0.838 | 0.739 | 20 | 1/9 | 36.4% | 5.00/72.00 s |
| adaptive | 0.865 | 0.781 | 21 | 1/9 | 46.3% | 5.25/72.00 s |

DLM is Bayesian local-level inference with correlated observation noise. Adaptive is an IMM approximation with small/large innovation regimes, not the published horseshoe dynamic-shrinkage algorithm. Conditional posterior uncertainty is not cognitive-state confidence.

## Bursts

Known-onset AUROC is a separate positive control. Continuous scanning receives no trial markers or stretch gates. Up to five flags per 2-/3-back excerpt; one-to-one target-onset matching within ±0.5 s.

| Model | Known-onset mean AUROC | Matched targets | Returned flags | Precision against target markers |
|---|---:|---:|---:|---:|
| mean_bins | 0.516 | 2/36 | 30 | 0.067 |
| zigzag | 0.552 | 6/36 | 30 | 0.200 |
| mean_bins_zigzag | 0.606 | 3/36 | 30 | 0.100 |

Zigzag uses actual H0/H1 persistence of five short EEG trajectory clouds and adjacent unions at three fixed radii. The 108 shape features intentionally discard absolute amplitude. They require a full 1.1-second window and do not establish sensitivity to arbitrarily small/brief changes. Unmatched flags are not proven absent neural activity.

## Eye controls and quality

| Eye-only model | Task/rest mean AUROC | Balanced accuracy |
|---|---:|---:|
| eog_power | 0.559 | 0.559 |
| eog_ema | 0.490 | 0.511 |
| eog_dlm | 0.552 | 0.529 |
| eog_adaptive | 0.566 | 0.563 |

Eye-only known-onset ERP mean AUROC: 0.492.
- Rest: 12/26 labeled two-second windows accepted.
- Task: 128/170 labeled two-second windows accepted.

## Prespecified descriptive decisions

A stretch alternative must improve whole-task matches without increasing rest overlap or lowering balanced accuracy. A burst alternative must retrieve more target markers without lower precision at the same maximum budget.

- stretch/ema: criterion met = False.
- stretch/dlm: criterion met = False.
- stretch/adaptive: criterion met = False.
- burst/zigzag: criterion met = True.
- burst/mean_bins_zigzag: criterion met = True.

These are small feasibility comparisons, not statistical significance or spontaneous cognitive-event validation. Task-related eye/motor/sensory signals remain possible. Short nearby rest limits false-alarm estimates; overlapping windows remain dependent despite the DLM's AR noise approximation. Invalid centers stay invalid and reset temporal state. Acquisition/ERP filtering remains offline. No weights transfer between sessions, and replay EEG does not measure the phone-video participant.

Alternative event exports preserve source and model identity and must not be pooled as independent corroboration. Protocol, source hashes, model cards, frozen model hashes, scores, masks, reports and plots accompany this file.
