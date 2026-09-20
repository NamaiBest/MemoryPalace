# EEG moment candidates

Runnable offline EEG branch for the work-session prototype. It independently identifies and exports **sustained stretches and short bursts**. Burst scoring implements the **oscillatory variant** of `framwork.tex`: shrinkage covariance → training-fitted tangent space → regularized linear classifier. A simpler log-band-power classifier is included for comparison; a calibrated frontal-power rule detects stretches.

**Latest decision: retain both stretches and bursts; choose learned band power + exponential smoothing for stretches and focus new research on short bursts.** Smoothing is the chosen interval-recovery tradeoff, not a winner on every metric. The selected VP002 wrappers and event files are in `outputs/smoothing_vp002/`, and the `combined` CLI now loads them by default (`--stretch-kind power_ema`); the smoothed integration replay is in `outputs/combined_vp002_smoothed/`. Historical results below preserve earlier defaults. **Burst status after 2026-09-19:** on four participants and six model variants, marker-free target retrieval never exceeded random placement; see the development diagnostic in `outputs/burst_diagnostic_dev/` and the frozen VP006 comparison in `outputs/background_vp006/`. The chosen stretch approach validated on VP006 gave balanced accuracy 0.60 with 28 of 72 s rest included; VP002 was its best case. Start with [LLM_HANDOFF.md](LLM_HANDOFF.md) for the current state, evidence, limitations, and next steps.

An accepted EEG burst candidate or audio/video moment cue should save the next 30 seconds from its estimated timestamp. Retain stretches independently, without requiring a burst or using them to gate bursts; dedicated stretch clip behavior remains unspecified. Task/rest and smoothing results do not establish useful brief-moment retrieval. See [session_pipeline.md](session_pipeline.md) for the current design. Video clipping and audio/video integration are not implemented by this EEG package.

**Current status: synthetic benchmark, real ERP feasibility test, and learned workload evaluation on a fresh participant.** The synthetic models detect injected oscillatory packets. Separately calibrated real-data ERP models were evaluated on Shin 2018 participant VP001; the new workload models were tested on untouched VP002 holdout blocks. These tests do not establish detection of confusion, insight, or spontaneous cognitive bursts. No unrelated EEG datasets have been merged.

## Walk-forward view of the state-change detector (presentation figures)

`backtest` rescans every block of every session of VP002–VP006 with the saved frozen task/rest models, draws the first six blocks as the in-sample calibration period and the last three as out of sample, and scores the out-of-sample AUROC against a circular time-shift null (2000 shifts of the intact score trace against the labels per session). Every recomputed out-of-sample AUROC equals the original experiment's saved value. Outputs: `outputs/backtest_state/` with `walkforward_<participant>.png`, `summary.png`, `RESULTS.md`, `report.json` and `INTERPRETATION.md`.

| Participant | Model | Out-of-sample AUROC, mean | Sessions with P ≤ 0.05 | Whole-task matches | Rest included | Eye-only control |
|---|---|---:|---:|---:|---:|---:|
| VP002 | power + EMA | 0.925 | 3/3 | 7/9 | 5.4/72 s | 0.883 |
| VP003 | power | 0.800 | 1/3 | 5/9 | 4.9/72 s | 0.848 |
| VP004 | power | 0.652 | 1/3 | 0/9 | 13.9/72 s | 0.522 |
| VP005 | power + EMA | 0.888 | 2/3 | 2/9 | 5.2/72 s | 0.559 |
| VP006 | power + EMA | 0.669 | 1/3 | 6/9 | 28.0/72 s | none |

Eight of fifteen sessions beat the shift null at 0.05. The eye-only control is close to the EEG detector on VP002 and VP003 and far below it on VP005, so the figures show where the signal is and is not explained by eyes.

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments backtest --out outputs/backtest_state_reproduction
```

## Fresh VP006: calibration-only background negatives and chosen-stretch validation

One untouched participant, protocol frozen in `background_negatives_protocol.md` before any VP006 EEG was loaded, all models fitted on calibration blocks and hashed before scoring. The burst comparison asked whether adding calibration-only background negatives (grid centres every 0.5 s farther than 0.5 s from any stimulus, labeled negative; `fit_erp(kind="mean_bins_background")`) to the ERP mean-amplitude classifier improves marker-free target retrieval on the held-out 2-/3-back blocks. Results: `outputs/background_vp006/INTERPRETATION.md`.

| Arm | Target matches | Flags near any stimulus (of 30) | Known-onset AUROC | P(uniform random ≥ matches) |
|---|---:|---:|---:|---:|
| mean_bins | 0/36 | 2 | 0.472 | 1.000 |
| mean_bins_background | 2/36 | 14 | 0.540 | 0.834 |
| uniform random flags, same grid | 3.05 [0–6] | 10.5 [6–16] | | |
| stimulus-blind random flags | 8.97 [5–14] | 30 | | |

The prespecified rule (more matches, matched fraction not lower, uniform-null probability at most 0.05) failed on the third condition; **nothing was adopted**. Background negatives moved flags toward stimuli, mostly non-targets, and did not create target discrimination that the aligned features lack (session AUROCs 0.61/0.72/0.29; eye-only 0.52/0.60/0.43).

The same run validated the chosen stretch approach on VP006: power AUROC 0.660, balanced accuracy 0.586, 2/9 whole-task matches, 19.82 of 72 s rest included; power + EMA 0.669, 0.604, 6/9, 28.00 s. Calibration CV AUROC was 0.844, 0.501 and 0.527 by session. VP002 (balanced accuracy 0.815, 5.39 s rest) was the best case for this approach, not the typical case.

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments background \
  --data data/shin2018/VP006 --out outputs/background_vp006_reproduction
```

