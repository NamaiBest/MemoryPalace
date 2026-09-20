"""Prespecified EWMA ablation on fresh, independently calibrated VP003 sessions."""
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np

from .data import write_json
from .shin import correct_ocular_from_pretask, load_session
from .volatility import (EEG_KINDS, KINDS, export_temporal_events, fit_temporal_models,
                         quality_counts, temporal_frame)
from .workload import TARGETS, labels_for_times, workload_metrics
from .workload_benchmark import assert_heldout, file_hash, interval_assessment, utc_now


def evaluate_session(blocks, models, session, out):
    pooled = {target: {kind: {"labels": [], "scores": []} for kind in KINDS} for target in TARGETS}
    reports, plots = [], []
    exports = {kind: [] for kind in EEG_KINDS}
    for block in blocks:
        if block.role != "evaluation":
            continue
        print(f"Session {session}: evaluating held-out {block.condition}-back", flush=True)
        for model in models.values():
            assert_heldout(block, model)
        frame = temporal_frame(block.recording, block.eog)
        row = {"recording_id": block.recording.recording_id, "condition": block.condition,
               "original_offset_s": block.original_offset_s, "classification": {}, "quality": {},
               "intervals": {}, "scorable_centers": {}}
        for target in TARGETS:
            labels = labels_for_times(block, frame.times, target)
            use = frame.evaluation_grid & frame.ready & (labels >= 0)
            row["quality"][target] = quality_counts(block, frame, target)
            row["classification"][target] = {}
            for kind in KINDS:
                model = models[(target, kind)]
                scores = model.score_features(block.recording, frame.features[kind][use])
                row["classification"][target][kind] = workload_metrics(labels[use], scores)
                pooled[target][kind]["labels"].extend(labels[use].tolist())
                pooled[target][kind]["scores"].extend(scores.tolist())
        dense_labels = labels_for_times(block, frame.times, "task_rest")
        for label, name in ((0, "rest"), (1, "task")):
            chosen = dense_labels == label
            row["scorable_centers"][name] = {"labeled": int(chosen.sum()),
                                             "raw_valid": int((chosen & frame.raw_valid).sum()),
                                             "history_ready": int((chosen & frame.ready).sum())}
        scans = {}
        for kind in EEG_KINDS:
            model = models[("task_rest", kind)]
            scan = model.scan_frame(block.recording, frame)
            scans[kind] = scan
            row["intervals"][kind] = interval_assessment(block, scan["stretches"])
            exports[kind].extend(export_temporal_events(block.recording, model, scan, block.original_offset_s))
        # Persist each diagnostic trace, including invalid centers as JSON nulls.
        write_json(out / f"session{session}.block{block.block_index + 1}.traces.json", {
            "recording_id": block.recording.recording_id, "times_s": frame.times.tolist(),
            "raw_valid": frame.raw_valid.tolist(), "history_ready": frame.ready.tolist(),
            "scores": {k: [float(s) if np.isfinite(s) else None for s in v["scores"]] for k, v in scans.items()}})
        reports.append(row)
        plots.append((block, scans))
    classification = {target: {kind: workload_metrics(v["labels"], v["scores"])
                               for kind, v in by_kind.items()} for target, by_kind in pooled.items()}
    report = {"session": session, "session_id": blocks[0].recording.session_id,
              "classification": classification, "blocks": reports, "heldout_scores": pooled}
    write_json(out / f"session{session}.report.json", report)
    for kind, events in exports.items():
        write_json(out / f"session{session}.{kind}.events.json", sorted(events, key=lambda e: e["anchor_s"]))
    plot_session(plots, out / f"session{session}.diagnostic.png", session)
    return report


