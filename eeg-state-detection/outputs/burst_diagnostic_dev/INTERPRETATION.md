# What the existing burst flags actually are

**None of the existing continuous burst detectors retrieves n-back target onsets
better than randomly placed flags.** Under the same valid grid, quality mask, budget
of five flags per block, 1.5 s separation and ±0.5 s tolerance, uniformly random
flags match 3.0–3.6 of 36 targets on average. The observed 2–6 matches sit inside
the random 95% interval for every model on every development participant. The
earlier reading of zigzag topology as an improvement over mean-amplitude bins
(6/36 versus 2/36 on VP005) is not supported: 6/36 has a random-placement
probability of about 0.13, and 2/36 is below the random mean.

| Model, participant | Observed | Uniform-random mean [95%] | P(random ≥ observed) |
|---|---:|---:|---:|
| mean_bins, VP001 | 4/36 | 3.0 [0, 6] | 0.35 |
| xdawn, VP001 | 6/36 | 3.0 [0, 6] | 0.07 |
| mean_bins, VP002 | 3/36 | 3.2 [0, 6] | 0.63 |
| mean_bins, VP005 | 2/36 | 3.6 [1, 7] | 0.90 |
| zigzag, VP005 | 6/36 | 3.6 [1, 7] | 0.13 |
| mean_bins + zigzag, VP005 | 3/36 | 3.6 [1, 7] | 0.72 |

**They also fail the easier task of finding stimuli at all.** A detector that placed
its five flags on stimulus onsets without knowing which are targets would match
about 9/36. Between 57% and 87% of the returned flags fall farther than 0.5 s from
any stimulus, either between stimuli or in the pre/post-task context. Only the
xdawn model on VP001 and zigzag on VP005 put half their flags near a stimulus, and
mostly near non-targets.

**On the continuous grid the classifier scores carry no usable information.**
Within-session AUROCs for target windows against background are 0.48–0.56, for
stimulus windows against background 0.49–0.55, and for target against non-target
windows 0.49–0.52. Median scores are the same in every category. The one clear
aligned signal is the mean-bins model on VP001: onset-aligned target versus
non-target AUROC 0.78, consistent with its saved known-onset result. Every other
model and participant is near 0.5 even when aligned to the markers.

## Two different failure modes

1. **Aligned discrimination exists but continuous ranking is random (VP001, mean bins).**
   This is what the handoff's hypothesis predicts. The classifier was trained only on
   stimulus-aligned epochs. Background centres are about two thirds of the scan grid
   and were never seen in training, so their margins are arbitrary; the top five
   scores per block come from wherever the background happens to be extreme.
   Calibration-only background negatives, or a separate stimulus-presence stage,
   address exactly this and can be tested.
2. **No aligned discrimination either (VP002, VP005, all models).** Onset-aligned
   AUROCs of 0.43–0.56 mean the features do not separate targets from non-targets
   for these participants even with the marker given. Background negatives cannot
   create a signal that is not there. Whether this is the participant, the 28-channel
   mean-bin representation, the ocular correction, or the small training set
   (24 targets per session) is not identified by this diagnostic.

Matched-flag timing offers nothing to exploit: two to six matches per model with
median signed offsets within ±0.35 s and no consistent direction.

## What follows

- A bounded test of calibration-only background negatives is justified, but its
  expected benefit is conditional on aligned discrimination existing for that
  participant. The fresh comparison must therefore report the known-onset AUROC
  next to continuous retrieval, and its adoption rule must require beating the
  uniform-random null, not just the baseline.
- Flags near any stimulus, measured against the stimulus-blind null, is the more
  basic feasibility endpoint: can brief stimulus-locked responses be localized
  without markers at all? Report it alongside target matches.
- For the product: with the current burst branch, EEG burst flags on a real session
  would be indistinguishable from randomly placed clips. Present the burst branch as
  unvalidated, and demonstrate the retrieval workflow with explicitly synthetic
  events until a detector clears the random baseline on an untouched participant.

## What this diagnostic is not

It fitted, tuned and thresholded nothing; all flags were recomputed from the frozen
models or saved traces and checked against the saved experiment outputs before
analysis. The nulls are descriptive reference distributions on dependent,
overlapping windows, not significance tests. All three participants were inspected
in earlier experiments, so nothing here is fresh validation. The endpoint is a task
target proxy, not spontaneous insight or confusion. An unmatched flag is unmatched
to this label, not proof of absent neural activity. See [RESULTS.md](RESULTS.md),
`report.json`, `flags.csv` and `diagnostic.png`.
