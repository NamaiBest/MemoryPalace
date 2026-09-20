# Fresh-participant burst comparison: calibration-only background negatives (VP006)

Prespecified on 2026-09-19, after the development diagnostic in
`outputs/burst_diagnostic_dev/` and before any VP006 EEG was loaded by an analysis.
VP006 was downloaded with CRC verification and has not been inspected.

## Question

Does adding calibration-only background negatives to the ERP mean-amplitude
classifier improve marker-free retrieval of n-back target onsets on an untouched
participant, and does either model beat randomly placed flags?

## Data and roles

Shin 2018 dataset A, VP006, three recordings treated as separate sessions. Same
loader, pre-task ocular regression, quality mask, resampling and block roles as all
earlier experiments: the first two blocks of each condition calibrate, the final
three evaluate. Burst arms use 2-/3-back blocks only, because 0-back lacks a
negative class: four calibration and two evaluation blocks per session, 36 target
markers in total. No VP006 data enters any decision after this file is frozen.

## Arms, fitted separately for each session on its calibration blocks only

1. `mean_bins`: the existing baseline, unchanged. Target versus non-target epochs
   from −0.1 to +1.0 s, 1–30 Hz, baseline-corrected; five 200 ms mean-amplitude bins
   over 28 channels; standardized, class-balanced logistic regression; C from
   {0.01, 0.1, 1, 10} by two-fold block-grouped cross-validation on average precision.
2. `mean_bins_background`: identical features, classifier, C grid, folds and
   scoring. The training set additionally contains background epochs from the same
   calibration blocks: grid centres every 0.5 s from 0.1 s whose distance to every
   stimulus onset exceeds 0.5 s and whose epoch passes the same quality mask,
   labeled negative. Groups remain blocks.
3. `eog_bins`: the existing eye-only known-onset control. It does not scan.

## Scanning and selection, identical for arms 1 and 2

0.1 s grid of proposed onsets, 1.1 s epochs, the same quality/edge mask, nonnegative
margins only, 1.5 s peak separation, up to five flags per evaluation 2-/3-back
block, one-to-one matching to target markers within ±0.5 s.

## Endpoints

Primary: one-to-one target matches out of 36, matched fraction of returned flags,
and the probability that uniformly random flags on the same valid grid, with the
same budget, separation and tolerance, match at least as many targets
(2000 draws, seed 19).

Secondary: returned flags within ±0.5 s of any stimulus against the stimulus-blind
null; known-onset AUROC and average precision on the evaluation blocks as the
aligned positive control; signed timing error of matched flags; returned flag
count; quality rejection; flag categories as defined in the development diagnostic.

## Decision rule, fixed now

`mean_bins_background` replaces `mean_bins` as the burst candidate model only if
all three hold on VP006: (a) more target matches than `mean_bins`; (b) matched
fraction of returned flags not lower than `mean_bins`; (c) probability that the
uniform null reaches its match count is at most 0.05. If (a) and (b) hold but (c)
fails, the result is reported as a relative gain within chance and nothing is
adopted. If neither arm satisfies (c), the burst branch remains unvalidated. One
run; no rerun with changed settings on VP006.

## Stretch validation on the same participant, frozen alongside

The chosen stretch approach is fitted per session on calibration blocks exactly as
saved for VP002: `fit_workload` power/task_rest, then `calibrate_smoothing` selects
the EMA half-life from {0.5, 1, 2} s on calibration folds with C fixed. Raw power
and smoothed power are evaluated on all nine evaluation blocks with the existing
metrics: balanced accuracy at zero margin and AUROC on non-overlapping accepted
labeled windows, whole-task matches at IoU ≥ 0.5, task time covered and rest
included. This is fresh validation of the already-chosen approach, not model
selection; no alternative stretch model is fitted and no criterion is applied.

## Freezing and integrity

Protocol and source SHA-256, fitted model files and in-memory hashes are written
before any evaluation block is scored. Evaluation blocks are checked against every
model's training recording IDs and sample hashes. Model state is verified unchanged
after inference.

## Limitations stated in advance

One participant and 36 targets. Overlapping windows are dependent, and the nulls are
descriptive reference distributions, not significance tests. Targets are a task
proxy, not spontaneous insight. Eye, motor and sensory contributions are not
isolated. 72 s of labeled rest cannot establish an hourly false-alarm rate.
