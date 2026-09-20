"""Locked comparison of band variance and explicit Fourier spectra on VP004."""
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np

from .data import write_json
from .fourier import (EEG_KINDS, KINDS, export_fourier_events, fit_fourier_models,
                      quality_counts, spectral_frame)
from .shin import correct_ocular_from_pretask, load_session
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
        frame = spectral_frame(block.recording, block.eog)
        row = {"recording_id": block.recording.recording_id, "condition": block.condition,
               "original_offset_s": block.original_offset_s, "classification": {}, "quality": {},
               "intervals": {}, "scorable_centers": {}}
        for target in TARGETS:
            labels = labels_for_times(block, frame.times, target)
            use = frame.evaluation_grid & frame.valid & (labels >= 0)
            row["quality"][target] = quality_counts(block, frame, target)
            row["classification"][target] = {}
            for kind in KINDS:
                scores = models[(target, kind)].score_features(block.recording, frame.features[kind][use])
                row["classification"][target][kind] = workload_metrics(labels[use], scores)
                pooled[target][kind]["labels"].extend(labels[use].tolist())
                pooled[target][kind]["scores"].extend(scores.tolist())
        labels = labels_for_times(block, frame.times, "task_rest")
        for label, name in ((0, "rest"), (1, "task")):
            row["scorable_centers"][name] = {"labeled": int((labels == label).sum()),
                                             "accepted": int(((labels == label) & frame.valid).sum())}
        scans = {}
        for kind in EEG_KINDS:
            model = models[("task_rest", kind)]
            scan = model.scan_frame(block.recording, frame)
            scans[kind] = scan
            row["intervals"][kind] = interval_assessment(block, scan["stretches"])
            exports[kind].extend(export_fourier_events(block.recording, model, scan, block.original_offset_s))
        spectrogram = 10 * np.log10(np.exp(frame.features["fft_bins"].reshape(-1, 26, 28)).mean(axis=-1))
        write_json(out / f"session{session}.block{block.block_index + 1}.traces.json", {
            "recording_id": block.recording.recording_id, "times_s": frame.times.tolist(),
            "valid": frame.valid.tolist(),
            "scores": {kind: [float(s) if np.isfinite(s) else None for s in v["scores"]] for kind, v in scans.items()},
            "spectrogram_frequency_bin_centers_hz": (np.arange(4, 30) + 0.5).tolist(),
            "spectrogram_db_mean_channel_power_uv2": [[float(x) if np.isfinite(x) else None for x in r] for r in spectrogram]})
        reports.append(row)
        plots.append((block, frame.times, scans, spectrogram))
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
    fig, axes = plt.subplots(4, 3, figsize=(15, 12), sharex="col", layout="constrained")
    values = np.concatenate([spectrogram[np.isfinite(spectrogram)] for _, _, _, spectrogram in items])
    vmin, vmax = np.percentile(values, [2, 98]) if len(values) else (-20, 20)
    colors = ("#2166ac", "#8c510a", "#762a83")
    for col, (block, times, scans, spectrogram) in enumerate(items):
        ax = axes[0, col]
        mesh = ax.pcolormesh(times, np.arange(4, 30) + 0.5, spectrogram.T,
                             cmap="magma", vmin=vmin, vmax=vmax, shading="nearest", rasterized=True)
        ax.axvline(block.task_start_s, color="white", ls="--", lw=1)
        ax.axvline(block.task_end_s, color="white", ls="--", lw=1)
        ax.set_ylabel("Frequency (Hz)")
        ax.set_title(f"Held-out {block.condition}-back | block {block.block_index + 1}")
        for row, kind in enumerate(EEG_KINDS, 1):
            ax, scan = axes[row, col], scans[kind]
            ax.axvspan(block.task_start_s, block.task_end_s, color="#a8c5b5", alpha=0.28, label="task")
            for i, (start, end) in enumerate(block.baseline_intervals_s):
                ax.axvspan(start, end, color="#86bfe5", alpha=0.25, label="rest" if i == 0 else None)
            ax.plot(times, scan["scores"], color=colors[row - 1], lw=1)
            ax.axhline(0, color="#444444", ls="--", lw=0.8)
            for s in scan["stretches"]:
                ax.axvspan(s["start_s"], s["end_s"], ymin=0.94, ymax=1, color="#cf493f")
            ax.set_ylabel(f"{kind}\nmargin")
            ax.grid(alpha=0.12)
            if row == 1 and col == 0:
                ax.legend(fontsize=8)
            if row == 3:
                ax.set_xlabel("Seconds within recorded excerpt")
    fig.colorbar(mesh, ax=list(axes[0]), label="Mean channel power, dB re 1 uV² per bin", shrink=0.85)
    fig.suptitle(f"VP004 session {session}: Fourier power above, frozen scores below | red bars = stretches", fontsize=13)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def summarize(sessions):
    macro, intervals, quality, scorable = {}, {}, {}, {}
    for target in TARGETS:
        macro[target] = {}
        for kind in KINDS:
            rows = [s["classification"][target][kind] for s in sessions]
            macro[target][kind] = {key: float(np.mean([r[key] for r in rows])) if all(r[key] is not None for r in rows) else None
                                   for key in ("auroc", "balanced_accuracy", "sensitivity", "specificity")}
        rows = [b["quality"][target] for s in sessions for b in s["blocks"]]
        quality[target] = {key: sum(r[key] for r in rows) for key in ("labeled_windows", "accepted_windows")}
        quality[target]["by_label"] = {label: {key: sum(r["by_label"][label][key] for r in rows)
                                               for key in ("labeled", "accepted")} for label in ("0", "1")}
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
    for name in ("task", "rest"):
        scorable[name] = {key: sum(b["scorable_centers"][name][key] for s in sessions for b in s["blocks"])
                          for key in ("labeled", "accepted")}
    comparisons = {}
    for reference in ("power", "fft_bands"):
        candidate, base = macro["task_rest"]["fft_bins"], macro["task_rest"][reference]
        complete = all(candidate[k] is not None and base[k] is not None for k in ("auroc", "balanced_accuracy"))
        comparisons[reference] = {
            "mean_auroc_delta": candidate["auroc"] - base["auroc"] if complete else None,
            "mean_balanced_accuracy_delta": candidate["balanced_accuracy"] - base["balanced_accuracy"] if complete else None,
            "rest_overlap_delta_s": intervals["fft_bins"]["rest_covered_s"] - intervals[reference]["rest_covered_s"],
            "meets_descriptive_improvement_rule": bool(complete and candidate["auroc"] > base["auroc"]
                                                       and candidate["balanced_accuracy"] > base["balanced_accuracy"]
                                                       and intervals["fft_bins"]["rest_covered_s"] <= intervals[reference]["rest_covered_s"])}
    return {"macro_session_metrics": macro, "interval_summary": intervals, "quality_summary": quality,
            "scorable_center_summary": scorable, "fft_bins_vs_reference": comparisons}


