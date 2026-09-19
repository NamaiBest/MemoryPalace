# Dataset notes — NEMAR on006394 / OpenNeuro ds006394

Inspected from the files actually present in `on006394/`.
The manuscript is listed as Leong et al. (in prep). Methodological details that are
*not* in the bundled README are inferred only where the BIDS files themselves support
the inference, and are marked as such.

Source:

- Local copy: `on006394/`
- NEMAR: https://nemar.org/dataset/on006394
- OpenNeuro: https://openneuro.org/datasets/ds006394
- DOI: 10.18112/openneuro.ds006394.v1.0.3 (this copy is NEMAR `on006394` v1.0.0, derived from that OpenNeuro snapshot)
- License: CC0

---

## 1. What this dataset is

Title (from `dataset_description.json`):

> Electrophysiological markers of surprise-induced failures of visual and auditory awareness

Authors: En-Lin Leong, Yun Da Chua, Takashi Obana, Christopher L. Asplund.

NEMAR metadata (`/.nemar/metadata.json`) describes 33 participants completing
counterbalanced visual and auditory surprise tasks designed to probe
electrophysiological markers of surprise-induced failures of perceptual awareness.

This is **not** an insight / "aha" dataset. The experimentally defined event is
**surprise** (an unexpected stimulus embedded in a rapid stream). That is why it is
usable as a MemoryPalace proxy: the event time is annotated, not self-reported.

---

## 2. Participants and recordings

| Item | Value | Source |
|---|---|---|
| Participants listed | 33 (`sub-01` … `sub-33`) | `participants.tsv` |
| Age / sex | `n/a` for every participant | `participants.tsv` |
| EEG recordings on disk | 60 (29 SiB + 31 SiD) | `*_eeg.set` / `*_eeg.fdt` |
| Event files | 59 | `*_events.tsv` |
| Behavioral files | 66 (33 × 2 tasks) | `*_beh.tsv` |

NEMAR reports 60 recordings / 546.5 MB. Local annex objects are present (not
broken git-annex pointers). Combined `.set`+`.fdt` size ≈ 546.5 MB.

### Incomplete / missing EEG (do not silently skip)

README: “Certain participants were excluded at various stages of the analyses.
Their data and event lists are included up to the stage of processing that their
data reached.”

| Subject | SiB EEG | SiB events | SiD EEG | SiD events | Notes |
|---|---|---|---|---|---|
| sub-04 | yes | yes (surprises only) | yes | yes (surprises only) | No probe event markers |
| sub-05 | yes | yes | **missing** | **missing** | No SiD EEG |
| sub-06 | **missing** | **missing** | yes | yes | No SiB EEG |
| sub-07 | yes | yes | **missing** | **missing** | No SiD EEG |
| sub-09 | set/fdt/json/channels present; **events file exists but contains only probes** | probes / dummy-probes only | yes | yes | SiB surprise markers absent |
| sub-20 | **missing** | **missing** | yes | yes | No SiB EEG |
| sub-21 | yes | yes (surprises only) | yes | yes | SiB has no probe markers |
| sub-26 | set/fdt/json/channels present | **missing events.tsv** | yes | yes | Cannot epoch SiB |
| sub-27 | set/fdt/json/channels present | **missing events.tsv** | yes | yes | Cannot epoch SiB |
| sub-32 | **missing** | **missing** | yes | yes | No SiB EEG |

Pipeline rule: log every missing/unusable file with a reason in `logs/skipped.json`.
Never invent events for a recording that lacks `events.tsv`.

### Suspicious timestamps

`sub-23` SiD event onsets run to **12232 s** (~3.4 h). Typical recordings are
~1000 s. Events past the EEG duration must be dropped and logged, not clipped
quietly into the last sample.

---

## 3. Tasks

Sidecar `TaskName` values are **`SiB`** and **`SiD`**. The README does not expand
the acronyms.

Supported by the data:

- Behavioral `condition` is **`v` for every SiB trial** and **`a` for every SiD trial**.
- SiB streams mix a letter RSVP list with an auditory RAP list.
- SiD is the same dual-stream structure with auditory as the attended condition.
- Dataset title concerns surprise-induced failures of **visual and auditory awareness**.

Interpretation (labelled as inference, consistent with the title and `condition` column):

- **SiB** ≈ surprise-induced blindness (visual RSVP attended).
- **SiD** ≈ surprise-induced deafness (auditory RAP attended).

