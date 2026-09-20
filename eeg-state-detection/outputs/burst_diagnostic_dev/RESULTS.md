# Where existing continuous burst flags fall (development data)

Frozen models and saved outputs from previously inspected participants. Nothing was fitted, tuned or thresholded here. Five flags per 2-/3-back evaluation block, 1.5 s separation, one-to-one matching within ±0.5 s. Recomputed flags were checked against each saved experiment before analysis.

## Flags by category

| Participant | Model | Flags | Target window | Non-target window | Between stimuli | Context margin | One-to-one target matches |
|---|---|---:|---:|---:|---:|---:|---:|
| VP001 | mean_bins | 30 | 4 | 7 | 12 | 7 | 4/36 |
| VP001 | xdawn | 29 | 6 | 12 | 7 | 4 | 6/36 |
| VP002 | mean_bins | 30 | 3 | 3 | 14 | 10 | 3/36 |
| VP005 | mean_bins | 30 | 2 | 2 | 18 | 8 | 2/36 |
| VP005 | zigzag | 30 | 6 | 9 | 9 | 6 | 6/36 |
| VP005 | mean_bins_zigzag | 30 | 3 | 10 | 10 | 7 | 3/36 |

A flag in a target window is not necessarily a one-to-one match: two flags can share one target.

## Observed matches against chance under the same grid, mask, budget and tolerance

| Participant | Model | Observed matches | Accessible targets | Uniform null mean [95% interval] | P(uniform ≥ observed) | Stimulus-blind null mean [95% interval] | P(stimulus-blind ≥ observed) |
|---|---|---:|---:|---:|---:|---:|---:|
| VP001 | mean_bins | 4/36 | 36 | 3.00 [0, 6] | 0.346 | 9.01 [5, 13] | 0.995 |
| VP001 | xdawn | 6/36 | 36 | 3.00 [0, 6] | 0.072 | 9.01 [5, 13] | 0.947 |
| VP002 | mean_bins | 3/36 | 36 | 3.15 [0, 6] | 0.632 | 9.15 [5, 14] | 0.999 |
| VP005 | mean_bins | 2/36 | 30 | 3.63 [1, 7] | 0.901 | 9.40 [5, 14] | 1.000 |
| VP005 | zigzag | 6/36 | 30 | 3.63 [1, 7] | 0.133 | 9.40 [5, 14] | 0.969 |
| VP005 | mean_bins_zigzag | 3/36 | 30 | 3.63 [1, 7] | 0.723 | 9.40 [5, 14] | 1.000 |

Null distributions use 2000 random draws per participant. The uniform null places flags anywhere on the valid grid. The stimulus-blind null places flags only at stimulus onsets, target or not: it is what a detector that finds stimuli but cannot tell targets from non-targets would score. These are descriptive reference points on dependent, overlapping windows, not significance tests.

## Score separation on the continuous grid

| Participant | Model | Median score: target window / non-target window / between / margin | AUROC target vs non-target window | AUROC target window vs background | AUROC stimulus windows vs background | AUROC onset-aligned target vs non-target |
|---|---|---|---:|---:|---:|---:|
| VP001 | mean_bins | -0.07 / -0.03 / -0.08 / -0.03 | 0.485 | 0.510 | 0.519 | 0.780 |
| VP001 | xdawn | -1.13 / -1.17 / -1.10 / -1.16 | 0.522 | 0.519 | 0.503 | 0.432 |
| VP002 | mean_bins | -0.39 / -0.38 / -0.33 / -0.34 | 0.488 | 0.480 | 0.486 | 0.533 |
| VP005 | mean_bins | -0.40 / -0.35 / -0.37 / -0.10 | 0.492 | 0.486 | 0.491 | 0.538 |
| VP005 | zigzag | -0.04 / -0.05 / -0.08 / -0.10 | 0.509 | 0.560 | 0.549 | 0.473 |
| VP005 | mean_bins_zigzag | -0.28 / -0.27 / -0.33 / -0.15 | 0.507 | 0.514 | 0.509 | 0.558 |

Background means grid centres farther than the tolerance from every stimulus, inside or outside the task. Each AUROC is computed within a session (its own classifier) and averaged over the three sessions; pooled values are in report.json. Grid windows overlap heavily, so these AUROCs describe ranking on dependent samples. The onset-aligned column uses one grid centre per marker (within 0.05 s of it) and should track the saved known-onset AUROCs.

## Timing of matched flags

| Participant | Model | Matched flags | Median signed offset (flag − target onset) | Interquartile range |
|---|---|---:|---:|---:|
| VP001 | mean_bins | 4 | -0.07 s | [-0.45, +0.35] s |
| VP001 | xdawn | 6 | +0.01 s | [-0.04, +0.03] s |
| VP002 | mean_bins | 3 | -0.32 s | [-0.38, -0.08] s |
| VP005 | mean_bins | 2 | +0.35 s | [+0.30, +0.40] s |
| VP005 | zigzag | 6 | +0.04 s | [-0.16, +0.16] s |
| VP005 | mean_bins_zigzag | 3 | -0.04 s | [-0.12, +0.10] s |

## Grid composition

| Participant | Blocks | Valid centres | Rejected centres | Target-window centres | Non-target-window centres | Background centres | Accessible targets |
|---|---:|---:|---:|---:|---:|---:|---:|
| VP001 | 6 | 3562 | 242 | 360 | 840 | 2362 | 36/36 |
| VP002 | 6 | 3516 | 292 | 360 | 834 | 2322 | 36/36 |
| VP005 | 6 | 2487 | 1248 | 297 | 656 | 1534 | 30/36 |

See INTERPRETATION.md for what these numbers do and do not support. `flags.csv` lists every flag; `diagnostic.png` shows categories, score distributions and null distributions.
