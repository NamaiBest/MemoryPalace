# PLAN — MemoryPalace surprise-EEG validation

All work stays in this folder (`xueqi-validation/`).
Teammate code under `eeg-neural-signal-processing/` is read-only for inspiration
and is never modified.

Dataset semantics are in [DATASET_NOTES.md](DATASET_NOTES.md). That document is
the label contract. If code and notes disagree, the notes win until the notes
are updated from the files.

---

## Question

Can 16-channel OpenBCI EEG detect a temporally localized, experimentally defined
surprise event (`trial_type == surprises`) versus a time-matched non-surprise
control (`trial_type == dummy-surprises`)?

This is a hardware-reality check for MemoryPalace, not a claim about insight.

---

## Ground truth (frozen before modeling)

| Class | `events.tsv` `trial_type` | Typical n / recording |
|---|---|---|
| Event (positive) | `surprises` | 24 |
| Control (negative) | `dummy-surprises` | 136 |

No other labels. Probe events are ignored for the detector. Behavioral
hit/miss is not the EEG target.

---

## Pipeline (run order)

```
python src/inspect_dataset.py
python src/run_all.py
```

`run_all.py` calls, in order:

1. `preprocess.py` — load EEGLAB BIDS EEG, divide by 24, 1–40 Hz bandpass,
   50 Hz notch, keep original left-earlobe reference, reject extreme epochs.
2. `extract_events.py` — read `events.tsv`, keep only surprise/dummy-surprise,
   drop onsets outside the recording, write a skip log.
3. `event_analysis.py` — grand-average ERP, difference waves, TFR, channel
   summaries. This runs **before** classification so we can see whether EEG
   actually changes around the event.
4. `extract_features.py` — fixed, a-priori feature set (no test-driven
   selection).
5. `train_classifier.py` / `evaluate.py` — majority baseline, logistic
   regression, random forest, histogram gradient boosting. Leave-one-subject-out.
6. `electrode_ablation.py` — all 16 / 8 / 4 / 2 channels.
7. `continuous_trigger.py` — sliding windows, persistence + cooldown, threshold
   tuned on training subjects only.
8. `make_figures.py` — publication/demo figures.

Random seed: 42 (`src/config.py`).

---

## Preprocessing decisions (and why)

| Step | Choice | Why |
|---|---|---|
| Scale | ÷ 24 | Dataset README / `channels.tsv` units `microV/24` |
| Filter | FIR 1–40 Hz | DC/drift out; 125 Hz Nyquist is 62.5 Hz; keep below line harmonics |
| Notch | 50 Hz | Sidecar `PowerLineFrequency`, not 60 Hz |
| Reference | keep left earlobe | Physically valid; average-ref is an optional ERP overlay only |
| Bad channels | none auto-dropped globally | 16 ch, no author bad-channel list; per-epoch peak-to-peak reject instead |
| Epoch | −0.2 to +0.8 s | Surprise ERP window; min ISI > 5 s so no overlap |
| Baseline | −0.2 to 0 s | Pre-event only |
| Reject | \|peak-to-peak\| > 150 µV after scaling | Obvious artifact; logged per recording |
| Preserve raw | yes | Original `.set`/`.fdt` never overwritten |

These are **not** copied from the teammate auditory-biometric pipeline
(4 s rest windows, 200 Hz, 60 Hz, different labels).

---

## Features (locked before seeing test metrics)

Defined in `src/config.py` / `src/extract_features.py`.

Time domain, post-event 0–0.8 s, per channel:

- mean amplitude, peak amplitude, peak latency, RMS, variance, signal energy

Frequency domain, same window, Welch:

- delta 1–4, theta 4–8, alpha 8–13, beta 13–30, low-gamma 30–40 Hz
- theta/alpha, beta/alpha
- spectral entropy

Low-gamma is truncated by the 40 Hz low-pass and 125 Hz sampling. It is **not**
a full gamma analysis.

No feature is added or dropped after looking at held-out subjects.

---

## Models

| ID | Model | Notes |
|---|---|---|
| 0 | Majority class | Chance floor for accuracy; balanced accuracy should be 0.5 |
| 1 | Logistic regression | L2, class_weight=balanced, scaler fit on train fold only |
| 2 | Random forest | class_weight=balanced |
| 3 | HistGradientBoosting | sklearn; XGBoost not required |

Evaluation: **leave-one-subject-out**. Epochs from the same person never appear
in both train and test. Both tasks (SiB, SiD) from a held-out subject go to test.

Metrics: accuracy, balanced accuracy, precision, recall, F1, ROC-AUC, confusion
matrix; mean and SD across subjects; per-subject distribution.

---

## Channel sets (hardware-honest)

| Config | Channels | Why |
|---|---|---|
| A all16 | Fp1 C3 Fp2 C4 Fz Cz O1 O2 F7 F8 F3 F4 T7 T8 P3 P4 | Full dataset montage |
| B half8 | Fz Cz F3 F4 F7 F8 C3 C4 | Frontocentral surprise / P3a-like coverage |
| C ganglion4 | Fz Cz F7 F8 | 4-ch board in the same 10–20 space as OpenBCI Ganglion |
| D glasses2 | F7 F8 | Temple contact on **blank eyeglass frames**, which HackMIT stocks |

D is **not** a claim that F7/F8 can be mounted on Meta Ray-Ban glasses.
Those are sealed. See teammate hardware notes; we do not repeat a false claim.

---

## Continuous trigger

MemoryPalace is a stream, not a trial classifier.

For each LOSO fold:

1. Train the chosen model on other subjects' epochs.
2. On training subjects' continuous recordings only, sweep
   (threshold quantile, consecutive-window count k, cooldown).
3. Freeze the operating point.
4. Run on the held-out subject.
5. Score: detection rate, misses, false triggers / hour, mean latency,
   bookmarks / hour.

A detection is a trigger within 0–2 s after a `surprises` onset.
Triggers elsewhere are false.

---

## Negative controls

1. Shuffle labels within each training fold, evaluate on real test labels
   (must fall to chance; else leakage).
2. Train/test using **pre-event only** features (must be near chance; else
   the “event” is actually a slow confound or leaked timing).
3. Majority baseline.

---

## Outputs

- `results/*.json`, `results/*.csv`
- `figures/*.png`
- `logs/skipped.json`
- `RESULTS.md` written from the JSON after the run
- `MEMORYPALACE_INTERPRETATION.md`

---

## Isolation / reproducibility

- pathlib only; no machine-specific absolute paths
- `requirements.txt`
- seeds in one config file
- skipped files logged
- labels never rewritten
- teammate folder untouched
