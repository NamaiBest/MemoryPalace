"""Fresh-participant burst comparison with calibration-only background negatives.

Follows background_negatives_protocol.md, which was frozen before any evaluation
block of the untouched participant was scored. The same run validates the chosen
stretch approach (band power + calibration-selected smoothing) on that participant.
"""
from collections import Counter
import hashlib
from pathlib import Path

import joblib
import numpy as np

from .benchmark import gate_metrics, retrieval_metrics
from .burst_diagnostic import BUDGET, CATEGORIES, TOLERANCE_S, block_frame, draw_flags
from .data import write_json
from .erp import classification_metrics, eog_epochs, erp_config, extract_epochs, fit_erp
from .model import select_events
from .real_benchmark import export_real_events
from .shin import correct_ocular_from_pretask, load_session
from .signal import prepare
from .smoothing import calibrate_smoothing, export_smoothed_events, smooth_scan
from .smoothing_benchmark import plot_session as plot_stretch_session
from .workload import export_workload_events, fit_workload, labels_for_times, workload_metrics
from .workload_benchmark import file_hash, interval_assessment, utc_now

INSPECTED = {"VP001", "VP002", "VP003", "VP004", "VP005"}
BURST_ARMS = ("mean_bins", "mean_bins_background")
BURST_KINDS = BURST_ARMS + ("eog_bins",)
STRETCH_KINDS = ("power", "power_ema")


def assert_fresh(block, model):
    """ERP cards store training_hashes; workload cards store training_sample_sha256."""
    card = model.model_card
    if block.role != "evaluation" or block.recording.recording_id in card["training_recordings"]:
        raise ValueError("A calibration block cannot be evaluated as held out.")
    digest = hashlib.sha256(block.recording.samples.tobytes()).hexdigest()
    if digest in (card.get("training_hashes") or card.get("training_sample_sha256") or []):
        raise ValueError("Held-out samples duplicate calibration data.")
    model.validate_recording(block.recording)


def nearest_category(frame, times, anchor):
    return str(frame["category"][int(np.argmin(np.abs(times - anchor)))])


