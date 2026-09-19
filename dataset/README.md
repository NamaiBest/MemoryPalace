# dataset/

Every dataset this repo uses, in one place. Read this before looking for data
anywhere else.

Two kinds live here: one recorded by the team and committed to git, and several
public datasets that are downloaded locally and deliberately **not** committed.

---

## Committed: `epocx-imagery/`

Personal 3-class mental imagery recordings, made by a teammate in January 2026.

| | |
|---|---|
| Hardware | Emotiv EPOC X, 14 channels, 128 Hz |
| Contents | 192 trials — 61 apple, 60 mouse, 71 remote |
| Trial length | ~10 s, one imagined object per file |
| Labels | Per file, from the filename. `intervalMarker.csv` files are all empty. |
| Layout | `extracted/<class>/<name>_EPOCX_*.bp.csv`, plus the original `.zip` exports |

**Analysed by [`my-dataset/`](../my-dataset/)** — that folder holds the code and the
result (65.79% 3-class, chance 33.3%, with a shuffled-label control at 34.79%).
`my-dataset/src/classify.py` reads `dataset/epocx-imagery/extracted/` directly.

A known data-handling trap: 70 of the 192 files carry an extra metadata preamble line
before the real CSV header. `load_trial()` skips it. Parsing these naively silently
drops a third of the data and biases the class balance — see
[`my-dataset/README.md`](../my-dataset/README.md) for why that moved the headline
number by 23 points.

## Not committed: public datasets

These are large public downloads, gitignored by the root `.gitignore` `data/` rule.
They stay inside the folder that analyses them, because each folder's scripts expect
them at that path. Regenerate rather than copy.

| Dataset | Lives at | Size | Fetch with |
|---|---|---|---|
| EEGMMIDB (motor imagery) | `eeg-neural-signal-processing/data/eegmmidb/` | 278 MB | `src/download.py eegmmidb` |
| Auditory oddball | `eeg-neural-signal-processing/data/auditory/` | 476 MB | `src/download.py auditory` |
| ds006394 (surprise) | `confusion-detector/data/ds006394/` | 548 MB | `src/fetch_ds006394.py` |

Full reproduction steps are in
[`eeg-neural-signal-processing/RESULTS.md`](../eeg-neural-signal-processing/RESULTS.md)
and [`confusion-detector/README.md`](../confusion-detector/README.md).

## Why public data never supplies deployed weights

Spatial filters are tied to specific electrode positions and impedances, so weights do
not transfer between people, sessions, or headsets. Public datasets here validate that
the *machinery* works; they never produce the model that ships. Retraining on the
target hardware, on the day, is mandatory. This is the technical reason the project is
built around per-user adaptation rather than a frozen pre-trained model — see the root
[`README.md`](../README.md).
