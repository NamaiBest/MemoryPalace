"""Fixed-protocol real EEG feasibility benchmark; see real_eeg_protocol.md."""
from dataclasses import asdict, replace
import hashlib
import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score

from .benchmark import gate_metrics, retrieval_metrics, stretch_metrics
from .data import write_json
from .erp import classification_metrics, eog_epochs, erp_config, extract_epochs, fit_erp
from .model import export_events, select_events
from .shin import EEG_CHANNELS, FRONTAL, correct_ocular_from_pretask, load_session
from .signal import Config, StretchReference, gate_mask, prepare, stretch_trace


def stretch_config():
    return Config(sample_rate=200.0, channels=EEG_CHANNELS, frontal_channels=FRONTAL,
                  quality_highpass_hz=1.0, quality_lowpass_hz=30.0)


def assess_stretches(block, prepared, reference, config):
    detected, times, z, valid = reference.detect(prepared, config)
    # Conservative task/rest comparison excludes transitions and instructions.
    task = (times >= block.task_start_s + 2) & (times <= block.task_end_s - 2)
    rest = np.zeros(len(times), dtype=bool)
    for start, end in block.baseline_intervals_s:
        rest |= (times >= start + 1) & (times <= end - 1)
    use = valid & (task | rest)
    labels = task[use].astype(int)
    auc = float(roc_auc_score(labels, z[use])) if len(np.unique(labels)) == 2 else None
    proxy_truth = {"stretches": [{"start_s": block.task_start_s, "end_s": block.task_end_s}]}
    interval_metrics = stretch_metrics(detected, proxy_truth)
    summary = {"condition": block.condition, "detected": detected,
               "task_interval_proxy": interval_metrics, "task_vs_rest_theta_auroc": auc,
               "task_median_z": float(np.median(z[task & valid])) if np.any(task & valid) else None,
               "rest_median_z": float(np.median(z[rest & valid])) if np.any(rest & valid) else None,
               "task_valid_centers": int((task & valid).sum()), "task_total_centers": int(task.sum()),
               "rest_valid_centers": int((rest & valid).sum()), "rest_total_centers": int(rest.sum()),
               "off_task_detected_onsets": sum(not block.task_start_s <= e["start_s"] <= block.task_end_s for e in detected),
               "interpretation": "Task intervals are behavioral proxies, not measured neural stretch truth."}
    return summary, {"times": times, "z": z, "valid": valid, "detected": detected}


def export_real_events(block, model, selected, stretches, scope):
    events = export_events(block.recording, model, selected, offset_s=block.original_offset_s,
                           stretches=stretches, scope=scope)
    for event in events:
        event["task_condition"] = block.condition
        if event["signal_type"] == "burst":
            onset = event["eeg_anchor_s"]
            event["event_type"] = "eeg_evoked_response_candidate"
            event["start_s"] = max(0, onset - 0.1) + block.original_offset_s
            event["end_s"] = min(block.recording.duration_s, onset + 1.0) + block.original_offset_s
            event["anchor_definition"] = "proposed stimulus onset; not the peak latency of a P300"
            event["evidence"] = "Frozen within-session ERP classifier ranked this EEG window as target-like; cognitive meaning unverified."
            event["model_version"] = f"real-shin2018-{model.kind}-v1"
    bursts = [e for e in events if e["signal_type"] == "burst"]
    sustained = [e for e in events if e["signal_type"] == "stretch"]
    for burst in bursts:
        burst["overlapping_stretch_ids"] = [s["event_id"] for s in sustained
                                            if burst["start_s"] < s["end_s"] and burst["end_s"] > s["start_s"]]
    for stretch in sustained:
        stretch["overlapping_burst_ids"] = [b["event_id"] for b in bursts
                                            if stretch["event_id"] in b["overlapping_stretch_ids"]]
    return events


