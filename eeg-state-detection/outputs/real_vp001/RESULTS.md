# First real EEG test

**Shin 2018 n-back, VP001. Three separately calibrated sessions.**

In each session, six early task blocks calibrate the models; three later blocks are held out.
No synthetic samples or weights. Recorded marker timestamps retained; no shuffled window split.

## Marker-aligned target/non-target classification

Known stimulus onsets are provided for this positive control. AP chance baseline is the retained target prevalence.

| Session | Model | Clean trials | Targets | AUROC | AP | AP baseline | Balanced accuracy |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | mean_bins | 40 | 12 | 0.753 | 0.661 | 0.300 | 0.679 |
| 1 | xdawn | 40 | 12 | 0.542 | 0.425 | 0.300 | 0.536 |
| 1 | eog_bins | 40 | 12 | 0.545 | 0.348 | 0.300 | 0.589 |
| 2 | mean_bins | 40 | 12 | 0.735 | 0.625 | 0.300 | 0.667 |
| 2 | xdawn | 40 | 12 | 0.399 | 0.367 | 0.300 | 0.494 |
| 2 | eog_bins | 40 | 12 | 0.351 | 0.263 | 0.300 | 0.399 |
| 3 | mean_bins | 40 | 12 | 0.818 | 0.678 | 0.300 | 0.708 |
| 3 | xdawn | 40 | 12 | 0.452 | 0.279 | 0.300 | 0.488 |
| 3 | eog_bins | 40 | 12 | 0.449 | 0.299 | 0.300 | 0.512 |

`eog_bins` uses eye channels only as a confounding control, never for EEG event export.

## Continuous scan without trial timestamps

Up to five candidates per held-out 2-/3-back block, ±0.5 s one-to-one target-onset matching.

| Model | Search | Matched / all target markers | Returned flags | Unmatched flags | Accessible targets | Valid-grid coverage |
|---|---|---:|---:|---:|---:|---:|
| mean_bins | all | 4 / 36 | 30 | 26 | 36 | 100.0% |
| mean_bins | onset | 0 / 36 | 0 | 0 | 0 | 0.0% |
| xdawn | all | 6 / 36 | 29 | 23 | 36 | 100.0% |
| xdawn | onset | 0 / 36 | 0 | 0 | 0 | 0.0% |

Unmatched means not near a labeled target onset; it does not prove absence of other neural activity.

## Sustained stretch rule

The fixed frontal-theta rule returned 0 stretch intervals; 0 / 9 held-out task intervals matched at IoU ≥ 0.5.
Task blocks are behavioral proxies, so this is a task-overlap check rather than validated mental-state detection.
Per-block theta task/rest separation and quality coverage appear in `report.json`.

## Interpretation limits

- One participant, three separately calibrated sessions; no population accuracy claim.
- Pre-task EOG regression may remove eye-correlated EEG and does not remove every artifact.
- Task intervals are workload proxies; target labels are not guaranteed single-trial P300 truth.
- ERP aligned metrics use known markers; continuous scan does not receive trial markers.
- Continuous tests use held-out 2-/3-back excerpts plus rest, not unconstrained daily work.
- EEG and EOG may reflect sensory, motor, and ocular differences; no isolated insight claim.
- No correctness/response-time logs, no complete artifact source separation.
- Filtered window overlap makes window-level observations dependent.

Sources: [dataset and download](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/), [data descriptor](https://doi.org/10.1038/sdata.2018.3).

See `session*.diagnostic.png`, `session*.audit.json`, and `session*.events.json` for evidence and replay outputs.
