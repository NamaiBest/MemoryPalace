# Burst localization using stretch context

Current prototype direction: see [session_pipeline.md](/home/albert/hackmit/session_pipeline.md) and [LLM_HANDOFF.md](/home/albert/hackmit/LLM_HANDOFF.md). Retain both stretches and bursts; the selected stretch approach is learned band power plus exponential smoothing, with short bursts the main research objective. Accepted brief EEG burst candidates or audio/video cues should trigger the next 30 seconds of playback. Preserve stretch intervals independently and do not gate bursts by stretches; dedicated stretch clip behavior is not yet specified. The stretch-led retrieval proposal and hardware-dependent schedule below are historical; the current demo uses phone audio/video and an explicitly simulated EEG input. The signal-processing discussion remains research context, not evidence that stretches improve brief-moment retrieval. Current implementation and experiment results are in [README.md](/home/albert/hackmit/README.md).

**Current scope: 20-hour hackathon**

This time limit supersedes the broad experiment below. Hardware and raw EEG are not currently available. Deliver a recording-to-review workflow; an exploratory burst test is conditional on obtaining usable EEG early enough. Keep the remaining sections as research notes; they are not a hackathon task list. No signal-processing implementation or EEG recording has yet been inspected here.

Reuse the existing stretch detector if its code and input format are available. Start with local band-power features from the framework's oscillatory branch. Add tangent covariance only if a working implementation is immediately reusable and acquisition provides multiple independent EEG channels. The written mathematics alone does not justify spending the remaining time rebuilding that pipeline.

| Elapsed time | Work | Required result |
| --- | --- | --- |
| 0–2 h | Confirm a specific device, access time, and raw-export path; define the timestamped EEG import format and recording/marker format | A concrete acquisition path or an explicit decision that it is unavailable |
| 2–6 h | Build recording, manual markers, import, and click-to-replay using clearly labeled fixtures; obtain a real raw EEG sample if hardware arrives | A functioning replay workflow and, by hour 6, a usable synchronized EEG recording if the EEG experiment is to proceed |
| 6–10 h | If real data is usable, compare stretch-only clips with one local power scorer around onset; freeze settings before a separate evaluation block | Decide whether burst scoring earns a place in the demo; otherwise continue the replay workflow |
| 10–14 h | Integrate the selected scorer, deduplication, and moment cards, or finish the explicitly manual-marker version | An end-to-end demonstration whose data source is clear |
| 14–18 h | Rehearse with fresh recordings; fix timestamp, missing-data, artifact, and replay failures | Repeatable demo plus a saved real-session backup |
| 18–20 h | Freeze features, prepare the presentation, and retain a recovery buffer | A stable demonstration and a clear statement of what was observed |

Times are budgets from now. If there is no concrete hardware/raw-export path at hour 2, give acquisition a strict remaining time budget while proceeding with replay. If there is no usable synchronized raw recording at hour 6, remove EEG detection from the critical demo path. A compatible real recording with independently known events can support an offline feasibility test, but unrelated public EEG does not validate this naturalistic burst hypothesis or provide matching screen footage. Synthetic EEG may test plumbing but cannot be presented as a detected cognitive event.

If acquisition succeeds, the burst experiment should answer one question: does a short local power departure improve useful-clip retrieval over the existing stretch score? Use one participant initially, one chosen event type, and two separate 10–15-minute work blocks. Start with a ±3-second onset search and at most two suitable window durations. Review the recordings with model scores hidden to annotate moments and ordinary high-effort periods. Include obvious movement/reporting actions as controls. Develop settings on the first block and freeze them before opening the second block's results. Use the same fixed clip duration and, provisionally, the top five distinct clips per block for both methods. Keep the full block for evaluating missed moments. This is a feasibility check, not a generalization claim.

By hour 10, retain burst scoring only if the held-out comparison shows a useful addition and inspection does not reveal an obvious artifact or timing explanation. If EEG works but burst scoring does not help, ship stretch-ranked clips and present burst localization as unresolved. If EEG remains unavailable, use explicitly manual markers for the replay demonstration. With too few annotated events, record the comparison as inconclusive; do not rescue it by repeatedly changing bands, windows, or evaluation clips.