The runner refuses VP001–VP005 and nonempty output directories. VP006 is now inspected; the command reproduces software, not fresh generalization. All 79 tests pass.

## Channel-set check for the burst branch (development data)

Asked on 2026-09-19: would restricting the ERP classifier to significant channels, such as the midline, help bursts? `channel-check` answers the prerequisite on the four inspected participants: known-onset AUROC on held-out 2-/3-back blocks for fixed physiological features (no fitting) and for the existing mean-bin classifier restricted to channel subsets, fitted on calibration blocks only. Three runs: the 1–30 Hz default (`outputs/channel_check_dev/`), plus descriptor-window fixed features at 0.2–0.4 s (`outputs/channel_check_dev_descriptor_window/`), plus a 0.5 Hz high-pass (`outputs/channel_check_dev_highpass05/`). Interpretation: `outputs/channel_check_dev/INTERPRETATION.md`.

| Feature set | Mean AUROC, 12 sessions (1–30 Hz) | Same at 0.5–30 Hz | Sessions ≥ 0.70 |
|---|---:|---:|---:|
| Fixed Pz, Cz or fronto-central-parietal cluster amplitude, 0.2–0.4 or 0.3–0.6 s | 0.51–0.56 | 0.53–0.57 | 0–2 of 12 |
| All 28 channels × 5 bins (current) | 0.586 | 0.600 | 4 / 3 |
| Midline AFz Cz Pz POz × 5 bins | 0.627 | 0.623 | 3 / 3 |
| C3 C4 × 5 bins | 0.577 | 0.570 | 2 / 2 |

The prespecified rule (midline or a fixed feature at or above 0.70 in at least 7 of 12 sessions) was not met in any run. Midline helps only where the full set was at or below chance and reaches about 0.59 there; no single-trial P300 amplitude separates targets in any participant; the 1 Hz high-pass is not the cause. Channel selection is not the lever. The data descriptor confirms every trial was answered with the right hand (index for targets, middle finger for non-targets), so there is no hand-lateralization confound.

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments channel-check --out outputs/channel_check_dev_reproduction
```

## Burst-flag diagnostic on development data

`burst-diagnostic` places every existing continuous burst flag on VP001, VP002 and VP005 relative to the trial markers, recomputing flags from the frozen models or saved traces and checking them against the saved experiments; it fits nothing. Results: `outputs/burst_diagnostic_dev/INTERPRETATION.md`.

| Model, participant | Target matches | Uniform random mean [95%] | P(random ≥ observed) | Flags farther than 0.5 s from any stimulus |
|---|---:|---:|---:|---:|
| mean_bins, VP001 | 4/36 | 3.0 [0, 6] | 0.35 | 19/30 |
| xdawn, VP001 | 6/36 | 3.0 [0, 6] | 0.07 | 11/29 |
| mean_bins, VP002 | 3/36 | 3.2 [0, 6] | 0.63 | 24/30 |
| mean_bins, VP005 | 2/36 | 3.6 [1, 7] | 0.90 | 26/30 |
| zigzag, VP005 | 6/36 | 3.6 [1, 7] | 0.13 | 15/30 |
| mean_bins + zigzag, VP005 | 3/36 | 3.6 [1, 7] | 0.72 | 17/30 |

No existing detector beats randomly placed flags under the same grid, mask, budget, separation and tolerance, and all fall far below a detector that merely found stimuli (about 9/36). Within-session AUROCs on the continuous grid are 0.48–0.56 for every comparison; only VP001 mean bins shows aligned discrimination (onset-aligned AUROC 0.78). This corrects the earlier reading of zigzag topology as an improvement over mean bins on VP005.

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments burst-diagnostic --out outputs/burst_diagnostic_dev_reproduction
```

## Smoothing on the original VP002 band-power models

The same-participant follow-up is complete: `outputs/smoothing_vp002/INTERPRETATION.md`. This run uses the **exact saved classifiers** behind the original 81–84% band-power result. Original predictions and all 34 stretch events were reproduced. Only exponential smoothing was added, with half-lives selected on calibration folds before evaluation.

| Same VP002 recordings and classifier weights | Original band power | Band power + smoothing |
|---|---:|---:|
| Mean balanced accuracy | 83.0% | 81.5% |
| Whole task blocks matched | 3/9 | 7/9 |
| Returned intervals | 34 | 15 |
| Rest incorrectly included / 72 s | 2.04 s | 5.39 s |

