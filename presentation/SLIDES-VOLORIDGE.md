# VoloRidge slides — build brief and speaker notes

**Two slides. 11a the approach, 11b the validation.** Everything here is copy-paste ready
and every number is sourced.

## How to use this file

It serves two readers. Take only your half.

| Section                                         | Who it is for                                                                                                        |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Slide 11a / 11b → the content blocks** | The person or agent**building the slides**. The text in the blockquotes and code fences is literal slide copy. |
| **Speaker notes**                         | The**presenter**, spoken aloud. **Never put these on a slide.**                                          |
| **If they ask**                           | The presenter, during Q&A. Not on a slide.                                                                           |
| **Appendix slides, only if asked**        | Both. Build these, keep them after the last slide.                                                                   |
| **Every number, sourced**                 | Both. Check against these; do not invent a figure.                                                                   |

**Agent building these slides: your instructions are the two slide sections and the
"deliberately not on either slide" table. Stop there.** If a line appears under Speaker
notes, it belongs in the notes field of the slide, not on the slide.

Deck conventions: Century Gothic, ivory ground `#F3EFE5`, near-black text, one brass
accent.

Source of truth for all of it:
[`eeg-state-detection/README.md`](../eeg-state-detection/README.md). Do not re-derive a
number from anywhere else.

## Why two and not one or three

VoloRidge said in person they judge four things: how you handle data analysis, how you
extract signal from noise, **how elegant the result is rather than how complex**, and how
you validate. Two slides cover all four without crowding either:

| Slide                         | Criteria it answers                             |
| ----------------------------- | ----------------------------------------------- |
| **11a, the approach**   | Signal extraction, and elegance over complexity |
| **11b, the validation** | How you validate, and how you handle the data   |

A third slide is not needed. The per-participant table, the walk-forward trace and the
limits are appendix material, listed at the end of this file. They appear only if asked.

**Numbering.** Call them 11a and 11b rather than renumbering 12 to 15. Timing: 30 seconds
each, so one minute for VoloRidge, shown only when VoloRidge is in front of you. If you are
compressed, 11a alone still makes the elegance argument; 11b alone does not stand up
without it.

---

# Slide 11a — The approach

**Two blocks under one headline. About 50 words.**

> # 84 numbers and a logistic regression

### Left block — the pipeline

```
28 EEG channels, 200 Hz
  → regress out the eye channels      frozen before use
  → log power, theta / alpha / beta   84 numbers, every 0.25 s
  → logistic regression, task vs rest
  → one moving average                one parameter
```

### Right block — what lost

Rejected rows muted grey, winner near-black with the brass accent. The visual argument is
that the winning row is the shortest one.

```
Riemannian tangent space     1218 features   ✗
26-bin Fourier spectrum       728 features   ✗
Zigzag topology               108 features   ✗
Bayesian state-space          latent state   ✗
                            + 3 more         ✗

Band power + logistic          84 features   ✓
```

### Speaker notes, 30 seconds

> "VoloRidge asked for signal out of public data. Ours is EEG. Twenty-eight channels,
> five people, fifteen sessions, from an open dataset we did not modify.
>
> The method is four steps. Take out the eye channels, measure power in three frequency
> bands, logistic regression, one moving average. Eighty-four numbers.
>
> It is that simple because we tried the alternatives. Riemannian geometry, topological
> data analysis, Bayesian state-space models. Each one tested on the same recordings
> against the same baseline. Every single one lost. The only thing we kept was a single
> smoothing parameter."

About 90 words.

---

# Slide 11b — The backtest

**One figure and two lines.** The figure does the work here; do not also put a table on it.

### The figure

`eeg-state-detection/outputs/backtest_state/summary.png`, full width across the slide.

It shows all fifteen sessions at once: blue dots are our detector out of sample, grey bars
are what a random alignment of the same signal scores, orange diamonds are the eye-channel
control. A judge who reads charts will get it before you finish the sentence.

### Caption line, directly under the figure

> Grey is what the same signal scores when randomly aligned. **8 of 15 sessions beat it at
> p ≤ 0.05.**

### Kicker, bottom of the slide, brass rule above it

