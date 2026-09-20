# Background negatives for burst candidates — fresh VP006

One untouched participant, three sessions calibrated separately, all models frozen before scoring. Burst arms scan the marker-free 0.1 s grid of the held-out 2-/3-back blocks with the same mask, budget (5 per block), 1.5 s separation and ±0.5 s matching. Protocol: `background_negatives_protocol.md`.

## Continuous target retrieval

| Arm | Target matches | Returned flags | Matched fraction | Flags near any stimulus | Known-onset AUROC | P(uniform null ≥ matches) | P(stimulus-blind null ≥ matches) |
|---|---:|---:|---:|---:|---:|---:|---:|
| mean_bins | 0/36 | 30 | 0.000 | 2 | 0.472 | 1.000 | 1.000 |
| mean_bins_background | 2/36 | 30 | 0.067 | 14 | 0.540 | 0.834 | 1.000 |

Random-flag references on this participant's own valid grid (2000 draws): uniform placement matches 3.05 targets [95% interval 0–6] and lands 10.5 of 30 flags near a stimulus [6–16]; stimulus-blind placement matches 8.97 [5–14]. Accessible targets under the shared mask: 36/36. Eye-only known-onset AUROC: 0.517.

| Arm | Target window | Non-target window | Between stimuli | Context margin | Mean localization error |
|---|---:|---:|---:|---:|---:|
| mean_bins | 0 | 2 | 14 | 14 | n/a s |
| mean_bins_background | 2 | 12 | 6 | 10 | 0.02 s |

## Prespecified decision

- (a) more target matches than the baseline: True
- (b) matched fraction of returned flags not lower: True
- (c) uniform-null probability at most 0.05: False
- baseline itself beats the uniform null at 0.05: False
- **Adopt background negatives: False**

## Known-onset control by session

| Session | mean_bins AUROC | mean_bins_background AUROC | eog_bins AUROC | Accepted trials (targets) |
|---|---:|---:|---:|---:|
| VP006-nback1 | 0.565 | 0.610 | 0.524 | 40 (12) |
| VP006-nback2 | 0.565 | 0.717 | 0.595 | 40 (12) |
| VP006-nback3 | 0.286 | 0.293 | 0.431 | 38 (11) |

## Chosen stretch approach on the same participant

| Model | Mean AUROC | Mean balanced accuracy | Intervals | Whole-task matches | Task covered | Rest included |
|---|---:|---:|---:|---:|---:|---:|
| power | 0.660 | 0.586 | 38 | 2/9 | 74.1% | 19.82/72 s |
| power_ema | 0.669 | 0.604 | 24 | 6/9 | 83.6% | 28.00/72 s |

Calibration-selected half-lives by session: 0.5 s, 0.5 s, 2 s. Accepted non-overlapping labeled windows: task 171/171, rest 25/27. This validates the already-chosen approach; no alternative stretch model was fitted and no selection was made.

Descriptive nulls on dependent windows are reference points, not significance tests. Targets are a task proxy, not spontaneous insight. Eye, motor and sensory contributions are not isolated. One participant limits every conclusion. Replay EEG does not describe the phone-video participant. See INTERPRETATION.md, report.json, per-session reports, traces, events and plots.
