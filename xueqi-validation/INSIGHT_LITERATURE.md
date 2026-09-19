# Insight literature (not evidence that EEG uniquely identifies an aha)

These papers motivate why MemoryPalace cares about cognitive transitions.
They do **not** prove that a wearable EEG trace can label an aha moment, and
they are not the dataset analyzed in this folder.

Our empirical work uses surprise-locked EEG (on006394), which has experimenter-
controlled timestamps. Insight, in these papers, is usually a **self-report**
after a problem is solved.

---

## 1. Sandkühler & Bhattacharya (2008)

Sandkühler, S., & Bhattacharya, J. (2008). Deconstructing insight: EEG
correlates of insightful problem solving. *PLoS ONE, 3*(1), e1459.

- URL: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0001459
- DOI: https://doi.org/10.1371/journal.pone.0001459
- PubMed: https://pubmed.ncbi.nlm.nih.gov/18213368/

**Task.** Verbal remote-associate problems (RAT-style). Hints were given after
impasse or for unsolved items. Participants rated restructuring and suddenness
trial by trial.

**Ground truth.** Behavioral solution, plus subjective ratings of restructuring
and of the feeling of suddenness — not an independent neural decoder of “aha.”

**Sensors.** Scalp EEG (BESA time–frequency analysis; average reference).

**Reported effects (authors’ interpretation).**

- Parieto-occipital gamma: attention / encoding–retrieval around solution or
  impasse, depending on power level.
- Right-temporal upper alpha increase for initially unsuccessful trials that
  later succeeded after a hint (interpreted as suppression of irrelevant info).
- Right prefrontal alpha decrease for high-restructuring trials (interpreted as
  greater cortical excitation).
- Suddenness ratings associated with parieto-occipital gamma, dissociable from
  the restructuring ratings.

**Relevance to MemoryPalace.** Shows that *self-reported* insight subprocesses
have EEG correlates in lab problem-solving. Useful as a hypothesis generator
for an insight validation task at HackMIT. Not a wearable trigger recipe.

**Raw data publicly downloadable?** No public EEG release was found (no
OpenNeuro/OSF raw EEG for this 2008 study). Paper and figures are open at PLoS.

---

## 2. Bieth et al. (2024)

Bieth, T., Ovando-Tellez, M., Lopez-Persem, A., Garcin, B., Hugueville, L.,
Lehongre, K., Levy, R., George, N., & Volle, E. (2024). Time course of EEG
power during creative problem-solving with insight or remote thinking.
*Human Brain Mapping, 45*(1), e26547.

- URL: https://onlinelibrary.wiley.com/doi/10.1002/hbm.26547
- DOI: https://doi.org/10.1002/hbm.26547
- PubMed: https://pubmed.ncbi.nlm.nih.gov/38060194/
- PMC: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10789201/
- Preprint: https://doi.org/10.1101/2021.11.26.470102

**Task.** Modified Remote Associates Test: find a word connecting three cue
words. Semantic remoteness of the solution was varied across trials.

**Ground truth.** Correct solution plus a participant-reported Eurêka / insight
flag. Remoteness is a property of the item, not of a brain state.

**Sensors.** EEG with source reconstruction (lab system, not consumer OpenBCI).

**Reported effects (authors’ interpretation).**

- Semantic remoteness: early left parieto-temporal alpha and right
  fronto-temporal beta increases; bilateral frontal theta just before response.
- Insight (Eurêka report): pre-response left temporal alpha and gamma
  increases, plus frontal theta. Insight-related EEG differences appeared
  mainly in the final response window, not throughout the trial.

**Relevance to MemoryPalace.** If insight has a short pre-response EEG change,
a bookmarking system would still need a buffer (the interesting context is
*before* the report). The Eurêka label is subjective. Effects are cluster-
level statistics in a high-density lab montage — not a 2-channel glasses
detector.

**Raw data publicly downloadable?** No OpenNeuro EEG dump was found for this
paper. Contact the corresponding authors (Bieth / Volle) if needed. Related
OSF materials from the same group exist for other projects, not this EEG set:
https://osf.io/user/627mz

---

## 3. Salvi et al. (2020)

Salvi, C., Simoncini, C., Grafman, J., & Beeman, M. (2020). Oculometric
signature of switch into awareness? Pupil size predicts sudden insight whereas
microsaccades predict problem-solving via analysis. *NeuroImage, 217*, 116933.

- URL: https://www.sciencedirect.com/science/article/pii/S1053811920304195
- DOI: https://doi.org/10.1016/j.neuroimage.2020.116933
- Data: https://data.mendeley.com/datasets/m4dd94r3kt/2
  (DOI 10.17632/m4dd94r3kt.2)

**Task.** Compound remote-associate / insight vs analysis problem solving
(reanalysis of eye-tracking data related to Salvi et al., 2015).

**Ground truth.** Participant report of insight vs analytic solution, plus
accuracy.

**Sensors.** Eye tracking (pupil diameter, microsaccades). **No EEG.**

**Reported effects (authors’ interpretation).**

- Pupil dilation ~500 ms before the solution on insight-reported trials.
- Microsaccade rate increased before analytic (non-insight) solutions.
- The two markers were not reliably correlated.
- Interpreted as LC–NE involvement in a “switch into awareness,” analogous to
  perceptual reversals — a hypothesis, not a unique neural ID of aha.

**Relevance to MemoryPalace.** Strong argument for **multimodal** sensing:
pupil (and by extension PPG/arousal) may carry information that EEG lacks,
especially for sudden awareness-like events. This is why `MULTIMODAL_NEXT.md`
exists. It still depends on self-report labels.

**Raw data publicly downloadable?** Yes — Mendeley Data `.evs` eye-tracking
file under CC BY-NC 3.0. That is **not** EEG, and NC licensing is more
restrictive than the CC0 surprise dataset used here.

---

## How to read these results for the hackathon

| Paper | What it measured | What it did not measure |
|---|---|---|
| Sandkühler 2008 | EEG vs insight subprocess ratings | A unique aha biomarker; wearable EEG |
| Bieth 2024 | EEG power vs remoteness and Eurêka report | Real-world spontaneous insight |
| Salvi 2020 | Pupil / microsaccades vs insight report | Brain electrical activity |

None of these studies show that an EEG voltage pattern *is* an aha moment.
They show associations under specific tasks, montages, and labels.

The honest HackMIT next experiment is a controlled insight task with
**participant self-report**, timestamped, plus the same EEG pipeline used here
on surprise — not a claim that surprise = insight.