> The same test killed our best brief-event detector. 3× baseline, **p = 0.13.**

### Speaker notes, 30 seconds

> "Here is how we know it is not noise.
>
> Models frozen and hashed before any test block is scored. Then a null. We do not shuffle
> the labels, because EEG windows overlap and shuffling would give us a p-value that is far
> too generous. We shift the whole signal against the labels instead, which keeps its
> structure. That is the grey bar. Blue is us. Eight of fifteen sessions beat it.
>
> Orange is the control, the same pipeline on eye channels only. On two people the eyes get
> close, so we cannot claim those are purely cortical, and we show it rather than hiding it.
>
> And the line I would want to hear: our best-looking detector for brief events scored three
> times the baseline. Against random darts, p of 0.13. So we threw it away."

About 130 words, so speak briskly or drop the orange-diamond paragraph, which the first
question usually recovers anyway.

---

## What is deliberately not on either slide

| Left off                                     | Why                                                                                                             |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| The word "confusion"                         | The label is task versus rest. Saying confusion invites the one question we cannot answer.                      |
| Accuracy percentages                         | AUROC against a null is what they asked for. A bare 92% invites "out of sample?" and burns your remaining time. |
| The AUROC range 0.65 to 0.93                 | Spoken, not shown. On screen it invites a number-by-number reapding.                                            |
| The per-participant table                    | Appendix.                                                                                                       |
| "State of the art", "novel", "deep learning" | The whole argument is that we did the plain thing and tested it hard.                                           |
| The other EEG folders in this repo           | They corroborate, but they dilute a one-minute slot.                                                            |

## Appendix slides, only if asked

| Question it answers                         | Asset                                                                                      |
| ------------------------------------------- | ------------------------------------------------------------------------------------------ |
| "What does one session actually look like?" | `eeg-state-detection/outputs/backtest_state/walkforward_VP002.png`                       |
| "Show me every participant"                 | The results table in`eeg-state-detection/README.md` § Results                           |
| "Where does it fail?"                       | `eeg-state-detection/outputs/backtest_state/walkforward_VP006.png`, the weak participant |
| "How did you kill the topology result?"     | `eeg-state-detection/outputs/burst_diagnostic_dev/diagnostic.png`                        |

---

## If they ask

**"Is this just eye movement?"**

> "Fair, and we ran that control. The same pipeline on eye channels alone. On two
> participants the eyes get close, 0.88 against our 0.92, so on those we cannot claim it is
> purely cortical. On another the detector gets 0.89 and the eyes get 0.56. We publish both
> columns."

**"Why a shift null instead of a permutation test?"**

> "Overlapping EEG windows are not independent, so shuffling breaks the autocorrelation and
> gives you a p-value that is much too generous. Shifting the whole trace keeps the
> structure. It is a harder test, and our null intervals reach 0.8 AUROC because of it. We
> report that width rather than hiding it."

**"Only 8 of 15 sessions? That is barely half."**

> "Yes, and two of our five participants are genuinely weak. We show them rather than
> dropping them. A method that works on three people in five, honestly measured, is more
> useful to you than one that works on a cherry-picked one."

**"What would you do with more time?"**

> "More training data per person, not a more complex model. We tested that direction too:
> restricting channels and fixed physiological features did not help, which points at the
> amount of labelled data rather than the representation."

---

## Every number, sourced

| Claim                                               | Where it comes from                                        |
| --------------------------------------------------- | ---------------------------------------------------------- |
| 84 features, log band power, 3 bands × 28 channels | `eeg-state-detection/README.md` § Extracting the signal |
| Seven complex alternatives, all lost                | `eeg-state-detection/README.md` § Elegance, table       |
| 1218 / 728 / 108 feature counts                     | same table                                                 |
| 8 of 15 sessions at p ≤ 0.05, AUROC 0.65–0.93     | `outputs/backtest_state/report.json`                     |
| Zigzag 6/36 vs 2/36, p = 0.13                       | `outputs/burst_diagnostic_dev/report.json`               |
| Eye control 0.883 vs 0.925, and 0.559 vs 0.888      | `outputs/backtest_state/report.json`                     |
