# Smoothing on the same VP002 recordings

**Smoothing improves recovery of long task intervals, but reduces balanced accuracy
and includes more resting time. It is a tradeoff, not an overall improvement.**

This comparison uses the exact saved classifiers behind the original 81–84%
band-power result. Same participant, same three sessions, same nine evaluation
blocks, same 28 EEG channels, same preprocessing, same thresholds and same
classifier weights. The original raw scores were reproduced to 1e-12 and all three
original event files were reproduced byte for byte.

| Metric | Original band power | Band power + smoothing |
|---|---:|---:|
| Mean balanced accuracy | 83.0% | 81.5% |
| Mean AUROC | 0.919 | 0.925 |
| Whole task blocks matched | 3/9 | 7/9 |
| Returned intervals | 34 | 15 |
| Task time covered | 78.4% | 86.2% |
| Rest incorrectly included, out of 72 s | 2.04 s | 5.39 s |

The smoother joins some short score dips into longer positive regions. It can also
keep a score above zero for longer after activity declines. The result is less
fragmentation but worse rest rejection on average. Mean task sensitivity rises
from 84.4% to 88.9%, while rest specificity falls from 81.5% to 74.1%. AUROC improves
slightly even though the fixed zero-margin decision rule becomes less accurate.

The effect varies by session. Balanced accuracy changes from 84.4% to 78.9%,
83.1% to 76.9%, and 81.4% to 88.6%. Calibration selected smoothing half-lives of
2 seconds, 2 seconds and 0.5 seconds respectively. Every alternative used the
same 207 evaluation windows: 180 task and 27 rest windows.

For context, the earlier covariance/tangent model on these same recordings matched
8/9 tasks while including 22.20 seconds of rest. Smoothed band power achieves 7/9
with 5.39 seconds of rest, but unsmoothed band power still includes the least rest
and has higher mean balanced accuracy. The covariance numbers are the preserved
earlier result, not a newly fitted comparator in this run.

Half-life selection used temporary classifiers fitted inside the original whole-block
calibration folds, with the original selected regularization held fixed. Those
temporary fits never replaced the original evaluation classifiers. All three
smoothing settings were frozen before evaluation. This isolates smoothing's effect
on the original models; the VP005 comparison instead retuned classifier regularization
separately for each temporal method.

All 67 tests pass. The original and wrapped model states and saved files stayed
unchanged, quality masks remained identical, and rejected windows reset smoothing.
Three fitted wrappers, six event files, nine score traces, acquisition audits,
model cards, source/protocol hashes and three diagnostic plots accompany the result.

VP002 was already inspected, so this is an exploratory follow-up, not fresh
validation. Task labels are proxies for workload, and short rest plus one participant
limits false-alarm conclusions. Residual ocular/motor/sensory confounds remain.
These replayed EEG events do not measure a separately filmed phone-video participant.
No existing default or original result was overwritten.

See [full results](RESULTS.md) and [selection protocol](../../smoothing_vp002_protocol.md).
