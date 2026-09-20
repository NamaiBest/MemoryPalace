# EEG moment retrieval — LLM handoff

Updated 2026-09-19. Workspace: `/home/albert/hackmit` (WSL Ubuntu). Windows path: `\\wsl.localhost\Ubuntu-24.04\home\albert\hackmit`.

## Read this first: latest user decisions

**Keep both stretch and burst detection. Use learned band power plus exponential smoothing as the chosen stretch approach. Focus new research effort on short bursts.** The immediately preceding suggestion to remove stretches from the product's useful signals was superseded by the user. Do not discard stretch outputs or restart a broad search for a better stretch model.

This is a practical model selection, not a claim that smoothing wins every metric. It produces more complete intervals on the original VP002 recordings, with worse rest rejection and slightly lower balanced accuracy. Preserve that tradeoff when explaining the choice.

**No reliable real-EEG burst detector has been established.** The next objective is to improve retrieval of brief candidate moments while retaining the chosen stretch branch independently. A stretch must not be required for a burst to be returned. A burst must not be required for a stretch to be retained.

**Decision 2026-09-20 (option 3):** the EEG model handles broad state changes (stretches); audio/video handles brief moments; burst research is stopped. The state detector is the entry for the Voloridge "find signal in noise" track. `outputs/backtest_state/` holds the walk-forward figures, the circular time-shift null and `INTERPRETATION.md` written for that audience; `backtest` regenerates them from the saved models.

**Burst status after 2026-09-19: at chance on four participants.** A development diagnostic (`outputs/burst_diagnostic_dev/`) showed that no saved continuous burst detector on VP001, VP002 or VP005 retrieves n-back targets better than randomly placed flags under the same grid, mask, budget and tolerance, correcting the earlier reading of zigzag topology as an improvement. A frozen comparison on untouched VP006 (`outputs/background_vp006/`) then tested calibration-only background negatives: 2/36 versus 0/36, still within random placement; not adopted. The same run validated the chosen stretch approach on VP006 at balanced accuracy 0.60 with 28 of 72 s rest included, far weaker than VP002. A channel-set check afterwards showed that no small channel set, fixed single-trial P300 amplitude or wider filter band carries a usable aligned target signal in three of the four participants. The next step is a user decision (see "Where to continue"), not another representation.

This handoff and the current product notes record the new selection. The `combined` CLI now loads the selected smoothed wrappers by default; the smoothed integration replay is saved in `outputs/combined_vp002_smoothed/` and the earlier unsmoothed replay is preserved unchanged. No model files or earlier experiment outputs were modified.

The user wants direct, critical reasoning, concise explanations, and progress within a hackathon time budget. Challenge unsupported claims rather than agreeing automatically. The project originally had about 20 hours; the remaining time is not known. Do not assume a new 20-hour budget.

## Product and hardware situation

Record a work session using phone video and audio. Identify moments worth revisiting, then display saved recordings on a chronological timeline. A brief event flagged by either the EEG branch or the audio/video branch can trigger retrieval; agreement is not required.

- No usable EEG acquisition hardware is available. Gold cup electrodes were available, but there was no acquisition board; NeuroSky was also unavailable.
- The demo uses explicitly synthetic EEG or explicitly replayed public EEG. Neither measures the person in the phone recording.
- Do not splice unrelated P300 and workload recordings and claim the result tests natural burst/stretch coupling. No such dataset merge was performed.
- Processing is offline after the session. The intended brief-event clip is `[event timestamp, event timestamp + 30 seconds]`, truncated at recording end. Anchor it to estimated occurrence time, not inference completion time.
- Preserve the full original recording. Optional 5–10-second pre-roll was suggested because post-event-only clips can miss the cause of a realization; the user has not adopted it as the default.
- Retain stretches as a separate signal, with interval start/end, onset, confirmation time, and score. Their dedicated clip behavior is not settled by the latest request; do not silently drop them or assume every long interval must become a 30-second clip.
- The intended audio/video provider is Elastic. The user will provide the actual API/model later. No working VLM adapter or confirmed timestamp/audio interface exists here.
- Audio/video cues include explicit spoken realization/difficulty and visible task changes. They are observations, not necessarily physiological EEG bursts.
- Timeline colors: red/high, yellow/medium, green/low **review priority**, not calibrated psychological intensity. Preserve source badges and evidence.
- Source flags may share playback, but temporal overlap does not establish the same internal occurrence or justify increasing confidence. Alternative EEG models also are not independent evidence.

This folder implements EEG research and event export. Phone capture, production clip extraction, VLM integration, and an interactive timeline UI are not implemented by this package. There are diagnostic plots, including a combined timeline PNG.

## Data and evaluation contract

