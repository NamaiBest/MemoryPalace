# Fresh VP006: background negatives did not yield a usable burst detector, and the chosen stretch approach is weak on this participant

VP006 had never been loaded by any analysis before `background_negatives_protocol.md`
was frozen. Three sessions were calibrated separately on their first six blocks; all
models were saved and hashed before any of the nine evaluation blocks was scored;
nothing was changed afterwards. See [RESULTS.md](RESULTS.md), `report.json`,
per-session reports, traces, event exports and plots.

## Burst branch: both arms remain at chance

| Arm | Target matches | Flags near any stimulus, of 30 | Known-onset AUROC, mean | P(uniform random ≥ matches) |
|---|---:|---:|---:|---:|
| mean_bins (baseline) | 0/36 | 2 | 0.47 | 1.00 |
| mean_bins_background | 2/36 | 14 | 0.54 | 0.83 |
| uniform random flags, same grid | 3.05 [0–6] | 10.5 [6–16] | | |
| stimulus-blind random flags | 8.97 [5–14] | 30 | | |

**The prespecified rule was not met.** Background negatives gave more matches than
the baseline (2 versus 0) at a matched fraction that is not lower, but 2/36 is what
random placement produces (probability 0.83 of at least as many). Neither arm beats
the uniform null; the baseline did not match a single target. Nothing is adopted.

**What the background negatives did change.** The baseline's flags avoided stimuli:
only 2 of 30 fell within 0.5 s of any stimulus, below the random reference, with
14 in the context margins and 14 between stimuli. The background arm's classifier
treats most of the grid as strongly negative and fires sparsely; 14 of its 30 flags
fell near a stimulus, 12 of them near non-targets. That is the partial effect the
development diagnostic predicted: calibration-only background negatives teach
"stimulus-locked versus background" to a degree, and cannot teach target versus
non-target when the aligned features barely separate them. Known-onset AUROCs were
0.57/0.57/0.29 for the baseline and 0.61/0.72/0.29 with background negatives; the
eye-only control was 0.52/0.60/0.43.

**Session 3 is below chance for every model, eye channels included.** Its two
evaluation blocks rejected 92 and 103 of about 630 grid windows against 40 in the
other sessions, so signal quality was worse. With 11 accepted targets, an AUROC
has a standard deviation near 0.1; 0.29 is far from 0.5 but rests on very few
trials. No setting was revisited because of it.

The background arm's cross-validated average precision (0.09–0.15) is not
comparable with the baseline's (0.29–0.55): its positive prevalence is about 6%
instead of 30%, and average precision scales with prevalence.

## Stretch branch: fresh validation of the already-chosen approach

| Model | Mean AUROC | Mean balanced accuracy | Intervals | Whole-task matches | Task covered | Rest included, of 72 s |
|---|---:|---:|---:|---:|---:|---:|
| power | 0.660 | 0.586 | 38 | 2/9 | 74.1% | 19.82 s |
| power + EMA (chosen) | 0.669 | 0.604 | 24 | 6/9 | 83.6% | 28.00 s |

Calibration already showed the problem: the band-power task/rest classifier reached
cross-validated AUROC 0.844 in session 1 but 0.501 and 0.527 in sessions 2 and 3.
Selected half-lives were 0.5, 0.5 and 2 s. Smoothing again produced more complete
intervals (6/9 whole-task matches) at the cost of more rest included: 28 of 72 s,
39% of the labeled rest, up from 19.82 s unsmoothed. On this participant the
smoothed detector calls most of each excerpt task-like, so whole-task matches come
cheaply and rest rejection is not usable.

Against the record: VP002 gave balanced accuracy 0.815 and 5.39 s rest included for
the same approach; VP003–VP005 power baselines gave 0.63–0.79. VP002 was the best
case, not the typical case. The chosen approach remains the chosen approach; this
result changes how it should be described, not the selection.

## What this settles and what it leaves open

Across four participants (VP001, VP002, VP005, VP006) and six representations or
training variants, marker-free retrieval of n-back target onsets has never exceeded
random placement. Aligned discrimination existed only for VP001. The remaining
options each need a decision by the user, not more unguided model trials:

1. **Training data, not representation.** Twenty-four targets per session is far
   below what single-trial ERP classifiers normally need. Pooling the three sessions
   of one participant would triple the targets but relaxes the current contract's
   rule against reusing weights across sessions. Untouched participants (VP007 and
   later) are available for a fresh test if that rule is changed for within-person use.
2. **Endpoint change.** Detecting any stimulus-locked response against background is
   the endpoint the background arm moved toward. It is further from "a moment worth
   revisiting" than target retrieval was.
3. **Stop.** Ship EEG stretches with their stated weaknesses, present bursts as
   unvalidated candidates, and rely on audio/video cues for brief moments.

One participant, 36 targets, dependent overlapping windows and descriptive nulls limit
every number here. Targets are a task proxy, not spontaneous insight. Eye, motor and
sensory contributions are not isolated. Replay EEG does not describe the person in
the phone video. VP006 is now inspected data; a rerun reproduces software, not fresh
generalization.
