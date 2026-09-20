"""Evaluation owns injection truth. The detector never receives it."""
from pathlib import Path

import joblib
import numpy as np
from scipy.optimize import linear_sum_assignment

from .data import write_json
from .model import export_events, select_events, train
from .signal import gate_mask
from .synthetic import simulate


def stretch_metrics(detected, truth, min_iou=0.5):
    """Match sustained intervals once each using intersection over union (IoU)."""
    targets = truth["stretches"]
    iou = np.zeros((len(detected), len(targets)))
    for i, event in enumerate(detected):
        for j, target in enumerate(targets):
            overlap = max(0, min(event["end_s"], target["end_s"]) - max(event["start_s"], target["start_s"]))
            union = event["end_s"] - event["start_s"] + target["end_s"] - target["start_s"] - overlap
            iou[i, j] = overlap / union if union else 0
    matches = []
    if iou.size:
        # Prioritize match count, with IoU as a tie-breaker.
        weights = np.where(iou >= min_iou, 1 + iou / (max(iou.shape) + 1), 0)
        rows, columns = linear_sum_assignment(weights, maximize=True)
        matches = [(i, j) for i, j in zip(rows, columns) if iou[i, j] >= min_iou]
    return {"truth_stretches": len(targets), "returned": len(detected),
            "true_positives": len(matches), "false_positives": len(detected) - len(matches),
            "false_negatives": len(targets) - len(matches), "minimum_iou": min_iou,
            "precision": len(matches) / len(detected) if detected else None,
            "recall": len(matches) / len(targets) if targets else None,
            "mean_iou": float(np.mean([iou[i, j] for i, j in matches])) if matches else None,
            "mean_abs_onset_error_s": float(np.mean([abs(detected[i]["start_s"] - targets[j]["start_s"])
                                                     for i, j in matches])) if matches else None,
            "mean_abs_end_error_s": float(np.mean([abs(detected[i]["end_s"] - targets[j]["end_s"])
                                                   for i, j in matches])) if matches else None}


def retrieval_metrics(selected, truth, tolerance_s=1.0):
    remaining = list(truth["bursts"])
    matches, errors = 0, []
    for event in selected:  # Highest score first; each injection can match once.
        if not remaining:
            break
        distances = [abs(event["anchor_s"] - target["anchor_s"]) for target in remaining]
        nearest = int(np.argmin(distances))
        if distances[nearest] <= tolerance_s:
            matches += 1
            errors.append(distances[nearest])
            remaining.pop(nearest)
    count = len(truth["bursts"])
    return {"truth_events": count, "returned": len(selected), "true_positives": matches,
            "false_positives": len(selected) - matches,
            "precision_of_returned": matches / len(selected) if selected else None,
            "recall_at_budget": matches / count if count else None,
            "mean_localization_error_s": float(np.mean(errors)) if errors else None}


def gate_metrics(times, mask, truth, tolerance_s=1.0):
    accessible = sum(bool(np.any(np.abs(times[mask] - e["anchor_s"]) <= tolerance_s))
                     for e in truth["bursts"])
    count = len(truth["bursts"])
    return {"accessible_events": accessible, "truth_events": count,
            "candidate_recall": accessible / count if count else None,
            "eligible_centers": int(mask.sum()), "valid_centers": len(times),
            "valid_center_fraction": float(mask.mean()) if len(mask) else 0.0}


def random_active_gate(times, stretches, onset_mask, config, rng):
    # Rotate the onset mask among scorable positions near/within detected stretches.
    # This matches center count exactly and stays in the same detected work context.
    active = np.zeros(len(times), dtype=bool)
    for stretch in stretches:
        active |= ((times >= stretch["start_s"] - config.gate_radius_s)
                   & (times <= stretch["end_s"] + config.gate_radius_s))
    indices = np.flatnonzero(active)
    mask = np.zeros(len(times), dtype=bool)
    if len(indices):
        mask[indices] = np.roll(onset_mask[indices], int(rng.integers(len(indices))))
    return mask