Real experiments use **Shin et al. 2018, dataset A, n-back**, not the proposed Nirabi arithmetic/Stroop merge. Local originals are under `data/shin2018/VP001` through `VP005`, plus `VP006`, used on 2026-09-19 for the frozen background-negatives comparison and chosen-stretch validation (`outputs/background_vp006/`); it is now inspected. VP007 and later are untouched and not downloaded (`scripts/fetch_shin.py --subject 7`). Source: [authors' dataset page](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/), [data descriptor](https://doi.org/10.1038/sdata.2018.3).

Each participant has three recordings treated as separate sessions. Each session contains nine task blocks: three each of 0-, 2-, and 3-back. The first two occurrences of each condition (six blocks) calibrate that session; the final three blocks evaluate it. There are nine evaluation task blocks per participant. Classifier tuning uses whole calibration blocks, not shuffled neighboring windows.

Calibration means fitting artifact correction, feature transforms/scaling, classifier weights, regularization, and applicable temporal settings using designated earlier data. It does not mean inspecting test results and adjusting the detector. Fitted session-specific weights must not be reused across people or sessions under the current contract.

Original acquisition: 30 recorded channels = **28 EEG + HEOG/VEOG**, 1000 Hz, TP9 reference. Analysis uses 200 Hz. All 28 EEG channels were retained:

```text
Fp1 AFF5h AFz F1 FC5 FC1 T7 C3 Cz CP5 CP1 P7 P3 Pz POz O1
Fp2 AFF6h F2 FC2 FC6 C4 T8 CP2 CP6 P4 P8 O2
```

EOG channels are excluded from EEG feature inputs and used for frozen pre-task eye regression and separate eye-only controls. Removing EOG inputs alone does not remove ocular contamination from scalp EEG. No Fp1/Fp2 or other electrode-removal experiment was run.

`shin.py` checks channel identity/order explicitly, preserves original marker times, anti-aliases resampling, and records acquisition/preprocessing audits. Actual stimulus spacing is about 2.2 seconds; task end is estimated from the last stimulus plus the block's median interval. Do not substitute nominal 40-second blocks.

Paradigm facts from the data descriptor (verified 2026-09-19 via the open-access full text): each trial shows a one-digit number for 0.5 s followed by a fixation cross, 20 trials per block with 30% targets; every trial is answered with the right hand, index finger for targets and middle finger for non-targets, so there is no hand-lateralization confound; each stimulus also carries an auditory beep, so every trial evokes N100/P200 components; the descriptor reports a P300 near 400 ms and the largest target/non-target difference at 0.2–0.4 s over frontal, central and parietal sites in grand averages.

Each analyzed excerpt includes a task and about ten seconds of surrounding context on either side. Labeled rest is four seconds before and four seconds after each task, away from its boundaries: **72 seconds across the nine evaluation blocks**. This is too little rest to establish a practical hourly false-alarm rate. Excerpts were selected using task markers; scanning receives no trial markers, but this is not an unrestricted one-hour work-session test.

Eye correction fits a two-channel linear regression on a separate pre-task segment and freezes it before labeled calibration/evaluation. Quality checks use a 1–30 Hz copy, fixed amplitude/step/flatline limits and a two-second guard. Rejected windows stay missing and break intervals/reset smoothing. Eye regression can remove eye-correlated neural activity; it does not prove clean cortical signals. See `real_eeg_protocol.md` for the calibration-only corrections made before the first held-out scoring.

All VP001–VP006 outcomes are now known. Reproducing them checks software, not fresh generalization. Within-experiment paired comparisons are meaningful; comparing a headline score from VP002 with one from VP005 does not isolate an algorithm improvement. Preserve raw originals, calibration/test separation, preprocessing identities, and experiment output directories.

## Chosen stretch branch: learned band power + smoothing

Implementation: `workload.py` plus `smoothing.py`.

1. Compute theta 4–8 Hz, alpha 8–13 Hz, and beta 13–30 Hz log variance across all 28 channels: 84 features from two-second windows.
2. Fit a standardized, class-balanced regularized logistic classifier for **task versus rest**. The original workload run selects C from 0.01/0.1/1/10 using whole-block calibration folds.
3. Scan every 0.25 seconds. Smooth classifier margins with an exponential moving average. Invalid windows reset the smoother; do not bridge quality gaps.
4. Require a nonnegative score for at least three seconds to emit a stretch. This is a task-like interval candidate, not a direct cognitive-state measurement.

The controlled smoothing follow-up reuses the exact original VP002 classifiers. Only half-life is selected from 0.5/1/2 seconds using calibration out-of-fold predictions, holding the original C fixed. Temporary fold fits are used for selection, never substituted for the original evaluation classifier. Selected half-lives for sessions 1/2/3 were **2 / 2 / 0.5 seconds**. Do not hard-code these as universal values for new sessions.

| Same VP002 recordings and classifier weights | Original band power | Band power + smoothing |
|---|---:|---:|
| Mean balanced accuracy | 83.0% | 81.5% |
| Mean AUROC | 0.919 | 0.925 |
| Whole task blocks matched | 3/9 | 7/9 |
| Returned intervals | 34 | 15 |
| Task time covered | 78.4% | 86.2% |
| Rest included, out of 72 seconds | 2.04 s | 5.39 s |

A whole-task match means one predicted interval matches a task interval with intersection-over-union at least 0.5, one-to-one. This rewards interval completeness; it is not burst recall. Rest rejection means leaving labeled rest outside predicted stretches. Balanced accuracy averages task sensitivity and rest specificity; AUROC measures score ranking, not percentage correctness.

The smoothing comparison used 207 accepted two-second classification windows: 180 task and 27 rest. Original raw predictions reproduced to 1e-12 and all three original event exports reproduced byte for byte. It is an exploratory follow-up on previously inspected VP002, not a fresh test.

Earlier covariance/tangent results on the same VP002 data recovered 8/9 tasks but included **22.20/72 seconds of rest**. Smoothed power is the user's chosen compromise: 7/9 with 5.39 seconds. Neither dominates all metrics. Strong eye-only performance on VP002 remains a major confound (task/rest AUROC 0.817–0.967).

**Fresh VP006 validation (2026-09-19, `outputs/background_vp006/`):** the same recipe fitted per session on VP006 calibration blocks gave, on the nine evaluation blocks, power AUROC 0.660 / balanced accuracy 0.586 / 2/9 whole-task matches / 19.82 of 72 s rest included, and power + EMA 0.669 / 0.604 / 6/9 / 28.00 s (half-lives 0.5/0.5/2 s). Calibration CV AUROC was 0.844, 0.501 and 0.527 by session, so two of three sessions barely separated task from rest even in calibration. Smoothing again completed intervals at the cost of rest: 39% of labeled rest was flagged. Describe the chosen approach with the range VP002–VP006 (balanced accuracy 0.60–0.82, rest included 5–28 of 72 s), not with VP002 alone.

**Walk-forward view and shift null (2026-09-20, `outputs/backtest_state/`):** `backtest.py` rescans all nine blocks per session with the saved models (VP002 smoothing wrappers, VP003 volatility power, VP004 Fourier power, VP005 dynamic power/EMA, VP006 background power/EMA), draws calibration then out-of-sample traces, and scores each out-of-sample session against 2000 circular shifts of its intact score trace. Recomputed out-of-sample AUROCs equal every saved report. Sessions beating the null at 0.05: VP002 3/3, VP003 1/3, VP004 1/3, VP005 2/3, VP006 1/3. Null 95% intervals reach 0.8 because a task period covers most of an excerpt; that width is the cost of autocorrelation and is reported, not hidden. Eye-only controls sit near the EEG detector on VP002/VP003 (0.85–0.88) and far below it on VP005 (0.56); VP006 had no eye control.

Use these existing artifacts:

- `outputs/smoothing_vp002/session{1,2,3}.power_ema.joblib`: selected, session-specific wrappers.
- `outputs/smoothing_vp002/session{1,2,3}.power_ema.events.json`: selected replay stretch outputs.
- Matching `.model_card.json` files: half-lives, folds, identities, and selection details.
- `outputs/smoothing_vp002/INTERPRETATION.md`, `RESULTS.md`, `report.json`: interpretation and metrics.
- Original classifiers remain in `outputs/workload_vp002/session{1,2,3}.task_rest.power.joblib`.

`SmoothedPowerModel.scan(recording)` returns times, smoothed scores, raw scores, validity, and intervals. `export_smoothed_events(...)` labels the score correctly as a **smoothed** margin. This branch differs from the synthetic detector's old fixed-theta rule and from the volatility experiment's EWMA feature extension.

## Main open objective: short bursts

There are two different experimental targets. Do not conflate them:

- **Synthetic oscillatory packets:** short increases of band-limited activity, with variable phase, injected by a simulator.
- **Real ERP proxy:** EEG windows associated with labeled n-back target stimuli. Labels identify task targets, not guaranteed P300 presence, spontaneous insight, or confusion.

### Synthetic implementation and result

`synthetic.py`, `signal.py`, `model.py`, `benchmark.py` implement an eight-channel, 128 Hz virtual session with 180-second blocks. Channels are Fp1/Fp2/F3/F4/C3/C4/P3/P4. This is a different input contract from the real 28-channel models.

The burst pipeline uses 750 ms windows on a 250 ms grid, three frequency bands, and local background contrasts. Compared features are log band power versus Ledoit–Wolf covariance mapped into a training-fitted Riemannian tangent space. Both use standardized, regularized linear classifiers, with C retuned on calibration recording groups. No evoked prototype is used for phase-variable packets.

Both models recovered **18/18 injected packets** with full scanning versus **5/18** near detected stretch onsets. The stretch rule recovered 24/24 injected stretches, with one false stretch. These small, easy generator-specific results validate plumbing, not biological detection. The generator chose the burst/stretch timing relationship. They do not establish that full scanning is universally better on real EEG.

The tangent-space numerical checks agree with an independent calculation to 1e-10 absolute tolerance. That verifies a computation, not the physiological hypothesis. No measured covariance advantage over power appeared in this synthetic test. Synthetic demo defaults use power/full scanning; the real chosen smoother is not fitted to these eight-channel signals.

### Real ERP baseline, VP001

`erp.py` implements known-onset calibration epochs from −0.1 to +1.0 seconds, with baseline correction and 1–30 Hz filtering. Mean-amplitude features are five 200 ms post-stimulus bins across channels. The framework comparator uses xDAWN (three target filters), prototype covariance, a fitted tangent map, scaling, and regularized logistic regression.

| VP001 model | Known-onset AUROC, sessions 1/2/3 | Continuous target matches | Returned flags |
|---|---|---:|---:|
| Mean-amplitude bins | 0.753 / 0.735 / 0.818 | 4/36 | 30 |
| xDAWN + covariance/tangent | 0.542 / 0.399 / 0.452 | 6/36 | 29 |

Continuous scans propose onset every 0.1 seconds without trial timestamps. Accept nonnegative margins, suppress candidates within 1.5 seconds, and return up to five per held-out 2-/3-back excerpt. Evaluation matches targets one-to-one within ±0.5 seconds. Zero-back is excluded from this target/non-target task because its marker scheme lacks the corresponding negative class.

The simple model ranks known-time trials better, but neither is a reliable continuous detector. Known-marker classification and finding unknown event times are different problems. An anchor here is a proposed **stimulus onset**, not the peak of a P300 or the precise time of a realization.

The old fixed frontal-theta rule found zero stretches on VP001; its onset-gated scans were empty. After learned stretch models were added on VP002, power onset gates left only 12/36 targets eligible and tangent gates only 1/36, versus 36/36 on the full valid grid. Those are **eligibility counts**, not detected bursts. No demonstrated stretch-gating advantage exists. Keep full scanning and retain stretch relationships as metadata.

### Actual zigzag TDA, VP005

`topology.py` uses Dionysus to compute actual zigzag H0/H1 persistence, not a name for generic signal wiggles. A 28-channel, 220-sample epoch is downsampled to 25 Hz. Five overlapping point clouds and adjacent unions form the zigzag sequence, at three fixed distance scales. Components/loops yield 108 fixed descriptors, followed by calibration-fitted regularized classification. Rips complexes include filled triangles.

Median-distance normalization intentionally removes uniform amplitude scaling. This is a shape representation, not a guarantee of sensitivity to arbitrarily small changes. Lifetimes are zigzag stages, not milliseconds. The descriptor needs the full 1.1-second epoch.

| Same VP005 data and review budget | Target matches | Returned flags | Matched fraction of flags | Mean known-onset AUROC |
|---|---:|---:|---:|---:|
| ERP mean-amplitude baseline | 2/36 | 30 | 6.7% | 0.516 |
| Zigzag alone | 6/36 | 30 | 20.0% | 0.552 |
| ERP + zigzag | 3/36 | 30 | 10.0% | 0.606 |

Zigzag is the strongest continuous-retrieval result **within this comparison**, but 24/30 flags were unmatched and 30/36 targets were missed. The later development diagnostic showed 6/36 is inside the range of uniformly random flags on this grid (mean 3.6, 95% interval 1–7, probability 0.13 of at least 6); it is not an improvement over chance. An unmatched flag is not proof of absent neural activity; it is unmatched to this task's target label. The result is not a significance test or validated above-chance insight detection. The combination's better known-onset AUROC did not produce better continuous retrieval.

The shared quality/edge mask left 30/36 targets accessible and rejected 1,248/3,735 continuous candidate windows. Known-onset analysis retained 95/120 trials including 30 targets. All settings and 36 models across stretch/burst/control branches were frozen before VP005 evaluation. Do not compare VP005 zigzag directly against VP001 xDAWN as a common-data leaderboard.

Artifacts: `outputs/dynamic_tda_vp005/session*.burst.{mean_bins,zigzag,mean_bins_zigzag}.joblib` and matching `.events.json`, plus `INTERPRETATION.md`, `RESULTS.md`, and reports. These are experimental alternatives, not a promoted production burst model. Do not pool their predictions as independent evidence.

### Development diagnostic and fresh VP006 comparison (2026-09-19)

`burst_diagnostic.py` (`burst-diagnostic` CLI) recomputed every saved continuous flag on VP001, VP002 and VP005 from the frozen models or traces, verified them against the saved experiments, and placed them relative to the markers. Under the same grid, mask, five-flag budget, 1.5 s separation and ±0.5 s tolerance, uniformly random flags match 3.0–3.6 of 36 targets; every saved result (2–6) lies inside the random 95% interval, and all lie far below the roughly 9/36 that a detector finding stimuli without target discrimination would reach. Between 57% and 87% of flags fall farther than 0.5 s from any stimulus. Within-session AUROCs on the continuous grid are 0.48–0.56 for target versus background, stimulus versus background and target versus non-target windows. Aligned discrimination exists only for VP001 mean bins (onset-aligned AUROC 0.78). Two failure modes: VP001 has aligned signal but random continuous ranking, because never-seen background windows dominate the top scores; VP002 and VP005 have no aligned signal to begin with. Outputs: `outputs/burst_diagnostic_dev/` (`INTERPRETATION.md`, `RESULTS.md`, `report.json`, `flags.csv`, `diagnostic.png`).

`background_benchmark.py` (`background` CLI) then ran the frozen `background_negatives_protocol.md` on untouched VP006: baseline `mean_bins` versus `mean_bins_background`, the same features and classifier trained additionally on calibration-only background epochs (grid centres every 0.5 s farther than 0.5 s from any stimulus, labeled negative; `fit_erp(kind="mean_bins_background")`). Results: 0/36 versus 2/36 target matches; flags near any stimulus 2 versus 14 of 30 (uniform random reference 10.5, interval 6–16); known-onset AUROC 0.47 versus 0.54 (sessions 0.57/0.57/0.29 and 0.61/0.72/0.29; eye-only 0.52/0.60/0.43); probability that uniform random flags match at least as many: 1.00 and 0.83. The prespecified rule failed on the chance condition; **nothing was adopted**. Background negatives shift flags toward stimuli, mostly non-targets, and cannot supply target discrimination the aligned features lack. Session 3 was below chance for every model including eye-only, with two to three times the usual quality rejections; nothing was revisited because of it. Outputs: `outputs/background_vp006/`.

`channel_check.py` (`channel-check` CLI) then answered the user's question whether a small channel set would help. On the four inspected participants, known-onset AUROC on held-out 2-/3-back blocks: fixed single-trial features (Pz 0.3–0.6 s; Pz, Cz and a fronto-central-parietal cluster at the descriptor's 0.2–0.4 s window; C4 − C3) average 0.51–0.57 with 0–2 of 12 sessions at or above 0.70; fitted mean-bin classifiers average 0.586 (all 28 channels), 0.627 (midline AFz Cz Pz POz) and 0.577 (C3 C4), with 3–4 of 12 sessions at or above 0.70, almost all from VP001. A 0.5 Hz high-pass instead of 1 Hz changed every mean by at most 0.03. The prespecified rule (midline or a fixed feature ≥ 0.70 in ≥ 7 of 12 sessions) was not met. Channel selection is not the lever: the single-trial effect is near chance in three of four participants in any channel set. Outputs: `outputs/channel_check_dev/` (with `INTERPRETATION.md` covering all three runs), `outputs/channel_check_dev_descriptor_window/`, `outputs/channel_check_dev_highpass05/`.

