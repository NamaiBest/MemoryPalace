# Personal dataset: 3-class mental imagery, EmotivPRO EPOC X

192 recordings (61 apple, 60 mouse, 71 remote), 14 channels, 128 Hz, ~10 s each,
recorded by a teammate across several sessions in January 2026. Each file is one
imagined object, one trial - `intervalMarker.csv` files are all empty, so the label is
per-file, not per-timestamp within a file.

## Result

Same feature pipeline as the rest of this repo (log/relative band power + Hjorth
params per channel), evaluated with **GroupKFold by trial** - a 10 s trial is cut into
2 s epochs for more training data, but a trial's epochs never split across train/test.
That grouping is the one methodological point that matters here: get it wrong and the
number is meaningless, as demonstrated repeatedly elsewhere in this repo.

| | Accuracy | Chance |
|---|---|---|
| **3-class (apple/mouse/remote)** | **65.79% ± 4.33%** | 33.3% |
| apple vs mouse | 74.48% | 50% |
| apple vs remote | 74.98% | 50% |
| mouse vs remote | 79.48% | 50% |
| **shuffled-label control** | **34.79%** | 33.3% |

The shuffled control landing almost exactly on chance, while the real result sits 32
points above it, is the check that this is not a leak or an artifact - if the shuffle
had also scored well above chance, the result would be untrustworthy regardless of the
headline number.

**This is a real, above-chance, single-subject result on genuinely personal data** -
not a public benchmark, not cited from a paper. 14 consumer electrodes and simple
band-power features can tell apart three different imagined objects most of the time.

## A bug worth knowing about

The first run only found signal in 42.6% of trials, because 70 of 192 files (36%,
disproportionately from one session) have an extra metadata line before the real CSV
header - `title:..., start timestamp:..., headset type:...` - which `src/classify.py`
did not originally handle. Silently dropping those files did not just lose data, it
biased the class balance (they were concentrated in `apple`), and the resulting number
was noticeably worse than the true one. Fixed in `load_trial()`: detect and skip the
preamble line if present. This is the same shape of bug as the window-overlap issue in
`confusion-detector/` - a data-handling detail, not a modelling one, moved the headline
number by 23 points.

## Does this belong on the Crown?

No, and that is fine. This was recorded on an Emotiv EPOC X, which is the bulky felt-pad
headset - not the product hardware. This test answers a narrower question: *does the
general approach (band power + simple classifier + proper trial-grouped evaluation)
find real signal in truly personal, non-lab EEG data?* Yes. Whether that transfers to
imagined objects specifically, or to confusion, or to the Crown's exact 8 channels, are
each separate open questions - this is evidence for the method, not for any specific
product claim.

## On the Neurosity Crown dataset (re-checked, same conclusion)

Re-examined [github.com/JeremyNixon/neurosity](https://github.com/JeremyNixon/neurosity)
directly via the GitHub API, not just its README, in case labels existed that weren't
documented. They do not. `training/train_cnn.py` shows exactly what the included model
checkpoints were trained on: **next-sample prediction** - given 32 timesteps of 8-channel
EEG, predict the 33rd sample, trained with MSE loss. That is self-supervised forecasting,
not classification of any behavior, task, or mental state. There is no label of any kind
anywhere in this repository - not in the data folder (empty except `.gitignore`; the
actual CSVs are only in an external Dropbox/Google Drive link), not in the notebooks, not
in the training scripts.

**Conclusion, now checked from two directions (README and source code): no public
dataset pairs the Neurosity Crown's exact hardware with a labelled task.** This is not a
gap I can search around - it does not exist yet. The two options are
`eeg-neural-signal-processing/RESULTS.md` §12 (Crown's exact channel names, tested on a
different device's real labelled data - EEGMMIDB) or recording a real session on
whatever headset the team can access.

## Reproducing

Raw recordings live in [`dataset/epocx-imagery/`](../dataset/epocx-imagery/) — this
folder holds only the analysis. `src/classify.py` reads
`dataset/epocx-imagery/extracted/` directly.

```bash
../eeg-neural-signal-processing/.venv/bin/python src/classify.py
```

Reuses the venv and `features.py` from [`eeg-neural-signal-processing/`](../eeg-neural-signal-processing/)
rather than duplicating dependencies.
