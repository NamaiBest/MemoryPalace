# Walk-forward view of the state-change detector

Saved frozen models rescanned on all nine blocks of every session: the first six blocks are the calibration (in-sample) period, the last three the out-of-sample period, as in the original experiments. AUROC and balanced accuracy use non-overlapping accepted labeled windows. The null circularly shifts each out-of-sample score trace against the labels (2000 draws per session), preserving autocorrelation; the probability is the fraction of shifts scoring at least the observed value.

| Participant | Session | Model | In-sample AUROC | Out-of-sample AUROC | Saved report | Null 95% interval | P(null ≥ observed) | Out-of-sample BA | Whole-task matches | Rest included | Eye-only AUROC |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| VP002 | 1 | smoothed (power_ema) | 0.989 | 0.904 | 0.904 | [0.21, 0.86] | 0.011 | 0.789 | 2/3 | 0.0/24 s | 0.967 |
| VP002 | 1 | power (power) | 0.975 | 0.909 | 0.909 | [0.22, 0.82] | 0.006 | 0.844 | 1/3 | 0.0/24 s | 0.967 |
| VP002 | 2 | smoothed (power_ema) | 1.000 | 0.898 | 0.898 | [0.22, 0.83] | 0.004 | 0.769 | 3/3 | 5.1/24 s | 0.817 |
| VP002 | 2 | power (power) | 1.000 | 0.911 | 0.911 | [0.25, 0.81] | 0.002 | 0.831 | 2/3 | 1.3/24 s | 0.817 |
| VP002 | 3 | smoothed (power_ema) | 0.994 | 0.972 | 0.972 | [0.22, 0.81] | 0.000 | 0.886 | 2/3 | 0.3/24 s | 0.867 |
| VP002 | 3 | power (power) | 1.000 | 0.935 | 0.935 | [0.25, 0.80] | 0.002 | 0.814 | 0/3 | 0.8/24 s | 0.867 |
| VP003 | 1 | power (power) | 0.990 | 0.716 | 0.716 | [0.20, 0.79] | 0.091 | 0.621 | 1/3 | 2.0/24 s | 0.909 |
| VP003 | 2 | power (power) | 1.000 | 0.930 | 0.930 | [0.20, 0.78] | 0.002 | 0.781 | 2/3 | 0.2/24 s | 0.827 |
| VP003 | 3 | power (power) | 0.981 | 0.754 | 0.754 | [0.21, 0.96] | 0.223 | 0.654 | 2/3 | 2.6/24 s | 0.807 |
| VP004 | 1 | power (power) | 0.926 | 0.809 | 0.809 | [0.17, 0.76] | 0.013 | 0.784 | 0/3 | 1.9/24 s | 0.521 |
| VP004 | 2 | power (power) | 0.841 | 0.605 | 0.605 | [0.20, 0.80] | 0.272 | 0.560 | 0/3 | 2.8/24 s | 0.437 |
| VP004 | 3 | power (power) | 0.799 | 0.543 | 0.543 | [0.26, 0.71] | 0.361 | 0.560 | 0/3 | 9.2/24 s | 0.606 |
| VP005 | 1 | smoothed (ema) | 0.997 | 0.726 | 0.726 | [0.22, 0.79] | 0.069 | 0.771 | 1/3 | 3.0/24 s | 0.325 |
| VP005 | 1 | power (power) | 0.995 | 0.731 | 0.731 | [0.21, 0.78] | 0.059 | 0.696 | 0/3 | 3.0/24 s | 0.325 |
| VP005 | 2 | smoothed (ema) | 0.965 | 1.000 | 1.000 | [0.22, 0.87] | 0.000 | 0.798 | 1/3 | 0.0/24 s | 0.495 |
| VP005 | 2 | power (power) | 0.884 | 0.835 | 0.835 | [0.21, 0.82] | 0.021 | 0.809 | 0/3 | 0.0/24 s | 0.495 |
| VP005 | 3 | smoothed (ema) | 0.978 | 0.938 | 0.938 | [0.21, 0.94] | 0.029 | 0.804 | 0/3 | 2.2/24 s | 0.857 |
| VP005 | 3 | power (power) | 1.000 | 0.830 | 0.830 | [0.27, 0.87] | 0.059 | 0.768 | 0/3 | 0.0/24 s | 0.857 |
| VP006 | 1 | smoothed (power_ema) | 1.000 | 0.658 | 0.658 | [0.21, 0.78] | 0.131 | 0.474 | 2/3 | 12.2/24 s | n/a |
| VP006 | 1 | power (power) | 1.000 | 0.616 | 0.616 | [0.24, 0.76] | 0.183 | 0.465 | 2/3 | 12.2/24 s | n/a |
| VP006 | 2 | smoothed (power_ema) | 0.997 | 0.480 | 0.480 | [0.23, 0.75] | 0.546 | 0.550 | 1/3 | 9.9/24 s | n/a |
| VP006 | 2 | power (power) | 1.000 | 0.485 | 0.485 | [0.28, 0.73] | 0.561 | 0.523 | 0/3 | 6.2/24 s | n/a |
| VP006 | 3 | smoothed (power_ema) | 0.921 | 0.871 | 0.871 | [0.18, 0.86] | 0.024 | 0.787 | 3/3 | 5.8/24 s | n/a |
| VP006 | 3 | power (power) | 0.888 | 0.879 | 0.879 | [0.24, 0.78] | 0.004 | 0.770 | 0/3 | 1.4/24 s | n/a |

## Per participant, chosen model, out of sample

| Participant | Model | Mean AUROC | Sessions with P ≤ 0.05 | Whole-task matches | Rest included | Mean eye-only AUROC |
|---|---|---:|---:|---:|---:|---:|
| VP002 | smoothed (power_ema) | 0.925 | 3/3 | 7/9 | 5.4/72 s | 0.883 |
| VP003 | power (power) | 0.800 | 1/3 | 5/9 | 4.9/72 s | 0.848 |
| VP004 | power (power) | 0.652 | 1/3 | 0/9 | 13.9/72 s | 0.522 |
| VP005 | smoothed (ema) | 0.888 | 2/3 | 2/9 | 5.2/72 s | 0.559 |
| VP006 | smoothed (power_ema) | 0.669 | 1/3 | 6/9 | 28.0/72 s | n/a |

The saved-report column is each original experiment's own out-of-sample AUROC; small differences for VP003 and VP004 come from their experiments' own window-selection rules. Whole-task matches require IoU ≥ 0.5 with the task interval. Rest included is labeled rest inside returned intervals, out of 72 s per participant. Eye-only AUROC is the saved eye-channel control of the same experiment; VP006 had none.

Figures: `walkforward_<participant>.png` (score trace over the session clock, calibration then out-of-sample, ground truth shaded, returned intervals as bars) and `summary.png` (out-of-sample AUROC per session against the shift-null interval and the eye-only control).