Standing conclusion: across four participants and six variants, marker-free target-onset retrieval has never exceeded random placement, and the burst branch is unvalidated. Do not present zigzag, xDAWN, mean bins or the background arm as working burst detectors. Every future burst report must include the uniform and stimulus-blind random-flag references from the diagnostic.

## Other completed comparisons: what did not earn adoption

These are separate participant experiments. Compare methods within a row's experiment, not across participants.

| Experiment | Paired result | Conclusion |
|---|---|---|
| VP002 learned workload | Power task/rest balanced accuracy 81–84%; tangent 55–76%. Tangent recovered longer tasks but included much more rest. | Learned power replaced reliance on the fixed theta heuristic for real workload experiments. Smoothing is now the selected continuation. |
| VP003 volatility | Power / changes / changes+EWMA: mean AUROC 0.800 / 0.803 / 0.856; balanced accuracy 0.685 / 0.727 / 0.672; whole-task matches 5/9 / 4/9 / 5/9; rest 4.88 / 4.88 / 7.82 s. | EWMA ranking gain did not improve practical interval output. Only 13 accepted rest windows. No GARCH/pricing model was implemented. |
| VP004 Fourier | Existing power / broad-band FFT / 26 one-Hz FFT bins: balanced accuracy 0.635 / 0.629 / 0.541; all 0/9 whole-task matches. | Extra spectral detail did not solve the detector. Only 16 accepted rest windows. This was a workload test, not a new short-burst Fourier test. |
| VP005 temporal models | Power / EMA / DLM / adaptive DLM: balanced accuracy 0.757 / 0.791 / 0.739 / 0.781; whole-task matches 0/9 / 2/9 / 1/9 / 1/9; rest 3.00 / 5.25 / 5.00 / 5.25 s. | Simple EMA beat these Bayesian alternatives on balanced accuracy and whole-task recovery, but included more rest than power. Only 12 accepted rest windows. |