Smoothing improves long-interval recovery while reducing rest rejection. It does not meet the joint improvement criterion, and no default has been replaced. Half-lives are 2/2/0.5 seconds across sessions; the original classifier weights and regularization remain unchanged. This is a follow-up on previously inspected evaluation data, not a fresh validation or a cross-participant comparison.

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments smoothing \
  --data data/shin2018/VP002 --models outputs/workload_vp002 \
  --out outputs/smoothing_vp002_reproduction
```

All 67 tests pass. The command verifies original calibration hashes, baseline scores, byte-identical original event exports and unchanged classifier state. It saves three smoothing wrappers, calibration choices, reports, plots, traces and separate replay event exports. `SmoothedPowerModel.scan(recording)` accepts only EEG samples with the original session/preprocessing identity; invalid windows remain missing and reset the smoother.

## Bayesian stretch and zigzag burst comparison — fresh VP005

The requested comparison is complete; see `outputs/dynamic_tda_vp005/INTERPRETATION.md` and `RESULTS.md`. **Simple exponential smoothing outperformed the Bayesian stretch alternatives. Zigzag TDA improved burst retrieval relative to the ERP baseline, but remained unreliable in absolute terms.** All models used all 28 EEG channels. Each session was calibrated separately; all 36 models were frozen before held-out scoring.

| Stretch pipeline | Mean balanced accuracy | Whole-task matches | Rest included / 72 s |
|---|---:|---:|---:|
| Power baseline | 0.757 | 0/9 | 3.00 s |
| Exponential smoothing | 0.791 | 2/9 | 5.25 s |
| Bayesian DLM | 0.739 | 1/9 | 5.00 s |
| Adaptive Bayesian DLM | 0.781 | 1/9 | 5.25 s |

The adaptive method is a switching Gaussian innovation model using approximate Bayesian inference (IMM), not the published horseshoe dynamic-shrinkage process. A calibrated AR(1) observation-noise model accounts for some window dependence. Invalid windows remain missing and reset state. No stretch alternative met the prespecified criterion of improved whole-task matches without extra rest overlap or lower balanced accuracy. Only 12 rest and 128 task windows survived quality checks.

| Burst pipeline | Matched / 36 target markers | Returned flags |
|---|---:|---:|
| ERP mean-amplitude baseline | 2 | 30 |
| Zigzag topology | 6 | 30 |
| ERP + zigzag topology | 3 | 30 |

TDA uses actual zigzag H0/H1 persistence of short EEG trajectory clouds, with 108 fixed shape descriptors and a calibration-fitted regularized classifier. It scans the same valid grid and uses the same review budget as the ERP baseline. Twenty-four of its 30 flags were unmatched; this is not reliable P300/insight detection or statistical evidence of above-chance retrieval. Median-distance normalization intentionally discards uniform amplitude scaling, so this does not establish sensitivity to arbitrarily small EEG changes. Details, eye controls, known-onset metrics and quality coverage are in the interpretation.

```bash
.venv/bin/python -m pip install -e '.[test,real,topology]'
.venv/bin/python scripts/fetch_shin.py --subject 5 --out data/shin2018/VP005
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments dynamic-tda \
  --data data/shin2018/VP005 --out outputs/dynamic_tda_vp005_reproduction
```

The command preserves existing output directories. It exports calibration cards and models, protocol/source hashes, acquisition audits, shared masks, scores, posterior SD traces, reports, plots and 21 alternative event files. All 65 tests pass; saved weights and fitted states stayed unchanged during inference. VP005 is now known data. Existing combined replay remains unchanged; these new alternatives are not automatically promoted or pooled as independent evidence.

## Combined stretch and burst output

`combined.py` runs a calibrated task/rest stretch model and an ERP burst-candidate model on the **same EEG recording**, independently. Either branch can emit an event. The union is chronological, preserves `signal_type`, and adds reciprocal overlap links without adding scores or confidence. All confirmed stretches remain; a separate burst budget limits duplicate review candidates. Both detectors use the same underlying EEG and can share artifact errors, so agreement is not independent corroboration.

The stretch branch now defaults to the selected smoothed models. `detect_combined` exports stretches with the model's own score definition: a `power_ema` model reports the peak exponentially smoothed margin with `model_version` `smoothing-v1-power-<half-life>s`, never a relabeled raw margin. The integration replay in `outputs/combined_vp002_smoothed/RESULTS.md` returned **15 stretches and 45 burst candidates** across the same nine previously inspected excerpts. The 15 stretches equal the standalone `outputs/smoothing_vp002/session*.power_ema.events.json` apart from navigation links. The 45 burst candidates are identical to the earlier unsmoothed run apart from their stretch links, and the refitted ERP model files have the same SHA-256 as before: the burst branch does not depend on the stretch model. Thirty-two burst candidates overlap smoothed stretches; thirteen do not and are still retained. Counts describe output volume, not accuracy. This is known-data integration verification, not fresh validation of either detector.

The earlier unsmoothed replay in `outputs/combined_vp002/RESULTS.md` (**34 stretches, 45 bursts**, 14 outside stretches) is preserved as the historical baseline and remains reproducible with `--stretch-kind power --workload-models outputs/workload_vp002 --out <new directory>`.

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments combined \
  --stretch-kind power_ema --workload-models outputs/smoothing_vp002 \
  --reference-bursts outputs/combined_vp002 \
  --out outputs/combined_vp002_smoothed_reproduction --top-k 5
```

