# Learned workload experiment — locked before VP002 results

This is the next experiment after the VP001 feasibility test. VP001 is development
history, not a fresh test set. Choose **VP002**, the next participant by ID, before
downloading it or inspecting its signals. Do not choose participants by results.
Original source: https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/ .

## Questions and split

1. Primary engineering question: can a session-calibrated EEG scorer distinguish
   n-back task periods from nearby rest and emit sustained task-like intervals?
2. Specificity check: can a separately trained scorer distinguish pooled 2-/3-back
   from 0-back, using task periods only? Task/rest separation alone is insufficient
   evidence of cognitive workload; visual, motor and eye activity also differ.

Use all three VP002 sessions, fitting separate weights in each. For each condition,
the first two occurrences are calibration and the third is evaluation: six early
blocks versus three late blocks. Use the existing strict marker/channel/unit audit,
independent pre-task EOG regression, 200 Hz resampling and nonoverlapping block
contexts. No VP001 weights transfer. The learned procedure is being tested on a new
participant, but each model still uses that participant's session calibration.

## Fixed features and training

- Preserve 28 EEG channels, bands 4–8, 8–13, 13–30 Hz, fourth-order zero-phase
  Butterworth filters, and existing 1–30 Hz quality checks (120 uV amplitude,
  60 uV/sample step, 0.05 uV flatness, 2 s artifact/edge guard). No ERP prototypes.
- Use centered 2 s windows. Training and quantitative classification evaluation
  use a nonoverlapping 2 s grid. Continuous inference uses a 0.25 s grid.
- Task labels require the entire window within [task start + 2 s, task end − 2 s].
  Rest labels require it within [task start − 8 s, task start − 4 s] or
  [task end + 4 s, task end + 8 s]. Everything else remains unlabeled.
  High/low labels use task windows only: 0-back=0, 2-/3-back=1.
- Primary model: log variance per band/channel, training-fitted StandardScaler,
  class-balanced L2 logistic regression. Comparator: centered Ledoit–Wolf covariance
  per band, one training-fitted affine-invariant tangent reference per band,
  StandardScaler, same classifier. No surrounding-window subtraction for sustained
  activity. Fit both feature models for both label definitions.
- Eye-only control: the same log-band-power classifier on HEOG/VEOG, using exactly
  the EEG-accepted windows. It is a confound diagnostic and cannot export EEG flags.
- C grid [0.01, 0.1, 1, 10], select mean calibration-fold AUROC (ties: first grid
  value). Two folds: first occurrence of every condition versus second occurrence.
  Keep whole blocks together and refit every learned transform inside each fold.
  Require both classes in training and validation; fail rather than weaken splits.
- Freeze and save all session models and preprocessing audits before evaluating
  any held-out block. Save protocol and source-code hashes before the run.

## Scores, intervals and reporting

Linear decision margins are uncalibrated scores, not probabilities or mental
intensity. Enter a stretch at margin >= 0; require consecutive valid nonnegative
centers spanning at least 3 s, close on a negative/rejected center or recording end.
No extra score smoothing, gap filling, or threshold selection from test data.
Record estimated onset, confirmation, end and peak score. Rank intervals by peak
within each model/type; export replay provenance and original recording timestamps.
Inference takes samples and acquisition metadata, never task markers or trial labels.

For each session and scorer report AUROC, AP and positive prevalence, balanced
accuracy at zero, sensitivity/specificity and quality exclusions on nonoverlapping
held-out labeled windows. Report task/rest performance per task condition, plus the
separate high/low result. Include the previous theta scorer and its fixed threshold
as a comparator on these same fresh data. Do not pool margins between sessions.

For task/rest EEG scorers and the fixed theta rule, report number of intervals,
one-to-one task interval matches at IoU >= 0.5, task/rest time coverage, and onset
errors for matched intervals. Also report onset-gate target accessibility (+/−3 s
around detected onset, +/−0.5 s target tolerance) on valid ERP grid positions in
2-/3-back evaluation blocks. This is only candidate eligibility, not burst detection
or an improvement in the existing ERP classifier. Keep burst training unchanged.

Use plots of score traces with evaluation labels as an audit. Preserve all results,
including failed quality gates, weak discrimination, excess intervals and empty
outputs. Do not retune after viewing VP002 evaluation scores. Do not treat overlapping
scan positions as independent samples or calculate a significance claim from them.
No neural stretch ground truth, insight/confusion labels, cross-person transfer,
full-day false-positive rate, or correspondence to the phone video is established.
The short near-task rest excerpts limit specificity and false-alarm assessment.
