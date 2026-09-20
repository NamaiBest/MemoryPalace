"""Where do existing continuous burst flags fall? Development-data diagnostic; fits nothing.

Uses previously inspected participants and frozen models only. It selects no
threshold, tunes nothing, and produces no fresh validation. Its purpose is to
test one hypothesis before any new model: that classifiers trained on
stimulus-aligned target/non-target epochs misbehave on the background windows
that dominate a marker-free scan.
"""
from collections import Counter
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score

from .benchmark import gate_metrics, retrieval_metrics
from .data import write_json
from .erp import erp_config
from .model import select_events
from .shin import correct_ocular_from_pretask, load_session
from .workload_benchmark import file_hash, utc_now

TOLERANCE_S = 0.5
BUDGET = 5
SEPARATION_S = 1.5
DRAWS = 2000
CATEGORIES = ("target_window", "nontarget_window", "between_stimuli", "context_margin")
# Development sources. Every participant here was inspected in an earlier experiment.
SOURCES = {
    "VP001": {"mode": "rescan", "models": "outputs/real_vp001", "kinds": ("mean_bins", "xdawn"),
              "model_file": "session{s}.{kind}.joblib", "flags_file": "session{s}.{kind}.all.events.json"},
    "VP002": {"mode": "rescan", "models": "outputs/combined_vp002", "kinds": ("mean_bins",),
              "model_file": "session{s}.{kind}.joblib", "flags_file": "session{s}.events.json"},
    "VP005": {"mode": "traces", "models": "outputs/dynamic_tda_vp005",
              "kinds": ("mean_bins", "zigzag", "mean_bins_zigzag")},
}


def block_frame(block, times, tolerance_s=TOLERANCE_S):
    """Label every scan-grid centre by its relation to the trial markers."""
    times = np.asarray(times, dtype=float)
    targets = np.array([t["time_s"] for t in block.trials if t["label"] == 1], dtype=float)
    nontargets = np.array([t["time_s"] for t in block.trials if t["label"] == 0], dtype=float)
    if not len(targets) or not len(nontargets):
        raise ValueError("The diagnostic needs both target and non-target markers.")
    d_target = np.abs(times[:, None] - targets[None, :]).min(axis=1)
    d_nontarget = np.abs(times[:, None] - nontargets[None, :]).min(axis=1)
    category = np.full(len(times), "context_margin", dtype=object)
    category[(times >= block.task_start_s) & (times <= block.task_end_s)] = "between_stimuli"
    category[d_nontarget <= tolerance_s] = "nontarget_window"
    category[d_target <= tolerance_s] = "target_window"
    signed = times - targets[np.abs(times[:, None] - targets[None, :]).argmin(axis=1)]
    onset_aligned = np.full(len(times), -1, dtype=int)
    for label, onsets in ((0, nontargets), (1, targets)):
        for onset in onsets:
            i = int(np.argmin(np.abs(times - onset)))
            if abs(times[i] - onset) <= 0.05 + 1e-9:
                onset_aligned[i] = label
    return {"targets": targets, "nontargets": nontargets, "d_target": d_target, "d_nontarget": d_nontarget,
            "category": category, "signed_offset": signed, "onset_aligned": onset_aligned}


def draw_flags(times, rng, pool, budget=BUDGET, separation_s=SEPARATION_S):
    """Random flags under the real budget/separation; pool = candidate grid indices."""
    chosen = []
    for i in rng.permutation(pool):
        if all(abs(times[i] - times[j]) >= separation_s for j in chosen):
            chosen.append(int(i))
            if len(chosen) == budget:
                break
    return [{"anchor_s": float(times[i]), "raw_score": 0.0} for i in chosen]


def null_totals(block_data, rng, kind, draws=DRAWS):
    """Total one-to-one target matches over the blocks for random flags of one kind."""
    totals = np.zeros(draws, dtype=int)
    pools = [np.arange(len(times)) if kind == "uniform" else np.flatnonzero(frame["onset_aligned"] >= 0)
             for _, times, _, frame in block_data]
    truths = [{"bursts": [{"anchor_s": float(t)} for t in frame["targets"]]} for _, _, _, frame in block_data]
    for d in range(draws):
        totals[d] = sum(retrieval_metrics(draw_flags(times, rng, pool), truth, TOLERANCE_S)["true_positives"]
                        for (_, times, _, _), pool, truth in zip(block_data, pools, truths))
    return totals


