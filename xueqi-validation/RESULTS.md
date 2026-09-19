# Results — can EEG detect a timed surprise event?

Everything below was computed in this folder from the local copy of
NEMAR **on006394** / OpenNeuro **ds006394**. Machine-readable numbers:
`results/*.json` and `results/*.csv`. Figures: `figures/`.

This is **not** an aha-moment paper. Labels are dataset `trial_type` values.

---

## 1. Dataset

Electrophysiological markers of surprise-induced failures of visual and
auditory awareness (Leong, Chua, Obana, Asplund; CC0).

- 33 participants listed; **56 usable recordings** after skips
- 16 EEG channels, 125 Hz, left-earlobe reference, 50 Hz mains
- Tasks: SiB (visual / `condition=v`) and SiD (auditory / `condition=a`)
- OpenBCI GUI v5.0.1 scale error: values divided by 24, as documented

Skipped (logged in `logs/skipped.json`, not silent):

| Reason | Recordings |
|---|---|
| Missing EEG file | sub-05 SiD, sub-06 SiB, sub-07 SiD, sub-09 SiB, sub-20 SiB, sub-32 SiB |
| Missing events.tsv | sub-26 SiB, sub-27 SiB |
| `.set` channel names `EEG 000`… instead of 10–20 labels | sub-02 SiB, sub-15 SiB |

---

## 2. Experimental question

Can 16-channel OpenBCI EEG distinguish a temporally localized
**surprise-related event** from a time-matched non-surprise control, in a
subject-independent (leave-one-subject-out) evaluation?

---

## 3. Ground-truth definition

Taken from `events.tsv` column `trial_type`. Not recoded.

| Class | Label | Epochs kept |
|---|---|---|
| Event | `surprises` | 1025 |
| Control | `dummy-surprises` | 5865 |

`dummy-surprises` counts match non-surprise behavioral trials (136 vs 24 per
complete recording). Probe events were **not** used as labels.

---

## 4. Preprocessing

See `PLAN.md`. Short version: ÷24 → 1–40 Hz → 50 Hz notch → keep earlobe
reference → epoch −0.2 to +0.8 s → baseline −0.2–0 s → reject peak-to-peak
> 150 µV. Raw `.set`/`.fdt` files were never overwritten.

---

## 5. Feature extraction

Locked before modeling (`src/extract_features.py`): per channel, 0–0.8 s
window, mean / peak / peak latency / RMS / variance / energy, log band power
(delta–low-gamma), theta/alpha, beta/alpha, spectral entropy. 224 features
on 16 channels. Same definitions on the pre-event window for the negative
control.

---

## 6. Models

| ID | Model |
|---|---|
| 0 | Majority class |
| 1 | Logistic regression (L2, balanced, scaler on train fold only) |
| 2 | Random forest (balanced) |
| 3 | HistGradientBoosting (sklearn; sample weights) |

---

## 7. Cross-validation

**Leave-one-subject-out.** Both tasks from the held-out person are test.
No epoch-level random split. Seed 42.

Chance for balanced accuracy and AUC is 0.5.

---

## 8. Full-channel results (16 ch, LOSO mean ± SD)

| Model | Balanced acc. | ROC-AUC | Recall | Specificity |
|---|---|---|---|---|
| Majority | 0.500 ± 0.000 | 0.500 ± 0.000 | 0.00 | 1.00 |
| LogReg | 0.653 ± 0.091 | 0.712 ± 0.120 | 0.647 | 0.660 |
| Random forest | **0.654 ± 0.109** | **0.747 ± 0.116** | 0.467 | 0.841 |
| HistGB | 0.633 ± 0.098 | 0.740 ± 0.103 | 0.365 | 0.900 |

Best full-channel detector: **random forest, LOSO AUC 0.75, balanced accuracy 0.65**.
That is clearly above chance, far from ceiling. Per-subject balanced accuracy
is spread out (see `figures/loso_balanced_accuracy.png`).

ERP check (before ML): grand-average surprise−control difference at Cz is
**+4.5 µV at 192 ms**. Posterior channels (P3, O1, O2) show a ~4 µV mean
difference in the 0.25–0.55 s window. EEG **does** change around the event.
We call this a surprise-related event-related response, not an aha signature.

---

## 9. Reduced-channel results (LogReg LOSO)

