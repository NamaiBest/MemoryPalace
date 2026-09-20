# Combined EEG integration replay

Both detectors scan the same EEG excerpts independently; their accepted events form one chronological list per session. Stretches use the selected band-power classifier with exponential smoothing of its margins. The half-life was selected on calibration folds and the classifier weights are the original saved ones. Bursts use an ERP mean-amplitude model calibrated on that same session.

| Session | Stretch model | Stretches | Burst candidates | Bursts overlapping stretches | Bursts outside stretches |
|---|---|---:|---:|---:|---:|
| VP002-nback1 | power_ema (2 s half-life) | 3 | 15 | 6 | 9 |
| VP002-nback2 | power_ema (2 s half-life) | 4 | 15 | 15 | 0 |
| VP002-nback3 | power_ema (0.5 s half-life) | 8 | 15 | 11 | 4 |

Counts describe output volume, not accuracy. This reuses previously inspected VP002 data and is an integration check, not fresh validation. Reliable continuous burst detection remains unestablished.

All confirmed stretches are retained. Up to 5 positive-margin burst candidates per excerpt survive 1.5-second peak separation. Burst search is never gated by stretches. Overlap creates reciprocal navigation links, without combining scores, labels, or confidence.

The 15 stretch events equal the standalone `power_ema` export in `outputs/smoothing_vp002` apart from navigation links. All fitted model states and saved weights remained unchanged during inference. No weights were transferred between sessions or participants.

The 45 burst candidates are identical to those in `outputs/combined_vp002` apart from their stretch links. The burst branch does not depend on which stretch model is loaded.

Each session*.events.json uses its original EEG session clock, with recording IDs and excerpt offsets preserved. Only the last three task-centered excerpts per session were scanned, including 0-back; this is not full-session validation. Colors in timeline.png are review-priority thirds within detector and excerpt, not mental intensity. Confidence remains null.

Replay EEG does not measure or corroborate the person in a separately recorded phone video. No insight/confusion labels or combined accuracy are inferred.