def evaluate(model, recording, truth, top_k=5):
    if recording.recording_id in model.model_card["training_recordings"]:
        raise ValueError("Evaluation recording was used for training.")
    import hashlib
    digest = hashlib.sha256(recording.samples.tobytes()).hexdigest()
    if digest in model.model_card["training_sample_sha256"]:
        raise ValueError("Evaluation samples duplicate a training recording.")
    if recording.recording_id != truth["recording_id"]:
        raise ValueError("Evaluation truth/recording ID mismatch.")
    scan = model.scan(recording)
    times, scores = scan["times"], scan["scores"]
    masks = {"all": np.ones(len(times), dtype=bool), "onset": scan["onset_mask"],
             "midpoint": gate_mask(times, scan["stretches"], model.config, "midpoint"),
             "end": gate_mask(times, scan["stretches"], model.config, "end")}
    rows = {}
    for scope, mask in masks.items():
        selected = select_events(times, scores, mask, model.config, top_k)
        rows[scope] = {**retrieval_metrics(selected, truth), **gate_metrics(times, mask, truth),
                       "selected": selected}
    rng = np.random.default_rng(truth["seed"] + 50000)
    random_rows = []
    for _ in range(100):
        mask = random_active_gate(times, scan["stretches"], scan["onset_mask"], model.config, rng)
        selected = select_events(times, scores, mask, model.config, top_k)
        random_rows.append({**retrieval_metrics(selected, truth), **gate_metrics(times, mask, truth)})
    rows["random_active_control"] = {
        "draws": len(random_rows),
        "mean_accessible_events": float(np.mean([r["accessible_events"] for r in random_rows])),
        "mean_true_positives": float(np.mean([r["true_positives"] for r in random_rows])),
        "mean_false_positives": float(np.mean([r["false_positives"] for r in random_rows])),
        "valid_center_fraction": rows["onset"]["valid_center_fraction"],
        "note": "Circular shifts within detected-work positions; descriptive matched-count control, not a p-value."}
    stretch_only = [{"anchor_s": e["start_s"], "raw_score": e["peak_z"]}
                    for e in sorted(scan["stretches"], key=lambda s: -s["peak_z"])[:top_k]]
    rows["stretch_only"] = {**retrieval_metrics(stretch_only, truth), "selected": stretch_only}
    result = {"recording_id": recording.recording_id, "scenario": truth["scenario"],
              "model": model.kind, "review_budget": top_k, "duration_s": recording.duration_s,
              "matching_tolerance_s": 1.0, "detected_stretches": scan["stretches"],
              "rejected_windows": scan["rejected_windows"], "total_windows": scan["total_windows"],
              "artifact_or_edge_fraction": scan["artifact_or_edge_fraction"], "comparisons": rows,
              "stretch_detection": stretch_metrics(scan["stretches"], truth)}
    return result, scan


def aggregate(results):
    summary = []
    for model in ("power", "tangent"):
        for scenario in ("mixed", "independent", "negative", "baseline"):
            blocks = [r for r in results if r["model"] == model and r["scenario"] == scenario]
            for scope in ("all", "onset", "midpoint", "end", "stretch_only"):
                rows = [r["comparisons"][scope] for r in blocks]
                count = sum(r["truth_events"] for r in rows)
                returned = sum(r["returned"] for r in rows)
                tp = sum(r["true_positives"] for r in rows)
                valid = sum(r.get("valid_centers", 0) for r in rows)
                summary.append({"model": model, "scenario": scenario, "scope": scope,
                                "blocks": len(blocks), "truth_events": count, "returned": returned,
                                "true_positives": tp, "false_positives": returned - tp,
                                "recall_at_budget": tp / count if count else None,
                                "precision_of_returned": tp / returned if returned else None,
                                "candidate_recall": (sum(r.get("accessible_events", 0) for r in rows) / count
                                                     if count and scope != "stretch_only" else None),
                                "valid_center_fraction": (sum(r.get("eligible_centers", 0) for r in rows) / valid
                                                          if valid else None)})
    return summary