def auroc(positive, negative):
    positive, negative = np.asarray(positive, float), np.asarray(negative, float)
    if not len(positive) or not len(negative):
        return None
    return float(roc_auc_score(np.r_[np.ones(len(positive)), np.zeros(len(negative))], np.r_[positive, negative]))


def summarize_scores(values):
    values = np.asarray(values, float)
    if not len(values):
        return {"n": 0, "median": None, "q25": None, "q75": None, "fraction_nonnegative": None}
    return {"n": int(len(values)), "median": float(np.median(values)), "q25": float(np.percentile(values, 25)),
            "q75": float(np.percentile(values, 75)), "fraction_nonnegative": float((values >= 0).mean())}


def analyze_kind(participant, kind, block_data):
    """block_data: list of (block, valid_times, scores, frame) for 2-/3-back evaluation blocks."""
    rows, matches, errors, accessible, targets_total = [], 0, [], 0, 0
    grid = {c: [] for c in CATEGORIES}
    onset = {0: [], 1: []}
    for block, times, scores, frame in block_data:
        selected = select_events(times, scores, np.ones(len(times), dtype=bool), erp_config(), BUDGET)
        truth = {"bursts": [{"anchor_s": float(t)} for t in frame["targets"]]}
        result = retrieval_metrics(selected, truth, TOLERANCE_S)
        matches += result["true_positives"]
        targets_total += result["truth_events"]
        accessible += gate_metrics(times, np.ones(len(times), dtype=bool), truth, TOLERANCE_S)["accessible_events"]
        remaining = list(frame["targets"])
        for rank, event in enumerate(selected, 1):
            i = int(np.argmin(np.abs(times - event["anchor_s"])))
            matched = False
            if remaining:
                distances = np.abs(event["anchor_s"] - np.asarray(remaining))
                if distances.min() <= TOLERANCE_S:
                    matched = True
                    errors.append(float(event["anchor_s"] - remaining[int(distances.argmin())]))
                    remaining.pop(int(distances.argmin()))
            rows.append({"participant": participant, "kind": kind, "session_id": block.recording.session_id,
                         "recording_id": block.recording.recording_id, "condition": block.condition,
                         "rank": rank, "anchor_s": float(event["anchor_s"]), "score": float(event["raw_score"]),
                         "category": str(frame["category"][i]), "one_to_one_target_match": matched,
                         "distance_to_nearest_target_s": float(frame["d_target"][i]),
                         "distance_to_nearest_nontarget_s": float(frame["d_nontarget"][i]),
                         "signed_offset_from_nearest_target_s": float(frame["signed_offset"][i])})
        for c in CATEGORIES:
            grid[c].extend(scores[frame["category"] == c].tolist())
        for label in (0, 1):
            onset[label].extend(scores[frame["onset_aligned"] == label].tolist())
    # Classifiers are fitted per session, so their margins share no scale: rank within
    # each session and average, as the saved experiments do. Pooled values are kept for reference.
    per_session = {}
    for block, times, scores, frame in block_data:
        session = per_session.setdefault(block.recording.session_id, {c: [] for c in CATEGORIES} | {"onset0": [], "onset1": []})
        for c in CATEGORIES:
            session[c].extend(scores[frame["category"] == c].tolist())
        for label in (0, 1):
            session[f"onset{label}"].extend(scores[frame["onset_aligned"] == label].tolist())

    def comparisons(g):
        background = g["between_stimuli"] + g["context_margin"]
        stimulus = g["target_window"] + g["nontarget_window"]
        return {"target_window_vs_nontarget_window": auroc(g["target_window"], g["nontarget_window"]),
                "target_window_vs_background": auroc(g["target_window"], background),
                "stimulus_windows_vs_background": auroc(stimulus, background),
                "onset_aligned_target_vs_nontarget": auroc(g["onset1"], g["onset0"]),
                "onset_aligned_target_vs_background": auroc(g["onset1"], background)}

    by_session = {session_id: comparisons(g) for session_id, g in per_session.items()}
    session_mean = {key: (float(np.mean([v[key] for v in by_session.values() if v[key] is not None]))
                          if any(v[key] is not None for v in by_session.values()) else None)
                    for key in next(iter(by_session.values()))}
    pooled = comparisons(grid | {"onset0": onset[0], "onset1": onset[1]})
    return {
        "participant": participant, "kind": kind, "blocks": len(block_data),
        "returned_flags": len(rows), "target_matches": matches, "targets": targets_total,
        "accessible_targets": accessible,
        "matched_fraction_of_flags": matches / len(rows) if rows else None,
        "flag_categories": {c: sum(r["category"] == c for r in rows) for c in CATEGORIES},
        "matched_signed_offset_s": summarize_scores(errors) if errors else {"n": 0},
        "matched_signed_offsets": errors,
        "grid_scores_by_category": {c: summarize_scores(grid[c]) for c in CATEGORIES},
        "grid_auroc": session_mean, "grid_auroc_by_session": by_session, "grid_auroc_pooled_across_sessions": pooled,
        "onset_aligned_counts": {"targets": len(onset[1]), "nontargets": len(onset[0])},
        "flags": rows,
    }


