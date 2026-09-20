# EWMA volatility comparison — fresh VP003

Three independently calibrated sessions; six early training blocks and three late test blocks per session. All models were frozen before held-out scoring. Model comparisons use identical training and test centers.

Power is the reference. Power_change adds signed recent changes. Power_ewma also adds lagged volatility and standardized innovations. Eye-only versions are confound controls and never export EEG events.

## Held-out classification

AUROC measures ranking (0.5 is chance); it is not accuracy. Balanced accuracy uses the fixed zero-margin boundary. AP's reference is the positive prevalence. All quantitative windows are nonoverlapping two-second windows, but their temporal history and shared blocks make them dependent.

### task_rest

| Session | Model | Windows | Positive prevalence | AUROC | AP | Balanced accuracy | Sensitivity | Specificity |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | power | 62 | 0.919 | 0.716 | 0.963 | 0.621 | 0.842 | 0.400 |
| 1 | power_change | 62 | 0.919 | 0.716 | 0.965 | 0.665 | 0.930 | 0.400 |
| 1 | power_ewma | 62 | 0.919 | 0.905 | 0.992 | 0.547 | 0.895 | 0.200 |
| 1 | eog_power | 62 | 0.919 | 0.909 | 0.992 | 0.851 | 0.702 | 1.000 |
| 1 | eog_power_ewma | 62 | 0.919 | 0.877 | 0.988 | 0.751 | 0.702 | 0.800 |
| 2 | power | 63 | 0.905 | 0.930 | 0.993 | 0.781 | 0.895 | 0.667 |
| 2 | power_change | 63 | 0.905 | 0.921 | 0.991 | 0.829 | 0.825 | 0.833 |
| 2 | power_ewma | 63 | 0.905 | 0.901 | 0.989 | 0.772 | 0.877 | 0.667 |
| 2 | eog_power | 63 | 0.905 | 0.827 | 0.975 | 0.711 | 0.754 | 0.667 |
| 2 | eog_power_ewma | 63 | 0.905 | 0.801 | 0.968 | 0.737 | 0.807 | 0.667 |
| 3 | power | 59 | 0.966 | 0.754 | 0.990 | 0.654 | 0.807 | 0.500 |
| 3 | power_change | 59 | 0.966 | 0.772 | 0.991 | 0.689 | 0.877 | 0.500 |
| 3 | power_ewma | 59 | 0.966 | 0.763 | 0.990 | 0.697 | 0.895 | 0.500 |
| 3 | eog_power | 59 | 0.966 | 0.807 | 0.992 | 0.645 | 0.789 | 0.500 |
| 3 | eog_power_ewma | 59 | 0.966 | 0.868 | 0.995 | 0.654 | 0.807 | 0.500 |

Descriptive mean across the three session metrics (no cross-session pooling of scores):

| Model | Mean AUROC | Mean balanced accuracy |
|---|---:|---:|
| power | 0.800 | 0.685 |
| power_change | 0.803 | 0.727 |
| power_ewma | 0.856 | 0.672 |
| eog_power | 0.848 | 0.735 |
| eog_power_ewma | 0.849 | 0.714 |

### high_low

| Session | Model | Windows | Positive prevalence | AUROC | AP | Balanced accuracy | Sensitivity | Specificity |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | power | 57 | 0.667 | 0.882 | 0.938 | 0.776 | 0.816 | 0.737 |
| 1 | power_change | 57 | 0.667 | 0.880 | 0.930 | 0.829 | 0.816 | 0.842 |
| 1 | power_ewma | 57 | 0.667 | 0.805 | 0.877 | 0.737 | 0.842 | 0.632 |
| 1 | eog_power | 57 | 0.667 | 0.679 | 0.745 | 0.658 | 0.737 | 0.579 |
| 1 | eog_power_ewma | 57 | 0.667 | 0.819 | 0.910 | 0.711 | 0.526 | 0.895 |
| 2 | power | 57 | 0.667 | 0.946 | 0.973 | 0.868 | 0.895 | 0.842 |
| 2 | power_change | 57 | 0.667 | 0.929 | 0.959 | 0.816 | 0.895 | 0.737 |
| 2 | power_ewma | 57 | 0.667 | 0.896 | 0.942 | 0.816 | 0.895 | 0.737 |
| 2 | eog_power | 57 | 0.667 | 0.731 | 0.852 | 0.658 | 0.684 | 0.632 |
| 2 | eog_power_ewma | 57 | 0.667 | 0.758 | 0.873 | 0.671 | 0.711 | 0.632 |
| 3 | power | 57 | 0.667 | 0.963 | 0.983 | 0.868 | 0.895 | 0.842 |
| 3 | power_change | 57 | 0.667 | 0.960 | 0.982 | 0.895 | 0.895 | 0.895 |
| 3 | power_ewma | 57 | 0.667 | 0.947 | 0.976 | 0.868 | 0.842 | 0.895 |
| 3 | eog_power | 57 | 0.667 | 0.425 | 0.613 | 0.487 | 0.816 | 0.158 |
| 3 | eog_power_ewma | 57 | 0.667 | 0.445 | 0.628 | 0.461 | 0.658 | 0.263 |

