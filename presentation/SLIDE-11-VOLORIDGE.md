# Slide 11 brief — VoloRidge

For whoever or whatever builds this slide. Everything here is copy-paste ready and every
number is sourced. Budget: **30 seconds.** Deck conventions: Century Gothic, ivory ground
`#F3EFE5`, near-black text, one brass accent.

Source of truth for all of it: [`eeg-state-detection/README.md`](../eeg-state-detection/README.md).
Do not re-derive numbers from anywhere else.

---

## The one thing to land

> **We tried the complicated things. They lost. Then we built a test that killed our own
> best-looking result.**

VoloRidge said in person they judge four things: how you handle data analysis, how you
extract signal from noise, **how elegant the result is rather than how complex**, and how
you validate. Elegance is the one most teams cannot show, and it is the one we can prove,
so it leads.

---

## Slide content, exactly

**Three elements. About 45 words total.** At 30 seconds the audience reads or listens, not
both, so anything past three elements costs you the speaker notes.

Build it in two reveals so the slide is never fully loaded while you are still talking.

### Reveal 1 — the headline and the ladder

> # We tried the complicated things. They lost.

Rejected rows in muted grey, winner in near-black with the brass accent. The visual argument
is that the winning row is the shortest one.

```
Riemannian tangent space     1218 features    ✗
26-bin Fourier spectrum       728 features    ✗
Zigzag topology               108 features    ✗
Bayesian state-space          latent state    ✗
                            + 3 more          ✗

Band power + logistic          84 features    ✓
```

### Reveal 2 — the validation block

Two lines, bottom of the slide, brass rule above them. This block carries the backtest and
the kicker together, because they are the same test:

> **8 of 15 sessions beat a time-shift null.**
> The same test killed our best brief-event detector. 3× baseline, **p = 0.13.**

That is the whole slide. Everything else lives in the speaker notes.

### What moved to the notes and why

| Cut from the slide | Why |
|---|---|
| Five participants, fifteen sessions | Spoken in the first line of the notes; on screen it is just more digits |
| AUROC range 0.65 to 0.93 | Invites a number-by-number reading during your 30 seconds |
| "Models frozen and hashed before scoring" | Strong, but it is a sentence you say, not a thing you show |
| The per-participant table | Appendix. Only appears if a judge asks. |

---

## Speaker notes, 30 seconds

> "VoloRidge asks for signal out of public data. Ours is EEG, 28 channels, five people,
> fifteen sessions.
>
> We tried the fancy things. Riemannian geometry, topological data analysis, Bayesian
> state-space models. Every one of them lost to log band power and a logistic regression.
> Eighty-four numbers.
>
> Then we tested it properly. Models frozen before scoring, and a null that shifts the
> signal against the labels instead of shuffling it, because EEG windows are not
> independent. Eight of fifteen sessions beat it.
>
> And the part I would want to hear: our best-looking detector for brief events looked three
> times better than baseline. Against random darts it came out at p equals 0.13. So we threw
> it away."

Roughly 95 words. If you are over time, cut the third paragraph and keep the fourth.

---

## Figure

**Do not put a figure on this slide.** At 30 seconds a chart and a table compete and both
lose.

Keep one in the appendix in case a judge asks how the walk-forward looks:

| Use | File |
|---|---|
| Out-of-sample AUROC per session against the null and the eye-only control | `eeg-state-detection/outputs/backtest_state/summary.png` |
| A single session, calibration then out-of-sample, with ground truth shaded | `eeg-state-detection/outputs/backtest_state/walkforward_VP002.png` |

If the deck must have an image on slide 11, use `summary.png` and drop the ladder, since the
figure already carries the nulls. You would then be making the validation argument instead
of the elegance argument, which is the weaker of the two for this audience.

---

## What not to put on this slide

- **The word "confusion."** The label is task versus rest. Saying confusion invites the one
  question we cannot answer.
- **Accuracy percentages.** AUROC against a null is the honest framing and the one they
  asked for. A bare 92% invites "out of sample?" and wastes your remaining time.
- **All five participants' numbers.** The range 0.65 to 0.93 is the honest summary. The
  table belongs in the appendix.
- **The words "state of the art," "novel," or "deep learning."** The entire argument is that
  we did the plain thing and tested it hard.
- **The other EEG folders.** They corroborate but they dilute a 30-second slot.

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
> "Yes, and two of our five participants are genuinely weak. We show them in the deck rather
> than dropping them. A method that works on three people in five, honestly measured, is
> more useful to you than one that works on a cherry-picked one."

**"What would you do with more time?"**
> "More training data per person, not a more complex model. We tested that direction too:
> restricting channels and fixed physiological features did not help, which points at the
> amount of labelled data rather than the representation."

---

## Every number, sourced

| Claim | Where it comes from |
|---|---|
| 84 features, log band power, 3 bands × 28 channels | `eeg-state-detection/README.md` § Extracting the signal |
| Seven complex alternatives, all lost | `eeg-state-detection/README.md` § Elegance, table |
| 1218 / 728 / 108 feature counts | same table |
| 8 of 15 sessions at p ≤ 0.05, AUROC 0.65–0.93 | `outputs/backtest_state/report.json` |
| Zigzag 6/36 vs 2/36, p = 0.13 | `outputs/burst_diagnostic_dev/report.json` |
| Eye control 0.883 vs 0.925, and 0.559 vs 0.888 | `outputs/backtest_state/report.json` |