def check_saved_flags(participant, kind, session, block, selected, source, spec):
    """The recomputed flags must equal the saved experiment output; otherwise stop."""
    if spec["mode"] == "traces":
        report = json.loads((source / f"session{session}.report.json").read_text())
        saved = next(b for b in report["blocks"] if b["recording_id"] == block.recording.recording_id)
        expected = [(round(e["anchor_s"], 6), e["raw_score"]) for e in saved["continuous_retrieval"][kind]["selected"]]
    else:
        events = json.loads((source / spec["flags_file"].format(s=session, kind=kind)).read_text())
        expected = [(round(e["eeg_anchor_s"], 6), e["raw_score"]) for e in events
                    if e["signal_type"] == "burst" and e["recording_id"] == block.recording.recording_id]
        expected.sort(key=lambda pair: -pair[1])
    actual = [(round(e["anchor_s"], 6), e["raw_score"]) for e in selected]
    if len(actual) != len(expected) or any(a[0] != b[0] or abs(a[1] - b[1]) > 1e-9 for a, b in zip(actual, expected)):
        raise RuntimeError(f"{participant} session {session} {kind}: recomputed flags differ from the saved experiment.")


def collect_participant(participant, spec, data_root):
    source = Path(spec["models"])
    directory = Path(data_root) / participant
    per_kind = {kind: [] for kind in spec["kinds"]}
    quality = []
    inputs = {}
    for session in (1, 2, 3):
        print(f"{participant} session {session}: {spec['mode']} with frozen outputs from {source}", flush=True)
        blocks, audit = load_session(directory, session)
        if spec["mode"] == "rescan":
            blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
            models = {}
            for kind in spec["kinds"]:
                path = source / spec["model_file"].format(s=session, kind=kind)
                models[kind] = joblib.load(path)
                inputs[str(path)] = file_hash(path)
                if models[kind].kind != kind:
                    raise ValueError(f"Unexpected model kind in {path}.")
        for block in blocks:
            if block.role != "evaluation" or block.condition not in (2, 3):
                continue
            if spec["mode"] == "rescan":
                scans = {}
                for kind, model in models.items():
                    if block.recording.recording_id in model.model_card["training_recordings"]:
                        raise ValueError("Evaluation block appears in model training.")
                    times, scores, rejected = model.scan(block.recording)
                    scans[kind] = (np.asarray(times, float), np.asarray(scores, float), int(rejected))
                times_ref = scans[spec["kinds"][0]][0]
            else:
                path = source / f"session{session}.block{block.block_index + 1}.traces.json"
                trace = json.loads(path.read_text())
                inputs[str(path)] = file_hash(path)
                if trace["recording_id"] != block.recording.recording_id:
                    raise ValueError("Trace/recording mismatch.")
                times_ref = np.asarray(trace["burst_times"], float)
                total = len(np.arange(0.1, block.recording.duration_s - 1.0, 0.1))
                scans = {kind: (times_ref, np.asarray(trace["burst_scores"][kind], float), total - len(times_ref))
                         for kind in spec["kinds"]}
            frame = block_frame(block, times_ref)
            quality.append({"recording_id": block.recording.recording_id, "condition": block.condition,
                            "valid_centres": int(len(times_ref)), "rejected_centres": scans[spec["kinds"][0]][2],
                            "targets": int(len(frame["targets"])),
                            "accessible_targets": gate_metrics(times_ref, np.ones(len(times_ref), dtype=bool),
                                                               {"bursts": [{"anchor_s": float(t)} for t in frame["targets"]]},
                                                               TOLERANCE_S)["accessible_events"],
                            "grid_category_counts": {c: int((frame["category"] == c).sum()) for c in CATEGORIES}})
            for kind, (times, scores, _) in scans.items():
                if not np.array_equal(times, times_ref):
                    raise RuntimeError("Kinds must share one valid grid.")
                selected = select_events(times, scores, np.ones(len(times), dtype=bool), erp_config(), BUDGET)
                check_saved_flags(participant, kind, session, block, selected, source, spec)
                per_kind[kind].append((block, times, scores, frame))
    return per_kind, quality, inputs


