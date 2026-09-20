"""Locked VP005 comparison of Bayesian stretch inference and zigzag bursts."""
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np

from .benchmark import gate_metrics, retrieval_metrics
from .data import write_json
from .dynamic import (KINDS, METHODS, dynamic_frame, export_dynamic_events, fit_dynamic_models)
from .erp import ERPMeanBins, classification_metrics, eog_epochs, erp_config, extract_epochs
from .model import select_events
from .real_benchmark import export_real_events
from .shin import correct_ocular_from_pretask, load_session
from .signal import prepare
from .topology import BURST_KINDS, burst_feature_bank, fit_topological_models, scan_burst_models
from .workload import labels_for_times, workload_metrics
from .workload_benchmark import assert_heldout, file_hash, interval_assessment, utc_now


def finite_list(values):
    return [float(v) if np.isfinite(v) else None for v in values]


def evaluate_session(blocks, workloads, bursts, out, session):
    workload_pool = {kind: {"labels": [], "scores": []} for kind in KINDS}
    burst_pool = {kind: {"labels": [], "scores": []} for kind in BURST_KINDS}
    workload_events = {kind: [] for kind in METHODS}
    burst_events = {kind: [] for kind in BURST_KINDS if kind != "eog_bins"}
    reports, plots = [], []
    for block in blocks:
        if block.role != "evaluation":
            continue
        print(f"Session {session}: evaluate {block.condition}-back; shared masks and frozen models", flush=True)
        for model in list(workloads.values()) + list(bursts.values()):
            assert_heldout(block, model)
        frame = dynamic_frame(block.recording, block)
        labels = labels_for_times(block, frame.times, "task_rest")
        use = frame.valid & frame.evaluation_grid & (labels >= 0)
        scans = {kind: model.scan_frame(block.recording, frame, allow_eye_control=True)
                 for kind, model in workloads.items()}
        row = {"recording_id": block.recording.recording_id, "condition": block.condition,
               "original_offset_s": block.original_offset_s, "workload": {}, "intervals": {},
               "quality": {str(label): {"labeled": int(((labels == label) & frame.evaluation_grid).sum()),
                                        "accepted": int(((labels == label) & use).sum())} for label in (0, 1)}}
        for kind, scan in scans.items():
            if not np.array_equal(np.isfinite(scan["scores"]), frame.valid):
                raise RuntimeError("Temporal alternatives do not share the original quality mask.")
            row["workload"][kind] = workload_metrics(labels[use], scan["scores"][use])
            workload_pool[kind]["labels"].extend(labels[use].tolist())
            workload_pool[kind]["scores"].extend(scan["scores"][use].tolist())
            if kind in METHODS:
                row["intervals"][kind] = interval_assessment(block, scan["stretches"])
                workload_events[kind].extend(export_dynamic_events(block.recording, workloads[kind], scan, block.original_offset_s))
        trace = {"recording_id": block.recording.recording_id, "workload_times": frame.times.tolist(),
                 "workload_valid": frame.valid.tolist(),
                 "workload_scores": {kind: finite_list(scan["scores"]) for kind, scan in scans.items()},
                 "conditional_posterior_sd": {kind: finite_list(scans[kind]["posterior_sd"]) for kind in ("dlm", "adaptive")},
                 "adaptive_change_regime_probability": finite_list(scans["adaptive"]["change_regime_probability"])}
        burst_scan = None
        if block.condition in (2, 3):
            marker_times = np.array([t["time_s"] for t in block.trials])
            epochs, valid = extract_epochs(prepare(block.recording, erp_config()), marker_times)
            y = np.array([t["label"] for t in block.trials])[valid]
            bank = burst_feature_bank(epochs)
            eye = eog_epochs(block, marker_times[valid])
            bank["eog_bins"] = ERPMeanBins().transform(eye) if len(eye) else np.empty((0, 10))
            row["aligned_erp"], row["continuous_retrieval"] = {}, {}
            row["erp_quality"] = {"trials": len(marker_times), "accepted": len(valid),
                                  "accepted_targets": int(y.sum())}
            for kind, model in bursts.items():
                scores = model.score_features(block.recording, bank[kind])
                row["aligned_erp"][kind] = classification_metrics(y, scores)
                burst_pool[kind]["labels"].extend(y.tolist())
                burst_pool[kind]["scores"].extend(scores.tolist())
            times, scores, rejected = scan_burst_models(block.recording, {k: v for k, v in bursts.items() if k != "eog_bins"})
            truth = {"bursts": [{"anchor_s": t["time_s"]} for t in block.trials if t["label"] == 1]}
            selected_by_kind = {}
            for kind, margins in scores.items():
                selected = select_events(times, margins, np.ones(len(times), dtype=bool), erp_config(), top_k=5)
                selected_by_kind[kind] = selected
                row["continuous_retrieval"][kind] = {
                    **retrieval_metrics(selected, truth, tolerance_s=0.5),
                    **gate_metrics(times, np.ones(len(times), dtype=bool), truth, tolerance_s=0.5),
                    "rejected_windows": int(rejected), "total_windows": len(times) + int(rejected), "selected": selected}
                events = export_real_events(block, bursts[kind], selected, [], "all")
                for event in events:
                    event["model_version"] = f"dynamic-tda-v1-{kind}"
                burst_events[kind].extend(events)
            trace.update({"burst_times": times.tolist(), "burst_scores": {k: v.tolist() for k, v in scores.items()}})
            burst_scan = times, scores, selected_by_kind
        write_json(out / f"session{session}.block{block.block_index + 1}.traces.json", trace)
        reports.append(row)
        plots.append((block, scans, burst_scan))
    report = {"session": session, "session_id": blocks[0].recording.session_id, "blocks": reports,
              "workload": {k: workload_metrics(v["labels"], v["scores"]) for k, v in workload_pool.items()},
              "aligned_erp": {k: classification_metrics(v["labels"], v["scores"]) for k, v in burst_pool.items()},
              "workload_heldout_scores": workload_pool, "erp_heldout_scores": burst_pool}
    write_json(out / f"session{session}.report.json", report)
    for prefix, exports in (("stretch", workload_events), ("burst", burst_events)):
        for kind, events in exports.items():
            write_json(out / f"session{session}.{prefix}.{kind}.events.json", sorted(events, key=lambda e: e["anchor_s"]))
    plot_session(plots, out / f"session{session}.diagnostic.png", session)
    return report