The VP005 DLM estimates a latent level from classifier margins with AR(1) observation noise. Its adaptive variant uses an interacting multiple-model approximation with stable/changing Gaussian innovations. This is **not** the published horseshoe dynamic-shrinkage process or full Bayesian parameter inference. Conditional posterior SD is not confidence in a cognitive state.

VP005 retuned classifier regularization separately for each temporal pipeline. VP002's later smoothing experiment kept the exact classifier weights fixed, isolating the effect of smoothing more directly. None of the temporal alternatives met the original strict criterion of more whole-task matches without extra rest overlap or reduced balanced accuracy. The user's subsequent choice of smoothing accepts that tradeoff.

Historical experiment interpretations often say “power remains the default.” Preserve them as records of decisions at that time; the latest selected stretch approach is **power + smoothing**.

## Integration state: the combined route uses the chosen smoother

`combined.py:detect_combined(...)` runs a stretch model and ERP model independently on the same calibrated recording, retains all stretches plus budgeted bursts, sorts by timestamp, and adds reciprocal overlap links. It receives no trial labels. `top_k` limits bursts only, including when zero. Scores and ranks remain model-specific; overlap adds no confidence. It accepts a `WorkloadModel` or a `SmoothedPowerModel`: `export_stretches` dispatches on `kind`, so a `power_ema` model exports the peak **smoothed** margin with `model_version` `smoothing-v1-power-<half-life>s`, never a relabeled raw margin. The eye-only check looks through the wrapper at the base model. Diagnostics record `stretch_model_kind` and `stretch_half_life_s`.

