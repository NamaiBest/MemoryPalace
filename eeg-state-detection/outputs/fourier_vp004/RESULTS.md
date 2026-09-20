# Fourier comparison — fresh VP004

Three separately calibrated sessions; all 36 models frozen before held-out scores. Power uses filtered variance; fft_bands uses Fourier power in the same three bands; fft_bins uses 26 one-Hz bands. Their eye-only controls cannot emit EEG events. All models share the same accepted two-second windows and unchanged three-second segmentation.

## task_rest

AUROC is ranking, not accuracy. AP's reference is the positive prevalence. Balanced accuracy uses the fixed zero-margin decision boundary.

| Session | Model | Windows | Positive prevalence | AUROC | AP | Balanced accuracy | Sensitivity | Specificity |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | power | 48 | 0.896 | 0.809 | 0.966 | 0.784 | 0.767 | 0.800 |
| 1 | fft_bands | 48 | 0.896 | 0.888 | 0.982 | 0.853 | 0.907 | 0.800 |
| 1 | fft_bins | 48 | 0.896 | 0.712 | 0.921 | 0.600 | 1.000 | 0.200 |
| 1 | eog_power | 48 | 0.896 | 0.521 | 0.914 | 0.526 | 0.651 | 0.400 |
| 1 | eog_fft_bands | 48 | 0.896 | 0.572 | 0.935 | 0.491 | 0.581 | 0.400 |
| 1 | eog_fft_bins | 48 | 0.896 | 0.488 | 0.878 | 0.584 | 0.767 | 0.400 |
| 2 | power | 48 | 0.896 | 0.605 | 0.926 | 0.560 | 0.721 | 0.400 |
| 2 | fft_bands | 48 | 0.896 | 0.567 | 0.892 | 0.484 | 0.767 | 0.200 |
| 2 | fft_bins | 48 | 0.896 | 0.493 | 0.901 | 0.565 | 0.930 | 0.200 |
| 2 | eog_power | 48 | 0.896 | 0.437 | 0.896 | 0.460 | 0.721 | 0.200 |
| 2 | eog_fft_bands | 48 | 0.896 | 0.665 | 0.955 | 0.526 | 0.651 | 0.400 |
| 2 | eog_fft_bins | 48 | 0.896 | 0.605 | 0.942 | 0.407 | 0.814 | 0.000 |
| 3 | power | 53 | 0.887 | 0.543 | 0.919 | 0.560 | 0.787 | 0.333 |
| 3 | fft_bands | 53 | 0.887 | 0.514 | 0.900 | 0.550 | 0.766 | 0.333 |
| 3 | fft_bins | 53 | 0.887 | 0.528 | 0.915 | 0.457 | 0.915 | 0.000 |
| 3 | eog_power | 53 | 0.887 | 0.606 | 0.918 | 0.456 | 0.745 | 0.167 |
| 3 | eog_fft_bands | 53 | 0.887 | 0.539 | 0.882 | 0.488 | 0.809 | 0.167 |
| 3 | eog_fft_bins | 53 | 0.887 | 0.234 | 0.811 | 0.489 | 0.979 | 0.000 |

Descriptive means across sessions; scores are not pooled between sessions.

| Model | Mean AUROC | Mean balanced accuracy |
|---|---:|---:|
| power | 0.652 | 0.635 |
| fft_bands | 0.657 | 0.629 |
| fft_bins | 0.578 | 0.541 |
| eog_power | 0.522 | 0.481 |
| eog_fft_bands | 0.592 | 0.501 |
| eog_fft_bins | 0.442 | 0.493 |

## high_low

AUROC is ranking, not accuracy. AP's reference is the positive prevalence. Balanced accuracy uses the fixed zero-margin decision boundary.