def run_session(directory, out, session):
    blocks, audit = load_session(directory, session)
    blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
    write_json(out / f"session{session}.audit.json", audit)
    calibration = [b for b in blocks if b.role == "calibration"]
    testing = [b for b in blocks if b.role == "evaluation"]
    config = stretch_config()
    calibrated = [prepare(b.recording, config) for b in calibration]
    reference = StretchReference.fit(calibrated, [b.baseline_intervals_s for b in calibration], config)
    models = {}
    for kind in ("mean_bins", "xdawn", "eog_bins"):
        print(f"Session {session}: fitting {kind} on calibration blocks only", flush=True)
        model = fit_erp(calibration, kind)
        models[kind] = model
        joblib.dump(model, out / f"session{session}.{kind}.joblib")
        write_json(out / f"session{session}.{kind}.model_card.json", model.model_card)
    joblib.dump({"reference": reference, "config": config, "session_id": calibration[0].recording.session_id},
                out / f"session{session}.stretch.joblib")
    traces, diagnostics, reports = [], [], []
    all_labels = []
    all_scores = {kind: [] for kind in models}
    all_events = {kind: {scope: [] for scope in ("all", "onset")} for kind in ("mean_bins", "xdawn")}
    for block in testing:
        print(f"Session {session}: evaluating held-out {block.condition}-back block", flush=True)
        stretch_result, trace = assess_stretches(block, prepare(block.recording, config), reference, config)
        trace["offset_s"] = block.original_offset_s
        trace["condition"] = block.condition
        trace["task"] = [block.task_start_s, block.task_end_s]
        traces.append(trace)
        report = {"recording_id": block.recording.recording_id, "condition": block.condition,
                  "original_offset_s": block.original_offset_s, "stretch": stretch_result}
        if block.condition == 0:
            for kind in all_events:
                for scope in all_events[kind]:
                    all_events[kind][scope].extend(export_real_events(block, models[kind], [], trace["detected"], scope))
            reports.append(report)
            continue
        prepared = prepare(block.recording, erp_config())
        marker_times = np.asarray([t["time_s"] for t in block.trials])
        labels = np.asarray([t["label"] for t in block.trials])
        epochs, valid = extract_epochs(prepared, marker_times)
        eye_epochs = eog_epochs(block, marker_times[valid])
        all_labels.extend(labels[valid])
        report["erp_quality"] = {"total_trials": len(labels), "accepted_trials": len(valid),
                                 "accepted_targets": int(labels[valid].sum()),
                                 "rejected_targets": int(labels.sum() - labels[valid].sum()),
                                 "rejected_non_targets": int(len(labels) - labels.sum() - len(valid) + labels[valid].sum()),
                                 "accepted_marker_times_s": marker_times[valid].tolist(),
                                 "bad_or_edge_fraction": float(prepared.bad.mean())}
        report["aligned_erp"] = {}
        report["continuous_retrieval"] = {}
        for kind, model in models.items():
            scores = model.score(block.recording, eye_epochs if kind == "eog_bins" else epochs)
            all_scores[kind].extend(scores)
            report["aligned_erp"][kind] = classification_metrics(labels[valid], scores)
            if kind == "eog_bins":
                continue
            # Marker-free inference: model.scan receives only samples and recording metadata.
            times, scan_scores, rejected = model.scan(block.recording)
            masks = {"all": np.ones(len(times), dtype=bool),
                     "onset": gate_mask(times, trace["detected"], config)}
            truth = {"bursts": [{"anchor_s": t["time_s"]} for t in block.trials if t["label"] == 1]}
            rows = {}
            for scope, mask in masks.items():
                selected = select_events(times, scan_scores, mask, replace(config, separation_s=1.5), top_k=5)
                metrics = retrieval_metrics(selected, truth, tolerance_s=0.5)
                gates = gate_metrics(times, mask, truth, tolerance_s=0.5)
                rows[scope] = {**metrics, **gates, "rejected_grid_centers": rejected, "selected": selected,
                               "matching_tolerance_s": 0.5, "review_budget": 5}
                all_events[kind][scope].extend(export_real_events(block, model, selected, trace["detected"], scope))
            report["continuous_retrieval"][kind] = rows
            if kind == "xdawn":
                trace["erp_times"], trace["erp_scores"] = times, scan_scores
                trace["targets"] = [t["anchor_s"] for t in truth["bursts"]]
        if len(valid):
            diagnostics.append({"epochs": epochs, "eog_epochs": eye_epochs, "labels": labels[valid]})
        reports.append(report)
    for kind, by_scope in all_events.items():
        for scope, events in by_scope.items():
            write_json(out / f"session{session}.{kind}.{scope}.events.json", sorted(events, key=lambda e: e["anchor_s"]))
    result = {"session": session, "session_id": calibration[0].recording.session_id,
              "stretch_reference": asdict(reference), "stretch_config": asdict(config),
              "training_blocks": len(calibration), "held_out_blocks": len(testing),
              "aligned_erp": {kind: classification_metrics(all_labels, scores) for kind, scores in all_scores.items()},
              "blocks": reports}
    plot_session(out / f"session{session}.diagnostic.png", traces, diagnostics, result)
    return result