def evaluate_session(blocks, bursts, power, ema, out, session, participant):
    rows, stretch_plots, burst_plots = [], [], []
    burst_events = {arm: [] for arm in BURST_ARMS}
    stretch_events = {kind: [] for kind in STRETCH_KINDS}
    aligned = {kind: {"y": [], "score": []} for kind in BURST_KINDS}
    stretch_pool = {kind: {"y": [], "score": []} for kind in STRETCH_KINDS}
    block_data = {arm: [] for arm in BURST_ARMS}
    for block in blocks:
        if block.role != "evaluation":
            continue
        print(f"{participant} session {session}: evaluate held-out {block.condition}-back block", flush=True)
        for model in list(bursts.values()) + [power, ema]:
            assert_fresh(block, model)
        row = {"recording_id": block.recording.recording_id, "condition": block.condition,
               "original_offset_s": block.original_offset_s, "stretch": {}}
        raw = power.scan(block.recording)
        smoothed = smooth_scan(raw, ema.half_life_s)
        scans = {"power": raw, "power_ema": smoothed}
        labels = labels_for_times(block, raw["times"], "task_rest")
        use = raw["valid"] & (np.arange(len(labels)) % 8 == 0) & (labels >= 0)
        row["stretch_quality"] = {str(label): {"labeled": int(((labels == label) & (np.arange(len(labels)) % 8 == 0)).sum()),
                                               "accepted": int((use & (labels == label)).sum())} for label in (0, 1)}
        for kind, scan in scans.items():
            if not np.array_equal(np.isfinite(scan["scores"]), raw["valid"]):
                raise RuntimeError("Smoothing changed the validity mask.")
            row["stretch"][kind] = {"classification": workload_metrics(labels[use], scan["scores"][use]),
                                    "intervals": interval_assessment(block, scan["stretches"])}
            stretch_pool[kind]["y"].extend(labels[use].tolist())
            stretch_pool[kind]["score"].extend(scan["scores"][use].tolist())
        stretch_events["power"].extend(export_workload_events(block.recording, power, raw, block.original_offset_s))
        stretch_events["power_ema"].extend(export_smoothed_events(block.recording, ema, smoothed, block.original_offset_s))
        stretch_plots.append((block, scans))
        trace = {"recording_id": block.recording.recording_id, "offset_s": block.original_offset_s,
                 "stretch_times": raw["times"].tolist(), "stretch_valid": raw["valid"].tolist(),
                 "stretch_scores": {kind: [float(x) if np.isfinite(x) else None for x in scan["scores"]]
                                    for kind, scan in scans.items()}}
        if block.condition in (2, 3):
            marker_times = np.array([t["time_s"] for t in block.trials])
            epochs, valid = extract_epochs(prepare(block.recording, erp_config()), marker_times)
            y = np.array([t["label"] for t in block.trials])[valid]
            eye = eog_epochs(block, marker_times[valid])
            row["aligned"], row["continuous"] = {}, {}
            row["aligned_quality"] = {"trials": int(len(marker_times)), "accepted": int(len(valid)), "accepted_targets": int(y.sum())}
            for kind, model in bursts.items():
                scores = np.asarray(model.score(block.recording, eye if kind == "eog_bins" else epochs), float)
                row["aligned"][kind] = classification_metrics(y, scores)
                aligned[kind]["y"].extend(y.tolist())
                aligned[kind]["score"].extend(scores.tolist())
            truth = {"bursts": [{"anchor_s": t["time_s"]} for t in block.trials if t["label"] == 1]}
            grids, arm_scores, arm_flags = {}, {}, {}
            for arm in BURST_ARMS:
                times, scores, rejected = bursts[arm].scan(block.recording)
                times, scores = np.asarray(times, float), np.asarray(scores, float)
                frame = block_frame(block, times)
                selected = select_events(times, scores, np.ones(len(times), dtype=bool), erp_config(), BUDGET)
                categories = Counter(nearest_category(frame, times, e["anchor_s"]) for e in selected)
                row["continuous"][arm] = {
                    **retrieval_metrics(selected, truth, TOLERANCE_S),
                    **gate_metrics(times, np.ones(len(times), dtype=bool), truth, TOLERANCE_S),
                    "rejected_windows": int(rejected), "total_windows": int(len(times) + rejected),
                    "flag_categories": {c: int(categories.get(c, 0)) for c in CATEGORIES},
                    "flags_near_any_stimulus": int(categories.get("target_window", 0) + categories.get("nontarget_window", 0)),
                    "selected": selected}
                events = export_real_events(block, bursts[arm], selected, [], "all")
                for event in events:
                    event["model_version"] = f"background-v1-{arm}"
                burst_events[arm].extend(events)
                block_data[arm].append((block, times, scores, frame))
                grids[arm], arm_scores[arm], arm_flags[arm] = times, scores, selected
                trace[f"burst_times_{arm}"], trace[f"burst_scores_{arm}"] = times.tolist(), scores.tolist()
            if not np.array_equal(grids["mean_bins"], grids["mean_bins_background"]):
                raise RuntimeError("Both burst arms must share one valid grid.")
            burst_plots.append((block, grids["mean_bins"], arm_scores, arm_flags))
        write_json(out / f"session{session}.block{block.block_index + 1}.traces.json", trace)
        rows.append(row)
    for kind, events in burst_events.items():
        write_json(out / f"session{session}.burst.{kind}.events.json", sorted(events, key=lambda e: e["anchor_s"]))
    for kind, events in stretch_events.items():
        write_json(out / f"session{session}.stretch.{kind}.events.json", sorted(events, key=lambda e: e["anchor_s"]))
    plot_stretch_session(stretch_plots, out / f"session{session}.stretch.png", session, ema.half_life_s, participant)
    plot_burst_session(burst_plots, out / f"session{session}.burst.png", session, participant)
    report = {"session": session, "session_id": power.session_id, "half_life_s": ema.half_life_s, "blocks": rows,
              "aligned": {kind: classification_metrics(v["y"], v["score"]) for kind, v in aligned.items()},
              "stretch": {kind: workload_metrics(v["y"], v["score"]) for kind, v in stretch_pool.items()},
              "aligned_heldout_scores": aligned, "stretch_heldout_scores": stretch_pool}
    write_json(out / f"session{session}.report.json", report)
    return report, block_data


