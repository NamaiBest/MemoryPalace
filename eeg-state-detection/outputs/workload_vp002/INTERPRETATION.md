# What the fresh workload test establishes

The learned scorers detect task-related differences that the fixed theta rule largely misses.
They are **not yet reliable cognitive-moment detectors**: eye signals also classify the tasks,
and sustained interval boundaries remain problematic.

VP002 was selected by ID before inspection. Each of three sessions fitted its own models
using six calibration blocks and tested on three later blocks. The method and all models
were frozen before held-out scoring. See [full numerical results](RESULTS.md) and
[locked protocol](../../workload_protocol.md).

| Primary power scorer | Held-out result |
|---|---|
| Task versus rest | AUROC 0.909 / 0.911 / 0.935; balanced accuracy 0.844 / 0.831 / 0.814 |
| Higher versus lower n-back demand | AUROC 0.984 / 0.992 / 1.000 |
| Continuous task-like stretches | 34 intervals; 78.4% of task time covered |
| Whole task-interval matches | 3 of 9 at one-to-one IoU ≥ 0.5 |
| Confirmed intervals overlapping labeled rest | 2.04 seconds out of 72 seconds |

AUROC describes ranking, not percentage accuracy. The task/rest evaluation contains
180 task windows and only 27 rest windows across all sessions. All 207 labeled windows
passed quality checks. Although the two-second windows do not overlap, they still share
blocks and one participant; they cannot be treated as 207 independent experiments.

The tangent covariance comparator covers 96.4% of task time and matches 8/9 task blocks,
but flags 22.20/72 seconds of rest. Its high AUROC does not make its zero-margin boundary
well calibrated for interval detection. The power scorer produces less rest overlap but
often breaks one task into several short stretches. We did not optimize thresholds or
gap merging using these held-out traces.

The eye-only control achieves AUROC 0.817–0.967 for task/rest and 0.914–0.971 for higher/lower
demand. That is a major limitation: the experiment does not isolate neural workload from
eye behavior or other task-correlated activity. The EEG models could contain useful neural
information, but these scores do not establish that it adds information beyond eye signals.
Near-task rest is also too short to estimate a practical work-session false-alarm rate.

For the original burst hypothesis, power-model onset gates retain only 12/36 target markers;
tangent gates retain 1/36, while full scanning leaves 36/36 eligible. These are eligibility
counts, not detected bursts. The power model's fragmented intervals create additional
onsets, increasing coverage without demonstrating a real leading-edge relationship.
Keep full burst scanning available; this experiment does not establish a gating advantage.

## What is ready to use

- `session*.task_rest.power.joblib`: session-specific primary task/rest scorers.
- `session*.high_low.power.joblib`: separate task-difficulty scorers, whose interpretation
  applies within this calibration paradigm, not as probabilities of mental intensity.
- `session*.power.events.json`: chronological replay stretch candidates with original
  EEG timestamps, duration, confirmation time, score, review priority and null confidence.
- `session*.diagnostic.png`: task/rest traces and detected intervals for both EEG models
  and the original theta rule.

Tangent exports are alternative predictions from the same recordings, not independent
evidence. The replayed EEG belongs to the dataset participant, not the person in a phone video.
The existing ERP/burst models were not changed in this experiment.

## Verification and next decision

All 32 tests passed. A final object-hash check in the initial run incorrectly compared
an in-memory model with a deserialized copy; serialization alone changed that hash on
a calibration-only reproduction. The corrected check verifies the same object before
and after inference and checks file SHA-256 separately. All 21 model files, held-out
scores, metrics and six event exports were identical on repetition. The first run is
retained; see `verification_notes.json`. This is one held-out experiment repeated for
software verification, not two independent studies.

For the hackathon, the primary replay stream now produces learned stretch candidates,
with the limitations above visible. A later model iteration should select segmentation
settings using whole calibration blocks, preserve the eye-control comparison, and test
on a new participant. VP002's test results are now known and are not a fresh tuning target.