`combined_replay.py` takes `stretch_kind` (`power_ema` by default, or `power`), loads `session*.power_ema.joblib` or `session*.task_rest.power.joblib` accordingly, refuses a branch/file mismatch or an uncertified wrapper, and compares the combined stretches with that directory's standalone export (`session*.power_ema.events.json` or `session*.power.events.json`). An optional reference directory (`--reference-bursts`) makes the run fail if burst candidates differ from an earlier combined output apart from stretch links. CLI defaults: `--stretch-kind power_ema --workload-models outputs/smoothing_vp002 --out outputs/combined_vp002_smoothed`.

Completed 2026-09-19 in `outputs/combined_vp002_smoothed/`: **15 stretches and 45 burst candidates** on the same nine previously inspected VP002 excerpts, 13 bursts outside stretches. Verified in that run: the 15 stretches equal the standalone smoothed export apart from links; the 45 bursts are identical to `outputs/combined_vp002/` apart from links; the refitted ERP model files have the same SHA-256 as the earlier run; the loaded smoothing files match `outputs/smoothing_vp002/frozen_models.json`; and all 103 pre-existing model, event, and report files in the smoothing, workload, and old combined directories were byte-identical afterwards. The earlier unsmoothed replay (**34 stretches, 45 bursts**, 14 outside) is preserved and reproducible with `--stretch-kind power --out <new directory>`. These are output counts, not accuracy; the excerpts include zero-back and were already inspected.