def plot_session(items, path, session):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 3, figsize=(15, 9), sharex="col")
    colors = ("#2166ac", "#8c510a", "#762a83")
    for col, (block, scans) in enumerate(items):
        for row, kind in enumerate(EEG_KINDS):
            ax, scan = axes[row, col], scans[kind]
            ax.axvspan(block.task_start_s, block.task_end_s, color="#a8c5b5", alpha=0.28, label="task")
            for i, (start, end) in enumerate(block.baseline_intervals_s):
                ax.axvspan(start, end, color="#86bfe5", alpha=0.25, label="rest" if i == 0 else None)
            ax.plot(scan["times"], scan["scores"], color=colors[row], lw=1.1)
            ax.axhline(0, color="#444444", lw=0.8, ls="--")
            for s in scan["stretches"]:
                ax.axvspan(s["start_s"], s["end_s"], ymin=0.94, ymax=1, color="#cf493f")
            ax.set_ylabel(f"{kind}\nmargin")
            ax.grid(alpha=0.12)
            if row == 0:
                ax.set_title(f"Held-out {block.condition}-back | block {block.block_index + 1}")
            if row == col == 0:
                ax.legend(fontsize=8)
            if row == 2:
                ax.set_xlabel("Seconds within recorded excerpt")
    fig.suptitle(f"VP003 session {session}: identical scoring windows | red bars = detected stretches", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def summarize(sessions):
    intervals = {}
    for kind in EEG_KINDS:
        rows = [b["intervals"][kind] for s in sessions for b in s["blocks"]]
        errors = [r["mean_abs_onset_error_s"] for r in rows if r["mean_abs_onset_error_s"] is not None]
        intervals[kind] = {"task_blocks": len(rows), "detected_intervals": sum(r["returned"] for r in rows),
                           "matched_task_intervals": sum(r["true_positives"] for r in rows),
                           "task_covered_s": sum(r["task_covered_s"] for r in rows),
                           "task_total_s": sum(r["task_total_s"] for r in rows),
                           "rest_covered_s": sum(r["rest_covered_s"] for r in rows),
                           "rest_total_s": sum(r["rest_total_s"] for r in rows),
                           "mean_abs_onset_error_s_matched_only": float(np.mean(errors)) if errors else None}
    macro = {}
    for target in TARGETS:
        macro[target] = {}
        for kind in KINDS:
            metrics = [s["classification"][target][kind] for s in sessions]
            macro[target][kind] = {key: float(np.mean([m[key] for m in metrics]))
                                  if all(m[key] is not None for m in metrics) else None
                                  for key in ("auroc", "balanced_accuracy", "sensitivity", "specificity")}
    comparisons = {}
    for reference in ("power", "power_change"):
        test, base = macro["task_rest"]["power_ewma"], macro["task_rest"][reference]
        complete = all(test[k] is not None and base[k] is not None for k in ("auroc", "balanced_accuracy"))
        comparisons[reference] = {
            "mean_auroc_delta": test["auroc"] - base["auroc"] if complete else None,
            "mean_balanced_accuracy_delta": test["balanced_accuracy"] - base["balanced_accuracy"] if complete else None,
            "rest_overlap_delta_s": intervals["power_ewma"]["rest_covered_s"] - intervals[reference]["rest_covered_s"],
            "meets_descriptive_improvement_rule": bool(complete and test["auroc"] > base["auroc"]
                                                       and test["balanced_accuracy"] > base["balanced_accuracy"]
                                                       and intervals["power_ewma"]["rest_covered_s"] <= intervals[reference]["rest_covered_s"]),
            "note": "One participant; descriptive prespecified criterion, not statistical significance or population validation."}
    quality = {}
    for target in TARGETS:
        rows = [b["quality"][target] for s in sessions for b in s["blocks"]]
        quality[target] = {key: sum(r[key] for r in rows)
                           for key in ("labeled_windows", "raw_valid_windows", "history_ready_windows")}
        quality[target]["by_label"] = {label: {key: sum(r["by_label"][label][key] for r in rows)
                                               for key in ("labeled", "raw_valid", "history_ready")}
                                        for label in ("0", "1")}
    scorable = {name: {key: sum(b["scorable_centers"][name][key] for s in sessions for b in s["blocks"])
                       for key in ("labeled", "raw_valid", "history_ready")}
                for name in ("task", "rest")}
    return {"macro_session_metrics": macro, "interval_summary": intervals,
            "ewma_vs_reference": comparisons, "quality_summary": quality, "scorable_center_summary": scorable}


def write_report(report, out):
    fmt = lambda v: "n/a" if v is None else f"{v:.3f}"
    lines = ["# EWMA volatility comparison — fresh VP003", "",
             "Three independently calibrated sessions; six early training blocks and three late test blocks per session. "
             "All models were frozen before held-out scoring. Model comparisons use identical training and test centers.", "",
             "Power is the reference. Power_change adds signed recent changes. Power_ewma also adds lagged volatility "
             "and standardized innovations. Eye-only versions are confound controls and never export EEG events.", "",
             "## Held-out classification", "",
             "AUROC measures ranking (0.5 is chance); it is not accuracy. Balanced accuracy uses the fixed zero-margin boundary. "
             "AP's reference is the positive prevalence. All quantitative windows are nonoverlapping two-second windows, "
             "but their temporal history and shared blocks make them dependent.", ""]
    for target in TARGETS:
        lines += [f"### {target}", "",
                  "| Session | Model | Windows | Positive prevalence | AUROC | AP | Balanced accuracy | Sensitivity | Specificity |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for session in report["sessions"]:
            for kind, m in session["classification"][target].items():
                lines.append(f"| {session['session']} | {kind} | {m['windows']} | {fmt(m['positive_prevalence'])} | "
                             f"{fmt(m['auroc'])} | {fmt(m['average_precision'])} | {fmt(m['balanced_accuracy'])} | "
                             f"{fmt(m['sensitivity'])} | {fmt(m['specificity'])} |")
        lines += ["", "Descriptive mean across the three session metrics (no cross-session pooling of scores):", "",
                  "| Model | Mean AUROC | Mean balanced accuracy |", "|---|---:|---:|"]
        for kind, m in report["macro_session_metrics"][target].items():
            lines.append(f"| {kind} | {fmt(m['auroc'])} | {fmt(m['balanced_accuracy'])} |")
        lines.append("")
    lines += ["## Sustained intervals", "",
              "Segmentation is unchanged: nonnegative margin for at least three seconds, with no gap filling. "
              "A whole task match requires one-to-one IoU ≥ 0.5. Coverage denominators include unscorable time.", "",
              "| Model | Intervals | Matched task blocks | Task time covered | Rest time included |",
              "|---|---:|---:|---:|---:|"]
    for kind, m in report["interval_summary"].items():
        lines.append(f"| {kind} | {m['detected_intervals']} | {m['matched_task_intervals']}/{m['task_blocks']} | "
                     f"{m['task_covered_s']/m['task_total_s']:.1%} | {m['rest_covered_s']:.2f}/{m['rest_total_s']:.2f} s |")
    lines += ["", "## Prespecified incremental-benefit check", "",
              "Require higher mean task/rest AUROC and balanced accuracy, with no increase in confirmed rest-overlap time. "
              "This descriptive criterion does not establish statistical significance.", ""]
    for reference, m in report["ewma_vs_reference"].items():
        lines.append(f"- EWMA versus {reference}: ΔAUROC {fmt(m['mean_auroc_delta'])}; "
                     f"Δbalanced accuracy {fmt(m['mean_balanced_accuracy_delta'])}; "
                     f"Δrest overlap {m['rest_overlap_delta_s']:.2f} s. Meets criterion: "
                     f"{'yes' if m['meets_descriptive_improvement_rule'] else 'no'}.")
    lines += ["", "## Quality and history availability", ""]
    for target, q in report["quality_summary"].items():
        lines.append(f"- {target}: {q['labeled_windows']} labeled two-second windows → "
                     f"{q['raw_valid_windows']} EEG-valid → {q['history_ready_windows']} history-ready. "
                     f"Negative windows: {q['by_label']['0']}; positive windows: {q['by_label']['1']}.")
    for name, q in report["scorable_center_summary"].items():
        lines.append(f"- Dense {name} centers: {q['history_ready']}/{q['labeled']} history-ready "
                     f"({q['history_ready']/max(q['labeled'],1):.1%}); {q['raw_valid']} EEG-valid before history warm-up.")
    lines += ["", "The history requirement removes early rest. Low rest flag time must not be read as successful "
              "rejection of unscorable periods. All models share this mask, so comparisons are paired but absolute "
              "rest specificity remains uncertain. Do not compare these numbers directly with VP002.", "",
              "## Limits and outputs", "",
              "- One new participant and nine test blocks; temporally correlated observations and very short rest.",
              "- EEG/EOG task separation can reflect ocular, sensory or motor effects; no isolated neural-load claim.",
              "- The EWMA forecast uses past feature windows, but the underlying EEG filters/windows are offline.",
              "- No ERP/burst classifier was retrained. Standardized innovations are not labeled aha or P300 events.",
              "- No parameters were retuned after held-out results. Alternative model exports are not independent evidence.",
              "- Replayed EEG belongs to the dataset participant and is unrelated to the phone video's person.", "",
              "Artifacts: `protocol_snapshot.json`, `frozen_models.json`, acquisition audits, model cards, fitted models, "
              "`session*.report.json`, `session*.diagnostic.png`, per-block trace JSON, and three alternative EEG event exports per session.", "",
              "Source: [Shin original EEG recordings](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/)."]
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n")


def run_volatility_benchmark(directory, out):
    directory, out = Path(directory), Path(out)
    if directory.name != "VP003":
        raise ValueError("The locked volatility protocol selects VP003.")
    if (out / "protocol_snapshot.json").exists():
        raise ValueError("Preserve the existing experiment; use a different output directory.")
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    protocol = root / "volatility_protocol.md"
    sources = sorted((root / "eeg_moments").glob("*.py")) + [root / "scripts/fetch_shin.py"]
    snapshot = {"started_utc": utc_now(), "participant": "VP003", "protocol_text": protocol.read_text(),
                "protocol_sha256": file_hash(protocol),
                "source_sha256": {str(p.relative_to(root)): file_hash(p) for p in sources},
                "versions": {p: version(p) for p in ("numpy", "scipy", "scikit-learn", "pyriemann", "mne")}}
    write_json(out / "protocol_snapshot.json", snapshot)
    contexts, frozen = [], {"models": {}, "in_memory_state_before_evaluation": {}}
    for session in (1, 2, 3):
        print(f"Session {session}: calibration only, all five feature models and both targets", flush=True)
        blocks, audit = load_session(directory, session)
        blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
        write_json(out / f"session{session}.audit.json", audit)
        models = fit_temporal_models([b for b in blocks if b.role == "calibration"])
        for (target, kind), model in models.items():
            path = out / f"session{session}.{target}.{kind}.joblib"
            joblib.dump(model, path)
            write_json(path.with_suffix(".model_card.json"), model.model_card)
            frozen["models"][path.name] = file_hash(path)
            frozen["in_memory_state_before_evaluation"][path.name] = joblib.hash(model)
        contexts.append((blocks, models))
    frozen.update({"frozen_utc": utc_now(), "protocol_sha256": snapshot["protocol_sha256"],
                   "heldout_evaluation_started": False})
    write_json(out / "frozen_models.json", frozen)
    evaluation_started = utc_now()
    sessions = [evaluate_session(blocks, models, session, out)
                for session, (blocks, models) in enumerate(contexts, 1)]
    for session, (_, models) in enumerate(contexts, 1):
        for (target, kind), model in models.items():
            path = out / f"session{session}.{target}.{kind}.joblib"
            if file_hash(path) != frozen["models"][path.name]:
                raise ValueError("Saved model changed during evaluation.")
            if joblib.hash(model) != frozen["in_memory_state_before_evaluation"][path.name]:
                raise ValueError("Fitted model state changed during evaluation.")
    report = {"participant": "VP003", "dataset": "Shin2018-A", "sessions": sessions,
              "protocol_sha256": snapshot["protocol_sha256"], "evaluation_started_utc": evaluation_started,
              "completed_utc": utc_now(), **summarize(sessions)}
    write_json(out / "report.json", report)
    write_report(report, out)
    return report
