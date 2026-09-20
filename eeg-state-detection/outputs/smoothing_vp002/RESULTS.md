# Smoothing on the original VP002 band-power models

Exploratory follow-up on previously inspected data. Same nine evaluation blocks, same 28 EEG channels, same preprocessing and exact saved classifier weights. The original raw scores and 34 event exports were reproduced. Only exponential smoothing was added; its half-life was selected on calibration folds before evaluation.

| Session | EMA half-life | Band-power BA | Smoothed BA | Band-power AUROC | Smoothed AUROC |
|---|---:|---:|---:|---:|---:|
| 1 | 2 s | 0.844 | 0.789 | 0.909 | 0.904 |
| 2 | 2 s | 0.831 | 0.769 | 0.911 | 0.898 |
| 3 | 0.5 s | 0.814 | 0.886 | 0.935 | 0.972 |

BA means balanced accuracy on the same nonoverlapping labeled windows.

| Same VP002 data | Original band power | Band power + smoothing |
|---|---:|---:|
| Mean balanced accuracy | 83.0% | 81.5% |
| Mean AUROC | 0.919 | 0.925 |
| Whole task blocks matched | 3/9 | 7/9 |
| Returned intervals | 34 | 15 |
| Task time covered | 78.4% | 86.2% |
| Rest incorrectly included | 2.04/72 s | 5.39/72 s |

Joint improvement criterion met: False. Requires more whole-task matches, no lower mean BA and no extra rest overlap.

The temporary calibration-fold classifiers used the original selected C; the final evaluation classifiers were never refitted. EMA initialization/reset, zero boundary, three-second minimum duration and quality masks were fixed. This differs from the VP005 experiment, which retuned C separately for each pipeline.

These are task/rest proxies from one participant and previously seen evaluation data. No fresh-validation, statistical significance or spontaneous cognitive-event claim. Only 72 seconds of nearby labeled rest limits false-alarm conclusions. Existing eye/motor/sensory confounds remain. Replay EEG does not correspond to the phone-video participant. Alternative event files retain null confidence and separate model identities.
