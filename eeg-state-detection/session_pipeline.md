# Work-session moment retrieval: current prototype

This is the current product direction. It supersedes the live-hardware deadline and software-only debugging pivot discussed previously. Inputs are a phone video with audio and an explicitly simulated EEG stream. Processing runs after the session. An accepted brief EEG burst candidate or an audio/video moment cue triggers a clip of the next 30 seconds from the estimated event time. Saved moments appear chronologically on a timeline. An observable audio/video cue is not necessarily a physiological EEG burst.

**Latest decision: retain stretch detection and focus new research on brief moments.** The user selected learned band power plus exponential smoothing as the stretch approach. Retain stretches independently of bursts; a burst does not need a stretch to qualify. Smoothing is a practical interval-recovery tradeoff, not an improvement on every metric. It has not demonstrated improved burst retrieval, so further stretch optimization is not the main research priority. Dedicated stretch clip behavior remains unspecified; do not discard stretch outputs. The selected wrappers and replay events exist in `outputs/smoothing_vp002/`, and the `combined` CLI now loads them by default; the smoothed integration replay is in `outputs/combined_vp002_smoothed/`. See [LLM_HANDOFF.md](LLM_HANDOFF.md) for the full continuation record. The clip policy below is a design specification; this update does not implement video clipping or the audio/video adapter. **Decision 2026-09-20:** option 3; the EEG model handles broad state changes, audio/video handles brief moments, and the state detector is the sponsor-track entry with walk-forward figures and a time-shift null in `outputs/backtest_state/`. **Burst status (2026-09-19):** no continuous burst detector has beaten randomly placed flags on any of four participants, including a frozen background-negatives comparison on untouched VP006; treat burst candidates as unvalidated. The chosen stretch approach on VP006 reached balanced accuracy 0.60 with 28 of 72 s of labeled rest included, so its VP002 result is a best case.

The EEG implementation is now in `eeg_moments/`; see `README.md` for runnable commands and `outputs/eeg_demo/RESULTS.md` for the synthetic benchmark. A first real-data test is now in `outputs/real_vp001/RESULTS.md`: marker-aligned ERP discrimination worked better with a simple amplitude model, but continuous target retrieval was poor and the fixed stretch rule did not trigger. This does not validate meaningful work-session EEG moments. EEG research branches export the event envelope with explicit source provenance; audio/video integration is pending. The EEG branch independently exports stretches and bursts using `signal_type`. Stretch events preserve start/end/confirmation times; burst events preserve their scoring windows. Full burst scanning is the default, with onset gating available as a research experiment. The following experiment summaries preserve historical outcomes; the latest selected stretch approach is power plus smoothing.

The learned workload follow-up is in `outputs/workload_vp002/INTERPRETATION.md`. On a fresh participant, session-calibrated power scores distinguish task/rest (AUROC 0.91–0.94), but interval boundaries fragment; the covariance comparator covers more tasks while flagging more rest. Eye-only controls also score highly, so neither model is validated as isolated cognitive workload. `session*.power.events.json` contains primary replay stretch candidates. The tangent exports are an alternative model, not extra corroborating evidence. This experiment does not retrain or improve the burst classifier, and onset gating still excludes most target markers.

Smoothing those exact saved VP002 classifiers is now tested in `outputs/smoothing_vp002/INTERPRETATION.md`. On the same nine blocks, whole-task recovery improves from 3/9 to 7/9 and intervals decrease from 34 to 15. Mean balanced accuracy falls from 83.0% to 81.5%, and rest included rises from 2.04 to 5.39 seconds. Calibration selected the smoothing half-life; final classifier weights remained identical. This is a tradeoff on previously inspected data, not fresh validation or a demonstrated overall improvement. Existing replay defaults remain unchanged.