def run_burst_diagnostic(data_root, out, draws=DRAWS, seed=19):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory is not empty; preserve previous results.")
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    started = utc_now()
    participants, all_flags, inputs = {}, [], {}
    for participant, spec in SOURCES.items():
        per_kind, quality, used = collect_participant(participant, spec, data_root)
        inputs.update(used)
        rng = np.random.default_rng(seed)
        first = per_kind[spec["kinds"][0]]
        nulls = {name: null_totals(first, rng, name, draws) for name in ("uniform", "stimulus_blind")}
        analyses = {}
        for kind, block_data in per_kind.items():
            analysis = analyze_kind(participant, kind, block_data)
            observed = analysis["target_matches"]
            analysis["null"] = {name: {"mean_matches": float(totals.mean()),
                                       "interval_95": [int(np.percentile(totals, 2.5)), int(np.percentile(totals, 97.5))],
                                       "probability_at_least_observed": float((totals >= observed).mean())}
                                for name, totals in nulls.items()}
            all_flags.extend(analysis.pop("flags"))
            analyses[kind] = analysis
        participants[participant] = {"mode": spec["mode"], "source": spec["models"], "blocks": quality,
                                     "null_draws": draws, "null_distributions": {k: v.tolist() for k, v in nulls.items()},
                                     "kinds": analyses}
    report = {"purpose": "development-data diagnostic of existing continuous burst flags; nothing fitted or tuned",
              "started_utc": started, "completed_utc": utc_now(), "tolerance_s": TOLERANCE_S, "budget_per_block": BUDGET,
              "separation_s": SEPARATION_S, "category_rule": {
                  "target_window": f"within {TOLERANCE_S} s of a target onset",
                  "nontarget_window": f"within {TOLERANCE_S} s of a non-target onset and not of a target",
                  "between_stimuli": "inside the task but farther than the tolerance from every stimulus",
                  "context_margin": "outside the task interval (pre/post context)"},
              "null_definitions": {
                  "uniform": "flags drawn uniformly from the valid scan grid, same budget and 1.5 s separation, one-to-one matching at the same tolerance",
                  "stimulus_blind": "flags drawn uniformly from the valid grid centres aligned to any stimulus onset (targets and non-targets alike)"},
              "participants": participants,
              "input_sha256": inputs,
              "source_sha256": {str(p.relative_to(root)): file_hash(p) for p in sorted((root / "eeg_moments").glob("*.py"))}}
    write_json(out / "report.json", report)
    write_flags(all_flags, out / "flags.csv")
    write_results(report, out)
    plot_diagnostic(report, out / "diagnostic.png")
    return report


def write_flags(rows, path):
    columns = ["participant", "kind", "session_id", "recording_id", "condition", "rank", "anchor_s", "score", "category",
               "one_to_one_target_match", "distance_to_nearest_target_s", "distance_to_nearest_nontarget_s",
               "signed_offset_from_nearest_target_s"]
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(f"{row[c]:.6g}" if isinstance(row[c], float) else str(row[c]) for c in columns))
    path.write_text("\n".join(lines) + "\n")


