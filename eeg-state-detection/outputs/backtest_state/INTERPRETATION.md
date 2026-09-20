# Signal against noise: the state-change detector, walk-forward

This is the presentation-grade view of the one result in this repository that holds up:
a session-calibrated EEG detector of task engagement versus rest. It is built like a
backtest. For each participant and session the first six blocks are the calibration
period (in sample), the last three are scored out of sample, exactly the split the
original experiments used, with models frozen and hashed before scoring. Every number
here was recomputed from the saved models and equals the value in each experiment's
own report, for all fifteen sessions. Nothing was fitted or tuned for this view.

## What "signal" means here, and what "noise" is

Signal: the detector's margin tracks the labeled task periods in recordings it never
saw. The label is task versus rest, defined by the experiment's own markers, not by us;
it is a proxy for a cognitive state change, not "focus" or "flow". Noise: scalp EEG at
microvolt scale under eye, muscle and drift artifacts, with 72 s of labeled rest per
participant.

## The benchmark: a null that respects the data's structure

Overlapping windows make ordinary p-values invalid, so the reference is a circular
time-shift null: keep each out-of-sample score trace intact, shift it against the
labels by a random amount, recompute the AUROC, 2000 times per session. Because a task
period covers most of an excerpt, a shifted trace can still score well by luck; the
95% intervals reach 0.8. That width is the honest cost of autocorrelation, and it is
why the per-session probabilities matter more than the raw AUROCs.

| Participant | Model | Out-of-sample AUROC, mean | Sessions with P ≤ 0.05 | Whole-task matches | Rest included, of 72 s | Eye-only control AUROC |
|---|---|---:|---:|---:|---:|---:|
| VP002 | power + EMA | 0.925 | 3/3 | 7/9 | 5.4 s | 0.883 |
| VP003 | power | 0.800 | 1/3 | 5/9 | 4.9 s | 0.848 |
| VP004 | power | 0.652 | 1/3 | 0/9 | 13.9 s | 0.522 |
| VP005 | power + EMA | 0.888 | 2/3 | 2/9 | 5.2 s | 0.559 |
| VP006 | power + EMA | 0.669 | 1/3 | 6/9 | 28.0 s | none run |

Eight of fifteen sessions beat the shift null at 0.05; the detector is above 0.5 in
fourteen of fifteen. The signal is real, session-calibrated, and variable across
people, from strong (VP002, VP005) to marginal (VP004, VP006).

## The confound the chart shows on purpose

The orange diamonds are the eye-channel-only control: the same pipeline run on the two
EOG channels, which carry no cortical signal. On VP002 and VP003 the eyes alone reach
0.85–0.88, close to the EEG detector. Reading a digit every two seconds moves the eyes
differently from resting with a fixation cross, so part of the EEG detector's signal on
those participants may be ocular even after the pre-task eye regression. VP005 is the
counter-example: EEG 0.89, eyes 0.56. We cannot claim a purely cortical signal; we can
show where it is and is not explained by eyes. VP006 has no eye control because that
run was scoped to the burst comparison.

## How to read the walk-forward figures

Grey traces are in sample; blue traces are out of sample, right of the divider. Shaded
spans are the true task periods, hatched spans the labeled rest, and the bars at the
top are the intervals the detector returned. In-sample AUROC is 0.80–1.00 everywhere,
which is what a fitted classifier looks like on its own training blocks; only the blue
part is evidence. VP006's traces show the failure mode plainly: the margin stays
positive through most of each excerpt, so returned intervals cover the task and much of
the rest, and whole-task matches (6/9) come cheaply while rest inclusion is 39%.

## What this does not show

The burst branch (brief evoked events) is absent from this view because it never beat
random placement on four participants; that record is in `outputs/burst_diagnostic_dev/`
and `outputs/background_vp006/`. One session's weights never transfer to another. Rest
is too short for an hourly false-alarm rate. Replay EEG describes these public
participants, not anyone filmed with a phone.