The runner loads each session's frozen stretch model (`session*.power_ema.joblib` for `power_ema`, `session*.task_rest.power.joblib` for `power`), refuses a branch/file mismatch, fits the existing ERP mean-amplitude method on that session's calibration blocks, and refuses to overwrite an output directory. `--reference-bursts` is optional; when given, the run fails if burst candidates differ from that earlier combined output apart from stretch links. `session*.events.json` contains both event types on the original EEG session clock; `timeline.png` shows intervals and points. Distinct sessions retain distinct clocks. The marker-selected excerpts include 0-back, but inference gets no task/trial labels and there is no target/non-target accuracy claim for these exports. `detect_combined(recording, workload_model, burst_model, top_k=5, offset_s=0)` is the label-free Python entry point for an already preprocessed recording with matching session calibration; it accepts a `WorkloadModel` or a `SmoothedPowerModel`.

All 70 tests pass. Integration verifies unchanged fitted state and saved weights and reproduces the standalone stretch exports. Tests cover burst-only and stretch-only output, retention of bursts outside stretches, reciprocal overlap links, clocks, separate budgets, rejection of mismatched calibration or eye-only controls (including an eye-only base inside the smoothing wrapper), the smoothed exporter's score definition and delayed onset, burst invariance to the stretch model, and the replay loader's branch checks.

## Fourier follow-up — fresh VP004

The sliding Fourier comparison is complete; see `outputs/fourier_vp004/INTERPRETATION.md` and `RESULTS.md`. The finer Fourier spectrum **did not improve the detector**. Fourier power in the original three bands was similar to the filtered-variance baseline; 26 narrow bins were worse on classification and included more rest.

| Same VP004 held-out windows | Existing power | Fourier, 3 bands | Fourier, 26 × 1 Hz bins |
|---|---:|---:|---:|
| Mean task/rest AUROC | 0.652 | 0.657 | 0.578 |
| Mean task/rest balanced accuracy | 0.635 | 0.629 | 0.541 |
| Whole task blocks matched | 0/9 | 0/9 | 0/9 |
| Task time covered | 49.8% | 39.2% | 63.6% |
| Rest time included in confirmed intervals | 13.94 s | 5.75 s | 16.68 s |

All models struggled on this participant. The 1 Hz model's higher task coverage comes with poor rest rejection; it is not a better detector. The three-band FFT control includes less rest but also less task time. Quality checks accepted 149/198 labeled task/rest windows, including only 16 rest windows; task gaps and score fragmentation limit interval recovery. Eye controls and detailed per-session/per-condition metrics remain in the report. Do not compare these figures directly with previous participants.

`fourier.py` keeps the two-second window, 0.25 s hop, common quality mask and three-second segmentation. It compares the old three-band filtered variance with a Hann-tapered real FFT on continuously filtered 1–40 Hz data. The one-sided PSD is integrated either over the same theta/alpha/beta bands or over 26 adjacent 1 Hz bins, retaining absolute log power. The raw FFT grid is 0.5 Hz; effective resolution is limited by window length/tapering. No phase, spectral-flux, or new burst/P300 detector was added. The experiment has no volatility history warm-up.

All six EEG/eye feature sets use the same calibration folds, accepted windows and regularized classifier. A shared C grid of 0.001/0.01/0.1/1/10 permits stronger regularization for the 728-feature narrow-spectrum model. All 36 models were frozen before any held-out scoring. No frequency/window/threshold settings were retuned afterward; the power model remains the baseline, with reliable continuous stretch detection still unestablished.

```bash
.venv/bin/python scripts/fetch_shin.py --subject 4 --out data/shin2018/VP004
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments fourier \
  --data data/shin2018/VP004 --out outputs/fourier_vp004_reproduction
```

Outputs include frozen models and hashes, preprocessing audits, model cards, reports, per-block traces/spectrograms, diagnostic plots and nine alternative replay event files. Use one model's output at a time; alternatives are not independent evidence. The method is locked in `fourier_protocol.md`. All 42 tests pass, including independent SciPy PSD agreement, Parseval power conservation, DC/Nyquist handling, bin partitioning, common window masks and frozen inference.

