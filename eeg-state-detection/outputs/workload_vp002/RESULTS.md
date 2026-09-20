# Fresh EEG workload test: VP002

One new participant, three separately calibrated sessions. First six blocks fit each model; last three blocks test it. Every model was saved before any held-out performance was evaluated.

## Nonoverlapping two-second windows

AUROC is ranking discrimination (0.5 is chance), not percentage accuracy. BA is balanced accuracy at the fixed decision boundary. AP should be compared with positive prevalence. The power model is prespecified primary; tangent is the framework comparator; eog_power uses eyes only.

### task_rest

| Session | Model | Windows | Positive prevalence | AUROC | AP | BA | Sensitivity | Specificity |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | power | 69 | 0.870 | 0.909 | 0.983 | 0.844 | 0.800 | 0.889 |
| 1 | tangent | 69 | 0.870 | 0.944 | 0.992 | 0.667 | 1.000 | 0.333 |
| 1 | eog_power | 69 | 0.870 | 0.967 | 0.995 | 0.925 | 0.850 | 1.000 |
| 1 | fixed_theta | 69 | 0.870 | 0.646 | 0.914 | 0.500 | 0.000 | 1.000 |
| 2 | power | 69 | 0.870 | 0.911 | 0.984 | 0.831 | 0.883 | 0.778 |
| 2 | tangent | 69 | 0.870 | 0.931 | 0.990 | 0.547 | 0.983 | 0.111 |
| 2 | eog_power | 69 | 0.870 | 0.817 | 0.972 | 0.756 | 0.733 | 0.778 |
| 2 | fixed_theta | 69 | 0.870 | 0.602 | 0.912 | 0.500 | 0.000 | 1.000 |
| 3 | power | 69 | 0.870 | 0.935 | 0.990 | 0.814 | 0.850 | 0.778 |
| 3 | tangent | 69 | 0.870 | 0.915 | 0.987 | 0.761 | 0.967 | 0.556 |
| 3 | eog_power | 69 | 0.870 | 0.867 | 0.979 | 0.811 | 0.733 | 0.889 |
| 3 | fixed_theta | 69 | 0.870 | 0.500 | 0.865 | 0.461 | 0.033 | 0.889 |

### high_low

| Session | Model | Windows | Positive prevalence | AUROC | AP | BA | Sensitivity | Specificity |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | power | 60 | 0.667 | 0.984 | 0.991 | 0.950 | 1.000 | 0.900 |
| 1 | tangent | 60 | 0.667 | 0.997 | 0.999 | 0.950 | 1.000 | 0.900 |
| 1 | eog_power | 60 | 0.667 | 0.914 | 0.957 | 0.788 | 0.925 | 0.650 |
| 2 | power | 60 | 0.667 | 0.992 | 0.997 | 0.975 | 0.950 | 1.000 |
| 2 | tangent | 60 | 0.667 | 0.998 | 0.999 | 0.988 | 0.975 | 1.000 |
| 2 | eog_power | 60 | 0.667 | 0.971 | 0.987 | 0.912 | 0.875 | 0.950 |
| 3 | power | 60 | 0.667 | 1.000 | 1.000 | 0.988 | 0.975 | 1.000 |
| 3 | tangent | 60 | 0.667 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 3 | eog_power | 60 | 0.667 | 0.971 | 0.987 | 0.825 | 0.950 | 0.700 |

Task/rest includes all three n-back conditions versus nearby rest. High/low compares 2-/3-back versus 0-back during tasks only. Neither isolates neural cognitive load.

## Sustained intervals from marker-free scoring

Require at least three seconds at nonnegative margin (fixed theta retains its original z/hysteresis rule). A task match requires one-to-one interval IoU ≥ 0.5. Fragmented intervals may cover task time without matching a whole task.

| Model | Detected intervals | Matched task blocks | Task time covered | Rest time flagged | Mean onset error, matches only |
|---|---:|---:|---:|---:|---:|
| power | 34 | 3 / 9 | 78.4% | 2.04 / 72.00 s | 2.333 s |
| tangent | 21 | 8 / 9 | 96.4% | 22.20 / 72.00 s | 4.719 s |
| fixed_theta | 1 | 0 / 9 | 0.9% | 0.00 / 72.00 s | n/a s |

## Burst-gate eligibility only

No burst detector was retrained in this experiment. The following counts show which labeled target onsets could be searched after restricting the ERP grid to ±3 seconds around detected stretch onsets. Eligibility is not successful detection; targets need not be spontaneous bursts.

| Gate model | Accessible target markers | Fraction of valid ERP grid searched |
|---|---:|---:|
| power | 12 / 36 | 31.3% |
| tangent | 1 / 36 | 12.2% |
| fixed_theta | 0 / 36 | 0.0% |
| Full grid | 36 / 36 | 100% |

## Limits and artifacts

- Session-specific calibration is required; this does not test transfer of weights between people.
- Only nine held-out task blocks from one new person; windows are correlated even when nonoverlapping.
- Nearby rest totals only 72 seconds. A low rest flag count does not establish an all-day false-alarm rate.
- Eye correction can remove eye-correlated neural activity, and residual ocular/motor/sensory confounds remain.
- Task block labels are behavioral proxies. No aha, confusion, or neural-stretch ground truth exists here.
- This is replayed EEG, unrelated to the person in a separately captured phone video.
- No threshold, feature or preprocessing was retuned after these held-out scores.

`session*.report.json` contains per-condition metrics, quality exclusions and raw held-out scores. `session*.diagnostic.png` shows all score traces. `session*.power.events.json` contains primary replay timeline events; tangent exports are an alternative model output, not additional independent evidence.

`protocol_snapshot.json`, `frozen_models.json`, model cards and acquisition audits record the procedure, hashes, training folds, fitted settings and freeze time.

Source: [original Shin EEG recordings](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/).