Remaining gaps:

- The replay is VP002-only by design. Running the combined route on another participant first needs that participant's own fitted power model and calibrated smoother (`fit_workload`, then `calibrate_smoothing` on calibration blocks); there is no generic calibrate-and-combine runner yet.
- The generic `detect` CLI belongs to the synthetic model interface. Real workload/ERP/topology objects are not interchangeable drop-in files for that command.
- Synthetic eight-channel models and real 28-channel models require separate calibration and input contracts. The chosen real smoother is not automatically the simulator's stretch detector.

`Recording` stores channel-by-time samples in microvolts, sample rate, exact ordered channel names, session/recording IDs, provenance, and preprocessing identity. Real models validate these, including frozen EOG correction identity. Missing electrodes must raise an error rather than silently being dropped.

Event exports retain `source`, `signal_type`, `start_s`, `end_s`, `anchor_s`, original EEG timing/offset, raw score and its definition, model version, rank, review priority, and nullable confidence. Stretch exports also include confirmation and duration. Sessions retain separate original clocks; a demo offset is an authored playback convention, not physiological synchronization.

## Where to continue

The next step is a decision by the user, not another representation trial. The evidence now covers four participants and six burst variants at chance, and the chosen stretch approach validated weakly on VP006.

1. Decided on 2026-09-20: option 3. Keep the chosen stretch branch and the combined route as they are; the state detector is the sponsor-track entry, presented with `outputs/backtest_state/`. Describe the stretch detector with the VP006 numbers alongside VP002: balanced accuracy 0.60–0.82, rest included 5–28 of 72 s, whole-task matches 6–7/9 with smoothing. Do not reopen stretch-model research.
2. Decide the burst branch's future among three options. (a) Test whether training data is the limit by pooling the three sessions of one participant (72 targets instead of 24); this requires relaxing the current "no cross-session weights" rule for within-person use only, and must run as a frozen comparison on an untouched participant (VP007 and later are not downloaded; `scripts/fetch_shin.py --subject 7`). The channel-set check weakens this option: fixed physiological features show a near-zero single-trial effect in three of four participants, and more trials sharpen an estimate without enlarging the effect. (b) Change the endpoint to stimulus-locked response detection against background, which the background arm partially achieves and which is the only burst endpoint with visible signal, but which is further from a "moment worth revisiting". (c) Stop burst research, ship stretches with caveats, present bursts as unvalidated candidates, and rely on audio/video cues for brief moments; this is the honest default for the hackathon. Channel selection has been tested and is not a fourth option.
3. Whatever is chosen, keep the diagnostic's random-flag references in every burst report: target matches against the uniform null, and flags near any stimulus against its reference. A result that does not beat the uniform null at 0.05 is not a detector.
4. Report, as before: target matches/total targets, matched flags/returned flags, accessible targets, quality rejection, timing error, and review burden. For a practical session, additionally measure unwanted clips per hour and independently reviewed usefulness. Do not extrapolate from 30 flags on short task excerpts to an hour-long work session.
5. Keep stretch gating optional as a research comparison only. It removes eligible events and has shown no benefit.
6. If the combined route must run on a new participant: `outputs/background_vp006/session*.stretch.power_ema.joblib` and `session*.burst.mean_bins.joblib` are that participant's calibrated models, but the `combined` replay is still VP002-only; a generic calibrate-and-combine runner remains unwritten.