def null_distributions(block_data, rng, draws):
    """Random flags on the real valid grid: target matches and flags near any stimulus."""
    result = {"uniform_matches": np.zeros(draws, int), "uniform_near_stimulus": np.zeros(draws, int),
              "stimulus_blind_matches": np.zeros(draws, int)}
    truths = [{"bursts": [{"anchor_s": float(t)} for t in frame["targets"]]} for _, _, _, frame in block_data]
    for d in range(draws):
        for (_, times, _, frame), truth in zip(block_data, truths):
            flags = draw_flags(times, rng, np.arange(len(times)))
            result["uniform_matches"][d] += retrieval_metrics(flags, truth, TOLERANCE_S)["true_positives"]
            result["uniform_near_stimulus"][d] += sum(nearest_category(frame, times, f["anchor_s"]) in ("target_window", "nontarget_window") for f in flags)
            blind = draw_flags(times, rng, np.flatnonzero(frame["onset_aligned"] >= 0))
            result["stimulus_blind_matches"][d] += retrieval_metrics(blind, truth, TOLERANCE_S)["true_positives"]
    return result


def null_summary(values, observed):
    values = np.asarray(values)
    return {"mean": float(values.mean()), "interval_95": [int(np.percentile(values, 2.5)), int(np.percentile(values, 97.5))],
            "probability_at_least_observed": float((values >= observed).mean())}


def mean_or_none(values):
    values = [v for v in values if v is not None]
    return float(np.mean(values)) if values else None


def summarize(sessions, nulls):
    burst = {}
    for arm in BURST_ARMS:
        cont = [b["continuous"][arm] for s in sessions for b in s["blocks"] if "continuous" in b]
        matches, returned = sum(c["true_positives"] for c in cont), sum(c["returned"] for c in cont)
        near = sum(c["flags_near_any_stimulus"] for c in cont)
        burst[arm] = {
            "target_matches": matches, "targets": sum(c["truth_events"] for c in cont),
            "accessible_targets": sum(c["accessible_events"] for c in cont), "returned_flags": returned,
            "matched_fraction_of_flags": matches / returned if returned else None,
            "flags_near_any_stimulus": near,
            "flag_categories": {c: sum(x["flag_categories"][c] for x in cont) for c in CATEGORIES},
            "rejected_windows": sum(c["rejected_windows"] for c in cont), "total_windows": sum(c["total_windows"] for c in cont),
            "mean_localization_error_s": mean_or_none([c["mean_localization_error_s"] for c in cont]),
            "mean_known_onset_auroc": mean_or_none([s["aligned"][arm]["auroc"] for s in sessions]),
            "mean_known_onset_average_precision": mean_or_none([s["aligned"][arm]["average_precision"] for s in sessions]),
            "null": {"uniform": null_summary(nulls["uniform_matches"], matches),
                     "stimulus_blind": null_summary(nulls["stimulus_blind_matches"], matches),
                     "uniform_near_any_stimulus": null_summary(nulls["uniform_near_stimulus"], near)}}
    burst["eog_bins"] = {"mean_known_onset_auroc": mean_or_none([s["aligned"]["eog_bins"]["auroc"] for s in sessions])}
    base, bg = burst["mean_bins"], burst["mean_bins_background"]
    decision = {"a_more_matches": bg["target_matches"] > base["target_matches"],
                "b_matched_fraction_not_lower": (bg["matched_fraction_of_flags"] or 0.0) >= (base["matched_fraction_of_flags"] or 0.0),
                "c_beats_uniform_null_p_at_most_0.05": bg["null"]["uniform"]["probability_at_least_observed"] <= 0.05,
                "baseline_beats_uniform_null_p_at_most_0.05": base["null"]["uniform"]["probability_at_least_observed"] <= 0.05}
    decision["adopt_background_negatives"] = all(decision[k] for k in ("a_more_matches", "b_matched_fraction_not_lower", "c_beats_uniform_null_p_at_most_0.05"))
    stretch = {}
    for kind in STRETCH_KINDS:
        classification = [s["stretch"][kind] for s in sessions]
        intervals = [b["stretch"][kind]["intervals"] for s in sessions for b in s["blocks"]]
        stretch[kind] = {"mean_" + key: mean_or_none([r[key] for r in classification])
                         for key in ("auroc", "balanced_accuracy", "sensitivity", "specificity")}
        stretch[kind].update({key: sum(row[key] for row in intervals) for key in
                              ("returned", "true_positives", "truth_stretches", "task_covered_s", "task_total_s", "rest_covered_s", "rest_total_s")})
    stretch["half_lives_s"] = [s["half_life_s"] for s in sessions]
    quality = {"stretch": {str(label): {key: sum(b["stretch_quality"][str(label)][key] for s in sessions for b in s["blocks"])
                                        for key in ("labeled", "accepted")} for label in (0, 1)},
               "aligned": {key: sum(b["aligned_quality"][key] for s in sessions for b in s["blocks"] if "aligned_quality" in b)
                           for key in ("trials", "accepted", "accepted_targets")}}
    return {"burst": burst, "decision": decision, "stretch": stretch, "quality": quality}