def plot_session(path, traces, diagnostics, result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 1, figsize=(13, 11), layout="constrained")
    colors = {0: "#707780", 2: "#24866e", 3: "#b55832"}
    for trace in traces:
        offset = trace["offset_s"]
        time = trace["times"] + offset
        axes[0].plot(time, np.where(trace["valid"], trace["z"], np.nan), color=colors[trace["condition"]],
                     label=f"{trace['condition']}-back")
        axes[0].axvspan(offset + trace["task"][0], offset + trace["task"][1], alpha=0.12, color=colors[trace["condition"]])
        for stretch in trace["detected"]:
            axes[0].axvspan(offset + stretch["start_s"], offset + stretch["end_s"], color="#daaa20", alpha=0.35)
        if "erp_times" in trace:
            gaps = np.flatnonzero(np.diff(trace["erp_times"]) > 0.15) + 1
            axes[1].plot(np.insert(trace["erp_times"] + offset, gaps, np.nan),
                         np.insert(trace["erp_scores"], gaps, np.nan), color=colors[trace["condition"]])
            for target in trace["targets"]:
                axes[1].axvline(target + offset, color="#ab3044", linestyle=":", alpha=0.6)
    axes[0].axhline(3, color="gray", linestyle="--", label="fixed stretch entry")
    axes[0].set_ylabel("Frontal theta robust z")
    axes[0].legend(loc="upper right")
    axes[0].set_title("Held-out task intervals (pale shading); detected stretches (gold)")
    axes[1].axhline(0, color="gray", linestyle="--")
    axes[1].set_ylabel("xDAWN scan margin")
    axes[1].set_xlabel("Original recording time (s); red dotted lines = target stimuli")
    axes[1].sharex(axes[0])
    if diagnostics:
        epochs = np.concatenate([d["epochs"] for d in diagnostics])
        eye = np.concatenate([d["eog_epochs"] for d in diagnostics])
        labels = np.concatenate([d["labels"] for d in diagnostics])
        time = np.arange(220) / 200 - 0.1
        for label, color in [(0, "#416b97"), (1, "#b84455")]:
            if not np.any(labels == label):
                continue
            word = "target" if label else "non-target"
            axes[2].plot(time, epochs[labels == label, EEG_CHANNELS.index("Pz")].mean(axis=0),
                         color=color, label=f"Pz {word} (n={np.sum(labels == label)})")
            for i, name in enumerate(("HEOG", "VEOG")):
                axes[3].plot(time, eye[labels == label, i].mean(axis=0), color=color,
                             linestyle="-" if i == 0 else "--", label=f"{name} {word}")
    axes[2].set_ylabel("Mean Pz voltage (uV)")
    axes[3].set_ylabel("Mean EOG voltage (uV)")
    axes[3].set_xlabel("Seconds relative to stimulus (averages use markers only for diagnostics)")
    for ax in axes[2:]:
        ax.axvline(0, color="gray", linewidth=0.8)
        ax.legend(loc="upper right")
    for ax in axes:
        ax.grid(alpha=0.15)
    fig.suptitle(f"Real EEG: VP001 session {result['session']} — within-session held-out feasibility test")
    fig.savefig(path, dpi=140)
    plt.close(fig)


