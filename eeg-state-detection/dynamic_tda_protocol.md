# Bayesian temporal workload and zigzag ERP comparison

Locked before VP005 scores are inspected. VP001–VP004 are development data. The
new participant is selected by ID, not performance. Keep all 28 EEG channels and
the existing separate pre-task EOG regression. No electrode-removal experiment.
Original dataset files remain unchanged. This is a feasibility test on task proxies,
not validation of spontaneous insight, confusion, or P300 presence on every trial.

## Data and isolation

Use all three Shin 2018 VP005 n-back sessions. Each fits its own first six blocks
(two per condition), then tests the final three. All models across all sessions
must be frozen before scoring any test blocks. No parameter selection on test
scores. Group calibration folds by task block. Masks are identical between model
alternatives within each branch. Invalid observations break stretches and reset
temporal inference; never fill rejected regions with confident predictions.

## Stretch experiment

Reuse 2-second theta/alpha/beta log-variance features every 0.25 seconds. Classifier
training and classification metrics use nonoverlapping centers 1, 3, 5, ... seconds.
Fit standardized, class-balanced logistic regression, C in .01/.1/1/10.
Compare power alone, simple exponential smoothing (half-life .5/1/2 seconds), a
Bayesian local-level DLM, and an adaptive-shrinkage switching DLM. Match each with
an eye-only control. Eye models cannot export EEG events.

The DLM observes classifier margins y = latent level + correlated error + small
white error. The level follows a Gaussian random walk. The error follows AR(1),
estimated from within-class residuals on calibration training blocks only; this
models some dependence introduced by overlapping windows. Estimate residual scale
and lag coefficient separately within each fold; clip phi to [0, .98], floor
variance at 1e-4. Use white measurement variance .01 times residual variance,
initial state mean zero and variances [4R, R]. Process variance for the level is
qR per .25-second step, q in .001/.01/.1. The error innovation variance is
R(1-phi^2). Kalman posterior moments give the fixed-DLM estimate.

Adaptive shrinkage is a two-regime Gaussian innovation prior: stable qR versus
changing R. Fixed regime transition matrix [[.98,.02],[.20,.80]]; stationary regime
prior. Use an interacting multiple-model filter, with Gaussian moment matching
within regimes and posterior likelihood weighting. This is approximate Bayesian
adaptive shrinkage toward small temporal changes. It is NOT an implementation of
the horseshoe dynamic-shrinkage process of Kowal et al. No MCMC or posterior
parameter uncertainty is claimed. The exported score is posterior latent-level
mean, with an optional model-conditional standard deviation, not probability of
cognitive workload. Temporal parameters remain frozen during evaluation; only
per-recording state inference updates, restarting after quality gaps.

For each alternative, select C and temporal settings by mean balanced accuracy at
zero across two calibration folds (first versus second occurrence per condition).
Break ties by AUROC, then smaller C and the listed temporal parameter order. Both
folds fit their own scaler, classifier and noise model. Fit the selected model on
all calibration blocks afterward. Nonnegative scores sustained for 3 seconds emit
intervals, with the existing segmentation rule. Evaluate AUROC, balanced accuracy,
whole-task interval IoU matches >=.5, task coverage and labeled-rest overlap.
Descriptive success requires more whole-task matches with no greater rest overlap
and no lower mean balanced accuracy than power; also report comparison with EMA.
No statistical significance claim from three sessions of one participant.

## Burst experiment

Use the same 1–30 Hz, -0.1 to +1 second baseline-corrected EEG epochs as the ERP
baseline. Only 2-/3-back trials have target/non-target labels for fitting/evaluation.
Compare ERP mean_bins, zigzag-only, and concatenated mean_bins+zigzag features;
retain an eye-only mean_bins control. C in .001/.01/.1/1/10 for all models; two
StratifiedGroupKFold calibration folds, random_state 19, select average precision.
All transforms are fixed or fit inside the training folds.

For zigzag features, antialias/resample each 200 Hz epoch to 25 Hz, giving 28 points
in 28-dimensional channel space. Normalize pairwise Euclidean distances by the
epoch's median nonzero distance (shape features intentionally omit absolute amplitude).
Use five overlapping eight-point clouds starting at indices 0,5,10,15,20. At
three fixed radii .75/1/1.25, construct Vietoris–Rips 2-skeletons on each cloud
and on each adjacent cloud union: K0 -> U01 <- K1 -> U12 <- ... <- K4.
Compute actual zigzag H0 and H1 barcodes using Dionysus 2.2.3. Features are nine
stage Betti counts and nine lifetime-count bins for each dimension/radius (108
features). Lifetimes are zigzag-stage units, NOT milliseconds or amplitude.
Close all intervals at stage 9; discard zero-duration intervals. An eight-point
cloud spans .28 seconds; the full descriptor needs the entire 1.1-second epoch.
This representation and window length cannot establish submillisecond detection.

Continuous inference scans all usable proposed onsets every .1 seconds, without
trial markers or stretch gating. Select up to five nonnegative-margin candidates
per 2-/3-back excerpt, at least 1.5 seconds apart. Score one-to-one target-onset
matches within .5 seconds, out of all 36 target markers, plus accepted-grid coverage,
precision of returned flags, and known-onset classification as a separate control.
Do not call unmatched flags proven non-neural activity or identified cognitive
events. Descriptive success means more target matches at the same review budget
without lower precision; report both denominators. Eye-only controls diagnose
possible confounds and never generate EEG events.

## Engineering checks and provenance

Verify Kalman moments against an independent batch Gaussian calculation, AR-error
and adaptive-regime behavior, reset/no-future-observation leakage, and frozen model
state. Verify zigzag H0/H1 on known complexes including a loop that appears and is
filled, plus invariance to channel permutation and positive amplitude scaling.
Record source/protocol/data/model hashes, settings, dependency versions, masks,
scores, metrics, event exports and diagnostic figures. Timelines from alternative
models are comparisons, never independent corroboration. All EEG is replayed and
does not measure the phone-video participant.

References:
- https://arxiv.org/abs/1707.00763 (dynamic shrinkage background; not the exact prior here)
- https://arxiv.org/abs/0812.0197 (zigzag persistence)
- https://mrzv.org/software/dionysus2/tutorial/zigzags.html (implementation)
- https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/ (dataset)
