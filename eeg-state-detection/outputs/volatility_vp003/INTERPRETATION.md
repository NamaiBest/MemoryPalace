# Decision after testing EEG volatility

**Keep power as the default.** Adding exponentially weighted volatility did not
improve the practical stretch detector under the prespecified comparison. It improved
ranking, but produced more rest flags and more fragments, without matching more tasks.
This tests an EWMA feature extension, not every possible volatility model.

VP003 was selected before inspection and is separate from VP001/VP002. Each of three
sessions used its own six calibration blocks and three held-out blocks. All 30
classifiers were frozen before held-out evaluation. No settings were changed afterward.
See [all results](RESULTS.md) and [locked protocol](../../volatility_protocol.md).

| Same VP003 test windows | Power | Power + changes | Power + changes + EWMA |
|---|---:|---:|---:|
| Mean task/rest AUROC | 0.800 | 0.803 | 0.856 |
| Mean task/rest balanced accuracy | 0.685 | 0.727 | 0.672 |
| Whole task blocks matched | 5/9 | 4/9 | 5/9 |
| Intervals returned | 23 | 25 | 27 |
| Task time covered | 81.7% | 74.1% | 79.6% |
| Rest time included | 4.88 s | 4.88 s | 7.82 s |

AUROC measures ranking across possible decision thresholds; balanced accuracy measures
the actual fixed zero-margin decision. Thus the EWMA model can rank task windows better
while making less useful decisions at the current boundary. This does not license
adjusting the boundary on this test set and calling the result fresh validation.

The change-only model is best on task/rest balanced accuracy in this run, but returns
more fragments, covers less task time and matches fewer complete tasks than power.
That tradeoff does not establish it as the best overall timeline detector.

The harder/easier task result also disfavors this EWMA extension: mean AUROC fell from
0.930 to 0.883, and balanced accuracy from 0.838 to 0.807. No GARCH fitting was added
after the EWMA extension failed the prespecified practical-benefit criterion.

## Why the result remains limited

- Only one fresh participant and nine held-out task blocks; time windows are correlated.
- Only **13 rest windows** remain, versus 171 task windows. Rest windows per session:
  5, 6 and 2. A single rest-window error therefore changes specificity substantially.
- Of 197 labeled task/rest windows, 194 passed EEG quality and 184 were history-ready.
  The common two-second warm-up removes early rest; only 41.4% of labeled dense rest
  centers can be scored. Unscorable rest is not demonstrated correctly rejected rest.
- All models share the same fitting and evaluation windows, so this comparison is
  paired. Different participant/history masks mean the scores cannot be compared
  directly with VP002 as evidence that a code change reduced performance.
- Eye-only task/rest models also rank well (mean AUROC 0.848 without EWMA). The experiment
  does not isolate neural workload from ocular, sensory or motor differences.

## What was implemented

The temporal model retains current log-band-power and adds signed recent changes,
predicted variability of those changes, and deviations normalized by that variability.
The forecast uses earlier differences and is updated only after scoring the current
one. Its half-life is fixed at two seconds. Rejected windows reset history; independent
blocks/sessions never share state. Offline filtering still uses surrounding samples.

Power-only, change-only and EWMA EEG models use the same classifier family, calibration
folds, C grid, accepted windows and three-second segmentation rule. Eye-only power and
EWMA versions are controls; they cannot emit EEG timeline flags.

The burst/ERP model is unchanged. Neither large innovations nor these workload scores
are established aha/P300 events. Replayed EEG is unrelated to a separately filmed user.

## Artifacts and verification

- `session*.task_rest.power_ewma.joblib`: experimental session-specific volatility models.
- `session*.power.events.json`: reference power stretch predictions under the common mask.
- `session*.power_change.events.json` and `session*.power_ewma.events.json`: alternatives,
  not independent evidence to merge with the reference predictions.
- Per-session reports, score plots and trace JSON retain the full held-out results.
- Protocol/source snapshots, acquisition audits, model cards and frozen-model hashes
  record the procedure and preprocessing identity.

All 37 tests pass. Independent weighted sums verify the EWMA moments; perturbation tests
verify that the current shock and future features cannot change an earlier forecast.
Validation confirmed unchanged fitted states and saved files, matched train/test labels
across models, and valid timestamps/provenance in all nine event exports.

The next useful experiment would choose the score boundary and interval persistence
using calibration blocks with more resting data, then test another untouched participant.
VP003 is now known data. This result does not justify replacing the power model or
claiming successful detection of natural cognitive moments.