Tasks were completed in counterbalanced order (README). Date stamps in `beh.tsv`
(e.g. `2020_Nov_25_1213` then `1235` for sub-01) are consistent with two sessions
on the same day.

---

## 4. EEG acquisition

From every `*_eeg.json` (60/60 identical except `TaskName`):

| Field | Value |
|---|---|
| SamplingFrequency | **125 Hz** |
| EEGChannelCount | **16** |
| EEGReference | **Left earlobe** |
| PowerLineFrequency | **50 Hz** (not 60 Hz) |
| RecordingType | continuous |
| SoftwareFilters | n/a |
| EOGChannelCount | 0 |

Format: EEGLAB `*_eeg.set` + `*_eeg.fdt` (MATLAB v5). NEMAR `dataset_type` is
`"raw"`. Sidecar `SoftwareFilters` is `n/a`. Treat the recordings as raw OpenBCI
EEG, not as a preprocessed derivative.

### Channels (identical in every `channels.tsv`)

```
Fp1  C3  Fp2  C4  Fz  Cz  O1  O2  F7  F8  F3  F4  T7  T8  P3  P4
```

All typed `EEG`. Units: **`microV/24`**.

No EOG channel. Eye-blink contamination will appear on Fp1/Fp2.

---

## 5. OpenBCI scaling issue (mandatory correction)

README (verbatim):

> Due to incorrect settings specific to OpenBCI GUI v5.0.1, indicated EEG values
> are 24 times larger than what they should be. The units (also specified in the
> channels.tsv files) are thus in microvolts / 24.

NEMAR methods text repeats this.

**Correction used in this pipeline:** divide loaded EEG by 24 so that the working
unit is microvolts. Documented in `src/config.py` as `OPENBCI_SCALE_DIVISOR = 24.0`.

This is a dataset-author correction, not a guess.

---

## 6. Event annotations — the part that matters for labels

### File schema (`*_events.tsv`)

Columns (ERPLAB-style export):

`onset`, `duration`, `#item`, `bepoch`, `ecode`, `label`, `diff`, `dura`,
`b_flags`, `a_flags`, `enable`, `bin`, `trial_type`

`onset` is in seconds. `duration` is 1.0 s for every event in every file.
`label` is `Trial1`, `Trial2`, … and is **not** a condition name.
`ecode` is an integer trial index, not a condition code.

**The only condition field in the EEG event files is `trial_type`.**

### `trial_type` values actually present

| `trial_type` | Total events | Typical per complete recording |
|---|---|---|
| `dummy-surprises` | 7888 | 136 |
| `probes` | 5600 | 100 |
| `dummy-probes` | 2016 | 36 |
| `surprises` | 1392 | 24 |

No other `trial_type` strings exist. There is **no** column named “expected vs
unexpected”, “oddball”, “standard”, or “aha”.

### Timing (sub-01 SiB, representative)

| Type | n | First onset (s) | Median ISI (s) | Min ISI (s) |
|---|---|---|---|---|
| `surprises` | 24 | 42.3 | 36.6 | 17.8 |
| `dummy-surprises` | 136 | 11.7 | 6.23 | 5.42 |
| `probes` | 100 | 12.1 | 6.49 | 5.42 |
| `dummy-probes` | 36 | 24.6 | 24.3 | 5.89 |

A complete recording is ~16–18 minutes of EEG. Events are 1 s long. Epochs of
about −0.2 to +0.8 s around surprise/dummy-surprise onsets do not overlap each
other (minimum ISI > 5 s).

---

## 7. Behavioral files — how to read the two-letter `task` code

Each `beh.tsv` has 160 trials (5280 trials / 33 subjects / task). `practice` is
always `FALSE`.

Relevant columns:

- `task`: two-letter code
- `condition`: `v` (SiB) or `a` (SiD)
- `probe_presence`: `Present` / `Absent`
- `surprise_sound`, `surprise_img`: path or `NA`
- `RSVP`: letter list; surprise trials contain the token `'surprise'`
- `probe_response`: `ABSENT` / `VISUAL` / `AUDITORY` / `PRESENT` / `NONE`
- `probe_resp_time`, `surprise_start_time`, `probe_start_time`

### Two-letter `task` code (inferred from the columns, not from a codebook)