Descriptive mean across the three session metrics (no cross-session pooling of scores):

| Model | Mean AUROC | Mean balanced accuracy |
|---|---:|---:|
| power | 0.930 | 0.838 |
| power_change | 0.923 | 0.846 |
| power_ewma | 0.883 | 0.807 |
| eog_power | 0.612 | 0.601 |
| eog_power_ewma | 0.674 | 0.614 |

## Sustained intervals

Segmentation is unchanged: nonnegative margin for at least three seconds, with no gap filling. A whole task match requires one-to-one IoU ≥ 0.5. Coverage denominators include unscorable time.

| Model | Intervals | Matched task blocks | Task time covered | Rest time included |
|---|---:|---:|---:|---:|
| power | 23 | 5/9 | 81.7% | 4.88/72.00 s |
| power_change | 25 | 4/9 | 74.1% | 4.88/72.00 s |
| power_ewma | 27 | 5/9 | 79.6% | 7.82/72.00 s |

## Prespecified incremental-benefit check

Require higher mean task/rest AUROC and balanced accuracy, with no increase in confirmed rest-overlap time. This descriptive criterion does not establish statistical significance.

- EWMA versus power: ΔAUROC 0.056; Δbalanced accuracy -0.013; Δrest overlap 2.95 s. Meets criterion: no.
- EWMA versus power_change: ΔAUROC 0.053; Δbalanced accuracy -0.055; Δrest overlap 2.95 s. Meets criterion: no.

## Quality and history availability

- task_rest: 197 labeled two-second windows → 194 EEG-valid → 184 history-ready. Negative windows: {'labeled': 26, 'raw_valid': 23, 'history_ready': 13}; positive windows: {'labeled': 171, 'raw_valid': 171, 'history_ready': 171}.
- high_low: 171 labeled two-second windows → 171 EEG-valid → 171 history-ready. Negative windows: {'labeled': 57, 'raw_valid': 57, 'history_ready': 57}; positive windows: {'labeled': 114, 'raw_valid': 114, 'history_ready': 114}.
- Dense task centers: 1349/1349 history-ready (100.0%); 1349 EEG-valid before history warm-up.
- Dense rest centers: 63/152 history-ready (41.4%); 142 EEG-valid before history warm-up.

The history requirement removes early rest. Low rest flag time must not be read as successful rejection of unscorable periods. All models share this mask, so comparisons are paired but absolute rest specificity remains uncertain. Do not compare these numbers directly with VP002.

## Limits and outputs

- One new participant and nine test blocks; temporally correlated observations and very short rest.
- EEG/EOG task separation can reflect ocular, sensory or motor effects; no isolated neural-load claim.
- The EWMA forecast uses past feature windows, but the underlying EEG filters/windows are offline.
- No ERP/burst classifier was retrained. Standardized innovations are not labeled aha or P300 events.
- No parameters were retuned after held-out results. Alternative model exports are not independent evidence.
- Replayed EEG belongs to the dataset participant and is unrelated to the phone video's person.

Artifacts: `protocol_snapshot.json`, `frozen_models.json`, acquisition audits, model cards, fitted models, `session*.report.json`, `session*.diagnostic.png`, per-block trace JSON, and three alternative EEG event exports per session.

Source: [Shin original EEG recordings](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/).
