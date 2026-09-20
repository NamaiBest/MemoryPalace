# Decision after the Fourier experiment

**The tested Fourier extension did not improve the detector.** Explicit Fourier power
in three broad bands was similar to the existing band-power classifier; a more detailed
26-bin spectrum was worse. The existing power model remains the baseline. None of these
models demonstrated reliable continuous stretch detection on this participant.

VP004 was selected by ID before inspection. Each of three sessions fitted its own
models on six calibration blocks, then tested three later blocks. All 36 models were
frozen before held-out scoring. No settings were adjusted after seeing these results.
See [full results](RESULTS.md) and [locked protocol](../../fourier_protocol.md).

| Same held-out VP004 windows | Existing power | Fourier, 3 bands | Fourier, 1 Hz bins |
|---|---:|---:|---:|
| Mean task/rest AUROC | 0.652 | 0.657 | 0.578 |
| Mean task/rest balanced accuracy | 0.635 | 0.629 | 0.541 |
| Whole task blocks matched | 0/9 | 0/9 | 0/9 |
| Intervals returned | 32 | 29 | 30 |
| Task time covered | 49.8% | 39.2% | 63.6% |
| Rest time included in intervals | 13.94 s | 5.75 s | 16.68 s |

The narrow-bin model recognizes more task time largely at the expense of rest
specificity: its mean window specificity is only 13.3%. The three-band FFT control
includes less resting time, but it also covers less task time. Neither tradeoff
establishes a better overall event detector.

The higher/lower task-demand comparison also favors existing power: mean AUROC is
0.826 for power, 0.687 for three-band FFT and 0.645 for narrow-bin FFT.

## Why whole-task recovery is zero

A whole-task match requires one predicted interval to overlap a task with IoU ≥0.5.
Quality gaps and brief negative scores split task-like activity into separate intervals.
Even a model covering much of a task can therefore fail the whole-interval match.
The stored traces and plots show this directly; it is not equivalent to seeing no
task-related signal. We deliberately kept the segmentation rule unchanged.

Quality checks accepted 149/198 labeled two-second task/rest windows: 133 task and
only 16 rest windows. Rejections removed 38 task windows and 11 rest windows. At the
dense scanning grid, 77.8% of labeled task centers and 83.7% of rest centers were
scorable. All six feature models share those exact masks, making their comparison
paired, but discarded data and sparse rest limit practical performance estimates.

This participant was harder for every tested model. Comparing these numbers directly
with VP002/VP003 would confound representation with participant and data quality.

## What Fourier changed

The current classifier already uses power in EEG frequency bands. The Fourier version
uses a sliding two-second, periodic-Hann-window real FFT, advanced every 0.25 seconds.
The PSD is integrated over either the same three frequency bands or 26 adjacent
1 Hz intervals spanning 4–30 Hz. Models retain absolute log power, with a fitted
regularized linear classifier. The narrow representation has 728 EEG features versus
84 for broad bands; limited calibration and spectral-estimation variability are
possible explanations for worse generalization, not causes established by this test.

The Fourier branches share a 1–40 Hz continuous prefilter and taper, so their broad
power estimates are not numerically identical to variance after the old three
band-pass filters. Comparing narrow bins against the broad FFT control addresses
whether the extra frequency detail helps independently of that estimator change.

A 0.5 Hz FFT grid does not establish 0.5 Hz resolving power, and a 0.25 s hop does not
establish that event timing accuracy. Window length and tapering impose tradeoffs.
No phase-sensitive ERP, spectral-flux, P300 or spontaneous-aha detector was added.
Reference: [SciPy spectral analysis](https://docs.scipy.org/doc/scipy/tutorial/signal.html#spectral-analysis).

## Artifacts and checks

- `session*.task_rest.fft_bins.joblib`: experimental narrow-spectrum classifiers.
- `session*.power.events.json`, `session*.fft_bands.events.json`, `session*.fft_bins.events.json`:
  alternative stretch predictions from the same EEG, not independent evidence to combine.
- `session*.diagnostic.png`: Fourier spectrograms and all three score traces. Spectrogram
  colors indicate spectral power, not workload or mental intensity; blank regions are rejected.
- Per-block trace JSON, complete per-session reports, model cards, acquisition audits,
  protocol/source snapshots and frozen-model hashes preserve the evidence.

All 42 tests pass. The PSD agrees with SciPy and conserves tapered signal power;
tests verify DC/Nyquist scaling, amplitude scaling, frequency-bin integration, common
time/quality masks, fold isolation, session/preprocessing contracts and unchanged
model state during inference. All 36 saved models and nine event files passed final
hash, timing, provenance and matched-label checks.

Only one fresh participant and nine test blocks were evaluated. Eye-only controls
remain in the report, and other non-neural contributions remain possible. Replayed
EEG is unrelated to the phone-video subject. The next test should address data quality
and calibration of interval boundaries on development data before using another
untouched holdout. VP004's outcomes are now known.