def write_report(report, out):
    fmt = lambda v: "n/a" if v is None else f"{v:.3f}"
    lines = ["# Fourier comparison — fresh VP004", "",
             "Three separately calibrated sessions; all 36 models frozen before held-out scores. "
             "Power uses filtered variance; fft_bands uses Fourier power in the same three bands; "
             "fft_bins uses 26 one-Hz bands. Their eye-only controls cannot emit EEG events. "
             "All models share the same accepted two-second windows and unchanged three-second segmentation.", ""]
    for target in TARGETS:
        lines += [f"## {target}", "", "AUROC is ranking, not accuracy. AP's reference is the positive prevalence. "
                  "Balanced accuracy uses the fixed zero-margin decision boundary.", "",
                  "| Session | Model | Windows | Positive prevalence | AUROC | AP | Balanced accuracy | Sensitivity | Specificity |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for session in report["sessions"]:
            for kind, m in session["classification"][target].items():
                lines.append(f"| {session['session']} | {kind} | {m['windows']} | {fmt(m['positive_prevalence'])} | "
                             f"{fmt(m['auroc'])} | {fmt(m['average_precision'])} | {fmt(m['balanced_accuracy'])} | "
                             f"{fmt(m['sensitivity'])} | {fmt(m['specificity'])} |")
        lines += ["", "Descriptive means across sessions; scores are not pooled between sessions.", "",
                  "| Model | Mean AUROC | Mean balanced accuracy |", "|---|---:|---:|"]
        for kind, m in report["macro_session_metrics"][target].items():
            lines.append(f"| {kind} | {fmt(m['auroc'])} | {fmt(m['balanced_accuracy'])} |")
        lines.append("")
    lines += ["## Sustained intervals", "", "Whole-task matches require one-to-one IoU ≥ 0.5. "
              "Fragmentation, onset offsets, and invalid samples can affect matches even when ranking is good.", "",
              "| Model | Intervals | Matched task blocks | Task time covered | Rest time included |",
              "|---|---:|---:|---:|---:|"]
    for kind, m in report["interval_summary"].items():
        lines.append(f"| {kind} | {m['detected_intervals']} | {m['matched_task_intervals']}/{m['task_blocks']} | "
                     f"{m['task_covered_s']/m['task_total_s']:.1%} | {m['rest_covered_s']:.2f}/{m['rest_total_s']:.2f} s |")
    lines += ["", "## Prespecified comparison", "", "Require higher mean task/rest AUROC AND balanced accuracy, "
              "with no extra confirmed rest-overlap time. This is a descriptive decision rule, not statistical significance.", ""]
    for reference, m in report["fft_bins_vs_reference"].items():
        lines.append(f"- FFT bins versus {reference}: ΔAUROC {fmt(m['mean_auroc_delta'])}; "
                     f"Δbalanced accuracy {fmt(m['mean_balanced_accuracy_delta'])}; Δrest overlap {m['rest_overlap_delta_s']:.2f} s. "
                     f"Meets criterion: {'yes' if m['meets_descriptive_improvement_rule'] else 'no'}.")
    lines += ["", "## Quality and limitations", ""]
    for target, q in report["quality_summary"].items():
        lines.append(f"- {target}: {q['accepted_windows']}/{q['labeled_windows']} labeled windows accepted; "
                     f"negative counts {q['by_label']['0']}, positive counts {q['by_label']['1']}.")
    for name, q in report["scorable_center_summary"].items():
        lines.append(f"- Dense {name} centers: {q['accepted']}/{q['labeled']} accepted ({q['accepted']/max(q['labeled'],1):.1%}).")
    lines += ["- One new participant, nine test blocks and short nearby rest. Even nonoverlapping windows share blocks and remain dependent.",
              "- No per-person weight transfer: each session has its own calibration. Eye, motor and sensory contributions remain possible.",
              "- The 0.5 Hz FFT grid and 0.25 s hop do not establish that spectral or event localization precision. Hann tapering broadens spectral peaks.",
              "- Two-second features are for sustained task patterns; no new ERP/P300/aha burst detection or gating result is claimed.",
              "- No parameters were tuned after these results. Replayed EEG does not correspond to a separately filmed person.", "",
              "Artifacts: protocol/source snapshots, frozen model hashes, acquisition audits, model cards, "
              "per-session reports, per-block score/spectrogram traces, diagnostic plots and three alternative EEG event exports per session. "
              "Do not merge model alternatives as independent evidence.", "",
              "References: [Shin dataset](https://doc.ml.tu-berlin.de/simultaneous_EEG_NIRS/), "
              "[SciPy spectral analysis](https://docs.scipy.org/doc/scipy/tutorial/signal.html#spectral-analysis)."]
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n")


def run_fourier_benchmark(directory, out):
    directory, out = Path(directory), Path(out)
    if directory.name != "VP004":
        raise ValueError("The locked Fourier protocol selects VP004.")
    if (out / "protocol_snapshot.json").exists():
        raise ValueError("Preserve the existing experiment; use another output directory.")
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    protocol = root / "fourier_protocol.md"
    sources = sorted((root / "eeg_moments").glob("*.py")) + [root / "scripts/fetch_shin.py"]
    snapshot = {"started_utc": utc_now(), "participant": "VP004", "protocol_text": protocol.read_text(),
                "protocol_sha256": file_hash(protocol), "source_sha256": {str(p.relative_to(root)): file_hash(p) for p in sources},
                "versions": {p: version(p) for p in ("numpy", "scipy", "scikit-learn", "pyriemann", "mne")}}
    write_json(out / "protocol_snapshot.json", snapshot)
    contexts, frozen = [], {"models": {}, "in_memory_state_before_evaluation": {}}
    for session in (1, 2, 3):
        print(f"Session {session}: calibration only, six feature models and two targets", flush=True)
        blocks, audit = load_session(directory, session)
        blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
        write_json(out / f"session{session}.audit.json", audit)
        models = fit_fourier_models([b for b in blocks if b.role == "calibration"])
        for (target, kind), model in models.items():
            path = out / f"session{session}.{target}.{kind}.joblib"
            joblib.dump(model, path)
            write_json(path.with_suffix(".model_card.json"), model.model_card)
            frozen["models"][path.name] = file_hash(path)
            frozen["in_memory_state_before_evaluation"][path.name] = joblib.hash(model)
        contexts.append((blocks, models))
    frozen.update({"frozen_utc": utc_now(), "protocol_sha256": snapshot["protocol_sha256"], "heldout_evaluation_started": False})
    write_json(out / "frozen_models.json", frozen)
    evaluation_started = utc_now()
    sessions = [evaluate_session(blocks, models, session, out) for session, (blocks, models) in enumerate(contexts, 1)]
    for session, (_, models) in enumerate(contexts, 1):
        for (target, kind), model in models.items():
            path = out / f"session{session}.{target}.{kind}.joblib"
            if file_hash(path) != frozen["models"][path.name] or joblib.hash(model) != frozen["in_memory_state_before_evaluation"][path.name]:
                raise ValueError("Fitted model or saved file changed during evaluation.")
    report = {"participant": "VP004", "dataset": "Shin2018-A", "sessions": sessions,
              "protocol_sha256": snapshot["protocol_sha256"], "evaluation_started_utc": evaluation_started,
              "completed_utc": utc_now(), **summarize(sessions)}
    write_json(out / "report.json", report)
    write_report(report, out)
    return report