def plot_session(rows, path, session):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 3, figsize=(16, 10), sharex="col", layout="constrained")
    colors = {"power": "#777777", "ema": "#bb8833", "dlm": "#2873a9", "adaptive": "#b24162"}
    for col, (block, scans, burst_scan) in enumerate(rows):
        times = scans["power"]["times"]
        for kind in METHODS:
            axes[0, col].plot(times, scans[kind]["scores"], label=kind, c=colors[kind], lw=1)
        axes[0, col].axvspan(block.task_start_s, block.task_end_s, color="#d6e9d8", alpha=0.45)
        for start, end in block.baseline_intervals_s:
            axes[0, col].axvspan(start, end, color="#abc9e6", alpha=0.3)
        axes[0, col].set_title(f"{block.condition}-back, block {block.block_index + 1}")
        axes[0, col].set_ylabel("Workload margin / temporal estimate")
        for kind in ("dlm", "adaptive"):
            mean, sd = scans[kind]["scores"], scans[kind]["posterior_sd"]
            axes[1, col].plot(times, mean, c=colors[kind], label=kind, lw=1)
            axes[1, col].fill_between(times, mean - 2 * sd, mean + 2 * sd, color=colors[kind], alpha=0.15)
        axes[1, col].set_ylabel("Latent estimate ± 2 conditional SD")
        if burst_scan is not None:
            ts, scores, selected = burst_scan
            gap = np.flatnonzero(np.diff(ts) > 0.15) + 1
            for kind, margins in scores.items():
                line, = axes[2, col].plot(np.insert(ts, gap, np.nan), np.insert(margins, gap, np.nan), label=kind, lw=0.8)
                axes[2, col].scatter([e["anchor_s"] for e in selected[kind]], [e["raw_score"] for e in selected[kind]],
                                     c=line.get_color(), s=14)
            for trial in block.trials:
                if trial["label"]:
                    axes[2, col].axvline(trial["time_s"], c="#777777", ls=":", alpha=0.5)
        else:
            axes[2, col].text(0.5, 0.5, "0-back has no target/non-target comparison", transform=axes[2, col].transAxes, ha="center", fontsize=8)
        axes[2, col].set_ylabel("ERP candidate margin")
        axes[2, col].set_xlabel("Seconds within EEG excerpt")
        for row in range(3):
            axes[row, col].axhline(0, c="#555555", ls="--", lw=0.6)
            axes[row, col].grid(alpha=0.15)
            if axes[row, col].get_legend_handles_labels()[0]:
                axes[row, col].legend(fontsize=7, loc="upper right")
    fig.suptitle(f"VP005 session {session}: frozen stretch and burst alternatives\nPosterior SD is model-conditional; target lines are evaluation labels, not input to scanning")
    fig.savefig(path, dpi=150)
    plt.close(fig)


