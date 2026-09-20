# Combined EEG integration replay

Both detectors scan the same EEG excerpts independently; their accepted events form one chronological list per session. Stretches use the existing power/task-rest model. Bursts use an ERP mean-amplitude model calibrated on that same session.

| Session | Stretches | Burst candidates | Bursts overlapping stretches |
|---|---:|---:|---:|
| VP002-nback1 | 10 | 15 | 8 |
| VP002-nback2 | 11 | 15 | 14 |
| VP002-nback3 | 13 | 15 | 9 |

Counts describe output volume, not accuracy. This reuses previously inspected VP002 data and is an integration check, not fresh validation. Reliable continuous burst detection remains unestablished.

All confirmed stretches are retained. Up to 5 positive-margin burst candidates per excerpt survive 1.5-second peak separation. Burst search is never gated by stretches. Overlap creates reciprocal navigation links, without combining scores, labels, or confidence.

The 34 existing stretch events were reproduced exactly apart from navigation links. All fitted model states and saved weights remained unchanged during inference. No weights were transferred between sessions or participants.

Each session*.events.json uses its original EEG session clock, with recording IDs and excerpt offsets preserved. Only the last three task-centered excerpts per session were scanned, including 0-back; this is not full-session validation. Colors in timeline.png are review-priority thirds within detector and excerpt, not mental intensity. Confidence remains null.

Replay EEG does not measure or corroborate the person in a separately recorded phone video. No insight/confusion labels or combined accuracy are inferred.