| Configuration | Channels | Balanced Accuracy | AUROC | Recall | False Positive Rate |
|---|---|---|---|---|---|
| A all16 | 16 | 0.653 | 0.712 | 0.647 | 0.340 |
| B half8 | Fz Cz F3 F4 F7 F8 C3 C4 | 0.638 | 0.705 | 0.636 | 0.359 |
| C ganglion4 | Fz Cz F7 F8 | 0.625 | 0.697 | 0.609 | 0.360 |
| D glasses2 | F7 F8 | 0.557 | 0.599 | 0.545 | 0.431 |

CSV: `results/electrode_ablation_table.csv`.

A 4-channel frontocentral set stays above chance. The 2-channel temple pair
is only marginally above chance. F7/F8 are plausible on **blank eyeglass
frames**. This is not a claim about Meta Ray-Ban glasses.

---

## 10. Continuous trigger results

Sliding 0.8 s windows, hop 0.2 s, logistic regression, persistence + cooldown.
Operating point (score quantile, consecutive windows k, cooldown) chosen on
**training subjects only**. Held-out subject is never used to pick the threshold.

Two grids were run:

1. **Loose** (q=0.7–0.9, k=1–3, cooldown 2–4 s): LOSO detection rate **0.18**,
   false triggers **~213 / hour**, latency ~0.76 s. Unusable as a bookmark button.
2. **Strict** (q=0.90–0.995, k=2–5, cooldown 4–15 s; target ≤12 false/hour on
   train): LOSO detection rate **0.015**, false triggers **~29 / hour**,
   latency ~1.11 s when anything fired.

Almost every fold selected the strictest candidate (k=5, cooldown 15 s,
quantile 0.995). Even then the 12/hour train cap was often missed, and
test detection collapsed to ~1–2%.

---

## 11. False-trigger rate

**~29 false triggers per hour** at the strict, train-tuned operating point
(SD ~40; some subjects 0, some >100). At the loose point, **~213 / hour**.

MemoryPalace cannot live on this EEG-only surprise detector.

---

## 12. Detection latency

When a surprise was detected in the strict stream, mean latency was
**~1.1 s** after the annotated onset (detection window 0–2 s). Latency is
not the bottleneck. Misses and false alarms are.

---

## 13. Negative controls

| Control | LOSO balanced acc. | LOSO AUC | Interpretation |
|---|---|---|---|
| Majority class | 0.500 | 0.500 | Class imbalance is not the story |
| Shuffled **train** labels, real test labels | 0.499 | 0.477 | No split leakage |
| Pre-event-only features (−0.2–0 s) | 0.499 | 0.503 | The useful information is post-onset, not a slow confound |

If shuffled or pre-event models had beaten chance, we would have stopped and
looked for leakage. They did not.

---

## 14. Limitations

- Surprise in an RSVP/RAP lab task is not insight, error awareness, or a
  real-world “I understand now.”
- 125 Hz, 16 OpenBCI channels, 50 Hz line, documented ×24 scale bug.
- Some recordings are incomplete; two `.set` files used anonymous channel
  names and were skipped.
- Class imbalance 1:5.7; metrics are balanced / AUC for that reason.
- Artifact rejection drops many epochs in noisy subjects (e.g. sub-03).
- No Pz electrode; posterior summary uses P3/P4.
- Low-gamma is 30–40 Hz only.
- Continuous evaluation uses the same features as epochs; a model built
  natively on streams might differ, but would still face the rare-event problem.
- Cross-subject transfer is the hard setting. A same-day wearer-calibrated
  model might do better and was not the primary test here.

---

## 15. What this DOES prove

On this public dataset, with labels the authors actually provided:

1. EEG voltage around annotated surprise onsets differs from time-matched
   controls (visible ERP, ~4–5 µV).
2. A linear or tree model, trained without the held-out person, can classify
   those epochs above chance (AUC ~0.75).
3. That signal survives a 4-channel subset; it is weak on two temple channels.
4. Negative controls are at chance, so the epoch result is not an obvious leak.
5. Turning the same model into a continuous bookmark trigger, with
   persistence and cooldown tuned on training people, does **not** yield a
   low false-alarm stream detector.

---

## 16. What this DOES NOT prove

- Universal cognitive-transition detection
- Memory decoding or thought decoding
- Spontaneous aha detection
- Clinical utility
- That glasses with two dry electrodes will catch insight at HackMIT
- That EEG-alone is a finished MemoryPalace trigger
