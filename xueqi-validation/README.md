# MemoryPalace — Cognitive Transition Detection

Independent analysis folder. Does **not** modify anything under
`eeg-neural-signal-processing/`.

## Hypothesis

Certain meaningful cognitive transitions produce transient, measurable
physiological signatures that inexpensive, non-invasive sensors can detect.

We are **not** claiming to read memories, thoughts, or aha moments.

This folder tests a narrower, timestamped proxy: **surprise**.

## Why this dataset

Spontaneous insight has no clean ground-truth clock. Surprise in this
experiment does. If EEG cannot even mark an experimenter-timed surprising
stimulus versus a dummy control, it is a weak ingredient for MemoryPalace.
If it can, EEG is a candidate **component**, not a finished product.

## Dataset

[NEMAR on006394](https://nemar.org/dataset/on006394) /
[OpenNeuro ds006394](https://openneuro.org/datasets/ds006394)
(CC0). Local copy: `on006394/`.

33 participants, 16-channel 125 Hz EEG (OpenBCI GUI v5.0.1), visual (SiB)
and auditory (SiD) surprise tasks. Indicated EEG values are 24× too large;
we divide by 24 as the README and `channels.tsv` require.

Full inventory: [DATASET_NOTES.md](DATASET_NOTES.md).

## Ground truth

`events.tsv` `trial_type`:

- **Event:** `surprises`
- **Control:** `dummy-surprises`

No invented aha labels. Probes are a different event and are not the
detector target.

## Pipeline

Python / MNE / sklearn. Config lives in `src/config.py`.

```
.venv/bin/python src/inspect_dataset.py
.venv/bin/python src/run_all.py
```

Load BIDS EEGLAB → scale correction → 1–40 Hz + 50 Hz notch → epoch
−0.2–0.8 s → locked features → leave-one-subject-out classifiers →
electrode ablation → sliding-window trigger → figures.

## Experiments

1. Event-related waveforms / TFR (is there a visible EEG change?)
2. Epoch classification, LOSO
3. 16 / 8 / 4 / 2 channel sets
4. Continuous trigger with persistence + cooldown (thresholds on train only)
5. Shuffled-label and pre-event negative controls

## Results

**Epoch classification works above chance. Continuous low-FP triggering does not.**

| Setting | Balanced acc. | AUC |
|---|---|---|
| RF, 16 channels, LOSO | 0.65 | **0.75** |
| LogReg, 4 channels (Fz Cz F7 F8) | 0.63 | 0.70 |
| LogReg, 2 temples (F7 F8) | 0.56 | 0.60 |
| Shuffled labels | 0.50 | 0.48 |
| Pre-event features only | 0.50 | 0.50 |

Grand-average surprise−control difference at Cz: **+4.5 µV at 192 ms**.

Strict stream trigger (train-tuned): **~1.5% event detection**, **~29 false
triggers / hour**, ~1.1 s latency when it fires.

Details: [RESULTS.md](RESULTS.md).

## Hardware simulation

HackMIT stocks OpenBCI Ganglion (4-ch) and Cyton (8-ch), plus blank
eyeglass frames. We simulated:

- 16 ch (this dataset)
- 8 frontocentral
- 4 (Fz, Cz, F7, F8)
- 2 temples (F7, F8) — **blank frames**, not Meta Ray-Bans

The 4-channel set still beats chance. Two temples are a thin signal.
EEG-only streaming is not a demo-ready bookmark button.

## Limitations

Lab surprise ≠ insight. 125 Hz OpenBCI, incomplete subjects, class
imbalance, no Pz. See RESULTS.md §14.

## Next step: multimodal fusion

Pupil and cardiovascular signals are the obvious second vote (Salvi et al.
2020 on pupil vs insight reports; digit-span load in ds003838). Plan only,
**no 253 GB download**: [MULTIMODAL_NEXT.md](MULTIMODAL_NEXT.md).

Insight papers (with the usual “association, not unique ID” caveat):
[INSIGHT_LITERATURE.md](INSIGHT_LITERATURE.md).

What this means for the product: [MEMORYPALACE_INTERPRETATION.md](MEMORYPALACE_INTERPRETATION.md).

## Reproducing the analysis

```bash
cd "xueqi-validation"
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/inspect_dataset.py
.venv/bin/python src/run_all.py          # add --skip-trigger to skip the slow stream stage
```

Requires the dataset already present in `on006394/` (git-annex objects
materialized). Random seed: 42. Skipped files: `logs/skipped.json`.
