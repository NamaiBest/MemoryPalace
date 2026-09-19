# Multimodal next step — do not download ds003838 in full

## Dataset

OpenNeuro **ds003838** (v1.0.2)

Pavlov, Y. G., Kasanov, D., Kosachenko, A. I., Kotyusov, A. I., & Busch, N. A.
(2022). Pupillometry and electroencephalography in the digit span task.
*Scientific Data.*

- OpenNeuro: https://openneuro.org/datasets/ds003838
- Paper: https://www.nature.com/articles/s41597-022-01542-9
- PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC9206021/

Title on OpenNeuro: “EEG, pupillometry, ECG and photoplethysmography, and
behavioral data in the digit span task and rest.”

**Do not download the full dataset automatically.** Current snapshots are on
the order of **~100 GB of EEG alone** in some indexes, and the user-facing
figure of **~253 GB** for the full multimodal tree is large enough to fill a
laptop. This file is a plan, not a downloader.

---

## What it contains (from the data descriptor)

| Modality | Approx. n | Format | Notes |
|---|---|---|---|
| Behavior | 86 | TSV | All participants |
| EEG | 65 | EEGLAB `.set`, 64 ch, 1000 Hz | 19 excluded for cap layout; 3 technical |
| ECG + PPG | 83 | EEGLAB `.set` on AUX | Wrist ECG, finger PPG |
| Pupillometry | 84 | TSV (Pupil Labs, 120 Hz) | No rest-pupil block |

Tasks: 4 min eyes-closed rest, then auditory digit span (memory vs passive
listen; loads 5 / 9 / 13; SOA 2 s).

License: check the OpenNeuro snapshot (commonly CC0 for this accession).

---

## What this dataset is for (and is not)

**Is:** complementary information about **changing cognitive demand**
(encoding / load / overload) across EEG, pupil, and cardiovascular signals.

**Is not:** an aha-labeled dataset. Digit span has no insight self-report.
Do not recode high load as “cognitive transition” without saying so.

MemoryPalace hypothesis this would test:

> EEG, pupil, and ECG/PPG carry non-redundant information about shifts in
> cognitive demand. Fusion should beat the best single modality on
> load-change detection, under subject-independent evaluation.

---

## Download a small subset only

Use OpenNeuro’s AWS public bucket or `openneuro-py` / DataLad. Pull
**metadata + 4–6 complete multimodal subjects**, not 86.

Example subject filter (adjust after reading `participants.tsv` for who has
all three of EEG, ECG, pupil):

```bash
# metadata only (tiny)
aws s3 sync --no-sign-request \
  s3://openneuro.org/ds003838/ \
  ds003838-meta \
  --exclude "*" \
  --include "dataset_description.json" \
  --include "participants.tsv" \
  --include "participants.json" \
  --include "README*" \
  --include "task-*_events.json"

# then, after choosing IDs that have eeg+ecg+pupil, e.g. sub-001:
aws s3 sync --no-sign-request \
  s3://openneuro.org/ds003838/sub-001 \
  ds003838/sub-001
```

Inspect `participants.tsv` first. The descriptor lists missingness:

- no pupil: sub-017, sub-094
- no ECG/PPG: sub-017, sub-037, sub-066
- no EEG: sub-013 … sub-031, sub-037, sub-066 (cap layout error)

Prefer subjects **with EEG + pupil + ECG/PPG**. Start with 4 subjects
(~a few GB, not 253 GB). If that pipeline works, add 10 more.

Also possible: `openneuro-py download --dataset ds003838 --include sub-001`.

---

## Planned analyses (after a subset exists)

Target: **memory vs listen**, and/or **load 5 vs 13**, time-locked to digit
onsets. Still subject-independent (GroupKFold / LOSO).

Features (locked a priori):

- EEG: same band-power / entropy family as this surprise pipeline, plus
  frontal theta (classic WM).
- Pupil: baseline-corrected diameter, slope, blink rate.
- ECG/PPG: HR, RMSSD / HF-HRV, pulse amplitude.

### Ablation matrix

| Condition | Inputs |
|---|---|
| EEG only | 64-ch or a glasses-plausible subset |
| Pupil only | diameter features |
| ECG/PPG only | HR / HRV / PPG amp |
| EEG + pupil | concat features |
| EEG + pupil + ECG/PPG | full fusion |

Report balanced accuracy, AUC, and — more important for MemoryPalace —
**false triggers per hour** on a sliding-window load-change detector, with
threshold fit on training subjects only.

Negative controls: shuffled labels; rest-only EEG (should not separate
digit-load conditions).

---

## Why wait

on006394 already answers the first pre-HackMIT question (can EEG mark a
timed surprise?). ds003838 is the **second** question (do other cheap sensors
add anything?). Mixing them before the surprise pipeline is done would blur
both claims.