Defer new xDAWN/prototype training, learning curves, a MOABB integration, cross-headset comparisons, learned timing priors, RIDE, BOSC integration, and new temporal models. Do not force a supervised classifier into a dataset with too few usable labels. If an existing validated pipeline can be reused within the signal-testing budget, compare it without widening the schedule. Keep artifact checks, temporal separation of development/evaluation, and explicit channel validation.

The user-facing result is a small set of “moments to review,” each linked to its recording context. Show measured scores as relative ranking signals. The hackathon evidence should say which real sessions were tested and whether the burst option improved their shortlist; it should not label a power peak as a verified realization.

---

Proposed experiment, 19 September 2026. Extends `framwork.pdf`; no real EEG or existing detector implementation is available in this workspace. This document specifies what to test, not a demonstrated detection capability. Numerical settings below are starting choices to freeze before evaluation, not physiological constants.

The central question is whether a brief EEG feature adds useful timing information within or near a detected load stretch. There are three separate claims: useful moments occur near stretches; some contain distinguishable brief activity; that activity improves retrieval beyond the stretch alone. Each can fail independently.

**1. What carries over from the supplied framework**

Keep shrinkage covariance, a training-fitted tangent reference, coordinate standardization, a regularized linear classifier, nested tuning at each training size, and ranked output. Change the definition of an example: the model now scores many short windows at candidate times, then consolidates overlapping results into events.

