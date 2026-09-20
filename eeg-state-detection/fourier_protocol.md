# Sliding Fourier experiment — locked before VP004 results

Select VP004, the next participant by ID, before download or inspection. VP001–003
are known development results. Source: https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/ .

## Question

Does a finer spectral representation improve the session-calibrated sustained
task detector? Filtered band variance already measures frequency-specific power;
a Fourier transform is an alternative representation, not a mental-state detector.
The primary candidate is a 1 Hz-bin power spectrum. A three-band FFT control
distinguishes any benefit of narrower features from a changed power estimator.

Fit six models for each of two targets (task/rest, and pooled 2-/3-back versus
0-back within tasks), separately for each of the three VP004 sessions:

- power: existing log variance after theta/alpha/beta filters (84 EEG features).
- fft_bands: log integrated Fourier PSD in [4,8), [8,13), [13,30) Hz (84 features).
- fft_bins: log integrated Fourier PSD in 26 adjacent [4,5), ... [29,30) Hz bins
  (728 EEG features). This is the prespecified primary candidate.
- eog_power, eog_fft_bands, eog_fft_bins: matching eye-only controls on HEOG/VEOG,
  using exactly the same accepted EEG windows; never export them as EEG events.

## Fixed signal processing

Retain the strict BrainVision channel/unit/marker audit, 200 Hz resampling,
session-specific independent pre-task ocular regression, and workload quality
settings (1–30 Hz check, 120 uV amplitude, 60 uV/sample step, 0.05 uV flatness,
2 s filter/artifact guard). No new artifact thresholds or missing-channel handling.

The power reference uses existing continuous fourth-order zero-phase filters in
4–8, 8–13 and 13–30 Hz. Fourier inputs use a continuous fourth-order zero-phase
1–40 Hz filter after identical artifact interpolation. The two preparations must
have identical quality masks. The broad filter suppresses very slow voltage drift
and out-of-range noise; this and windowing mean FFT band estimates need not equal
the old filtered variances. The fft_bands control shares the fft_bins preparation.

Use two-second, 400-sample centered windows, every 0.25 seconds at scan time.
Within each Fourier window subtract its mean, multiply by a periodic Hann window,
compute a 400-point real FFT with no zero padding, and form a one-sided PSD:

    PSD = abs(rfft((x - mean(x)) * hann))**2 / (fs * sum(hann**2))

Double interior positive-frequency bins, not DC or Nyquist. PSD units are uV²/Hz.
Integrate using sum(PSD bins) * 0.5 Hz, with half-open frequency intervals, then
take natural log with a fixed power floor of 1e-12 uV². Retain absolute power;
no per-window normalization, ratios, entropy, phase or spectral-flux features.
The FFT grid is 0.5 Hz; tapering limits effective spectral resolution. A 0.25 s
hop is not 0.25 s localization precision. This is a sliding window Fourier-power
representation of sustained signals, not validated P300/aha burst timing.

No volatility history warm-up. All models score the identical EEG-valid windows.
Training and quantitative evaluation select every eighth original scan-grid center
to retain nonoverlapping two-second windows. Keep the existing complete-window
task/rest labeling and independent block contexts. Fourier inference receives no
condition, task marker, trial time, label or position-in-task feature.

## Calibration and evaluation

First two occurrences per condition (six early blocks) calibrate each session;
third occurrence (three late blocks) is held out. Use two whole-block calibration
folds: first versus second occurrence across all conditions. Each fold fits its own
StandardScaler and class-balanced L2 logistic regression. For ALL six models,
select C by calibration AUROC over [0.001, 0.01, 0.1, 1, 10], ties taking first.
The extra low C allows stronger regularization of the wider spectral feature set.
No test-driven frequency/window/threshold/regularization changes. Fail rather than
weaken a split lacking a class. Save all 36 model fits, source/protocol hashes and
preprocessing audits before inspecting held-out scores.

Keep interval segmentation unchanged: margin >=0 continuously for at least 3 s;
negative/invalid centers break the interval. No smoothing or gap merging. Report
per-session and per-condition AUROC, AP/prevalence, balanced accuracy at zero,
sensitivity/specificity, class-specific exclusions and scorable center coverage.
Report intervals, one-to-one task IoU >=0.5 matches, task/rest overlap and onset error.
Macro-average session metrics descriptively; do not pool margins across sessions or
treat nearby windows as independent. Compare on VP004 itself, not against VP002/003.

Before viewing results, define practical improvement for fft_bins versus power as
higher mean task/rest AUROC AND balanced accuracy, with no increase in total confirmed
rest-overlap time. Also compare fft_bins versus fft_bands before attributing a gain
to finer frequency features. Report whole-task matches/fragmentation regardless.
This descriptive criterion is not statistical significance or population validation.

Retain all outcomes, including quality failures. Freeze checks compare the same
in-memory objects before/after inference and separately check saved-file SHA-256.
Use EEG-only replay event exports and score plots, plus a Fourier spectrogram for
inspection. Spectrogram colors are spectral power, not workload or mental intensity.

No burst/ERP retraining, no onset-gating claim, no attribution to a separately filmed
person. Eye/sensory/motor confounds, one participant, nine test blocks, short nearby
rest, offline filters and time/frequency tradeoffs limit interpretation. All VP004
test results become known after this experiment; do not tune on them and call it fresh.

Implementation reference: https://docs.scipy.org/doc/scipy/tutorial/signal.html#spectral-analysis
