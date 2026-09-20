# Decision after the Bayesian/TDA experiment

**The Bayesian stretch models did not outperform simple smoothing. Zigzag TDA
improved burst retrieval relative to the ERP baseline on this participant, but
absolute performance remains poor.** Keep the existing pipeline as the baseline;
these exports are experimental alternatives, not newly validated cognitive events.

VP005 was selected before inspection. Each of three sessions used six calibration
blocks and three later evaluation blocks. All 36 classifiers and temporal settings
were frozen before any held-out scoring. All 28 EEG channels were retained, and
the existing separate pre-task EOG correction was applied. No settings were changed
after the results. See [full results](RESULTS.md) and the
[locked protocol](../../dynamic_tda_protocol.md).

## Stretch results

| Method | Mean balanced accuracy | Whole-task matches | Rest included, out of 72 s |
|---|---:|---:|---:|
| Power baseline | 0.757 | 0/9 | 3.00 s |
| Simple exponential smoothing | 0.791 | 2/9 | 5.25 s |
| Bayesian DLM | 0.739 | 1/9 | 5.00 s |
| Adaptive Bayesian DLM | 0.781 | 1/9 | 5.25 s |

Simple smoothing gives the best ranking (AUROC 0.888), balanced accuracy and whole-task
recovery among these alternatives. It also flags more rest than the baseline. The
adaptive model improves over the fixed DLM but does not beat the simpler comparator.
None meets the prespecified requirement to improve whole-task matches without
increasing rest overlap or reducing balanced accuracy. These are task/rest proxies,
not direct measurements of sustained cognitive workload.

This comparison fits the classifier regularization separately for each temporal
method using calibration folds. It compares complete calibrated pipelines; changes
cannot be attributed solely to smoothing an identical set of classifier weights.
All EEG methods share the same usable evaluation windows. Quality checks retained
128/170 task windows and only 12/26 rest windows, limiting specificity estimates.

The DLM infers a latent level from the existing classifier margin and models
correlated observation noise with AR(1). Bayesian inference here concerns the latent
state conditional on fitted parameters. The adaptive version uses an interacting
multiple-model approximation with stable/changing innovation variances. It shrinks
most changes while allowing larger ones. This is **not** the published dynamic
horseshoe process, and does not include full Bayesian parameter inference. Posterior
SD is model-conditional uncertainty, not a calibrated mental-state confidence.
Rejected observations remain missing and reset state rather than being bridged.

## Burst results

| Method | Targets matched, out of 36 | Returned flags | Matched fraction of flags |
|---|---:|---:|---:|
| Existing ERP mean-amplitude features | 2 | 30 | 6.7% |
| Zigzag topology alone | 6 | 30 | 20.0% |
| ERP plus zigzag topology | 3 | 30 | 10.0% |

Each method received exactly the same marker-free candidate grid and budget of five
flags per held-out 2-/3-back excerpt. The topology-only model matched two targets in
each session, versus 0/1/1 for the ERP baseline. This passes the deliberately modest
descriptive improvement criterion, but **24 of its 30 flags were unmatched and
30 of the 36 target markers were missed**. Unmatched flags are not proof of absent
neural activity; the labels only identify task targets. The experiment does not
establish above-chance performance statistically or detection of spontaneous insight.

All methods could access 30/36 targets under the shared artifact/edge mask. The
continuous grid rejected 1,248/3,735 candidate windows. Known-onset classification
accepted 95/120 trials, including 30 targets. Mean known-onset AUROC was 0.516 for
ERP, 0.552 for topology and 0.606 for the combination. The combination's better
known-time ranking did not translate into the best continuous retrieval.

The implementation computes actual zigzag persistent homology using Dionysus,
including connected components and loops, with triangles filled in the Rips
complexes. It summarizes five overlapping clouds of multichannel EEG trajectory
points and their adjacent unions at three fixed distance scales. The resulting
108 features describe shape; median-distance normalization intentionally makes
them insensitive to uniform amplitude scaling. Lifetimes are zigzag stage indices,
not microvolts or milliseconds. The descriptor requires a full 1.1-second epoch.

Consequently, this result does not support the premise that zigzag persistence
automatically detects arbitrarily small fluctuations. It tests one concrete
topological representation, not every possible TDA method or burst physiology.

## Eye controls, verification and use

Eye-only workload AUROCs were 0.490–0.566 across methods; eye-only ERP mean AUROC
was 0.492. These controls are weaker here than in previous participants, but do
not prove that residual eye/motor/sensory contributions have been isolated.
Short rest, artifact gaps, dependent windows and one participant limit conclusions.
Results across different participants must not be compared as algorithm gains.

All 65 tests pass. Kalman moments agree with independent batch Gaussian conditioning;
identical adaptive regimes reduce to the ordinary Kalman filter. Tests cover no
future-score leakage, reset on missing data, known zigzag births/fillings, filled
triangles, amplitude/channel-order invariance, calibration separation and frozen
inference. The final artifact check verified all 36 saved model hashes, 21 event
files, nine shared-mask traces and unchanged in-memory fitted states.

Use `session*.stretch.*.events.json` and `session*.burst.*.events.json` to inspect
individual alternatives. Source remains `replayed_eeg`, confidence remains null,
and timestamps preserve the original EEG session clock. Replay EEG does not measure
or corroborate the participant in the phone video. Do not pool alternative model
flags as independent evidence. VP005 is now known data, so further tuning requires
another untouched holdout for a fresh evaluation.