def run_background_benchmark(directory, out, draws=2000, seed=19):
    directory, out = Path(directory), Path(out)
    if directory.name in INSPECTED:
        raise ValueError("This comparison requires an untouched participant; VP001-VP005 were already inspected.")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory is not empty; preserve previous results.")
    root = Path(__file__).resolve().parent.parent
    protocol = root / "background_negatives_protocol.md"
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "protocol_snapshot.json", {
        "started_utc": utc_now(), "participant": directory.name,
        "purpose": "fresh-participant burst comparison with calibration-only background negatives; validation of the chosen stretch approach",
        "protocol": protocol.read_text(), "protocol_sha256": file_hash(protocol),
        "data_sha256": {p.name: file_hash(p) for p in sorted(directory.glob("nback*"))},
        "source_sha256": {str(p.relative_to(root)): file_hash(p) for p in sorted((root / "eeg_moments").glob("*.py"))},
        "null_draws": draws, "seed": seed})
    contexts, frozen = [], {"models": {}, "in_memory_hashes": {}}
    for session in (1, 2, 3):
        print(f"{directory.name} session {session}: calibrate every model on calibration blocks only", flush=True)
        blocks, audit = load_session(directory, session)
        blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
        write_json(out / f"session{session}.audit.json", audit)
        calibration = [b for b in blocks if b.role == "calibration"]
        bursts = {kind: fit_erp(calibration, kind) for kind in BURST_KINDS}
        power = fit_workload(calibration, "power", "task_rest")
        ema = calibrate_smoothing(calibration, power)
        models = {f"session{session}.burst.{kind}.joblib": model for kind, model in bursts.items()}
        models.update({f"session{session}.stretch.power.joblib": power, f"session{session}.stretch.power_ema.joblib": ema})
        for name, model in models.items():
            joblib.dump(model, out / name)
            write_json((out / name).with_suffix(".model_card.json"), model.model_card)
            frozen["models"][name] = file_hash(out / name)
            frozen["in_memory_hashes"][name] = joblib.hash(model)
        contexts.append((session, blocks, bursts, power, ema, models))
    frozen["frozen_utc"] = utc_now()
    write_json(out / "frozen_models.json", frozen)
    evaluation_started = utc_now()
    sessions, block_data = [], {arm: [] for arm in BURST_ARMS}
    for session, blocks, bursts, power, ema, _ in contexts:
        report, data = evaluate_session(blocks, bursts, power, ema, out, session, directory.name)
        sessions.append(report)
        for arm in BURST_ARMS:
            block_data[arm].extend(data[arm])
    for _, _, _, _, _, models in contexts:
        for name, model in models.items():
            if joblib.hash(model) != frozen["in_memory_hashes"][name] or file_hash(out / name) != frozen["models"][name]:
                raise RuntimeError("Evaluation changed fitted state or saved weights.")
    nulls = null_distributions(block_data["mean_bins"], np.random.default_rng(seed), draws)
    summary = summarize(sessions, nulls)
    report = {"participant": directory.name, "purpose": "fresh-participant burst comparison; chosen-stretch validation",
              "protocol_sha256": file_hash(protocol), "evaluation_started_utc": evaluation_started,
              "completed_utc": utc_now(), "fitted_states_unchanged": True, "sessions": sessions,
              "null_draws": draws, "null_distributions": {k: v.tolist() for k, v in nulls.items()}, **summary}
    write_json(out / "report.json", report)
    write_results(report, out)
    plot_nulls(report, out / "nulls.png")
    return report