The original prototype branch stacks an averaged class waveform with each trial. Its off-diagonal covariance blocks compare corresponding time samples. That is appropriate for a repeatable waveform with sufficiently consistent alignment; stretch detection does not automatically provide that alignment. The official [pyRiemann XdawnCovariances documentation](https://pyriemann.readthedocs.io/en/latest/generated/pyriemann.estimation.XdawnCovariances.html) likewise describes this as an ERP construction.

Write a stretch's estimated onset as s and a possible burst time as τ = s + δ. The unknown offset δ must be searched or modeled. If waveforms h(t − δ) are averaged while aligned to s, their mean is h convolved with the distribution of δ: timing variability blurs the prototype. For an oscillatory burst whose phase varies across trials, averaging voltage can cancel the oscillation even when its power increases reliably. Sliding a poor prototype afterward does not undo its training-time cancellation.

The oscillatory branch already in the PDF is therefore the first branch to test for a burst of band power. A short oscillatory burst need not be an ERP.

**2. Define the timing reference and candidate windows**

Store three timestamps separately: estimated stretch onset, the time the duration criterion confirms the stretch, and stretch end. Search relative to estimated onset. Retain the original EEG throughout the recording so the experiment can measure events missed by the gate.

As a first fixed gate, consider candidate centers from 3 seconds before to 3 seconds after estimated onset. Include both sides because detector smoothing, duration rules, and the unknown cognitive sequence make an exact one-sided assumption premature. Compare this with equal-duration gates at the stretch midpoint and end, matched random gates, and a whole-session search. Inspect the empirical event-offset distribution on training data before narrowing the gate. Merge overlapping gates and count their union when calculating coverage.

Use a 50 ms candidate-center step as a computational grid, with band-dependent feature windows initially chosen from 250, 500, and 1,000 ms. Do not interpret the grid spacing as timing precision. As a design rule, require at least roughly three cycles at the band's lower frequency: a 250 ms window contains only one 4 Hz cycle, while a 1 s window contains four. Frequency selectivity, filter support, window length, and annotation uncertainty all limit localization.

Filter continuous valid segments with adequate context before cropping windows; do not independently filter tiny crops. Measure the actual processing chain's response to a transient and a smooth power transition. Offline zero-phase processing is permissible, but activity can spread across time and apparent onsets can shift; [MNE's filtering examples](https://mne.tools/stable/auto_tutorials/preprocessing/25_background_filtering.html) illustrate these effects. Guard intervals around fold boundaries, recording edges, and missing data must account for the full filter and context support.

**3. Compare three scoring methods**

| Method | Features and model | What it tests |
| --- | --- | --- |
| A: local band-power baseline | Log power by channel and band, plus contrasts against nearby background; regularized linear classifier when labels exist | Whether a simple local energy feature is sufficient |
| B: short-window tangent covariance | Shrinkage covariance per band, fixed-reference tangent features, optional local contrasts; same classifier | Whether channel covariance adds information beyond power |
| C: sliding waveform prototype | Training-fitted xDAWN/prototype augmentation, evaluated at candidate offsets; same downstream classifier | Whether a repeatable voltage waveform helps when timing is uncertain |

For A, use broad, predeclared bands compatible with the acquisition passband. An initial set is theta 4–8 Hz, alpha 8–13 Hz, and beta 13–30 Hz. A 30–45 Hz exploratory branch requires adequate raw acquisition and separate artifact checks. These are candidate features, not assigned meanings such as “theta equals confusion” or “gamma equals insight.” Tune any reduced feature set using training data only.

For B, let X[b,t,w] denote the centered, band-filtered C-channel window of duration w at t. Estimate:

    Σ[b,t,w] = shrinkage_covariance(X[b,t,w])
    v[b,t,w] = svec(log(M[b,w]^(-1/2) Σ[b,t,w] M[b,w]^(-1/2)))

Here svec uses the PDF's √2 weighting for off-diagonal entries. Fit each reference M[b,w] on training examples only, freeze it, and concatenate selected bands/scales. For a small channel count, start with sensor covariance directly: the linear model learns combinations of its coordinates. Do not assume xDAWN's evoked-response objective is suitable for a phase-variable oscillatory target. Optional spatial dimension reduction must be fitted and compared within training folds.

Add a context contrast as an ablation:

    Δv[b,t,w] = v[b,t,w] − mean(v[b,u,w] for u in background(t,w))

Use a fixed rule for clean flanking windows with the same band and window duration, excluding the candidate and a gap justified by filter support. A provisional background region is 1–3 seconds on either side, enlarged when necessary. All features remain in the same frozen tangent chart. Candidate-specific background features are allowed under this fixed deployment rule; fitting a new tangent reference per candidate would change the coordinate system. Define insufficient clean context as “unscorable,” rather than silently changing feature definitions.

Compare both sides separately as well as their average. A transient should differ from its surrounding state, but a sharp load transition can also yield large contrasts. The classifier therefore needs hard negatives containing load rises without a reported moment. Neither subtraction nor a local maximum establishes a burst by itself.

For C, learn prototypes from independently labeled, reasonably aligned calibration examples; search their offsets at inference. If the labels only identify a several-second interval, do not label the largest EEG peak in that interval as ground truth. Latent-time or multiple-instance learning could handle interval labels later, but a small dataset makes overfitting particularly easy. [RIDE](https://pubmed.ncbi.nlm.nih.gov/21895682/) demonstrates an approach to separating latency-variable ERP components in experimental data; it does not establish that an unknown naturalistic event has a usable template.

**4. Turn window scores into a shortlist**

Use the linear decision score for ranking; do not present it as a probability of insight. Start with equal temporal weighting within the gate. After measuring training-only offsets, a soft timing preference is an optional comparison:

    score(t) = EEG_score(t) + λ log(π[t − s] + ε)

Here π is a discrete offset distribution on the candidate grid, ε prevents zero weights, and λ is tuned within training folds. This is a ranking heuristic unless the underlying scores are appropriately calibrated likelihoods. Always compare λ = 0; otherwise the timing prior can appear to localize events without evidence from EEG.

Merge adjacent high-scoring windows across scales and overlapping stretches before choosing the top k. Freeze the merge rule, clip length, and review budget. A provisional prototype output is up to five distinct clips per 20-minute block, with the candidate time and its timing uncertainty. There is no reason to require a clip from every stretch. More scanned windows give more opportunities for an extreme noise score, so evaluate the entire scan-and-merge procedure, including variable gate lengths and missing data.

**5. Collect labels that can answer the question**

Keep insight, confusion, and surprise as separate annotations initially. A pooled “worth revisiting” label is a product outcome; it does not imply these experiences share a burst waveform. Select one target for the first supervised analysis and retain the others for descriptive results.

Obtain annotations independently of model scores. Record an immediate marker if feasible, then review the recording with EEG scores hidden to mark a plausible event interval, event type, and usefulness. The report/keypress timestamp is an upper bound or noisy proxy for the experience, not its exact neural onset. Log typing, clicks, speech, blinks, and movement where available. Include similar reporting actions on control trials so a model cannot succeed simply by recognizing the response.

Review complete held-out blocks, or use a prespecified sampling scheme covering both inside and outside gates. Reviewing only model-selected clips cannot estimate missed events. If annotations are only accurate to several seconds, report clip retrieval and interval overlap; a claim of 200 ms localization would be unsupported.

A timed surprise task can establish whether acquisition and analysis recover a task-related response. That is an engineering positive control, not validation of naturalistic insight or transfer from calibration to everyday work. Same-session calibration does not eliminate this task-distribution change.

**6. The decisive evaluation**

Use separate chronological calibration and evaluation blocks within each session. For model selection inside calibration, keep all overlapping windows, context windows, and examples from a given event/trial in the same fold. Group repeated task items where appropriate. Fit spatial filters, prototypes, covariance references, scalers, artifact rules, offset priors, and regularization within the applicable training fold. A new participant/session gets its own calibration, matching the intended deployment.

Run these comparisons with the same held-out labels, clip lengths, and final review budget:

| Comparison | Question |
| --- | --- |
| Stretch-only ranking versus stretch plus A or B | Does short-window EEG add information beyond stretch strength, duration, and slope? |
| A versus B | Does covariance justify its additional parameters? |
| Onset versus midpoint/end versus matched random gates | Is the leading edge specifically useful? |
| Gated versus whole-session use of the same scorer | Is the reduction in search space worth the missed events? |
| Model versus matched artifact/behavior features | Could retrieval success be explained by eyes, muscle, speech, or input actions? |

For onset versus random comparisons, match eligible duration and behavioral context. Pure idle-time random windows are too easy a control for an active-work gate. Keep a descriptive random-time comparison if desired, but do not use it alone to establish onset specificity.

Report candidate recall across all labeled events, valid-time coverage of the gate, precision among the top k distinct clips, recall at that review budget, and temporal error relative to the independent annotation interval. Report how many candidates are unscorable. A useful descriptive enrichment is candidate recall divided by valid-time coverage, with matched controls and uncertainty; it is not proof of a neural burst.

Use paired differences across held-out blocks/sessions and uncertainty estimates resampled at the block/session level, not at the level of heavily overlapping windows. A tiny dataset is exploratory. If onset gating fails to enrich events, expand or replace the gate before increasing classifier complexity. If adding burst features does not improve on stretch-only retrieval, report that short-burst detection has not been demonstrated. If A and B perform similarly, prefer A for the first product iteration.

**7. Controls against a false positive result**

Before the empirical benchmark, test synthetic no-burst signals containing a smooth sustained power increase, abrupt steps, isolated artifact-like impulses, and noise. Add known brief waveforms and random-phase oscillatory packets at known offsets. Run the actual preprocessing, stretch detection, candidate scan, and merging on each. This tests whether the pipeline invents bursts at a transition and whether timing survives processing; it cannot demonstrate cognitive sensitivity.

Artifact calibration should include blink, gaze movement, jaw tension, speaking, and movement examples relevant to the recording setup. Reject or flag unusable windows, while evaluating the surviving false positives. A brief high-frequency peak is a particularly weak standalone argument: [simultaneous eye-tracking/EEG work](https://pubmed.ncbi.nlm.nih.gov/18466752/) showed that a commonly observed transient gamma response could reflect miniature saccades, and [neuromuscular-blockade recordings](https://pubmed.ncbi.nlm.nih.gov/17574912/) demonstrated substantial muscle contamination of higher-frequency scalp EEG. These findings motivate controls; they do not imply every gamma effect is an artifact.

The classic [Jung-Beeman et al. insight study](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.0020097) found a right-temporal gamma difference beginning roughly 300 ms before reported solutions in a controlled verbal task. It used solution-relative timing and condition comparisons. My inference is that it motivates an exploratory short-window feature, while providing no direct evidence that a frontal workload onset predicts that feature in single naturalistic trials.

**8. Other methods worth considering after the first comparison**

| Alternative | When it helps | Limitation |
| --- | --- | --- |
| Wavelet power / BOSC-style oscillation detection | A burst has variable phase but several oscillatory cycles | Detects oscillatory episodes, not their cognitive meaning; power/duration criteria can miss very brief events |
| Transient-versus-step model on a local feature trajectory | Need to distinguish a short departure-and-return from a persistent load change | Model assumptions and artifact rejection still matter; a change-point method allowing two nearby boundaries is not ruled out by event discreteness |
| Screen/audio/input event anchors | A displayed result, navigation, or spoken response provides a measurable timestamp | An interaction is not automatically a mental event; test EEG's added value over behavior alone |

[BOSC's human-alpha validation](https://pubmed.ncbi.nlm.nih.gov/20807577/) supports background-spectrum-aware oscillation detection. Its power-and-duration approach is a candidate feature extractor, not a replacement for ranked moment retrieval. Thresholds used to define valid oscillations or reject artifacts are compatible with ranking the final results.

**9. Hardware and synchronization gates**

Require raw voltage samples, actual sample rate, channel names and positions, reference scheme, acquisition passband, sample timestamps, and dropout markers. Electrode material and DIN plugs do not specify an EEG recording system; the amplifier and digitizer determine what is available. Treat missing required channels as an explicit failed comparison, consistent with the earlier dataset gate.

A conventional NeuroSky forehead sensor plus reference gives one EEG channel, not two independent spatial channels; see [NeuroSky's measurement description](https://support.neurosky.com/kb/science/thinkgear-measurements-mindset-protgem). Then unaugmented covariance is scalar and the tangent feature reduces to log variance relative to a reference, so it cannot supply multichannel spatial-noise subtraction. The [ThinkGear socket protocol](https://developer.neurosky.com/docs/doku.php?id=thinkgear_socket_protocol) distinguishes raw samples from metrics commonly emitted at 1 Hz. Use raw data for the burst experiment and verify the actual model's output rather than assuming a rate. A one-channel experiment remains useful for feasibility, with limited source/artifact discrimination.

Synchronize using events observable in both relevant streams. A clap only visible in audio does not independently align EEG. At least two separated shared markers allow offset and drift to be estimated; additional markers help detect nonuniform timing errors. Preserve synchronization uncertainty in the reported event interval.

**10. Corrections to carry into implementation from the original math**

These follow from the displayed equations and do not require new EEG evidence:

- With row-centering, rank(X) ≤ T − 1, so full-rank C-channel sample covariance requires T ≥ C + 1, plus independent rows. The augmented empirical covariance is only guaranteed positive semidefinite before appropriate regularization; all-zero/invalid windows need rejection.
- xDAWN's inclusion of electrode selection in its feasible set guarantees an optimum no worse for its fitted Rayleigh quotient. It does not guarantee better held-out classification or an objective appropriate to an induced burst.
- Affine invariance applies when the same invertible transform acts on both covariances. It does not make features invariant to changing the gain of a new trial while keeping M fixed. For example, replacing Σ by a²Σ adds 2 log|a| times the identity to its whitened matrix logarithm.
- Refitting M or a scaler on unlabeled test EEG is test-distribution leakage under this inductive protocol, rather than necessarily label leakage. A new reference also changes the features seen by the frozen classifier. Local background contrasts defined in advance are a different operation.

The first empirical deliverable is a comparison of stretch-only retrieval, local band-power retrieval, and short-window tangent-covariance retrieval, together with gate coverage/recall and artifact controls. The prototype method becomes a priority only if calibration supports a repeatable, sufficiently aligned waveform.
