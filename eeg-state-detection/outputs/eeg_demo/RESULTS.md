# EEG engineering benchmark

**Synthetic data only. No real EEG or insight validation.**

Six calibration blocks; ten held-out blocks in the same virtual session. Each block is 180 s.
Scenarios share three held-out noise seeds for paired controls; the ten blocks are not independent samples.
Burst retrieval: margin >= 0, at most five distinct burst flags per block, one-to-one matching within 1 s.
Candidate coverage is the fraction of scorable window centers, not the full recording duration.

| Model | Scenario | Search | Found / injected | False flags | Gate coverage |
|---|---|---|---:|---:|---:|
| power | mixed | all | 9 / 9 | 0 | 100.0% |
| power | mixed | onset | 3 / 9 | 0 | 11.6% |
| power | independent | all | 9 / 9 | 0 | 100.0% |
| power | independent | onset | 2 / 9 | 0 | 11.6% |
| power | negative | all | 0 / 0 | 0 | 100.0% |
| power | negative | onset | 0 / 0 | 0 | 11.6% |
| power | baseline | all | 0 / 0 | 0 | 100.0% |
| power | baseline | onset | 0 / 0 | 0 | 1.9% |
| tangent | mixed | all | 9 / 9 | 0 | 100.0% |
| tangent | mixed | onset | 3 / 9 | 0 | 11.6% |
| tangent | independent | all | 9 / 9 | 0 | 100.0% |
| tangent | independent | onset | 2 / 9 | 0 | 11.6% |
| tangent | negative | all | 0 / 0 | 0 | 100.0% |
| tangent | negative | onset | 0 / 0 | 0 | 11.6% |
| tangent | baseline | all | 0 / 0 | 0 | 100.0% |
| tangent | baseline | onset | 0 / 0 | 0 | 1.9% |

Stretch interval detection: 24/24 injected stretches recovered, 1 false stretch flags, mean matched IoU 0.900 (required >= 0.5).
All confirmed stretches are exported independently of the burst budget, including stretches with no burst.
The negative scenario contains stretches without bursts; baseline contains neither, but retains artifact controls.

Full report also compares midpoint/end gates, matched-count random active gates, and stretch-only anchors.
See `diagnostic.png` for the first held-out block and `*.events.json` for timeline-ready output.

Neither synthetic classifier is authorized by these results for interpreting real physiology.