def run_real_benchmark(directory, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(out.resolve() / ".matplotlib"))
    protocol = Path(__file__).resolve().parent.parent / "real_eeg_protocol.md"
    write_json(out / "protocol_snapshot.json", {"sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
                                                "text": protocol.read_text()})
    sessions = []
    for session in (1, 2, 3):
        result = run_session(directory, out, session)
        sessions.append(result)
        write_json(out / f"session{session}.report.json", result)
    blocks = [b for s in sessions for b in s["blocks"]]
    intervals = [b["stretch"]["task_interval_proxy"] for b in blocks]
    summary = {"task_blocks": len(blocks), "matched_task_intervals": sum(r["true_positives"] for r in intervals),
               "detected_stretches": sum(r["returned"] for r in intervals),
               "unmatched_stretches": sum(r["false_positives"] for r in intervals),
               "note": "IoU >=0.5 against task intervals; not neural-stretch ground truth."}
    retrieval = {}
    for kind in ("mean_bins", "xdawn"):
        retrieval[kind] = {}
        for scope in ("all", "onset"):
            rows = [b["continuous_retrieval"][kind][scope] for b in blocks if "continuous_retrieval" in b]
            total, found = sum(r["truth_events"] for r in rows), sum(r["true_positives"] for r in rows)
            returned = sum(r["returned"] for r in rows)
            retrieval[kind][scope] = {"targets": total, "matched_targets": found, "returned": returned,
                                     "unmatched_flags": returned - found, "target_recall": found / total if total else None,
                                     "target_precision": found / returned if returned else None,
                                     "accessible_targets": sum(r["accessible_events"] for r in rows),
                                     "gate_valid_grid_fraction": sum(r["eligible_centers"] for r in rows) / max(sum(r["valid_centers"] for r in rows), 1)}
    report = {"status": "real_single_participant_feasibility", "dataset": "Shin2018-A", "participant": "VP001",
              "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
              "stretch_summary": summary, "continuous_retrieval_summary": retrieval, "sessions": sessions,
              "limitations": ["One participant, three separately calibrated sessions; no population accuracy claim.",
                              "Pre-task EOG regression may remove eye-correlated EEG and does not remove every artifact.",
                              "Task intervals are workload proxies; target labels are not guaranteed single-trial P300 truth.",
                              "ERP aligned metrics use known markers; continuous scan does not receive trial markers.",
                              "Continuous tests use held-out 2-/3-back excerpts plus rest, not unconstrained daily work.",
                              "EEG and EOG may reflect sensory, motor, and ocular differences; no isolated insight claim.",
                              "No correctness/response-time logs, no complete artifact source separation.",
                              "Filtered window overlap makes window-level observations dependent."]}
    write_json(out / "report.json", report)
    lines = ["# First real EEG test", "", "**Shin 2018 n-back, VP001. Three separately calibrated sessions.**", "",
             "In each session, six early task blocks calibrate the models; three later blocks are held out.",
             "No synthetic samples or weights. Recorded marker timestamps retained; no shuffled window split.", "",
             "## Marker-aligned target/non-target classification", "",
             "Known stimulus onsets are provided for this positive control. AP chance baseline is the retained target prevalence.", "",
             "| Session | Model | Clean trials | Targets | AUROC | AP | AP baseline | Balanced accuracy |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    fmt = lambda value: "n/a" if value is None else f"{value:.3f}"
    for session in sessions:
        for kind, metrics in session["aligned_erp"].items():
            lines.append(f"| {session['session']} | {kind} | {metrics['trials']} | {metrics['targets']} | "
                         f"{fmt(metrics['auroc'])} | {fmt(metrics['average_precision'])} | "
                         f"{fmt(metrics['target_prevalence'])} | {fmt(metrics['balanced_accuracy_margin_zero'])} |")
    lines += ["", "`eog_bins` uses eye channels only as a confounding control, never for EEG event export.", "",
              "## Continuous scan without trial timestamps", "",
              "Up to five candidates per held-out 2-/3-back block, ±0.5 s one-to-one target-onset matching.", "",
              "| Model | Search | Matched / all target markers | Returned flags | Unmatched flags | Accessible targets | Valid-grid coverage |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for kind, scopes in retrieval.items():
        for scope, metrics in scopes.items():
            lines.append(f"| {kind} | {scope} | {metrics['matched_targets']} / {metrics['targets']} | {metrics['returned']} | "
                         f"{metrics['unmatched_flags']} | {metrics['accessible_targets']} | {metrics['gate_valid_grid_fraction']:.1%} |")
    lines += ["", "Unmatched means not near a labeled target onset; it does not prove absence of other neural activity.", "",
              "## Sustained stretch rule", "",
              f"The fixed frontal-theta rule returned {summary['detected_stretches']} stretch intervals; "
              f"{summary['matched_task_intervals']} / {summary['task_blocks']} held-out task intervals matched at IoU ≥ 0.5.",
              "Task blocks are behavioral proxies, so this is a task-overlap check rather than validated mental-state detection.",
              "Per-block theta task/rest separation and quality coverage appear in `report.json`.", "",
              "## Interpretation limits", ""]
    lines += [f"- {limitation}" for limitation in report["limitations"]]
    lines += ["", "Sources: [dataset and download](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/), "
              "[data descriptor](https://doi.org/10.1038/sdata.2018.3).", "",
              "See `session*.diagnostic.png`, `session*.audit.json`, and `session*.events.json` for evidence and replay outputs."]
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n")
    return report