def fmt(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def write_results(report, out):
    b, d, s, q = report["burst"], report["decision"], report["stretch"], report["quality"]
    lines = [f"# Background negatives for burst candidates — fresh {report['participant']}", "",
             "One untouched participant, three sessions calibrated separately, all models frozen before scoring. "
             "Burst arms scan the marker-free 0.1 s grid of the held-out 2-/3-back blocks with the same mask, budget "
             f"({BUDGET} per block), 1.5 s separation and ±{TOLERANCE_S} s matching. Protocol: `background_negatives_protocol.md`.", "",
             "## Continuous target retrieval", "",
             "| Arm | Target matches | Returned flags | Matched fraction | Flags near any stimulus | Known-onset AUROC | P(uniform null ≥ matches) | P(stimulus-blind null ≥ matches) |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for arm in BURST_ARMS:
        a = b[arm]
        lines.append(f"| {arm} | {a['target_matches']}/{a['targets']} | {a['returned_flags']} | {fmt(a['matched_fraction_of_flags'])} | "
                     f"{a['flags_near_any_stimulus']} | {fmt(a['mean_known_onset_auroc'])} | {a['null']['uniform']['probability_at_least_observed']:.3f} | "
                     f"{a['null']['stimulus_blind']['probability_at_least_observed']:.3f} |")
    u, sb, un = b["mean_bins"]["null"]["uniform"], b["mean_bins"]["null"]["stimulus_blind"], b["mean_bins"]["null"]["uniform_near_any_stimulus"]
    lines += ["", f"Random-flag references on this participant's own valid grid ({report['null_draws']} draws): uniform placement matches "
              f"{u['mean']:.2f} targets [95% interval {u['interval_95'][0]}–{u['interval_95'][1]}] and lands {un['mean']:.1f} of 30 flags near a stimulus "
              f"[{un['interval_95'][0]}–{un['interval_95'][1]}]; stimulus-blind placement matches {sb['mean']:.2f} [{sb['interval_95'][0]}–{sb['interval_95'][1]}]. "
              f"Accessible targets under the shared mask: {b['mean_bins']['accessible_targets']}/{b['mean_bins']['targets']}. "
              f"Eye-only known-onset AUROC: {fmt(b['eog_bins']['mean_known_onset_auroc'])}.", "",
              "| Arm | Target window | Non-target window | Between stimuli | Context margin | Mean localization error |", "|---|---:|---:|---:|---:|---:|"]
    for arm in BURST_ARMS:
        c = b[arm]["flag_categories"]
        lines.append(f"| {arm} | {c['target_window']} | {c['nontarget_window']} | {c['between_stimuli']} | {c['context_margin']} | {fmt(b[arm]['mean_localization_error_s'], 2)} s |")
    lines += ["", "## Prespecified decision", ""]
    lines += [f"- (a) more target matches than the baseline: {d['a_more_matches']}",
              f"- (b) matched fraction of returned flags not lower: {d['b_matched_fraction_not_lower']}",
              f"- (c) uniform-null probability at most 0.05: {d['c_beats_uniform_null_p_at_most_0.05']}",
              f"- baseline itself beats the uniform null at 0.05: {d['baseline_beats_uniform_null_p_at_most_0.05']}",
              f"- **Adopt background negatives: {d['adopt_background_negatives']}**", "",
              "## Known-onset control by session", "",
              "| Session | mean_bins AUROC | mean_bins_background AUROC | eog_bins AUROC | Accepted trials (targets) |", "|---|---:|---:|---:|---:|"]
    for sess in report["sessions"]:
        aq = [blk["aligned_quality"] for blk in sess["blocks"] if "aligned_quality" in blk]
        lines.append(f"| {sess['session_id']} | {fmt(sess['aligned']['mean_bins']['auroc'])} | {fmt(sess['aligned']['mean_bins_background']['auroc'])} | "
                     f"{fmt(sess['aligned']['eog_bins']['auroc'])} | {sum(x['accepted'] for x in aq)} ({sum(x['accepted_targets'] for x in aq)}) |")
    lines += ["", "## Chosen stretch approach on the same participant", "",
              "| Model | Mean AUROC | Mean balanced accuracy | Intervals | Whole-task matches | Task covered | Rest included |", "|---|---:|---:|---:|---:|---:|---:|"]
    for kind in STRETCH_KINDS:
        r = s[kind]
        lines.append(f"| {kind} | {fmt(r['mean_auroc'])} | {fmt(r['mean_balanced_accuracy'])} | {r['returned']} | {r['true_positives']}/{r['truth_stretches']} | "
                     f"{r['task_covered_s'] / r['task_total_s']:.1%} | {r['rest_covered_s']:.2f}/{r['rest_total_s']:.0f} s |")
    lines += ["", f"Calibration-selected half-lives by session: {', '.join(f'{h:g} s' for h in s['half_lives_s'])}. "
              f"Accepted non-overlapping labeled windows: task {q['stretch']['1']['accepted']}/{q['stretch']['1']['labeled']}, rest {q['stretch']['0']['accepted']}/{q['stretch']['0']['labeled']}. "
              "This validates the already-chosen approach; no alternative stretch model was fitted and no selection was made.", "",
              "Descriptive nulls on dependent windows are reference points, not significance tests. Targets are a task proxy, not spontaneous insight. "
              "Eye, motor and sensory contributions are not isolated. One participant limits every conclusion. Replay EEG does not describe the phone-video participant. "
              "See INTERPRETATION.md, report.json, per-session reports, traces, events and plots.", ""]
    (out / "RESULTS.md").write_text("\n".join(lines))


def plot_burst_session(rows, path, session, participant):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if not rows:
        return
    fig, axes = plt.subplots(len(BURST_ARMS), len(rows), figsize=(7 * len(rows), 3.2 * len(BURST_ARMS)), squeeze=False, layout="constrained")
    for col, (block, times, scores, flags) in enumerate(rows):
        for row, arm in enumerate(BURST_ARMS):
            ax = axes[row, col]
            ax.axvspan(block.task_start_s, block.task_end_s, color="#e6efe8", alpha=0.6)
            for trial in block.trials:
                ax.axvline(trial["time_s"], color="#2b7a4b" if trial["label"] else "#c9c9c9", lw=1.2 if trial["label"] else 0.6, alpha=0.9)
            ax.plot(times, scores[arm], color="#347b9b", lw=0.9)
            ax.axhline(0, color="#555555", ls="--", lw=0.7)
            ax.scatter([f["anchor_s"] for f in flags[arm]], [f["raw_score"] for f in flags[arm]], color="#cf493f", zorder=5, s=28)
            ax.set_ylabel(f"{arm}\nmargin")
            ax.grid(alpha=0.15)
            if row == 0:
                ax.set_title(f"{block.condition}-back, block {block.block_index + 1}: green = target onsets, grey = non-targets, red = returned flags", fontsize=9)
            else:
                ax.set_xlabel("Seconds within recorded excerpt")
    fig.suptitle(f"{participant} session {session}: marker-free burst scan of held-out blocks; models frozen before scoring")
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_nulls(report, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    nulls = {k: np.asarray(v) for k, v in report["null_distributions"].items()}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), layout="constrained")
    colors = {"mean_bins": "#8b1e1e", "mean_bins_background": "#1f5f8b"}
    panels = [("uniform_matches", "target matches, uniform random flags", "target_matches"),
              ("stimulus_blind_matches", "target matches, stimulus-blind random flags", "target_matches"),
              ("uniform_near_stimulus", "flags near any stimulus, uniform random flags", "flags_near_any_stimulus")]
    for ax, (key, title, observed_key) in zip(axes, panels):
        values = nulls[key]
        ax.hist(values, bins=np.arange(values.min() - 0.5, values.max() + 1.5), color="#9aa7b1", density=True)
        for arm in BURST_ARMS:
            ax.axvline(report["burst"][arm][observed_key], color=colors[arm], lw=2, label=f"{arm}: {report['burst'][arm][observed_key]}")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("count over six held-out blocks")
        ax.legend(fontsize=8)
    fig.suptitle(f"{report['participant']}: observed counts against random-flag references on the same grid, mask, budget and tolerance")
    fig.savefig(path, dpi=130)
    plt.close(fig)
