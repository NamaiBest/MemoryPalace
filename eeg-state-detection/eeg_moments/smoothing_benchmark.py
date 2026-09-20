"""Same-model, same-recording smoothing comparison on previously inspected VP002."""
import json
from pathlib import Path

import joblib
import numpy as np

from .data import write_json
from .shin import correct_ocular_from_pretask, load_session
from .smoothing import calibrate_smoothing, export_smoothed_events, smooth_scan
from .workload import export_workload_events, labels_for_times, workload_metrics
from .workload_benchmark import assert_heldout, file_hash, interval_assessment, utc_now


def evaluate_session(blocks, model, previous, out, session):
    pooled = {kind: {"y": [], "score": []} for kind in ("power", "power_ema")}
    exports = {kind: [] for kind in pooled}
    rows, plots = [], []
    for block in blocks:
        if block.role != "evaluation":
            continue
        assert_heldout(block, model)
        raw = model.base_model.scan(block.recording)
        smoothed = smooth_scan(raw, model.half_life_s)
        scans = {"power": raw, "power_ema": smoothed}
        labels = labels_for_times(block, raw["times"], "task_rest")
        use = raw["valid"] & (np.arange(len(labels)) % 8 == 0) & (labels >= 0)
        row = {"recording_id": block.recording.recording_id, "classification": {}, "intervals": {},
               "quality": {str(label): int((use & (labels == label)).sum()) for label in (0, 1)}}
        for kind, scan in scans.items():
            if not np.array_equal(np.isfinite(scan["scores"]), raw["valid"]):
                raise RuntimeError("Smoothing changed the original validity mask.")
            row["classification"][kind] = workload_metrics(labels[use], scan["scores"][use])
            row["intervals"][kind] = interval_assessment(block, scan["stretches"])
            pooled[kind]["y"].extend(labels[use].tolist())
            pooled[kind]["score"].extend(scan["scores"][use].tolist())
        exports["power"].extend(export_workload_events(block.recording, model.base_model, raw, block.original_offset_s))
        exports["power_ema"].extend(export_smoothed_events(block.recording, model, smoothed, block.original_offset_s))
        write_json(out / f"session{session}.block{block.block_index + 1}.traces.json", {
            "recording_id": block.recording.recording_id, "offset_s": block.original_offset_s,
            "times": raw["times"].tolist(), "valid": raw["valid"].tolist(),
            "scores": {kind: [float(x) if np.isfinite(x) else None for x in scan["scores"]] for kind, scan in scans.items()}})
        rows.append(row)
        plots.append((block, scans))
    prior = json.loads((previous / f"session{session}.report.json").read_text())
    np.testing.assert_array_equal(pooled["power"]["y"], prior["scores"]["task_rest"]["power"]["y"])
    np.testing.assert_allclose(pooled["power"]["score"], prior["scores"]["task_rest"]["power"]["score"], rtol=0, atol=1e-12)
    for kind, events in exports.items():
        events.sort(key=lambda e: e["anchor_s"])
        if kind == "power" and events != json.loads((previous / f"session{session}.power.events.json").read_text()):
            raise RuntimeError("The original band-power event export was not reproduced exactly.")
        write_json(out / f"session{session}.{kind}.events.json", events)
    report = {"session": session, "session_id": model.session_id, "half_life_s": model.half_life_s,
              "original_baseline_reproduced": True, "blocks": rows, "heldout_scores": pooled,
              "classification": {kind: workload_metrics(row["y"], row["score"]) for kind, row in pooled.items()}}
    write_json(out / f"session{session}.report.json", report)
    plot_session(plots, out / f"session{session}.diagnostic.png", session, model.half_life_s)
    return report