The volatility feature comparison on a further fresh participant is in `outputs/volatility_vp003/INTERPRETATION.md`. Adding EWMA volatility improved task/rest ranking but reduced balanced accuracy, increased rest overlap, and did not improve whole-task interval matches. Power remains the default. Simple recent-change features improved balanced accuracy in that run but fragmented more tasks. This is a small experiment with only 13 accepted rest windows after a shared history warm-up; no reliable EEG mental-state detection is established. Its three EEG model exports are alternatives, not three independent sources.

The Fourier comparison is in `outputs/fourier_vp004/INTERPRETATION.md`. Explicit three-band Fourier power performed similarly to the existing power classifier, while a 26-bin spectrum performed worse. None of the models matched a whole task block on VP004, despite detecting task fragments. All models shared quality gaps and the unchanged interval rule. The power model remains a baseline, not a validated reliable stretch detector; spectral detail did not resolve the practical event-boundary problem. Spectrogram colors represent power, not mental intensity. Replay flags from alternative models must not be pooled as corroboration.

The real EEG branches are now connected through `detect_combined` in `eeg_moments/combined.py`. A workload detector and ERP burst-candidate detector scan the same recording independently, and accepted events from either branch are retained. This combines different event types; the alternative workload models remain comparison choices. The current default replay with the selected smoothed stretch models returned 15 stretches and 45 burst candidates across nine already inspected VP002 excerpts, 13 of the bursts outside stretches (`outputs/combined_vp002_smoothed/`). The earlier unsmoothed replay (34 stretches, the same 45 bursts, 14 outside) is preserved under `outputs/combined_vp002/`. The counts are not accuracy measurements. Stretch outputs equal the standalone exports, burst candidates are identical across both stretch models apart from links, and fitted model states remained unchanged. Each EEG session has its own chronological export; overlap creates navigation links only. Both branches observe the same signal and can share artifact errors, so overlap supplies no automatic confidence increase. Real burst reliability remains unestablished.

**Decision on EEG data**

The Bayesian/TDA follow-up is complete in `outputs/dynamic_tda_vp005/INTERPRETATION.md`. All 28 EEG channels were retained. Simple exponential smoothing beat the fixed and adaptive Bayesian DLMs on mean balanced accuracy and whole-task matches, but included more rest than the power baseline. No stretch alternative met the full improvement criterion. Zigzag TDA matched 6/36 target markers versus 2/36 for the ERP baseline, at 30 flags each; 24 TDA flags remained unmatched. This is a small relative gain, not reliable cognitive-event detection. The adaptive DLM uses an approximate switching Gaussian shrinkage model, not the full horseshoe dynamic-shrinkage process. TDA computes actual evolving components/loops and does not automatically detect arbitrarily small changes. Treat these event files as experimental alternatives; existing replay defaults remain in place.

The development diagnostic in `outputs/burst_diagnostic_dev/INTERPRETATION.md` then showed that none of the saved continuous burst detectors on VP001, VP002 or VP005 retrieves target markers better than uniformly random flags under the same grid, mask, five-flag budget and ±0.5 s tolerance (random mean 3.0–3.6 of 36; observed 2–6), and that 57–87% of flags fall farther than 0.5 s from any stimulus. The zigzag result above is within random placement. A frozen comparison on untouched VP006 (`outputs/background_vp006/INTERPRETATION.md`) tested calibration-only background negatives: 2/36 versus 0/36 matches, still within random placement, not adopted. A channel-set check (`outputs/channel_check_dev/INTERPRETATION.md`) then showed that no small channel set, no fixed single-trial P300 amplitude and no wider filter band produces a usable marker-aligned target signal in three of the four participants, so channel selection is not the lever either. The burst branch is unvalidated on four participants; brief-moment retrieval in the product should not rely on it until a detector beats the random-flag reference on an untouched participant.

Do not combine unrelated P300 and workload datasets for the filmed-session demo. Use two separate activities:

