# Aligned target discrimination by channel set (development data)

Known-onset AUROC on the held-out 2-/3-back blocks of each session, all participants previously inspected. Fixed features fit nothing. Channel-subset classifiers use the existing mean-amplitude-bin pipeline, C grid, block-grouped folds and scoring on the calibration blocks only. No continuous scan and no threshold selection.

| Participant | Session | fixed_pz_p300 | fixed_c4_minus_c3 | full | midline | c3c4 | Evaluation trials (targets) |
|---|---|---:|---:|---:|---:|---:|---:|
| VP001 | 1 | 0.51 | 0.62 | 0.75 | 0.74 | 0.52 | 40 (12) |
| VP001 | 2 | 0.57 | 0.49 | 0.74 | 0.69 | 0.72 | 40 (12) |
| VP001 | 3 | 0.45 | 0.62 | 0.82 | 0.82 | 0.76 | 40 (12) |
| VP002 | 1 | 0.63 | 0.49 | 0.59 | 0.64 | 0.62 | 40 (12) |
| VP002 | 2 | 0.60 | 0.51 | 0.52 | 0.53 | 0.52 | 39 (12) |
| VP002 | 3 | 0.59 | 0.44 | 0.59 | 0.56 | 0.58 | 40 (12) |
| VP005 | 1 | 0.56 | 0.41 | 0.44 | 0.61 | 0.45 | 38 (12) |
| VP005 | 2 | 0.53 | 0.52 | 0.40 | 0.44 | 0.43 | 34 (11) |
| VP005 | 3 | 0.40 | 0.41 | 0.76 | 0.71 | 0.63 | 23 (7) |
| VP006 | 1 | 0.48 | 0.54 | 0.57 | 0.54 | 0.57 | 40 (12) |
| VP006 | 2 | 0.66 | 0.34 | 0.57 | 0.69 | 0.67 | 40 (12) |
| VP006 | 3 | 0.42 | 0.76 | 0.29 | 0.54 | 0.45 | 38 (11) |

| Feature set | Mean AUROC over 12 sessions | Sessions at or above 0.70 | VP001 | VP002 | VP005 | VP006 |
|---|---:|---:|---:|---:|---:|---:|
| fixed_pz_p300 | 0.533 | 0/12 | 0.51 | 0.61 | 0.50 | 0.52 |
| fixed_c4_minus_c3 | 0.511 | 1/12 | 0.58 | 0.48 | 0.45 | 0.54 |
| full | 0.586 | 4/12 | 0.77 | 0.57 | 0.53 | 0.47 |
| midline | 0.627 | 3/12 | 0.75 | 0.58 | 0.59 | 0.59 |
| c3c4 | 0.577 | 2/12 | 0.67 | 0.57 | 0.50 | 0.56 |

Fixed features (calibration blocks, 24 targets per session; no fitting so these are additional evidence, not training):

| Participant | Session | fixed_pz_p300 calibration AUROC | fixed_c4_minus_c3 calibration AUROC |
|---|---|---:|---:|
| VP001 | 1 | 0.42 | 0.50 |
| VP001 | 2 | 0.63 | 0.65 |
| VP001 | 3 | 0.52 | 0.52 |
| VP002 | 1 | 0.41 | 0.43 |
| VP002 | 2 | 0.65 | 0.56 |
| VP002 | 3 | 0.72 | 0.56 |
| VP005 | 1 | 0.48 | 0.69 |
| VP005 | 2 | 0.63 | 0.40 |
| VP005 | 3 | 0.38 | 0.40 |
| VP006 | 1 | 0.61 | 0.42 |
| VP006 | 2 | 0.54 | 0.51 |
| VP006 | 3 | 0.39 | 0.49 |

Prespecified rule: midline bins or a fixed feature reach evaluation AUROC >= 0.70 in at least 7 of 12 sessions. **Met: False.**

AUROC on 11–12 targets per session has a standard deviation near 0.1; read the mean and the count of sessions, not single cells. Fixed-feature AUROC below 0.5 means the deflection has the opposite sign from the stated convention. This checks whether an aligned signal exists in a small channel set; it says nothing about marker-free scanning, which failed for VP001 despite an aligned AUROC near 0.78.