def plot_session(rows, path, session, half_life, participant="VP002"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 6), sharex="col", sharey="col", layout="constrained")
    for col, (block, scans) in enumerate(rows):
        for row, (kind, scan) in enumerate(scans.items()):
            ax = axes[row, col]
            ax.axvspan(block.task_start_s, block.task_end_s, color="#d0e4d4", alpha=0.4)
            for start, end in block.baseline_intervals_s:
                ax.axvspan(start, end, color="#8cbad8", alpha=0.3)
            ax.plot(scan["times"], scan["scores"], color="#347b9b" if row == 0 else "#b14d48", lw=1)
            ax.axhline(0, color="#555555", ls="--", lw=0.7)
            for s in scan["stretches"]:
                ax.axvspan(s["start_s"], s["end_s"], ymin=0.95, ymax=1, color="#cf493f")
            ax.set_ylabel(kind + " margin")
            ax.grid(alpha=0.15)
            if row == 0:
                ax.set_title(f"{block.condition}-back, block {block.block_index + 1}")
            else:
                ax.set_xlabel("Seconds within recorded excerpt")
    fig.suptitle(f"{participant} session {session}: same frozen classifier; EMA half-life {half_life:g}s\nGreen = task proxy; blue = labeled rest; red bars = returned intervals")
    fig.savefig(path, dpi=150)
    plt.close(fig)


def summarize(sessions):
    result = {}
    for kind in ("power", "power_ema"):
        classification = [s["classification"][kind] for s in sessions]
        intervals = [b["intervals"][kind] for s in sessions for b in s["blocks"]]
        result[kind] = {"mean_" + key: float(np.mean([r[key] for r in classification]))
                        for key in ("auroc", "balanced_accuracy", "sensitivity", "specificity")}
        result[kind].update({key: sum(row[key] for row in intervals) for key in
                            ("returned", "true_positives", "truth_stretches", "task_covered_s", "task_total_s", "rest_covered_s", "rest_total_s")})
    base, ema = result["power"], result["power_ema"]
    result["joint_improvement_criterion_met"] = bool(ema["mean_balanced_accuracy"] >= base["mean_balanced_accuracy"]
        and ema["true_positives"] > base["true_positives"] and ema["rest_covered_s"] <= base["rest_covered_s"])
    return result


def write_report(report, out):
    lines = ["# Smoothing on the original VP002 band-power models", "",
             "Exploratory follow-up on previously inspected data. Same nine evaluation blocks, same 28 EEG channels, "
             "same preprocessing and exact saved classifier weights. The original raw scores and 34 event exports were reproduced. "
             "Only exponential smoothing was added; its half-life was selected on calibration folds before evaluation.", "",
             "| Session | EMA half-life | Band-power BA | Smoothed BA | Band-power AUROC | Smoothed AUROC |",
             "|---|---:|---:|---:|---:|---:|"]
    for s in report["sessions"]:
        a, b = s["classification"]["power"], s["classification"]["power_ema"]
        lines.append(f"| {s['session']} | {s['half_life_s']:g} s | {a['balanced_accuracy']:.3f} | {b['balanced_accuracy']:.3f} | {a['auroc']:.3f} | {b['auroc']:.3f} |")
    lines += ["", "BA means balanced accuracy on the same nonoverlapping labeled windows.", "",
              "| Same VP002 data | Original band power | Band power + smoothing |", "|---|---:|---:|"]
    a, b = report["summary"]["power"], report["summary"]["power_ema"]
    lines += [f"| Mean balanced accuracy | {a['mean_balanced_accuracy']:.1%} | {b['mean_balanced_accuracy']:.1%} |",
              f"| Mean AUROC | {a['mean_auroc']:.3f} | {b['mean_auroc']:.3f} |",
              f"| Whole task blocks matched | {a['true_positives']}/{a['truth_stretches']} | {b['true_positives']}/{b['truth_stretches']} |",
              f"| Returned intervals | {a['returned']} | {b['returned']} |",
              f"| Task time covered | {a['task_covered_s']/a['task_total_s']:.1%} | {b['task_covered_s']/b['task_total_s']:.1%} |",
              f"| Rest incorrectly included | {a['rest_covered_s']:.2f}/{a['rest_total_s']:.0f} s | {b['rest_covered_s']:.2f}/{b['rest_total_s']:.0f} s |", "",
              f"Joint improvement criterion met: {report['summary']['joint_improvement_criterion_met']}. "
              "Requires more whole-task matches, no lower mean BA and no extra rest overlap.", "",
              "The temporary calibration-fold classifiers used the original selected C; the final evaluation classifiers were never refitted. "
              "EMA initialization/reset, zero boundary, three-second minimum duration and quality masks were fixed. "
              "This differs from the VP005 experiment, which retuned C separately for each pipeline.", "",
              "These are task/rest proxies from one participant and previously seen evaluation data. No fresh-validation, statistical significance or spontaneous cognitive-event claim. "
              "Only 72 seconds of nearby labeled rest limits false-alarm conclusions. Existing eye/motor/sensory confounds remain. "
              "Replay EEG does not correspond to the phone-video participant. Alternative event files retain null confidence and separate model identities.", ""]
    (out / "RESULTS.md").write_text("\n".join(lines))