- Evaluate the EEG model on an unchanged public dataset with documented event markers, such as the previously identified Shin n-back recording. This evaluates a task-event proxy, not naturalistic insight.
- Exercise the demo pipeline using a reproducible synthetic stream with exactly the channel order, units, sampling rate, and preprocessing expected by the model. Its timestamps map to the phone recording by an explicit demo convention; they are not measurements of the filmed person.

If replaying a public EEG recording instead of generating a stream, label it `replayed_eeg`. Real EEG from another participant is still unrelated to the phone video. Never describe their shared playback clock as physiological synchronization.

For a minimal simulator, generate colored background activity, a gradual narrow-band power envelope representing a simulated stretch, optional brief transients, and selected artifact-like disturbances. Use a fixed spatial mixing matrix within each virtual recording. Choose the transient type to match the tested model branch: an ERP-like waveform for the prototype branch, or a phase-variable oscillatory packet for the power/covariance branch. Do not call an oscillatory packet a P300.

This preserves an input format and explicit generative assumptions. It does not preserve every feature of original recordings or establish biological realism. A more elaborate implementation can use [MNE's source simulation and noise utilities](https://mne.tools/stable/auto_examples/simulation/simulate_raw_data.html), but a head-model simulation is outside the first demo's critical path.

Include stretch without transient, transient without stretch, onset-adjacent and late transients, baseline noise, and artifact cases. Keep injected-event truth in an evaluation-only file. The detector gets samples and input metadata, never the injection schedule. Hold out random seeds/background realizations and vary amplitude, latency, duration, and waveform parameters. Report synthetic injection recovery separately from public-dataset performance.

For a deliberately staged presentation, a scenario file can place simulated events at chosen video times. Label this an authored scenario. If the VLM selects those times, the simulated EEG is dependent on its output and cannot be counted as independent corroboration. Independent simulation timings are preferable for the integration test.

**Recording and common clock**

Use one phone video file as the primary media asset, with audio from that same file. Set session time zero to the first presentation timestamp after documented normalization. Keep video, extracted audio, transcript segments, and analyzed frames on that same clock. Use media timestamps rather than frame-number/FPS arithmetic because phone recordings may have variable frame rates.

Place the phone so the work surface or screen is readable and speech is intelligible. First check a 30-second sample. A camera pointed only at the person's face does not provide evidence of what they were looking at. Blurred text should be treated as unavailable evidence.

For simulated EEG, define sample time as t = sample_index / sample_rate + demo_offset. Store the offset and simulated provenance. For uploaded clips, preserve the original session offset when sending a chunk for analysis, then translate returned chunk-relative event times back into session time.

**Audio/video analysis**

The user has confirmed Elastic as the intended provider; the exact model and API details will follow. Keep this connection behind an adapter so other components can proceed. Elastic's [multimodal search documentation](https://www.elastic.co/docs/solutions/search/multimodal-search) describes embedding and retrieval capabilities; that alone does not specify a model that produces timestamped event explanations. Confirm the actual inference endpoint, accepted modalities, and output schema before integration. If necessary, combine a timestamped transcript with video frames whose timestamps are supplied explicitly to a vision-capable model.

Ask for observable evidence: explicit spoken realization, explicit statement of difficulty, repeated attempts, a visible result change, or a user bookmark. Every proposed moment needs a time interval and a short evidence description or transcript quote. Separate observations from interpretations. Facial expression or silence alone should not become a definitive confusion label.

Use overlapping chunks, then deduplicate boundary events. Validate that returned times fall within the analyzed chunk and original media duration. A similarity score from an embedding model is not automatically an event probability or intensity.

**Event contract and OR rule**

Both detector adapters emit the same envelope:

```json
{
  "event_id": "demo-eeg-003",
  "session_id": "demo-session",
  "source": "synthetic_eeg",
  "signal_type": "burst",
  "start_s": 72.2,
  "end_s": 73.0,
  "anchor_s": 72.6,
  "event_type": "synthetic_transient_candidate",
  "raw_score": 2.4,
  "score_definition": "detector-specific decision score",
  "confidence": null,
  "review_priority": "medium",
  "evidence": "The EEG detector flagged a transient in the simulated stream.",
  "model_version": "configured-at-runtime"
}
```

Allowed sources initially are `audio_video`, `synthetic_eeg`, `replayed_eeg`, and `manual`. The example values above are illustrative. Keep confidence nullable unless its meaning and calibration are established. Each source applies its own acceptance rule before emitting a flag. Raw scores from different sources are not numerically interchangeable.

For EEG exports, `signal_type` is `burst` or `stretch`; `raw_score` is the burst classifier margin, the original stretch rule's peak robust z, or the learned workload scorer's peak margin. The chosen smoother exports a peak exponentially smoothed margin. Read `score_definition` and `model_version` rather than assuming a shared scale. Rank and priority are assigned separately within each model/type. All confirmed stretches remain in the export even when the burst review budget is zero. Retain both event types in the session; the defined 30-second brief-event clip rule applies to accepted bursts and audio/video moment cues, while dedicated stretch clip behavior remains open. Stretches never gate a burst. Temporally overlapping EEG events retain separate IDs with reciprocal navigation links when exported together; workload-only exports initially have empty burst links.

Process the union of accepted brief EEG burst flags and audio/video moment cues, plus manual bookmarks. Consolidate repeated windows from the same detector into one source event. Keep EEG and audio/video source events distinct: nearby timestamps do not establish the same internal occurrence. Overlapping playback can be reused if each event's requested interval remains available; preserve both event IDs, labels, and evidence without boosting confidence. Do not blindly join overlapping clips into one long chain.

For an accepted event at `anchor_s = t`, save `[t, min(t + 30 seconds, recording_end)]`, validating the anchor against media bounds. Use the estimated occurrence timestamp, not the time inference finishes. Generate and save the video clip, its source event references, original start/end times, and a thumbnail. Preserve the complete original recording for later context changes. The requested default has no pre-roll; an optional 5–10 seconds before the event would help recover what prompted a realization, but is a proposed extension rather than the default. Deterministic moment identifiers prevent retrying a job from creating duplicate clips. An upload-only session is sufficient for the first version; live processing is deferred.

Evaluate useful clips among returned clips, missed independently labeled moments, unwanted clips per hour, event timing error, and total playback time required for review. Measure EEG proxy-event retrieval, synthetic injection recovery, and usefulness on the filmed session separately. A high task/rest score or whole-task match rate does not establish any of these outcomes. Bursts are candidates: neither a brief EEG fluctuation nor a high detector score by itself establishes a realization.

**Timeline**

Sort moments by anchor time. Use the requested colors: red/high, yellow/medium, green/low. Define the scale as review priority for this prototype. Neither a VLM score nor an EEG anomaly score measures a shared psychological intensity.

Keep confidence and source-specific signal strength separate in the detail panel. Give synthetic/replayed EEG a visible badge and a different marker outline; an audio/video-plus-simulation moment retains both badges. Include text labels or shapes so color is not the only encoding. A source filter lets viewers inspect audio/video detections without the simulation.

Clicking a dot opens the saved clip, its timestamp, the evidence that triggered it, source labels, and a keep/dismiss action. The simulation label must remain visible in the clip view and exported metadata. A low-priority green dot is still a saved event, not an assertion that the person was calm.

**First acceptance check**

Use a short phone recording and a seeded simulation containing an EEG-burst-only flag, an audio/video-only flag, overlapping flags, a stretch without a burst, and no-event intervals. Verify that either accepted brief-event source independently produces a playable clip, a stretch without a burst is still retained as an interval signal, and overlapping events preserve distinct source references. Check chronological order and the requested 30-second post-event window, truncated at recording end. Compare detector results with hidden injection truth and independently reviewed video labels separately. This establishes the two-input retrieval workflow; it does not validate EEG/audio-video correspondence or detection of internal realizations.