| Session | Model | Windows | Positive prevalence | AUROC | AP | Balanced accuracy | Sensitivity | Specificity |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | power | 43 | 0.558 | 0.928 | 0.950 | 0.802 | 0.708 | 0.895 |
| 1 | fft_bands | 43 | 0.558 | 0.838 | 0.870 | 0.717 | 0.750 | 0.684 |
| 1 | fft_bins | 43 | 0.558 | 0.787 | 0.804 | 0.717 | 0.750 | 0.684 |
| 1 | eog_power | 43 | 0.558 | 0.601 | 0.637 | 0.560 | 0.542 | 0.579 |
| 1 | eog_fft_bands | 43 | 0.558 | 0.724 | 0.789 | 0.664 | 0.750 | 0.579 |
| 1 | eog_fft_bins | 43 | 0.558 | 0.719 | 0.779 | 0.712 | 0.792 | 0.632 |
| 2 | power | 43 | 0.651 | 0.921 | 0.957 | 0.808 | 0.750 | 0.867 |
| 2 | fft_bands | 43 | 0.651 | 0.595 | 0.710 | 0.573 | 0.679 | 0.467 |
| 2 | fft_bins | 43 | 0.651 | 0.524 | 0.693 | 0.506 | 0.679 | 0.333 |
| 2 | eog_power | 43 | 0.651 | 0.679 | 0.758 | 0.593 | 0.786 | 0.400 |
| 2 | eog_fft_bands | 43 | 0.651 | 0.624 | 0.754 | 0.570 | 0.607 | 0.533 |
| 2 | eog_fft_bins | 43 | 0.651 | 0.619 | 0.781 | 0.542 | 0.750 | 0.333 |
| 3 | power | 47 | 0.596 | 0.628 | 0.713 | 0.549 | 0.571 | 0.526 |
| 3 | fft_bands | 47 | 0.596 | 0.628 | 0.740 | 0.603 | 0.786 | 0.421 |
| 3 | fft_bins | 47 | 0.596 | 0.624 | 0.730 | 0.559 | 0.750 | 0.368 |
| 3 | eog_power | 47 | 0.596 | 0.231 | 0.463 | 0.338 | 0.571 | 0.105 |
| 3 | eog_fft_bands | 47 | 0.596 | 0.299 | 0.481 | 0.355 | 0.500 | 0.211 |
| 3 | eog_fft_bins | 47 | 0.596 | 0.374 | 0.541 | 0.462 | 0.714 | 0.211 |

Descriptive means across sessions; scores are not pooled between sessions.

| Model | Mean AUROC | Mean balanced accuracy |
|---|---:|---:|
| power | 0.826 | 0.720 |
| fft_bands | 0.687 | 0.631 |
| fft_bins | 0.645 | 0.594 |
| eog_power | 0.504 | 0.497 |
| eog_fft_bands | 0.549 | 0.530 |
| eog_fft_bins | 0.571 | 0.572 |

## Sustained intervals

Whole-task matches require one-to-one IoU ≥ 0.5. Fragmentation, onset offsets, and invalid samples can affect matches even when ranking is good.

| Model | Intervals | Matched task blocks | Task time covered | Rest time included |
|---|---:|---:|---:|---:|
| power | 32 | 0/9 | 49.8% | 13.94/72.00 s |
| fft_bands | 29 | 0/9 | 39.2% | 5.75/72.00 s |
| fft_bins | 30 | 0/9 | 63.6% | 16.68/72.00 s |

## Prespecified comparison

Require higher mean task/rest AUROC AND balanced accuracy, with no extra confirmed rest-overlap time. This is a descriptive decision rule, not statistical significance.

- FFT bins versus power: ΔAUROC -0.074; Δbalanced accuracy -0.094; Δrest overlap 2.74 s. Meets criterion: no.
- FFT bins versus fft_bands: ΔAUROC -0.079; Δbalanced accuracy -0.088; Δrest overlap 10.93 s. Meets criterion: no.

## Quality and limitations

- task_rest: 149/198 labeled windows accepted; negative counts {'labeled': 27, 'accepted': 16}, positive counts {'labeled': 171, 'accepted': 133}.
- high_low: 133/171 labeled windows accepted; negative counts {'labeled': 57, 'accepted': 53}, positive counts {'labeled': 114, 'accepted': 80}.
- Dense task centers: 1049/1349 accepted (77.8%).
- Dense rest centers: 128/153 accepted (83.7%).
- One new participant, nine test blocks and short nearby rest. Even nonoverlapping windows share blocks and remain dependent.
- No per-person weight transfer: each session has its own calibration. Eye, motor and sensory contributions remain possible.
- The 0.5 Hz FFT grid and 0.25 s hop do not establish that spectral or event localization precision. Hann tapering broadens spectral peaks.
- Two-second features are for sustained task patterns; no new ERP/P300/aha burst detection or gating result is claimed.
- No parameters were tuned after these results. Replayed EEG does not correspond to a separately filmed person.

Artifacts: protocol/source snapshots, frozen model hashes, acquisition audits, model cards, per-session reports, per-block score/spectrogram traces, diagnostic plots and three alternative EEG event exports per session. Do not merge model alternatives as independent evidence.

References: [Shin dataset](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/), [SciPy spectral analysis](https://docs.scipy.org/doc/scipy/tutorial/signal.html#spectral-analysis).
