# Aligned target discrimination by channel set (development data; ERP band 0.5-30 Hz)

Known-onset AUROC on the held-out 2-/3-back blocks of each session, all participants previously inspected. Fixed features fit nothing. Channel-subset classifiers use the existing mean-amplitude-bin pipeline, C grid, block-grouped folds and scoring on the calibration blocks only. No continuous scan and no threshold selection.

| Participant | Session | fixed_pz_p300 | fixed_c4_minus_c3 | fixed_pz_200_400 | fixed_cz_200_400 | fixed_cluster_200_400 | full | midline | c3c4 | Evaluation trials (targets) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| VP001 | 1 | 0.48 | 0.66 | 0.53 | 0.49 | 0.51 | 0.75 | 0.73 | 0.59 | 40 (12) |
| VP001 | 2 | 0.46 | 0.63 | 0.51 | 0.55 | 0.55 | 0.69 | 0.70 | 0.71 | 40 (12) |
| VP001 | 3 | 0.39 | 0.71 | 0.55 | 0.64 | 0.66 | 0.87 | 0.88 | 0.83 | 40 (12) |
| VP002 | 1 | 0.83 | 0.54 | 0.75 | 0.72 | 0.72 | 0.45 | 0.52 | 0.55 | 40 (12) |
| VP002 | 2 | 0.62 | 0.51 | 0.58 | 0.56 | 0.56 | 0.55 | 0.59 | 0.55 | 39 (12) |
| VP002 | 3 | 0.67 | 0.50 | 0.62 | 0.57 | 0.61 | 0.74 | 0.68 | 0.64 | 40 (12) |
| VP005 | 1 | 0.53 | 0.39 | 0.64 | 0.59 | 0.56 | 0.45 | 0.54 | 0.48 | 38 (12) |
| VP005 | 2 | 0.47 | 0.43 | 0.41 | 0.51 | 0.49 | 0.39 | 0.41 | 0.47 | 34 (11) |
| VP005 | 3 | 0.40 | 0.45 | 0.38 | 0.36 | 0.40 | 0.69 | 0.73 | 0.38 | 23 (7) |
| VP006 | 1 | 0.46 | 0.55 | 0.45 | 0.50 | 0.54 | 0.50 | 0.49 | 0.51 | 40 (12) |
| VP006 | 2 | 0.68 | 0.38 | 0.67 | 0.73 | 0.74 | 0.56 | 0.56 | 0.63 | 40 (12) |
| VP006 | 3 | 0.38 | 0.68 | 0.42 | 0.44 | 0.46 | 0.57 | 0.65 | 0.50 | 38 (11) |

| Feature set | Mean AUROC over 12 sessions | Sessions at or above 0.70 | VP001 | VP002 | VP005 | VP006 |
|---|---:|---:|---:|---:|---:|---:|
| fixed_pz_p300 | 0.532 | 1/12 | 0.44 | 0.71 | 0.47 | 0.51 |
| fixed_c4_minus_c3 | 0.535 | 1/12 | 0.67 | 0.51 | 0.42 | 0.53 |
| fixed_pz_200_400 | 0.544 | 1/12 | 0.53 | 0.65 | 0.48 | 0.51 |
| fixed_cz_200_400 | 0.555 | 2/12 | 0.56 | 0.62 | 0.49 | 0.56 |
| fixed_cluster_200_400 | 0.569 | 2/12 | 0.57 | 0.63 | 0.49 | 0.58 |
| full | 0.600 | 3/12 | 0.77 | 0.58 | 0.51 | 0.54 |
| midline | 0.623 | 3/12 | 0.77 | 0.60 | 0.56 | 0.57 |
| c3c4 | 0.570 | 2/12 | 0.71 | 0.58 | 0.44 | 0.55 |

Fixed features (calibration blocks, 24 targets per session; no fitting so these are additional evidence, not training):

| Participant | Session | fixed_pz_p300 calibration AUROC | fixed_c4_minus_c3 calibration AUROC | fixed_pz_200_400 calibration AUROC | fixed_cz_200_400 calibration AUROC | fixed_cluster_200_400 calibration AUROC |
|---|---|---:|---:|---:|---:|---:|
| VP001 | 1 | 0.34 | 0.60 | 0.33 | 0.38 | 0.38 |
| VP001 | 2 | 0.49 | 0.71 | 0.52 | 0.49 | 0.48 |
| VP001 | 3 | 0.52 | 0.56 | 0.55 | 0.60 | 0.61 |
| VP002 | 1 | 0.48 | 0.51 | 0.49 | 0.49 | 0.52 |
| VP002 | 2 | 0.69 | 0.53 | 0.73 | 0.74 | 0.73 |
| VP002 | 3 | 0.76 | 0.58 | 0.73 | 0.70 | 0.71 |
| VP005 | 1 | 0.50 | 0.71 | 0.49 | 0.42 | 0.42 |
| VP005 | 2 | 0.65 | 0.49 | 0.64 | 0.59 | 0.60 |
| VP005 | 3 | 0.48 | 0.42 | 0.48 | 0.48 | 0.48 |
| VP006 | 1 | 0.61 | 0.44 | 0.63 | 0.69 | 0.72 |
| VP006 | 2 | 0.66 | 0.54 | 0.58 | 0.58 | 0.57 |
| VP006 | 3 | 0.41 | 0.48 | 0.43 | 0.45 | 0.45 |

Prespecified rule: midline bins or a fixed feature reach evaluation AUROC >= 0.70 in at least 7 of 12 sessions. **Met: False.**

AUROC on 11–12 targets per session has a standard deviation near 0.1; read the mean and the count of sessions, not single cells. Fixed-feature AUROC below 0.5 means the deflection has the opposite sign from the stated convention. This checks whether an aligned signal exists in a small channel set; it says nothing about marker-free scanning, which failed for VP001 despite an aligned AUROC near 0.78.