Reference: [SciPy spectral analysis](https://docs.scipy.org/doc/scipy/tutorial/signal.html#spectral-analysis). Existing band power already measures frequency-specific energy; the Fourier experiment changes its estimator and spectral detail rather than introducing an independent physiological signal.

## Volatility follow-up — fresh VP003

The EWMA comparison is complete; see `outputs/volatility_vp003/INTERPRETATION.md` and `RESULTS.md`. It **did not justify replacing the power model**. Within the same fresh participant, mean task/rest AUROC improved with volatility, but balanced accuracy and rest overlap worsened. Segmentation was unchanged to isolate the feature change.

| VP003 held-out measure | Power | Power + changes | Power + changes + EWMA |
|---|---:|---:|---:|
| Mean task/rest AUROC across sessions | 0.800 | 0.803 | 0.856 |
| Mean task/rest balanced accuracy | 0.685 | 0.727 | 0.672 |
| Whole task blocks matched | 5/9 | 4/9 | 5/9 |
| Intervals returned | 23 | 25 | 27 |
| Rest time included in confirmed intervals | 4.88 s | 4.88 s | 7.82 s |

There were only **13 scorable two-second rest windows**, versus 171 task windows. Signal rejection and the common history requirement removed other windows; only 41.4% of labeled dense rest centers were history-ready. All models used identical remaining train/test windows, but this small sample limits specificity estimates. These numbers cannot be compared directly with VP002. Eye-only task/rest AUROC remained high (mean 0.848 without EWMA), so isolated neural workload is still unproven.

EWMA also reduced mean higher/lower task-demand AUROC from 0.930 to 0.883. The change-only model had the highest task/rest balanced accuracy but matched fewer whole tasks; it is an alternative to investigate rather than a demonstrated better overall detector. The original power model remains the default, and the burst model is unchanged. GARCH was not added after this first volatility test failed the prespecified practical-improvement criterion.

`volatility.py` computes log power every 0.25 s, then adds signed change, log predicted standard deviation and standardized innovation. The EWMA half-life is fixed at two seconds; the current change is scored before updating its reference. History resets at invalid windows and each independent excerpt. All models share a two-second history warm-up, including the power-only control. Classifier fitting/evaluation selects the original nonoverlapping two-second grid. C is retuned separately for every session, feature set and target using the existing whole-block folds; nothing was tuned on held-out results. The temporal recursion uses earlier features, while underlying filtering remains offline/zero-phase.

```bash
.venv/bin/python scripts/fetch_shin.py --subject 3 --out data/shin2018/VP003
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments volatility \
  --data data/shin2018/VP003 --out outputs/volatility_vp003_reproduction
```

Outputs contain 30 frozen classifiers (five EEG/eye feature sets × two targets × three sessions), model cards, audits, protocol/source hashes, plots, traces and nine alternative EEG event files. Use one EEG model's exports at a time; the alternatives are predictions from the same signal, not independent sources to merge. `volatility_protocol.md` documents the locked comparison. All 37 tests pass, including independent weighted-moment verification and checks against future/current-shock leakage into the volatility forecast.

## Learned workload result — fresh VP002

See `outputs/workload_vp002/INTERPRETATION.md` and `RESULTS.md`. The new `workload.py` branch fits labeled **task/rest** and **higher/lower task demand** scorers instead of requiring a fixed frontal-theta rise. All three VP002 sessions use their own early six calibration blocks and final three evaluation blocks. All model settings were frozen before held-out scoring; calibration weights do not transfer from VP001 or between sessions.

| Primary log-band-power model | Session 1 | Session 2 | Session 3 |
|---|---:|---:|---:|
| Task/rest AUROC | 0.909 | 0.911 | 0.935 |
| Task/rest balanced accuracy at zero margin | 0.844 | 0.831 | 0.814 |
| 2-/3-back versus 0-back AUROC, task windows only | 0.984 | 0.992 | 1.000 |

These are nonoverlapping two-second windows, not independent participants: each session has only three held-out task blocks. **The eye-only control also separates task difficulty strongly (AUROC 0.914–0.971).** These results establish task-related signal differences, not isolated brain workload. No eye-control subtraction or claim of incremental neural information is justified by these scores alone.

| Continuous task/rest interval output | Power, primary | Tangent, comparator | Previous fixed theta rule |
|---|---:|---:|---:|
| Intervals returned | 34 | 21 | 1 |
| Task blocks matched at IoU ≥ 0.5 | 3/9 | 8/9 | 0/9 |
| Task time covered | 78.4% | 96.4% | 0.9% |
| Labeled rest time flagged, out of 72 seconds | 2.04 s | 22.20 s | 0.00 s |

The power model often fragments a task into several stretches. Tangent intervals cover more of each task but also flag much more rest. A high ranking score does not guarantee a useful event boundary. No segmentation settings were adjusted using these results.

Onset gating still excludes most labeled target markers: 12/36 remain eligible for the power model's gates and 1/36 for tangent gates, versus 36/36 on the full valid ERP grid. This is eligibility, not burst detection; the ERP classifier was not retrained. More fragmented stretches create more onset gates, so gate coverage alone cannot validate the biological leading-edge hypothesis. Keep full burst scanning available.

```bash
.venv/bin/python scripts/fetch_shin.py --subject 2 --out data/shin2018/VP002
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments workload \
  --data data/shin2018/VP002 --out outputs/workload_vp002_reproduction
```

The command refuses to overwrite an experiment directory. It saves a protocol/source snapshot, acquisition and EOG-correction audits, model cards, 18 fitted classifiers plus three theta references, per-session reports/plots, and six chronological event files. Use `session*.power.events.json` as the primary replay stretch output; tangent files are alternative predictions and must not be added as independent evidence. The exported stretches have `replayed_eeg` provenance, `eeg_workload_candidate` type, uncalibrated peak margins, and null confidence. They do not correspond to the phone video's subject.

Both EEG feature models use theta/alpha/beta windows: log variance or Ledoit–Wolf covariance followed by a frozen affine-invariant tangent map. Standardization and class-balanced logistic regression are fitted inside two whole-block calibration folds, with C selected from 0.01/0.1/1/10 by AUROC. The sustained branch has no ERP prototype or local-context subtraction. A nonnegative score sustained for three seconds creates an interval; rejected centers break it. `WorkloadModel.scan(recording)` receives no task or trial markers. Preprocessing identity and session checks remain mandatory; this real model uses the `workload` workflow, not synthetic `detect`.

`workload_protocol.md` records the prespecified method. `verification_notes.json` records a correction to the final model-integrity check: serialization alone changed an object hash, so the check now compares each in-memory object before and after inference and independently verifies saved-file hashes. All 21 saved models, held-out scores, metrics and event exports were identical on repetition. The initial run is retained in `outputs/workload_vp002_initial_guard_check`; repetition is software verification, not a second independent experiment.

## Real EEG result

See `outputs/real_vp001/RESULTS.md` and `report.json`. Three sessions were calibrated independently on their first six task blocks and evaluated on the final three blocks. The data were downloaded unchanged from the authors' archive; original member CRCs and SHA-256 hashes are recorded in `data/shin2018/VP001/download_manifest.json` and the session audits. Marker timing differs from nominal task timing, so the loader uses recorded timestamps rather than imposing 2-second intervals.

| Check | Held-out result |
|---|---|
| Simple ERP mean-amplitude model, known stimulus onsets | AUROC 0.753 / 0.735 / 0.818 across the three sessions |
| Framework xDAWN + tangent covariance, known onsets | AUROC 0.542 / 0.399 / 0.452 |
| Simple model scanning without trial timestamps | 4 target matches among 30 returned flags; 36 total target markers |
| Framework model scanning without trial timestamps | 6 target matches among 29 flags; 36 total targets |
| Fixed frontal-theta stretch rule | No detected stretches on nine held-out task blocks |

Known-time discrimination is a positive control, not marker-free detection. The current continuous retrieval and stretch rule are not demonstrated to provide reliable work-session moments. Task intervals/target markers are behavioral proxies, not ground-truth insight or guaranteed visible P300s. Onset gates were empty because the stretch rule did not trigger, so this run cannot settle whether a *working* stretch detector would improve burst retrieval.

The preprocessing audit initially rejected nearly all calibration data. Before looking at held-out scores, a separate pre-task EOG regression was added and quality checks were aligned to the analyzed 1–30 Hz band. Coefficients are frozen per session; their calibration segment does not overlap labeled blocks. Original voltages remain unchanged on disk. This correction can also remove eye-correlated EEG; the report includes an EOG-only classification control and waveform diagnostics. The method changes and rationale are recorded in `real_eeg_protocol.md`. No settings were retuned after held-out results.

To reproduce (MNE is the optional real-data dependency):

```bash
.venv/bin/python -m pip install 'mne==1.10.1'
.venv/bin/python scripts/fetch_shin.py --subject 1 --out data/shin2018/VP001
.venv/bin/python -m eeg_moments real --data data/shin2018/VP001 --out outputs/real_vp001
```

The downloader retrieves only the original n-back members via HTTP ranges and verifies ZIP CRCs; it does not synthesize or splice signals. A previously interrupted full-archive request is retained as `.zip.part`, not used for analysis. The analysis command runs entirely offline once files/dependencies are present.

Real outputs include per-session acquisition audits, protocol snapshot, models/model cards, figures, reports, and chronologically ordered `*.events.json` files with `replayed_eeg` provenance. The real ERP models use the `real` workflow, not the synthetic `detect` command. Their input must carry the exact calibrated ocular preprocessing identity; the model rejects raw or differently corrected samples. These results are experimental and are not validation that events match a separately filmed person.

The next workload experiment is now completed on VP002, above. VP001 and VP002 results are now known; future tuning must not reuse their held-out blocks as a claimed fresh validation.

## Run now

The project already has a local `.venv` with the dependencies installed. From this directory:

```bash
.venv/bin/python -m eeg_moments demo --out outputs/eeg_demo
.venv/bin/python -m pytest -q
```

For a fresh Python 3.11+ environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

Ubuntu may require its `python3-venv` package to create a pip-enabled environment. `requirements.lock.txt` records the complete environment used for this run.

The demo generates six calibration blocks, trains both models, and evaluates ten held-out scenario blocks. Calibration and evaluation use different noise/event seeds but share one virtual session's spatial mixing. Scenarios reuse three held-out noise backgrounds for paired comparisons; the ten blocks are **not** ten independent samples.

Outputs:

| File in `outputs/eeg_demo/` | Contents |
|---|---|
| `RESULTS.md`, `report.json` | Retrieval results, gate coverage/recall, controls, and limitations |
| `diagnostic.png` | Samples, detected stretches, gates, classifier scores, and evaluation-only injection truth |
| `power.joblib`, `tangent.joblib` | Session-specific fitted models |
| `*.model_card.json` | Configuration, selected regularization, calibration hashes, limitations |
| `power.all.events.json`, `tangent.all.events.json` | Full-scan burst events plus independent stretch events, chronologically |
| `power.onset.events.json`, `tangent.onset.events.json` | Burst events restricted to onset gates, plus all confirmed stretch events |
| `calibration/manifest.json` | Reusable training manifest |
| `evaluation/`, `evaluation_truth/` | Separate EEG samples and hidden injection truth |

## First result and deployment choice

At the default seed, both models recovered all 18 injected packets across the mixed and independent scenarios during full scans. Onset-only search recovered 5/18, while examining about 11.6% of scorable window centers. Neither burst classifier emitted a burst flag on the two no-burst control blocks; those blocks correctly still produce stretch events. These are easy, small, generator-specific controls, **not an accuracy estimate for real EEG**.

The mixed scenario deliberately plants only one of three bursts near a stretch onset; the others occur late in a stretch and outside a stretch. The independent scenario samples burst timing without referencing stretch timing. The third stretch in each mixed block has no burst. Blink-like and muscle-like disturbances are also present.

Two additional `baseline` controls contain neither injected stretches nor bursts, while retaining artifacts. The benchmark separately scores stretch interval recovery using one-to-one matches with intersection-over-union (IoU) ≥ 0.5, plus onset/end error. See `stretch_summary` and each block's `stretch_detection` in `report.json`; burst and stretch results have separate denominators.

The result demonstrates that the gate can discard otherwise detectable candidates. It does not disprove the biological onset hypothesis; the simulator chooses the timing relationship. There is no measured advantage for covariance over power here. For the demo, use the **power model with full scanning**, retain the tangent model as the framework implementation, and keep onset gating as an explicit comparison. Both outputs preserve each candidate's relationship to the nearest detected stretch.

## Detect a new block and export for the timeline

```bash
.venv/bin/python -m eeg_moments simulate \
  --out outputs/new_block --seed 3000 --session-seed 19

.venv/bin/python -m eeg_moments detect \
  --recording outputs/new_block/recording.npz \
  --model outputs/eeg_demo/power.joblib \
  --scope all --top-k 5 \
  --session-id phone-session-001 --offset-s 0 \
  --out outputs/new_block/events.json
```

`detect` takes **no truth file**. Use `--scope onset` for the leading-edge burst experiment. `--scope` and `--top-k` apply only to bursts; all confirmed stretches are exported independently. With `--top-k 5`, an output may contain five bursts plus several stretches. Setting `--top-k 0` returns stretches only. The current benchmark implementation scores the full recording before applying gates so that both searches can be compared; it does not claim a measured inference speedup from gating.

`--offset-s` places the EEG block on the video's playback clock. This is an authored demo convention, not a physiological alignment. It must be nonnegative. The media integration must additionally check the final timestamps against the video duration. `--session-id` changes the output work-session ID without bypassing EEG calibration checks.

Flags include:

- Stable event ID, session IDs, recording ID, and explicit `synthetic_eeg` provenance.
- `signal_type: "burst"` or `"stretch"`. Stretches use `synthetic_stretch_candidate`; bursts retain `synthetic_transient_candidate` for compatibility.
- `start_s`, `end_s`, `anchor_s`, original `eeg_anchor_s`, and the playback offset.
- Burst decision margin or stretch peak robust z, `confidence: null`, rank, and `review_priority`.
- Bursts: `within_onset_gate`, nearest stretch onset, and offset from that onset. Stretches: full interval, duration, and confirmation time; anchor is the estimated onset.
- Reciprocal `overlapping_stretch_ids` / `overlapping_burst_ids` for navigation. Overlap keeps both events and does not increase confidence.
- Model/version and evidence text that names the synthetic signal.

Map `high` → red, `medium` → yellow, `low` → green. These are **relative rank thirds within each signal type**, not physiological intensity, calibrated confidence, or comparable scores across sources/types. A single returned candidate of a type is high priority by this rule. A burst interval is the scored feature window; a stretch interval is the detected sustained rise. Neither is a timing confidence interval. The timeline can place a dot at each anchor while showing stretch duration as a bar or in event details.

This package exports events. Phone capture, clip extraction, VLM integration, and the timeline UI remain separate work.

## Signal and model choices

1. **Quality checks:** require finite samples, exact channel order, explicit microvolt units, matching sample rate and session. Reject gross amplitude/step artifacts and local flat channels. Interpolate rejected samples only to keep filtering numerically stable; reject affected feature/context windows with a 2 s guard. This is limited artifact handling, not complete EEG cleaning.
2. **Continuous filtering:** fourth-order Butterworth filters, offline zero phase, in theta (4–8 Hz), alpha (8–13 Hz), and beta (13–30 Hz). Each independent block is processed separately. A numerical impulse test checks residual filter response beyond the guard; IIR filters do not have exact finite support.
3. **Stretch reference:** frontal theta log power in centered 2 s windows. Fit median and scaled MAD from clean calibration baselines only. Enter at robust z ≥ 3, release below 1.5, require 3 s duration. Store estimated onset and confirmation separately. Search ±3 s around **estimated onset**, not confirmation. This is a power heuristic, not a validated cognitive-load score.
4. **Burst windows:** 750 ms windows every 250 ms, with two equal-duration background windows centered 2 s before/after. Background features describe local departures. Filters, context, and smoothing limit temporal resolution; the grid spacing is not detection precision.
5. **Power model:** log variance per band/channel, concatenated with the difference from mean surrounding log variance.
6. **Tangent model:** Ledoit–Wolf covariance per band; one affine-invariant reference fitted on the current windows in each training fold; frozen tangent maps for current/background windows; concatenate current coordinates and their local contrasts. The implementation uses pyRiemann's Ledoit–Wolf normalization, not a hand-coded unbiased sample estimator. Tests independently check the matrix-log mapping and √2 off-diagonal weighting to 1e-10 absolute tolerance.
7. **Classifier:** standardize coordinates and fit class-balanced L2 logistic regression. Tune C over 0.01, 0.1, 1, 10 using three-fold **recording-group** CV on calibration only. Every fold refits references/scaler/classifier. Select by average precision; report this as a model-selection score, not held-out performance. Re-running training retunes C. There is no learning-curve benchmark yet.
8. **Retrieval:** provisional nonnegative decision-margin acceptance, then descending rank, 2 s suppression, and a maximum of five events per 180 s test block. No forced event if all margins are negative. This acceptance rule is fixed for the engineering test and is not calibrated to a real-world false-alarm rate.

No xDAWN/prototype augmentation is used for these phase-variable packets. An ERP/P300 branch would require suitable independently labeled, time-aligned real calibration trials; changing only the labels would not implement it.

## Input and calibration contract

NPZ files load with `allow_pickle=False` and contain:

| Key | Type / meaning |
|---|---|
| `samples` | Finite float array, channels × samples, microvolts |
| `sample_rate` | Scalar Hz; default model requires 128 |
| `channels` | String array in exact model order |
| `units` | Literal `uV` |
| `session_id` | EEG acquisition/calibration session ID |
| `recording_id` | Unique continuous block ID |
| `source` | `synthetic_eeg`, `replayed_eeg`, or `recorded_eeg` |
| `processing_id` | Explicit preprocessing identity; defaults to `raw` for older NPZ files |

Default channels: `Fp1 Fp2 F3 F4 C3 C4 P3 P4`; default frontal subset: `Fp1 Fp2 F3 F4`. Missing or reordered channels raise an error. The loader never silently selects an intersection. New configurations can be passed through the Python `Config` API and require retraining. Synthetic models refuse real/replayed input, and models refuse a different EEG session.

Training manifest format (paths relative to the manifest):

```json
[
  {"recording": "block-01.npz", "labels": "block-01.labels.json"},
  {"recording": "block-02.npz", "labels": "block-02.labels.json"},
  {"recording": "block-03.npz", "labels": "block-03.labels.json"}
]
```

Each label file has `recording_id`, `baseline_intervals_s` (pairs of seconds), `bursts` (objects with `anchor_s`), and optional `artifacts` (objects with `start_s`/`end_s`). Positive calibration windows are within 250 ms of the labeled center; negatives are at least 1.5 s away. Negatives are sampled reproducibly, with additional artifact-adjacent negatives. Labels describe the simulator's injected packet centers in this version; real annotations need an independently justified label/window rule.

```bash
.venv/bin/python -m eeg_moments train \
  --manifest outputs/eeg_demo/calibration/manifest.json \
  --kind tangent --out outputs/retrained/tangent.joblib
```

At least three independent blocks from one session are required. Group IDs and sample hashes catch exact duplicate blocks; callers must also ensure blocks do not overlap. Keep overlapping windows/event siblings in one block. Only load trusted locally produced `.joblib` models because this format executes Python during deserialization.

## Evaluation and next scientific step

The report measures one-to-one packet recovery within 1 s, precision among returned flags, recall at the review budget, candidate recall, rejection counts, and gate coverage as a fraction of **valid window centers**. It includes onset/midpoint/end gates, a matched-count random gate within detected-work positions, full scanning, and stretch-only ranking. Random controls are descriptive; they do not establish significance.

[Shin et al.'s dataset A](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/) contains 0-/2-/3-back tasks and target/non-target ERP responses in the same recordings. The real-data section above describes the completed first test and its limitations. The real ERP branch is separate from the synthetic oscillatory classifier. Separate workload and ERP datasets could also validate their respective components individually, but would not test their timing relationship.

The model follows the design in `burst_framework.md`. `session_pipeline.md` describes how EEG events and audio/video events remain separate evidence while sharing playback clips.

Primary implementation references: [pyRiemann TangentSpace](https://pyriemann.readthedocs.io/en/latest/generated/pyriemann.tangentspace.TangentSpace.html), [scikit-learn GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html), [MNE filtering background](https://mne.tools/stable/auto_tutorials/preprocessing/25_background_filtering.html).
