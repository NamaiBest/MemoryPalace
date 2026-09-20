"""Fresh-participant workload evaluation, with all fits completed before testing."""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np

from .benchmark import gate_metrics, stretch_metrics
from .data import write_json
from .erp import erp_config, extract_epochs
from .shin import correct_ocular_from_pretask, load_session
from .signal import StretchReference, gate_mask, prepare
from .workload import (KINDS, TARGETS, export_workload_events, extract_workload_windows,
                       eye_windows, fit_workload, labels_for_times, workload_config,
                       workload_features, workload_metrics)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def covered_seconds(intervals, regions):
    return float(sum(max(0, min(s["end_s"], end) - max(s["start_s"], start))
                     for s in intervals for start, end in regions))


def interval_assessment(block, stretches):
    truth = {"stretches": [{"start_s": block.task_start_s, "end_s": block.task_end_s}]}
    result = stretch_metrics(stretches, truth)
    result.update({"task_covered_s": covered_seconds(stretches, [[block.task_start_s, block.task_end_s]]),
                   "task_total_s": block.task_end_s - block.task_start_s,
                   "rest_covered_s": covered_seconds(stretches, block.baseline_intervals_s),
                   "rest_total_s": sum(end - start for start, end in block.baseline_intervals_s),
                   "detected": stretches})
    return result


def assert_heldout(block, model):
    if block.role != "evaluation" or block.recording.recording_id in model.model_card["training_recordings"]:
        raise ValueError("A calibration block cannot be evaluated as held out.")
    digest = hashlib.sha256(block.recording.samples.tobytes()).hexdigest()
    if digest in model.model_card["training_sample_sha256"]:
        raise ValueError("Held-out samples duplicate calibration data.")
    model.validate_recording(block.recording)


def evaluate_session(blocks, models, reference, out, session):
    config = workload_config()
    pooled = {target: {kind: {"y": [], "score": []} for kind in KINDS} for target in TARGETS}
    pooled["task_rest"]["fixed_theta"] = {"y": [], "score": []}
    exports = {kind: [] for kind in ("power", "tangent")}
    reports, plots = [], []
    for block in blocks:
        if block.role != "evaluation":
            continue
        print(f"Session {session}: held-out {block.condition}-back evaluation", flush=True)
        for model in models.values():
            assert_heldout(block, model)
        prepared = prepare(block.recording, config)
        epochs, times, accepted = extract_workload_windows(prepared)
        features = {kind: workload_features(eye_windows(block, times[accepted]) if kind == "eog_power" else epochs, kind)
                    for kind in KINDS} if len(accepted) else {kind: [] for kind in KINDS}
        theta_events, theta_times, theta_scores, theta_valid = reference.detect(prepared, config)
        theta_scan = {"times": theta_times, "scores": theta_scores, "valid": theta_valid, "stretches": theta_events}
        scans = {kind: models[("task_rest", kind)].scan(block.recording) for kind in ("power", "tangent")}
        scans["fixed_theta"] = theta_scan
        row = {"recording_id": block.recording.recording_id, "condition": block.condition,
               "original_offset_s": block.original_offset_s, "task_start_s": block.task_start_s,
               "task_end_s": block.task_end_s, "window_quality": {}, "classification": {}, "intervals": {},
               "onset_gate": {}}
        for target in TARGETS:
            labels = labels_for_times(block, times, target)
            keep = labels[accepted] >= 0
            y = labels[accepted][keep]
            row["window_quality"][target] = {
                "labeled_windows": int((labels >= 0).sum()), "accepted_windows": int(keep.sum()),
                "labeled_positives": int((labels == 1).sum()), "accepted_positives": int((y == 1).sum()),
                "labeled_negatives": int((labels == 0).sum()), "accepted_negatives": int((y == 0).sum())}
            row["classification"][target] = {}
            for kind in KINDS:
                scores = models[(target, kind)].score_features(block.recording, features[kind])[keep]
                row["classification"][target][kind] = workload_metrics(y, scores)
                pooled[target][kind]["y"].extend(y.tolist())
                pooled[target][kind]["score"].extend(scores.tolist())
            if target == "task_rest":
                # Same accepted nonoverlapping windows as the learned models.
                scores = np.interp(times[accepted][keep], theta_times, theta_scores)
                row["classification"][target]["fixed_theta"] = workload_metrics(y, scores, 3.0)
                pooled[target]["fixed_theta"]["y"].extend(y.tolist())
                pooled[target]["fixed_theta"]["score"].extend(scores.tolist())
        for kind, scan in scans.items():
            row["intervals"][kind] = interval_assessment(block, scan["stretches"])
            if kind != "fixed_theta":
                exports[kind].extend(export_workload_events(block.recording, models[("task_rest", kind)],
                                                           scan, block.original_offset_s))
        if block.condition in (2, 3):
            # Only candidate eligibility is measured; no new burst classifier is fitted.
            grid = np.arange(0.1, block.recording.duration_s - 1.0, 0.1)
            _, valid = extract_epochs(prepare(block.recording, erp_config()), grid)
            grid = grid[valid]
            truth = {"bursts": [{"anchor_s": t["time_s"]} for t in block.trials if t["label"] == 1]}
            row["onset_gate"]["all"] = gate_metrics(grid, np.ones(len(grid), dtype=bool), truth, 0.5)
            for kind, scan in scans.items():
                row["onset_gate"][kind] = gate_metrics(grid, gate_mask(grid, scan["stretches"], config), truth, 0.5)
        reports.append(row)
        plots.append((block, scans))
    metrics = {target: {kind: workload_metrics(v["y"], v["score"], 3.0 if kind == "fixed_theta" else 0.0)
                        for kind, v in by_kind.items()} for target, by_kind in pooled.items()}
    for kind, events in exports.items():
        write_json(out / f"session{session}.{kind}.events.json", sorted(events, key=lambda e: e["anchor_s"]))
    result = {"session": session, "session_id": blocks[0].recording.session_id,
              "classification": metrics, "blocks": reports,
              "scores": pooled, "score_pooling": "Within this session only; never across sessions."}
    write_json(out / f"session{session}.report.json", result)
    plot_session(plots, out / f"session{session}.diagnostic.png", session)
    return result