def summarize(sessions):
    def mean_metric(rows, name):
        values = [r[name] for r in rows]
        return float(np.mean(values)) if all(v is not None for v in values) else None

    workload = {kind: {key: mean_metric([s["workload"][kind] for s in sessions], key)
                       for key in ("auroc", "balanced_accuracy", "sensitivity", "specificity")} for kind in KINDS}
    aligned = {kind: {key: mean_metric([s["aligned_erp"][kind] for s in sessions], key)
                      for key in ("auroc", "average_precision")} for kind in BURST_KINDS}
    intervals, retrieval = {}, {}
    for kind in METHODS:
        rows = [b["intervals"][kind] for s in sessions for b in s["blocks"]]
        intervals[kind] = {key: sum(r[key] for r in rows) for key in
                            ("returned", "true_positives", "truth_stretches", "task_covered_s", "task_total_s", "rest_covered_s", "rest_total_s")}
    for kind in (k for k in BURST_KINDS if k != "eog_bins"):
        rows = [b["continuous_retrieval"][kind] for s in sessions for b in s["blocks"] if "continuous_retrieval" in b]
        m = {key: sum(r[key] for r in rows) for key in ("returned", "true_positives", "truth_events", "accessible_events", "rejected_windows", "total_windows")}
        m["precision_of_returned"] = m["true_positives"] / m["returned"] if m["returned"] else None
        m["recall_at_budget"] = m["true_positives"] / m["truth_events"] if m["truth_events"] else None
        retrieval[kind] = m
    quality = {label: {key: sum(b["quality"][label][key] for s in sessions for b in s["blocks"])
                       for key in ("labeled", "accepted")} for label in ("0", "1")}
    decisions = {"stretch": {}, "burst": {}}
    for kind in METHODS[1:]:
        m, base = intervals[kind], intervals["power"]
        a, b = workload[kind]["balanced_accuracy"], workload["power"]["balanced_accuracy"]
        decisions["stretch"][kind] = bool(a is not None and b is not None and a >= b
            and m["true_positives"] > base["true_positives"] and m["rest_covered_s"] <= base["rest_covered_s"])
    for kind in ("zigzag", "mean_bins_zigzag"):
        m, base = retrieval[kind], retrieval["mean_bins"]
        decisions["burst"][kind] = bool(m["true_positives"] > base["true_positives"]
            and m["precision_of_returned"] is not None and base["precision_of_returned"] is not None
            and m["precision_of_returned"] >= base["precision_of_returned"])
    return {"macro_workload": workload, "macro_aligned_erp": aligned, "intervals": intervals,
            "retrieval": retrieval, "workload_quality": quality, "descriptive_improvement": decisions}