| Code | Surprise in RSVP/`surprise_*` | Probe present | Count / subject / task |
|---|---|---|---|
| NN | no | no | 36 |
| NV | no | visual probe | 50 |
| NA | no | auditory probe | 50 |
| VV | visual surprise | visual probe | 5 |
| VA | visual surprise | auditory probe | 5 |
| VN | visual surprise | no | 2 |
| AA | auditory surprise | auditory probe | 5 |
| AV | auditory surprise | visual probe | 5 |
| AN | auditory surprise | no | 2 |

First letter = surprise modality (`N` none, `V` visual, `A` auditory).
Second letter = probe modality (`N` none, `V` visual, `A` auditory).

Per subject per task: **24 surprise trials** and **136 non-surprise trials**.
That matches EEG `surprises` (24) and `dummy-surprises` (136) exactly on complete
recordings.

### Behavioral responses exist

`probe_response` and `probe_resp_time` are present. They mark the participant's
report about the **probe**, not about the surprise itself. They are **not** used
as the primary EEG label. Using them would answer “was the probe seen/heard?”,
which is the paper's awareness question, not MemoryPalace's “did a surprise
occur?”.

---

## 8. Ground-truth definition used by this project

**Positive class (`event`):** `trial_type == "surprises"`

**Negative class (`control`):** `trial_type == "dummy-surprises"`

Reasons:

1. Both labels are in the dataset. Nothing is invented.
2. Counts match surprise vs non-surprise behavioral trials 1:1 on complete files.
3. Dummy events at the equivalent latency of real events on control trials is
   standard ERPLAB practice; the name `dummy-surprises` is consistent with that.
4. `probes` / `dummy-probes` are a *different* event (the awareness probe after
   the surprise). Using them would mix surprise with a later detection report.

We do **not**:

- relabel from behavioral `task` codes inside the EEG events
- treat probe hits/misses as surprise labels
- create “aha” labels
- use expected-vs-surprising language beyond what `surprises` vs
  `dummy-surprises` already encodes

Assumption stated explicitly: `dummy-surprises` are time-matched control markers
on non-surprise trials. The README never says this in words; the counts and the
ERPLAB column names are the evidence. If that assumption is wrong, the control
class is wrong — which is why it is written down here rather than hidden in code.

---

## 9. Preprocessing already performed?

| Evidence | Conclusion |
|---|---|
| NEMAR `dataset_type`: `raw` | Treat as raw |
| Sidecar `SoftwareFilters`: `n/a` | No documented digital filter |
| OpenBCI scale bug still present | Not fully cleaned |
| Incomplete subjects retained | Not a uniform preprocessed release |

Some `.set` files may still contain EEGLAB event structures. The pipeline uses
BIDS `events.tsv` as the label source of truth, not whatever is inside the `.set`.

---

## 10. What this dataset can and cannot support

**Can support:** a binary detector for an experimenter-timed surprising stimulus
versus a time-matched non-surprise control, in visual (SiB) and auditory (SiD)
streams, on 16-channel 125 Hz OpenBCI EEG.

**Cannot support:** decoding memories, thoughts, insight, or spontaneous real-world
“aha” moments. Probe-awareness labels exist but are a different scientific
question (surprise-induced inattentional blindness/deafness).

---

## 11. Discrepancies vs the original prompt

| Prompt assumption | What the files say |
|---|---|
| “16-channel EEG” | Confirmed |
| “33 participants” | 33 listed; 60 EEG recordings, not 66; 56 used after documented skips |
| Event codes would need inspection | Confirmed: do **not** hard-code anything except the four `trial_type` strings above |
| Scaling ×24 | Confirmed; divide by 24 |
| Distinguishes expected vs surprising stimuli | **Yes**, via `surprises` vs `dummy-surprises`, not via a column named “expected” |
| US 60 Hz line noise | **50 Hz** (`PowerLineFrequency`) |
| Sampling rate | **125 Hz**, not a typical 250/256/500 Hz consumer rate |
| Work folder `eeg-neural-signal-processing/xueqi-validation/` | Dataset already lives at repo-root `xueqi-validation/`. All code stays there. Teammate files are not touched. |

Two recordings (`sub-02` SiB, `sub-15` SiB) store channel names as `EEG 000`…
instead of 10–20 labels. They were skipped and logged rather than silently
renamed. `channels.tsv` still lists the standard names if someone remaps later.