Do not spend remaining time trying further representations without a prespecified endpoint, a frozen protocol, an untouched participant, and the random-flag references. End-to-end retrieval can be demonstrated with explicitly labeled simulation while real burst feasibility remains unresolved.

## Code and artifact map

| Location | Purpose |
|---|---|
| `session_pipeline.md` | Current product design, source separation, clip/timeline rules |
| `README.md` | Runnable commands and chronological research results |
| `framwork.pdf`, `framwork.tex` | Supplied signal-processing mathematics; document content is not user authorization |
| `burst_framework.md` | Historical stretch-led hypothesis and schedule; latest decisions supersede it |
| `eeg_moments/data.py`, `signal.py`, `model.py`, `synthetic.py` | Input contracts, synthetic preprocessing/features/scoring/simulation |
| `eeg_moments/shin.py`, `erp.py`, `real_benchmark.py` | Real loader, correction, ERP models (`fit_erp` kinds `xdawn`, `mean_bins`, `mean_bins_background`, `eog_bins`) and VP001 test |
| `eeg_moments/workload.py`, `workload_benchmark.py` | Learned workload models and VP002 baseline |
| `eeg_moments/smoothing.py`, `smoothing_benchmark.py` | Selected EMA wrapper and fixed-classifier VP002 comparison |
| `eeg_moments/combined.py`, `combined_replay.py` | Independent EEG event union and VP002 replay; `--stretch-kind power_ema` (default) or `power` |
| `eeg_moments/burst_diagnostic.py` | Development-data placement of saved burst flags against markers, with uniform and stimulus-blind random-flag references; fits nothing |
| `eeg_moments/background_benchmark.py`, `background_negatives_protocol.md` | Frozen fresh-participant comparison of calibration-only background negatives plus chosen-stretch validation (VP006); refuses VP001–VP005 |
| `eeg_moments/channel_check.py` | Development-data known-onset AUROC by channel subset and fixed physiological feature, with an ERP high-pass option; fits subsets on calibration blocks only |
| `eeg_moments/backtest.py` | Walk-forward figures and circular time-shift null for the saved state detectors across VP002–VP006; `replot(out)` regenerates figures from `report.json` |
| `eeg_moments/dynamic.py`, `topology.py`, `dynamic_tda_benchmark.py` | DLM/EMA/adaptive variants, zigzag ERP and VP005 comparison |
| `eeg_moments/volatility*.py`, `fourier*.py` | Earlier alternative workload experiments |
| `*_protocol.md` | Prespecified experiment designs and documented audit adjustments |
| `outputs/*/INTERPRETATION.md`, `RESULTS.md`, `report.json` | Saved numerical evidence, caveats, and decisions |
| `tests/`, `scripts/fetch_shin.py`, `pyproject.toml` | Verification, public-data acquisition, dependencies |