def fmt(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def write_results(report, out):
    lines = ["# Where existing continuous burst flags fall (development data)", "",
             "Frozen models and saved outputs from previously inspected participants. Nothing was fitted, tuned or thresholded here. "
             f"Five flags per 2-/3-back evaluation block, 1.5 s separation, one-to-one matching within ±{TOLERANCE_S} s. "
             "Recomputed flags were checked against each saved experiment before analysis.", "",
             "## Flags by category", "",
             "| Participant | Model | Flags | Target window | Non-target window | Between stimuli | Context margin | One-to-one target matches |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for participant, p in report["participants"].items():
        for kind, a in p["kinds"].items():
            c = a["flag_categories"]
            lines.append(f"| {participant} | {kind} | {a['returned_flags']} | {c['target_window']} | {c['nontarget_window']} | "
                         f"{c['between_stimuli']} | {c['context_margin']} | {a['target_matches']}/{a['targets']} |")
    lines += ["", "A flag in a target window is not necessarily a one-to-one match: two flags can share one target.", "",
              "## Observed matches against chance under the same grid, mask, budget and tolerance", "",
              "| Participant | Model | Observed matches | Accessible targets | Uniform null mean [95% interval] | P(uniform ≥ observed) | Stimulus-blind null mean [95% interval] | P(stimulus-blind ≥ observed) |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for participant, p in report["participants"].items():
        for kind, a in p["kinds"].items():
            u, s = a["null"]["uniform"], a["null"]["stimulus_blind"]
            lines.append(f"| {participant} | {kind} | {a['target_matches']}/{a['targets']} | {a['accessible_targets']} | "
                         f"{u['mean_matches']:.2f} [{u['interval_95'][0]}, {u['interval_95'][1]}] | {u['probability_at_least_observed']:.3f} | "
                         f"{s['mean_matches']:.2f} [{s['interval_95'][0]}, {s['interval_95'][1]}] | {s['probability_at_least_observed']:.3f} |")
    lines += ["", f"Null distributions use {report['participants']['VP001']['null_draws']} random draws per participant. "
              "The uniform null places flags anywhere on the valid grid. The stimulus-blind null places flags only at stimulus onsets, "
              "target or not: it is what a detector that finds stimuli but cannot tell targets from non-targets would score. "
              "These are descriptive reference points on dependent, overlapping windows, not significance tests.", "",
              "## Score separation on the continuous grid", "",
              "| Participant | Model | Median score: target window / non-target window / between / margin | AUROC target vs non-target window | AUROC target window vs background | AUROC stimulus windows vs background | AUROC onset-aligned target vs non-target |",
              "|---|---|---|---:|---:|---:|---:|"]
    for participant, p in report["participants"].items():
        for kind, a in p["kinds"].items():
            g, r = a["grid_scores_by_category"], a["grid_auroc"]
            medians = " / ".join(fmt(g[c]["median"], 2) for c in CATEGORIES)
            lines.append(f"| {participant} | {kind} | {medians} | {fmt(r['target_window_vs_nontarget_window'])} | "
                         f"{fmt(r['target_window_vs_background'])} | {fmt(r['stimulus_windows_vs_background'])} | {fmt(r['onset_aligned_target_vs_nontarget'])} |")
    lines += ["", "Background means grid centres farther than the tolerance from every stimulus, inside or outside the task. "
              "Each AUROC is computed within a session (its own classifier) and averaged over the three sessions; pooled values are in report.json. "
              "Grid windows overlap heavily, so these AUROCs describe ranking on dependent samples. "
              "The onset-aligned column uses one grid centre per marker (within 0.05 s of it) and should track the saved known-onset AUROCs.", "",
              "## Timing of matched flags", "",
              "| Participant | Model | Matched flags | Median signed offset (flag − target onset) | Interquartile range |",
              "|---|---|---:|---:|---:|"]
    for participant, p in report["participants"].items():
        for kind, a in p["kinds"].items():
            m = a["matched_signed_offset_s"]
            if m["n"]:
                lines.append(f"| {participant} | {kind} | {m['n']} | {m['median']:+.2f} s | [{m['q25']:+.2f}, {m['q75']:+.2f}] s |")
            else:
                lines.append(f"| {participant} | {kind} | 0 | n/a | n/a |")
    lines += ["", "## Grid composition", "",
              "| Participant | Blocks | Valid centres | Rejected centres | Target-window centres | Non-target-window centres | Background centres | Accessible targets |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for participant, p in report["participants"].items():
        q = p["blocks"]
        total = lambda key: sum(b["grid_category_counts"][key] for b in q)
        lines.append(f"| {participant} | {len(q)} | {sum(b['valid_centres'] for b in q)} | {sum(b['rejected_centres'] for b in q)} | "
                     f"{total('target_window')} | {total('nontarget_window')} | {total('between_stimuli') + total('context_margin')} | "
                     f"{sum(b['accessible_targets'] for b in q)}/{sum(b['targets'] for b in q)} |")
    lines += ["", "See INTERPRETATION.md for what these numbers do and do not support. `flags.csv` lists every flag; `diagnostic.png` shows categories, score distributions and null distributions.", ""]
    (out / "RESULTS.md").write_text("\n".join(lines))


def plot_diagnostic(report, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    combos = [(p, k) for p, pd in report["participants"].items() for k in pd["kinds"]]
    fig = plt.figure(figsize=(16, 13), layout="constrained")
    grid = fig.add_gridspec(3, len(combos))
    colors = {"target_window": "#2b7a4b", "nontarget_window": "#c98a1b", "between_stimuli": "#6a6a6a", "context_margin": "#b8b8b8"}
    ax = fig.add_subplot(grid[0, :])
    bottoms = np.zeros(len(combos))
    for c in CATEGORIES:
        values = np.array([report["participants"][p]["kinds"][k]["flag_categories"][c] for p, k in combos])
        ax.bar(range(len(combos)), values, bottom=bottoms, color=colors[c], label=c.replace("_", " "))
        bottoms += values
    matches = [report["participants"][p]["kinds"][k]["target_matches"] for p, k in combos]
    ax.plot(range(len(combos)), matches, "k_", markersize=25, markeredgewidth=2, label="one-to-one target matches")
    ax.set_xticks(range(len(combos)), [f"{p}\n{k}" for p, k in combos])
    ax.set_ylabel("Returned flags (30 per participant/model)")
    ax.set_title("Where the existing flags fall relative to the trial markers (development participants)")
    ax.legend(loc="upper right", fontsize=8, ncol=5)
    for i, (p, k) in enumerate(combos):
        ax = fig.add_subplot(grid[1, i])
        a = report["participants"][p]["kinds"][k]
        g = a["grid_scores_by_category"]
        stats = [{"med": g[c]["median"] or 0, "q1": g[c]["q25"] or 0, "q3": g[c]["q75"] or 0,
                  "whislo": g[c]["q25"] or 0, "whishi": g[c]["q75"] or 0, "label": c.split("_")[0]} for c in CATEGORIES]
        ax.bxp(stats, showfliers=False, patch_artist=True,
               boxprops={"facecolor": "#dfe7ee"}, medianprops={"color": "#8b1e1e"})
        ax.axhline(0, color="#444444", lw=0.7, ls="--")
        ax.set_title(f"{p} {k}\nAUROC target vs non-target {fmt(a['grid_auroc']['target_window_vs_nontarget_window'], 2)}; "
                     f"target vs background {fmt(a['grid_auroc']['target_window_vs_background'], 2)}", fontsize=8)
        ax.set_ylabel("grid score (median, IQR)" if i == 0 else "")
        ax.tick_params(axis="x", labelsize=7)
    for i, (p, k) in enumerate(combos):
        ax = fig.add_subplot(grid[2, i])
        pd = report["participants"][p]
        for name, color in (("uniform", "#5b6d7a"), ("stimulus_blind", "#c98a1b")):
            values = np.asarray(pd["null_distributions"][name])
            ax.hist(values, bins=np.arange(-0.5, values.max() + 1.5), alpha=0.55, color=color, label=f"{name} null", density=True)
        ax.axvline(pd["kinds"][k]["target_matches"], color="#8b1e1e", lw=2, label="observed")
        ax.set_title(f"{p} {k}: observed {pd['kinds'][k]['target_matches']}/{pd['kinds'][k]['targets']}", fontsize=8)
        ax.set_xlabel("total target matches over 6 blocks")
        if i == 0:
            ax.set_ylabel("null density")
            ax.legend(fontsize=7)
    fig.suptitle("Continuous burst-flag diagnostic on previously inspected data; nothing fitted. Not fresh validation.", fontsize=11)
    fig.savefig(path, dpi=130)
    plt.close(fig)
