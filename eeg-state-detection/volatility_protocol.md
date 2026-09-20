# EWMA volatility ablation — locked before VP003 results

Choose VP003, the next participant by ID, before downloading or inspecting it.
VP001/VP002 are known development results and are not fresh evaluation sets.
Source: https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/ .

## Question and comparisons

Does adding temporal volatility to log-band-power improve task/rest classification
or sustained interval detection over power alone? Secondary: 2-/3-back versus
0-back during tasks only. Neither label establishes a mental state or an aha.

Fit five models for each target, separately for each of three VP003 sessions:

1. power: current log-band-power only, the reference model family.
2. power_change: power plus its signed change from the preceding 0.25 s center.
3. power_ewma: power plus signed change, log predicted standard deviation of changes,
   and the standardized innovation relative to the predicted mean change.
4. eog_power: power in the two eye channels, as a confound control.
5. eog_power_ewma: matching temporal features in eye channels only.

The change-only ablation separates any benefit of volatility normalization from
simply adding recent history. These are linear classifier features, not a financial
pricing equation, GARCH fit, or a newly validated ERP/burst detector.

## Data and fixed processing

Keep the previous strict original-BrainVision loader, exact 28 EEG + 2 EOG channel
contract, 200 Hz resampling, separate pre-task ocular regression, and signal-quality
rules. Use the same theta/alpha/beta filters and centered two-second power windows.
The underlying filters are offline/zero-phase: a causal volatility recursion does
not make the overall signal-processing pipeline causal or suitable for live use.

Compute the log-power sequence every 0.25 s for ALL models, for both training and
inference. Select every eighth original grid position for classifier fitting and
quantitative classification evaluation, preserving the old nonoverlapping 2 s grid.
Apply the previous complete-window label rules unchanged. Do not interpolate
invalid feature windows or compress time across rejected windows.

Every independent recording excerpt starts with empty history. Require nine
consecutive valid power centers (a two-second span) before any model scores that
center. The seven earlier power differences initialize the mean/variance forecast
before the current eighth difference is scored. Use population variance with a
fixed standard-deviation floor of 0.01 log-power units per 0.25 s. All subsequent
forecasts use exponentially weighted mean and centered variance, half-life 2 s:

    a = 1 - 2**(-0.25 / 2)
    d_t = log_power_t - log_power_(t-1)
    innovation_t = d_t - mean_(t-1)
    sigma_t = sqrt(max(variance_(t-1), 0.01**2))
    standardized_t = innovation_t / sigma_t
    mean_t = mean_(t-1) + a * innovation_t
    variance_t = (1-a) * (variance_(t-1) + a * innovation_t**2)

Score using the forecast BEFORE updating it with the current difference. The
variance floor applies to the forecast denominator/log feature, not to the stored
variance recursion. No clipping of standardized innovations. Reject any nonfinite
input. Reset history at every invalid center. No state crosses recording excerpts,
folds, calibration/evaluation splits or sessions. No timestamp, position-in-block,
task marker, condition or label is a model input.

Warm-up reduces usable windows, including some pre-task rest. Require the SAME
history-ready windows for all five classifiers in training, evaluation and scanning.
Report exclusions by label, comparing raw EEG-valid counts with history-ready counts.
For continuous metrics, report both all labeled time and scorable-center fractions.
Do not hide early unscorable rest in the interpretation of low rest flag counts.

## Fitting and held-out evaluation

Use first two occurrences of every condition (six early blocks) for calibration,
third occurrence (three late blocks) for evaluation. Keep session-specific weights.
Use two whole-block CV folds, first occurrence of all conditions versus second.
Fit StandardScaler + class-balanced L2 logistic regression; tune C over
[0.01, 0.1, 1, 10] by calibration-fold AUROC, ties selecting first. No other
hyperparameter tuning. Require both classes in each fold; fail rather than loosen
splits/quality. All fitted models and code/protocol hashes are saved before any
held-out scoring. Check fitted in-memory state and saved-file SHA-256 after inference.

Keep segmentation unchanged: margin >=0 continuously for at least three seconds;
negative or invalid centers end an interval. No smoothing, merging or hysteresis
added. Export original-clock replay EEG stretch events, not eye-only events.

Report per-session/per-condition AUROC, AP with prevalence, balanced accuracy,
sensitivity, specificity and quality/history exclusions. Report intervals returned,
one-to-one task-block IoU >=0.5 matches, task/rest coverage and matched onset error.
Compare models within this same participant and accepted windows, not VP002 scores.
Macro-average metrics across sessions descriptively; do not pool margins across
sessions or treat windows as independent replicates. No significance claim.

Before results, define evidence of practical improvement as an increase in mean
task/rest balanced accuracy AND mean AUROC, with no increase in total confirmed
rest-overlap time versus power. Interval matches and fragmentation are additional
checks; meeting the descriptive criterion is not population validation. Compare
against power_change separately before attributing benefit to volatility features.

Keep existing burst/ERP training unchanged. Do not rename an unusual innovation
an aha/P300 or claim it matches the person in the phone recording. Preserve eye
controls: volatility may amplify ocular or muscle artifacts. Only nine held-out
blocks, short nearby rest excerpts, one new person, and temporally correlated
features limit the interpretation. Do not retune after viewing VP003 outcomes.