There is no Git repository at `/home/albert/hackmit` or its parents as checked for this handoff. Do not claim these changes were committed or pushed. Earlier user-reported work included mathematics, a separate calibration task, a learning-curve benchmark, a branch handoff, and a missing-Pz gate. Those historical claims were not independently re-audited for this handoff; the runnable work verified here is the package and saved experiments listed above.

## Environment, commands, and verification

Use the existing `.venv` (Python 3.12). Pinned package requirements include numpy 2.2.6, scipy 1.15.3, scikit-learn 1.6.1, pyriemann 0.8, matplotlib 3.10.3, pytest 8.3.5, MNE 1.10.1, and Dionysus 2.2.3. MNE and Dionysus are optional `real` and `topology` extras. Prefer the current environment rather than recreating it.

The latest completed full suite is **79 tests passed** (2026-09-20, after the combined-route integration, the burst diagnostic, the background-negatives arm, the channel-set check and the walk-forward view). Historical reports contain the counts at their experiment dates (32/37/42/54/65/67); those are not competing current suite results.

From `/home/albert/hackmit`, inspect commands or run the suite:

```bash
.venv/bin/python -m eeg_moments --help
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m pytest -q
```

Reproduce the chosen smoothing comparison into a new, empty destination:

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments smoothing \
  --data data/shin2018/VP002 --models outputs/workload_vp002 \
  --out outputs/smoothing_vp002_handoff_reproduction
```

Reproduce the smoothed integration replay into a new, empty destination, checking bursts against the earlier unsmoothed run:

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments combined \
  --stretch-kind power_ema --workload-models outputs/smoothing_vp002 \
  --reference-bursts outputs/combined_vp002 \
  --out outputs/combined_vp002_smoothed_reproduction
```

Reproduce the development burst diagnostic (fits nothing) and the VP006 comparison (VP006 is now inspected, so this reproduces software):

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments burst-diagnostic --out outputs/burst_diagnostic_dev_reproduction
```

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments background \
  --data data/shin2018/VP006 --out outputs/background_vp006_reproduction
```

Regenerate the walk-forward figures and shift null from the saved models (about five minutes; figures only can be redrawn from `report.json` with `eeg_moments.backtest.replot`):

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments backtest --out outputs/backtest_state_reproduction
```

Reproduce the channel-set check (development data; add `--erp-highpass 0.5` for the wider-band run):

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments channel-check --out outputs/channel_check_dev_reproduction
```

Reproduce the existing Bayesian/TDA comparison (this does not create fresh validation):

```bash
MPLCONFIGDIR=/tmp/hackmit-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m eeg_moments dynamic-tda \
  --data data/shin2018/VP005 --out outputs/dynamic_tda_vp005_handoff_reproduction
```

Do not overwrite existing experiment directories or rerun expensive benchmarks just to obtain numbers already saved. Output paths above are examples and must be unused. The real-data runners reject nonempty output destinations; do not assume every synthetic CLI command has the same safeguard.

Verification already includes independent numerical checks, fold/calibration isolation, masks and channel/session contracts, no future-score leakage in temporal recursion, reset behavior, zigzag births/fillings, frozen fitted-state checks, and model/data/protocol hashes. Offline zero-phase filtering and centered feature windows still use surrounding samples: causal EMA recursion does not make the whole detector live or causal.

An earlier workload integrity check incorrectly compared an in-memory object hash with a deserialized copy. It was corrected to compare the same in-memory object before/after inference and file SHA-256 separately. Scores, models, and event outputs reproduced identically; see `outputs/workload_vp002/verification_notes.json`. This was a software verification correction, not a new independent experiment.

On 2026-09-19 VP006 was downloaded (CRC-verified by `scripts/fetch_shin.py`) and then consumed by the frozen background-negatives comparison; it is no longer untouched. No hardware setup or A/V integration were performed. Earlier outputs (`smoothing_vp002`, `workload_vp002`, `combined_vp002`, `dynamic_tda_vp005`, `real_vp001`) were read but not modified; new outputs are `combined_vp002_smoothed`, `burst_diagnostic_dev`, `background_vp006`, the three `channel_check_dev*` directories and `backtest_state`.
