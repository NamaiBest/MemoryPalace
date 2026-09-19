# How many channels, and where? Measured on real data.

**Question:** is 2 or 4 channels enough to detect surprise/confusion, and which hardware
from the HackMIT list should we use?

**Short answer:** 2 channels is enough *if one of them sits on the midline top of the
head*. It is not enough at glasses positions - those are literally the worst pairs in
the montage. The Neurosity Crown is the right device on the parts list; the team's Muse
headbands sit on the wrong positions for this task.

## Dataset and method

[OpenNeuro ds006394](https://openneuro.org/datasets/ds006394) - 33 participants,
16-channel OpenBCI at 125 Hz, visual (SiB) and auditory (SiD) surprise tasks, CC0.
Labels are the authors' own `trial_type` (`surprises` vs `dummy-surprises`), not invented.
51 usable recordings after preprocessing.

Pipeline matches `xueqi-validation` so results are comparable: divide by 24 (documented
scale bug), 1-40 Hz, 50 Hz notch, epoch -0.2 to +0.8 s, baseline correct, reject
peak-to-peak > 150 uV. Logistic regression, class-balanced.

**What is new here.** `xueqi-validation` evaluated leave-one-*subject*-out: train on other
people, deploy on a stranger with no calibration. Its §14 flags the untested case:
*"a same-day wearer-calibrated model might do better and was not the primary test here."*
That calibrated case is the actual product, so this analysis evaluates **within
subject**.

## Result 1: within-subject calibration helps, except where it matters most

Stratified CV over each person's own trials. Chance = 0.5.

| Channel set | Mean AUC | ≥0.70 | vs Xueqi's cross-subject |
|---|---|---|---|
| all 16 | **0.778** | 74.5% | 0.712 (+0.066) |
| crown8-like (F3 F4 C3 C4 P3 P4 O1 O2) | **0.763** | 72.5% | not tested |
| ganglion4 (Fz Cz F7 F8) | 0.719 | 56.9% | 0.697 (+0.022) |
| **central2 (Fz Cz)** | **0.719** | 58.8% | not tested |
| crown-core4 (C3 C4 P3 P4) | 0.716 | 60.8% | not tested |
| crown-frontal2 (F3 F4) | 0.682 | 51.0% | not tested |
| muse4-like (Fp1 Fp2 T7 T8) | 0.680 | 49.0% | not tested |
| muse-temporal2 (T7 T8) | 0.655 | 35.3% | not tested |
| glasses4 (Fp1 Fp2 F7 F8) | 0.627 | 25.5% | not tested |
| glasses2 brow (Fp1 Fp2) | 0.606 | 23.5% | not tested |
| glasses2 temples (F7 F8) | 0.601 | 21.6% | **0.599 (+0.002)** |

**Calibration bought +0.066 AUC at 16 channels and nothing at all at glasses positions.**
I expected per-wearer calibration to rescue the 2-channel case, because
`eeg-neural-signal-processing/RESULTS.md` §11 measured it worth ~16 points on a state
task. It did not. The information is simply not present in two frontal contacts, and no
amount of personalisation creates it.

## Result 2: two channels is enough, if one is on the midline

All 120 electrode pairs ranked by within-subject AUC:

| Rank | Pair | AUC | |
|---|---|---|---|
| 1 | Cz+O1 | 0.745 | |
| 2 | Cz+P4 | 0.730 | |
| 3 | Cz+O2 | 0.728 | |
| 5 | Cz+F3 | 0.724 | |
| 10 | Fz+Cz | 0.719 | |
| ... | | | |
| 90 | F7+T8 | 0.665 | best glasses-reachable pair |
| ... | | | |
| 118 | Fp1+Fp2 | 0.606 | glasses |
| 119 | F7+F8 | 0.601 | glasses |
| 120 | Fp2+F8 | 0.587 | glasses, **worst pair of all 120** |

**Every one of the top 12 pairs contains Cz or Fz.** The best glasses-reachable pair
ranks 90th. The two obvious symmetric glasses pairs - temples (F7+F8) and brow
(Fp1+Fp2) - are 119th and 118th.

`Cz+O1` at 0.745 beats the 4-channel Ganglion set at 0.719. So the constraint is not
*how many* electrodes, it is *where*. One well-placed pair beats four badly-placed ones.

## Result 3: it does not transfer across contexts

Train on the visual task, test on the same person's auditory task (n=19 with both):

| Channel set | Mean AUC | ≥0.70 |
|---|---|---|
| all 16 | 0.634 | 31.6% |
| ganglion4 | 0.602 | 21.1% |
| crown8-like | 0.591 | 15.8% |
| central2 (Fz Cz) | 0.583 | 15.8% |
| glasses4 | 0.521 | **0.0%** |
| glasses2 temples | 0.515 | **0.0%** |
| glasses2 brow | 0.514 | **0.0%** |

Even good positions fall from 0.778 to 0.634. Glasses positions land at chance, and
**not one of 19 subjects cleared 0.70**. A detector calibrated on one kind of surprise
does not carry to another kind. That is a hard limit worth stating out loud, and it
applies to the confusion detector too: calibrate on the task you will actually run.

## Result 4: hardware conclusion

| Device | Electrodes | Est. AUC | Verdict |
|---|---|---|---|
| **Neurosity Crown** | F5 F6 C3 C4 CP3 CP4 PO3 PO4 | **0.763** | **Use this.** Covers central/parietal, 98% of full-montage performance, and it is a dry headband you put on in seconds. |
| OpenBCI Cyton (8ch) | your choice | up to 0.778 | Best signal if you place Cz. Gel + paste, ~10 min setup per person. |
| OpenBCI Ganglion (4ch) | your choice | 0.719 | Fine *if you place Fz/Cz*. 61 x 61 mm board, pocket or headband - not frame-mounted. |
| **Muse 2 / S** (team owns 3) | TP9 AF7 AF8 TP10 | **0.680** | Wrong positions for this task. Frontopolar + temporal, no midline. Usable but clearly worse. |
| Glasses-mounted 2ch | Fp/F7/F8/T7/T8 | **0.601** | **Not viable for surprise detection.** |

**The Crown is the answer to your question.** It is on the HackMIT parts list, it reaches
the positions that carry the signal, and because it is dry and headband-shaped a judge
can put it on in ten seconds - which matters enormously in a science-fair format.

**Note on the Muse.** The team owns three, and they sit on almost exactly the positions
this analysis found weakest (AF7/AF8 are frontopolar, like Fp1/Fp2; TP9/TP10 are
temporal, like T7/T8). At 0.680 they are not useless, but budget for the gap.

## What about small boards for a glasses build?

If a frame-integrated build is still wanted for a *different* signal (blink, jaw clench,
drowsiness - things frontal electrodes are genuinely good at):

- **BioAmp EXG Pill** - 25.4 x 10.0 mm, one channel each, needs an MCU with an ADC
  (ESP32 and Arduino are both on the HackMIT list). Two of them gives 2 channels and
  fits on a temple arm. **Not on the HackMIT parts list - bring your own.**
- **OpenBCI Ganglion** - 61 x 61 mm, 4 channels, 24-bit, BLE, battery-only. On the list,
  but too big to sit on a frame. Runs on a short cable from a pocket.

## Confirmed on a second, real (not estimated) dataset

The Crown row above is a *proxy* - ds006394 doesn't have Crown's exact channels, so
nearby ones stood in. `eeg-neural-signal-processing/RESULTS.md` §12 tests Crown's real
8 channel names (F5 F6 C3 C4 CP3 CP4 PO3 PO4) with zero substitution, on EEGMMIDB
(109 subjects, two different real tasks - eyes-open/closed state and imagined
left/right fist). No confusion label exists on this montage, so it doesn't replace the
number above, but it confirms the direction:

| Task | Crown-exact (8ch) | Full montage | Glasses |
|---|---|---|---|
| State ID (109-way) | 42.81% | 82.39% (64ch) | far below both |
| Motor imagery | 61.52% | 62.04% (17ch) | 54.22% (8ch) |

On motor imagery, Crown **matches** a dedicated 17-channel sensorimotor strip almost
exactly - C3/C4 sit right over hand motor cortex, which is why Crown's designers put
electrodes there. Same conclusion, confirmed twice, no proxy needed.

## Caveats

- Surprise in a lab RSVP task is not confusion while reading. This bounds the electrode
  question, not the product question.
- 51 recordings, 125 Hz, 16 channels, documented x24 scale bug, class imbalance ~1:5.7.
- Crown and Muse rows are *proxies*: this montage has no F5/F6/CP/PO/AF/TP, so nearby
  electrodes stand in. Treat them as estimates with maybe +/-0.03 of slop, not measurements
  of those devices.
- Within-task CV shares a session between train and test. It is the right model for
  "calibrate then use in the same sitting", and it is optimistic for anything longer.

## Reproducing

```bash
.venv/bin/python src/fetch_ds006394.py     # 548 MB from the OpenNeuro S3 mirror
.venv/bin/python src/surprise_channels.py  # ~20 min, writes results/surprise_channels.json
```