def diagnostic_plot(path, recording, truth, scans, config):
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(Path(path).parent / ".matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True, layout="constrained")
    t = np.arange(recording.samples.shape[1]) / recording.sample_rate
    axes[0].plot(t, recording.samples[2], linewidth=0.45, label="F3 (uV)")
    axes[0].plot(t, recording.samples[6] - 55, linewidth=0.45, label="P3 (offset -55 uV)")
    axes[0].set_ylabel("Simulated EEG (uV)")
    base = scans["tangent"]
    axes[1].plot(base["trace_times"], np.where(base["trace_valid"], base["stretch_z"], np.nan),
                 color="#336699", label="Frontal theta robust z")
    axes[1].axhline(config.stretch_z, color="gray", linestyle="--", label="Stretch entry rule")
    axes[1].set_ylabel("Stretch score")
    for kind, scan in scans.items():
        breaks = np.flatnonzero(np.diff(scan["times"]) > config.step_s * 1.5) + 1
        plot_times = np.insert(scan["times"], breaks, np.nan)
        plot_scores = np.insert(scan["scores"], breaks, np.nan)
        axes[2].plot(plot_times, plot_scores, linewidth=1.0, label=kind)
    axes[2].axhline(0, color="gray", linestyle="--", label="Provisional acceptance margin")
    axes[2].set_ylabel("Decision margin")
    axes[2].set_xlabel("Recording time (seconds)")
    for ax in axes:
        for i, event in enumerate(truth["bursts"]):
            ax.axvline(event["anchor_s"], color="#c83f49", linestyle=":", alpha=0.8,
                       label="Injected burst truth" if i == 0 else None)
        for i, stretch in enumerate(base["stretches"]):
            ax.axvspan(stretch["start_s"] - config.gate_radius_s,
                       stretch["start_s"] + config.gate_radius_s, color="#f4c55e", alpha=0.25,
                       label="Detected onset gate" if i == 0 else None)
        ax.legend(loc="upper right", fontsize=8, ncol=3)
        ax.grid(alpha=0.15)
    fig.suptitle("Synthetic EEG only — held-out block; gates can miss injected packets", fontsize=14)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run_demo(out, seed=19):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    calibration, manifest = [], []
    for index in range(6):
        rec, truth = simulate(seed=1000 + index, session_seed=seed)
        rec.save(out / "calibration" / f"{rec.recording_id}.npz")
        write_json(out / "calibration" / f"{rec.recording_id}.labels.json", truth)
        calibration.append((rec, truth))
        manifest.append({"recording": f"{rec.recording_id}.npz",
                         "labels": f"{rec.recording_id}.labels.json"})
    write_json(out / "calibration" / "manifest.json", manifest)
    models = {}
    for kind in ("power", "tangent"):
        print(f"Training {kind} on six calibration blocks...", flush=True)
        model = train(calibration, kind=kind, seed=seed)
        models[kind] = model
        joblib.dump(model, out / f"{kind}.joblib")
        write_json(out / f"{kind}.model_card.json", model.model_card)
    results = []
    plot_scans = {}
    plot_recording = plot_truth = None
    for scenario, count in [("mixed", 3), ("independent", 3), ("negative", 2), ("baseline", 2)]:
        for index in range(count):
            rec, truth = simulate(seed=2000 + index, session_seed=seed, scenario=scenario)
            rec.save(out / "evaluation" / f"{rec.recording_id}.npz")
            write_json(out / "evaluation_truth" / f"{rec.recording_id}.json", truth)
            for kind, model in models.items():
                print(f"Evaluating {kind}: {rec.recording_id}", flush=True)
                result, scan = evaluate(model, rec, truth)
                results.append(result)
                if scenario == "mixed" and index == 0:
                    plot_scans[kind] = scan
                    plot_recording, plot_truth = rec, truth
                    for scope in ("all", "onset"):
                        selected = result["comparisons"][scope]["selected"]
                        events = export_events(rec, model, selected, stretches=scan["stretches"], scope=scope)
                        write_json(out / f"{kind}.{scope}.events.json", events)
    summary = aggregate(results)
    # Both burst models share the same stretch detector; count each block once.
    stretch_rows = [r["stretch_detection"] for r in results if r["model"] == "power"]
    stretch_summary = {key: sum(r[key] for r in stretch_rows)
                       for key in ("truth_stretches", "returned", "true_positives", "false_positives", "false_negatives")}
    stretch_summary["minimum_iou"] = 0.5
    stretch_summary["mean_iou"] = float(sum((r["mean_iou"] or 0) * r["true_positives"] for r in stretch_rows)
                                         / max(stretch_summary["true_positives"], 1))
    report = {"status": "synthetic_engineering_test_only", "session_seed": seed,
              "calibration_blocks": 6, "evaluation_blocks": 10,
              "held_out": "Different noise/event seeds; same virtual-session spatial mixing.",
              "paired_scenarios": "Scenarios reuse noise seeds 2000-2002 for paired comparisons; ten blocks are not ten independent backgrounds.",
              "limitations": ["Generator defines the signal and its timing; this cannot validate a brain hypothesis.",
                              "Mixed scenario deliberately includes exactly one onset-adjacent burst of three.",
                              "Independent scenario decouples injection timing from stretch onset.",
                              "Matched random controls are descriptive, with no significance claim.",
                              "Two stretch-only, two baseline, and six burst-positive blocks are small engineering checks.",
                              "Real EEG, P300 detection, and alignment to phone video remain unvalidated."],
              "summary": summary, "stretch_summary": stretch_summary, "blocks": results}
    write_json(out / "report.json", report)
    lines = ["# EEG engineering benchmark", "", "**Synthetic data only. No real EEG or insight validation.**", "",
             "Six calibration blocks; ten held-out blocks in the same virtual session. Each block is 180 s.",
             "Scenarios share three held-out noise seeds for paired controls; the ten blocks are not independent samples.",
             "Burst retrieval: margin >= 0, at most five distinct burst flags per block, one-to-one matching within 1 s.",
             "Candidate coverage is the fraction of scorable window centers, not the full recording duration.", "",
             "| Model | Scenario | Search | Found / injected | False flags | Gate coverage |", "|---|---|---|---:|---:|---:|"]
    for row in summary:
        if row["scope"] not in {"all", "onset"}:
            continue
        lines.append(f"| {row['model']} | {row['scenario']} | {row['scope']} | "
                     f"{row['true_positives']} / {row['truth_events']} | {row['false_positives']} | "
                     f"{row['valid_center_fraction']:.1%} |")
    lines += ["", f"Stretch interval detection: {stretch_summary['true_positives']}/{stretch_summary['truth_stretches']} injected stretches recovered, "
              f"{stretch_summary['false_positives']} false stretch flags, mean matched IoU {stretch_summary['mean_iou']:.3f} (required >= 0.5).",
              "All confirmed stretches are exported independently of the burst budget, including stretches with no burst.",
              "The negative scenario contains stretches without bursts; baseline contains neither, but retains artifact controls.",
              "", "Full report also compares midpoint/end gates, matched-count random active gates, and stretch-only anchors.",
              "See `diagnostic.png` for the first held-out block and `*.events.json` for timeline-ready output.",
              "", "Neither synthetic classifier is authorized by these results for interpreting real physiology."]
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n")
    diagnostic_plot(out / "diagnostic.png", plot_recording, plot_truth, plot_scans, models["tangent"].config)
    return report