def run_smoothing_benchmark(directory, previous, out):
    directory, previous, out = map(Path, (directory, previous, out))
    if directory.name != "VP002":
        raise ValueError("This follow-up compares the original VP002 experiment.")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Preserve existing outputs; choose an empty directory.")
    paths = [previous / f"session{s}.task_rest.power.joblib" for s in (1, 2, 3)]
    input_hashes = {str(p.resolve()): file_hash(p) for p in paths}
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    protocol = root / "smoothing_vp002_protocol.md"
    write_json(out / "protocol_snapshot.json", {
        "started_utc": utc_now(), "purpose": "known-data smoothing-only follow-up; not fresh validation",
        "protocol": protocol.read_text(), "protocol_sha256": file_hash(protocol),
        "input_model_sha256": input_hashes,
        "source_sha256": {str(p.relative_to(root)): file_hash(p) for p in sorted((root / "eeg_moments").glob("*.py"))}})
    contexts, frozen = [], {"models": {}, "in_memory_hashes": {}}
    for session, path in zip((1, 2, 3), paths):
        print(f"Session {session}: select smoothing on calibration folds; preserve saved weights", flush=True)
        blocks, audit = load_session(directory, session)
        blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
        write_json(out / f"session{session}.audit.json", audit)
        base = joblib.load(path)
        before = joblib.hash(base)
        model = calibrate_smoothing([b for b in blocks if b.role == "calibration"], base)
        if before != joblib.hash(base):
            raise RuntimeError("Selecting smoothing changed the original classifier.")
        saved = out / f"session{session}.power_ema.joblib"
        joblib.dump(model, saved)
        write_json(saved.with_suffix(".model_card.json"), model.model_card)
        frozen["models"][saved.name] = file_hash(saved)
        frozen["in_memory_hashes"][saved.name] = joblib.hash(model)
        contexts.append((blocks, model, before))
    frozen["frozen_utc"] = utc_now()
    write_json(out / "frozen_models.json", frozen)
    evaluation_started = utc_now()
    sessions = [evaluate_session(blocks, model, previous, out, i)
                for i, (blocks, model, _) in enumerate(contexts, 1)]
    for i, (_, model, before) in enumerate(contexts, 1):
        path = out / f"session{i}.power_ema.joblib"
        if (joblib.hash(model.base_model) != before or joblib.hash(model) != frozen["in_memory_hashes"][path.name]
                or file_hash(path) != frozen["models"][path.name]):
            raise RuntimeError("Evaluation changed fitted state or saved weights.")
    if any(file_hash(path) != digest for path, digest in input_hashes.items()):
        raise RuntimeError("An original classifier file changed.")
    report = {"participant": "VP002", "purpose": "known-data smoothing-only follow-up",
              "evaluation_started_utc": evaluation_started, "completed_utc": utc_now(),
              "sessions": sessions, "summary": summarize(sessions), "frozen_states_unchanged": True}
    write_json(out / "report.json", report)
    write_report(report, out)
    return report