def write_report(report, out):
    fmt = lambda x: "n/a" if x is None else f"{x:.3f}"
    lines = ["# Bayesian stretch and zigzag burst comparison — VP005", "",
             "One previously untested participant, three independently calibrated sessions, nine evaluation blocks. "
             "All 36 models were frozen before test scoring. All 28 EEG channels retained, with pre-task ocular correction.", "",
             "## Stretches", "", "Means of per-session metrics. All alternatives use identical accepted windows. "
             "Whole-task matches require IoU ≥ 0.5; counts are out of nine task blocks.", "",
             "| Model | AUROC | Balanced accuracy | Intervals | Whole-task matches | Task covered | Rest included |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for kind in METHODS:
        m, i = report["macro_workload"][kind], report["intervals"][kind]
        lines.append(f"| {kind} | {fmt(m['auroc'])} | {fmt(m['balanced_accuracy'])} | {i['returned']} | {i['true_positives']}/{i['truth_stretches']} | {i['task_covered_s']/i['task_total_s']:.1%} | {i['rest_covered_s']:.2f}/{i['rest_total_s']:.2f} s |")
    lines += ["", "DLM is Bayesian local-level inference with correlated observation noise. Adaptive is an IMM approximation with small/large innovation regimes, not the published horseshoe dynamic-shrinkage algorithm. Conditional posterior uncertainty is not cognitive-state confidence.", "",
              "## Bursts", "", "Known-onset AUROC is a separate positive control. Continuous scanning receives no trial markers or stretch gates. "
              "Up to five flags per 2-/3-back excerpt; one-to-one target-onset matching within ±0.5 s.", "",
              "| Model | Known-onset mean AUROC | Matched targets | Returned flags | Precision against target markers |",
              "|---|---:|---:|---:|---:|"]
    for kind, m in report["retrieval"].items():
        lines.append(f"| {kind} | {fmt(report['macro_aligned_erp'][kind]['auroc'])} | {m['true_positives']}/{m['truth_events']} | {m['returned']} | {fmt(m['precision_of_returned'])} |")
    lines += ["", "Zigzag uses actual H0/H1 persistence of five short EEG trajectory clouds and adjacent unions at three fixed radii. "
              "The 108 shape features intentionally discard absolute amplitude. They require a full 1.1-second window and do not establish sensitivity to arbitrarily small/brief changes. Unmatched flags are not proven absent neural activity.", "",
              "## Eye controls and quality", "", "| Eye-only model | Task/rest mean AUROC | Balanced accuracy |", "|---|---:|---:|"]
    for kind in KINDS[4:]:
        m = report["macro_workload"][kind]
        lines.append(f"| {kind} | {fmt(m['auroc'])} | {fmt(m['balanced_accuracy'])} |")
    lines += ["", f"Eye-only known-onset ERP mean AUROC: {fmt(report['macro_aligned_erp']['eog_bins']['auroc'])}."]
    for label, q in report["workload_quality"].items():
        lines.append(f"- {'Rest' if label == '0' else 'Task'}: {q['accepted']}/{q['labeled']} labeled two-second windows accepted.")
    lines += ["", "## Prespecified descriptive decisions", "", "A stretch alternative must improve whole-task matches without increasing rest overlap or lowering balanced accuracy. A burst alternative must retrieve more target markers without lower precision at the same maximum budget.", ""]
    for branch, decisions in report["descriptive_improvement"].items():
        for kind, improved in decisions.items():
            lines.append(f"- {branch}/{kind}: criterion met = {improved}.")
    lines += ["", "These are small feasibility comparisons, not statistical significance or spontaneous cognitive-event validation. "
              "Task-related eye/motor/sensory signals remain possible. Short nearby rest limits false-alarm estimates; overlapping windows remain dependent despite the DLM's AR noise approximation. "
              "Invalid centers stay invalid and reset temporal state. Acquisition/ERP filtering remains offline. "
              "No weights transfer between sessions, and replay EEG does not measure the phone-video participant.", "",
              "Alternative event exports preserve source and model identity and must not be pooled as independent corroboration. Protocol, source hashes, model cards, frozen model hashes, scores, masks, reports and plots accompany this file.", ""]
    (out / "RESULTS.md").write_text("\n".join(lines))


def run_dynamic_tda_benchmark(directory, out):
    directory, out = Path(directory), Path(out)
    if directory.name != "VP005":
        raise ValueError("The locked dynamic/TDA protocol selects VP005.")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Preserve previous results; choose an empty output directory.")
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    protocol = root / "dynamic_tda_protocol.md"
    snapshot = {"started_utc": utc_now(), "participant": "VP005", "protocol": protocol.read_text(),
                "protocol_sha256": file_hash(protocol),
                "source_sha256": {str(p.relative_to(root)): file_hash(p) for p in sorted((root / "eeg_moments").glob("*.py"))},
                "versions": {p: version(p) for p in ("numpy", "scipy", "scikit-learn", "pyriemann", "mne", "dionysus")}}
    write_json(out / "protocol_snapshot.json", snapshot)
    contexts, frozen = [], {"saved_sha256": {}, "in_memory_hashes": {}}
    for session in (1, 2, 3):
        print(f"Session {session}: load EEG and fit on calibration blocks only", flush=True)
        blocks, audit = load_session(directory, session)
        blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
        write_json(out / f"session{session}.audit.json", audit)
        calibration = [b for b in blocks if b.role == "calibration"]
        workloads = fit_dynamic_models(calibration)
        print(f"Session {session}: fit ERP and zigzag models on calibration trials", flush=True)
        bursts = fit_topological_models(calibration)
        objects = {**{f"stretch.{k}": v for k, v in workloads.items()}, **{f"burst.{k}": v for k, v in bursts.items()}}
        for name, model in objects.items():
            path = out / f"session{session}.{name}.joblib"
            joblib.dump(model, path)
            write_json(path.with_suffix(".model_card.json"), model.model_card)
            frozen["saved_sha256"][path.name] = file_hash(path)
            frozen["in_memory_hashes"][path.name] = joblib.hash(model)
        contexts.append((blocks, workloads, bursts, objects))
    frozen["frozen_utc"] = utc_now()
    write_json(out / "frozen_models.json", frozen)
    evaluation_started = utc_now()
    sessions = [evaluate_session(blocks, workloads, bursts, out, i)
                for i, (blocks, workloads, bursts, _) in enumerate(contexts, 1)]
    for i, (_, _, _, objects) in enumerate(contexts, 1):
        for name, model in objects.items():
            path = out / f"session{i}.{name}.joblib"
            if file_hash(path) != frozen["saved_sha256"][path.name] or joblib.hash(model) != frozen["in_memory_hashes"][path.name]:
                raise RuntimeError("Evaluation altered a fitted model or saved file.")
    report = {"participant": "VP005", "sessions": sessions, "evaluation_started_utc": evaluation_started,
              "completed_utc": utc_now(), "fitted_states_unchanged": True, **summarize(sessions)}
    write_json(out / "report.json", report)
    write_report(report, out)
    return report