def plot_session(items, path, session):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 3, figsize=(15, 9), sharex="col")
    colors = {"power": "#2166ac", "tangent": "#762a83", "fixed_theta": "#c25d08"}
    for column, (block, scans) in enumerate(items):
        for row, (kind, scan) in enumerate(scans.items()):
            ax = axes[row, column]
            ax.axvspan(block.task_start_s, block.task_end_s, color="#a8c5b5", alpha=0.28, label="task label")
            for start, end in block.baseline_intervals_s:
                ax.axvspan(start, end, color="#86bfe5", alpha=0.25, label="rest label" if start < 10 else None)
            ax.plot(scan["times"], np.where(scan["valid"], scan["scores"], np.nan), color=colors[kind], lw=1.1)
            ax.axhline(3 if kind == "fixed_theta" else 0, color="#444444", lw=0.8, ls="--")
            for s in scan["stretches"]:
                ax.axvspan(s["start_s"], s["end_s"], ymin=0.94, ymax=1, color="#cf493f")
            ax.set_ylabel("theta z" if kind == "fixed_theta" else f"{kind} margin")
            ax.grid(alpha=0.12)
            if row == 0:
                ax.set_title(f"Held-out {block.condition}-back | block {block.block_index + 1}")
                if column == 0:
                    ax.legend(fontsize=8, loc="lower right")
            if row == 2:
                ax.set_xlabel("Seconds within recorded excerpt")
    fig.suptitle(f"VP002 session {session}: frozen task/rest models | red bars = detected intervals", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def aggregate_intervals(sessions):
    result = {}
    for kind in ("power", "tangent", "fixed_theta"):
        rows = [b["intervals"][kind] for s in sessions for b in s["blocks"]]
        gates = [b["onset_gate"][kind] for s in sessions for b in s["blocks"] if b["onset_gate"]]
        onset_errors = [r["mean_abs_onset_error_s"] for r in rows if r["mean_abs_onset_error_s"] is not None]
        result[kind] = {
            "task_blocks": len(rows), "detected_intervals": sum(r["returned"] for r in rows),
            "matched_task_intervals": sum(r["true_positives"] for r in rows),
            "unmatched_intervals": sum(r["false_positives"] for r in rows),
            "task_covered_s": sum(r["task_covered_s"] for r in rows),
            "task_total_s": sum(r["task_total_s"] for r in rows),
            "rest_covered_s": sum(r["rest_covered_s"] for r in rows),
            "rest_total_s": sum(r["rest_total_s"] for r in rows),
            "mean_abs_onset_error_s_matched_only": float(np.mean(onset_errors)) if onset_errors else None,
            "gate_accessible_targets": sum(r["accessible_events"] for r in gates),
            "gate_all_targets": sum(r["truth_events"] for r in gates),
            "gate_eligible_centers": sum(r["eligible_centers"] for r in gates),
            "gate_valid_centers": sum(r["valid_centers"] for r in gates)}
    return result


def write_report(report, out):
    fmt = lambda v: "n/a" if v is None else f"{v:.3f}"
    lines = ["# Fresh EEG workload test: VP002", "",
             "One new participant, three separately calibrated sessions. First six blocks fit each model; "
             "last three blocks test it. Every model was saved before any held-out performance was evaluated.", "",
             "## Nonoverlapping two-second windows", "",
             "AUROC is ranking discrimination (0.5 is chance), not percentage accuracy. "
             "BA is balanced accuracy at the fixed decision boundary. AP should be compared with positive prevalence. "
             "The power model is prespecified primary; tangent is the framework comparator; eog_power uses eyes only.", ""]
    for target in TARGETS:
        lines += [f"### {target}", "",
                  "| Session | Model | Windows | Positive prevalence | AUROC | AP | BA | Sensitivity | Specificity |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for session in report["sessions"]:
            for kind, m in session["classification"][target].items():
                lines.append(f"| {session['session']} | {kind} | {m['windows']} | {fmt(m['positive_prevalence'])} | "
                             f"{fmt(m['auroc'])} | {fmt(m['average_precision'])} | {fmt(m['balanced_accuracy'])} | "
                             f"{fmt(m['sensitivity'])} | {fmt(m['specificity'])} |")
        lines.append("")
    lines += ["Task/rest includes all three n-back conditions versus nearby rest. High/low compares "
              "2-/3-back versus 0-back during tasks only. Neither isolates neural cognitive load.", "",
              "## Sustained intervals from marker-free scoring", "",
              "Require at least three seconds at nonnegative margin (fixed theta retains its original z/hysteresis rule). "
              "A task match requires one-to-one interval IoU ≥ 0.5. Fragmented intervals may cover task time without matching a whole task.", "",
              "| Model | Detected intervals | Matched task blocks | Task time covered | Rest time flagged | Mean onset error, matches only |",
              "|---|---:|---:|---:|---:|---:|"]
    for kind, m in report["interval_summary"].items():
        lines.append(f"| {kind} | {m['detected_intervals']} | {m['matched_task_intervals']} / {m['task_blocks']} | "
                     f"{m['task_covered_s'] / m['task_total_s']:.1%} | "
                     f"{m['rest_covered_s']:.2f} / {m['rest_total_s']:.2f} s | "
                     f"{fmt(m['mean_abs_onset_error_s_matched_only'])} s |")
    lines += ["", "## Burst-gate eligibility only", "",
              "No burst detector was retrained in this experiment. The following counts show which labeled "
              "target onsets could be searched after restricting the ERP grid to ±3 seconds around detected stretch onsets. "
              "Eligibility is not successful detection; targets need not be spontaneous bursts.", "",
              "| Gate model | Accessible target markers | Fraction of valid ERP grid searched |",
              "|---|---:|---:|"]
    for kind, m in report["interval_summary"].items():
        lines.append(f"| {kind} | {m['gate_accessible_targets']} / {m['gate_all_targets']} | "
                     f"{m['gate_eligible_centers'] / max(m['gate_valid_centers'], 1):.1%} |")
    full = [b["onset_gate"]["all"] for s in report["sessions"] for b in s["blocks"] if b["onset_gate"]]
    lines += [f"| Full grid | {sum(g['accessible_events'] for g in full)} / {sum(g['truth_events'] for g in full)} | 100% |", "",
              "## Limits and artifacts", "",
              "- Session-specific calibration is required; this does not test transfer of weights between people.",
              "- Only nine held-out task blocks from one new person; windows are correlated even when nonoverlapping.",
              "- Nearby rest totals only 72 seconds. A low rest flag count does not establish an all-day false-alarm rate.",
              "- Eye correction can remove eye-correlated neural activity, and residual ocular/motor/sensory confounds remain.",
              "- Task block labels are behavioral proxies. No aha, confusion, or neural-stretch ground truth exists here.",
              "- This is replayed EEG, unrelated to the person in a separately captured phone video.",
              "- No threshold, feature or preprocessing was retuned after these held-out scores.", "",
              "`session*.report.json` contains per-condition metrics, quality exclusions and raw held-out scores. "
              "`session*.diagnostic.png` shows all score traces. `session*.power.events.json` contains primary replay timeline events; "
              "tangent exports are an alternative model output, not additional independent evidence.", "",
              "`protocol_snapshot.json`, `frozen_models.json`, model cards and acquisition audits record the procedure, "
              "hashes, training folds, fitted settings and freeze time.", "",
              "Source: [original Shin EEG recordings](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/)."]
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n")


def run_workload_benchmark(directory, out):
    directory, out = Path(directory), Path(out)
    if directory.name != "VP002":
        raise ValueError("This locked fresh-data protocol selects VP002; define a new protocol for another participant.")
    if (out / "protocol_snapshot.json").exists():
        raise ValueError("Experiment output exists. Use a new output directory; preserve the original result.")
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    protocol = root / "workload_protocol.md"
    sources = sorted((root / "eeg_moments").glob("*.py")) + [root / "scripts/fetch_shin.py"]
    snapshot = {"started_utc": utc_now(), "participant": "VP002", "protocol_text": protocol.read_text(),
                "protocol_sha256": file_hash(protocol),
                "source_sha256": {str(p.relative_to(root)): file_hash(p) for p in sources},
                "versions": {p: version(p) for p in ("numpy", "scipy", "scikit-learn", "pyriemann", "mne")}}
    write_json(out / "protocol_snapshot.json", snapshot)
    contexts, frozen = [], {"models": {}, "in_memory_state_before_evaluation": {}}
    # Complete every session's calibration before accessing any held-out scores.
    for session in (1, 2, 3):
        print(f"Session {session}: loading and applying the locked pre-task ocular calibration", flush=True)
        blocks, audit = load_session(directory, session)
        blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
        write_json(out / f"session{session}.audit.json", audit)
        calibration = [b for b in blocks if b.role == "calibration"]
        reference = StretchReference.fit([prepare(b.recording, workload_config()) for b in calibration],
                                         [b.baseline_intervals_s for b in calibration], workload_config())
        reference_path = out / f"session{session}.fixed_theta.joblib"
        joblib.dump(reference, reference_path)
        frozen["models"][reference_path.name] = file_hash(reference_path)
        frozen["in_memory_state_before_evaluation"][reference_path.name] = joblib.hash(reference)
        models = {}
        for target in TARGETS:
            for kind in KINDS:
                print(f"Session {session}: fitting {target}/{kind} on calibration blocks", flush=True)
                model = fit_workload(calibration, kind, target)
                path = out / f"session{session}.{target}.{kind}.joblib"
                joblib.dump(model, path)
                write_json(path.with_suffix(".model_card.json"), model.model_card)
                frozen["models"][path.name] = file_hash(path)
                frozen["in_memory_state_before_evaluation"][path.name] = joblib.hash(model)
                models[(target, kind)] = model
        contexts.append((blocks, models, reference))
    frozen.update({"frozen_utc": utc_now(), "protocol_sha256": snapshot["protocol_sha256"],
                   "heldout_evaluation_started": False})
    write_json(out / "frozen_models.json", frozen)
    evaluation_started = utc_now()
    sessions = [evaluate_session(blocks, models, reference, out, session)
                for session, (blocks, models, reference) in enumerate(contexts, 1)]
    # Ensure fitted objects were not mutated by inference or tangent-space adaptation.
    for session, (_, models, reference) in enumerate(contexts, 1):
        objects = {f"session{session}.{target}.{kind}.joblib": model
                   for (target, kind), model in models.items()}
        objects[f"session{session}.fixed_theta.joblib"] = reference
        for name, model in objects.items():
            path = out / name
            if file_hash(path) != frozen["models"][path.name]:
                raise ValueError("Frozen model file changed during evaluation.")
            # Serialization can alter object aliasing/array layout and thus joblib.hash
            # without changing fitted values. Compare the SAME in-memory object across
            # inference, and separately check the saved file's cryptographic digest.
            if frozen["in_memory_state_before_evaluation"][name] != joblib.hash(model):
                raise ValueError("Model state changed during inference.")
    report = {"participant": "VP002", "dataset": "Shin2018-A", "evaluation_started_utc": evaluation_started,
              "completed_utc": utc_now(), "protocol_sha256": snapshot["protocol_sha256"],
              "primary_model": "power", "sessions": sessions, "interval_summary": aggregate_intervals(sessions)}
    write_json(out / "report.json", report)
    write_report(report, out)
    return report
