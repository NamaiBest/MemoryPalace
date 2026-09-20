"""Integration replay on previously inspected VP002, not fresh validation."""
import hashlib
import json
from pathlib import Path

import joblib

from .combined import detect_combined
from .data import write_json
from .erp import fit_erp
from .shin import correct_ocular_from_pretask, load_session
from .smoothing import SmoothedPowerModel
from .workload_benchmark import assert_heldout, file_hash, utc_now

STRETCH_BRANCHES = {
    "power": {
        "model": "session{s}.task_rest.power.joblib", "events": "session{s}.power.events.json",
        "description": "existing frozen power/task_rest classifier; peak raw linear margins",
        "summary": "Stretches use the existing power/task-rest model with raw margins."},
    "power_ema": {
        "model": "session{s}.power_ema.joblib", "events": "session{s}.power_ema.events.json",
        "description": "selected frozen power/task_rest classifier wrapped in calibration-selected exponential smoothing; peak smoothed margins",
        "summary": ("Stretches use the selected band-power classifier with exponential smoothing of its margins. "
                    "The half-life was selected on calibration folds and the classifier weights are the original saved ones.")},
}
DEFAULT_MODEL_DIRECTORIES = {"power_ema": "outputs/smoothing_vp002", "power": "outputs/workload_vp002"}
BURST_LINK_FIELDS = ("overlapping_stretch_ids", "nearest_stretch_onset_s",
                     "offset_from_stretch_onset_s", "within_onset_gate")


def load_stretch_model(path, kind):
    """Load one session's stretch model and refuse a branch/file mismatch."""
    path = Path(path)
    if kind not in STRETCH_BRANCHES:
        raise ValueError("Unknown stretch branch.")
    model = joblib.load(path)
    if getattr(model, "kind", None) != kind or getattr(model, "target", None) != "task_rest":
        raise ValueError(f"Expected a {kind}/task_rest stretch model in {path.name}.")
    if kind == "power_ema":
        if not isinstance(model, SmoothedPowerModel) or model.base_model.kind != "power":
            raise ValueError("The smoothed branch must wrap the original power classifier.")
        if not model.model_card.get("base_classifier_weights_unchanged"):
            raise ValueError("The smoothed model card does not certify unchanged base weights.")
    return model


def without(event, fields):
    return {k: v for k, v in event.items() if k not in fields}


def run_combined_replay(directory, workload_directory, out, top_k=5, stretch_kind="power_ema", reference=None):
    directory, workload_directory, out = map(Path, (directory, workload_directory, out))
    reference = Path(reference) if reference is not None else None
    if directory.name != "VP002":
        raise ValueError("This integration replay uses previously inspected VP002.")
    if stretch_kind not in STRETCH_BRANCHES:
        raise ValueError("Unknown stretch branch.")
    if top_k < 0:
        raise ValueError("top_k must be nonnegative.")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory is not empty; preserve previous results.")
    branch = STRETCH_BRANCHES[stretch_kind]
    input_paths = [workload_directory / branch["model"].format(s=s) for s in (1, 2, 3)]
    input_hashes = {str(p.resolve()): file_hash(p) for p in input_paths}
    started = utc_now()
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    contexts = []
    for session, path in zip((1, 2, 3), input_paths):
        print(f"Session {session}: reuse frozen {stretch_kind} stretch model; calibrate ERP branch", flush=True)
        blocks, audit = load_session(directory, session)
        blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
        write_json(out / f"session{session}.audit.json", audit)
        workload_model = load_stretch_model(path, stretch_kind)
        for block in blocks:
            workload_model.validate_recording(block.recording)
        calibration = [b for b in blocks if b.role == "calibration"]
        burst_model = fit_erp(calibration, kind="mean_bins")
        burst_path = out / f"session{session}.mean_bins.joblib"
        joblib.dump(burst_model, burst_path)
        write_json(burst_path.with_suffix(".model_card.json"), burst_model.model_card)
        contexts.append((session, blocks, workload_model, burst_model, burst_path,
                         joblib.hash(workload_model), joblib.hash(burst_model), file_hash(burst_path)))
    manifest = {
        "started_utc": started, "purpose": "integration replay; not fresh model validation",
        "participant": "VP002", "stretch_kind": stretch_kind, "workload_model": branch["description"],
        "stretch_half_lives_s": {f"session{s}": getattr(m, "half_life_s", None) for s, _, m, *_ in contexts},
        "stretch_model_directory": str(workload_directory.resolve()),
        "burst_model": "mean_bins, fitted separately on each session's calibration blocks",
        "burst_top_k_per_excerpt": top_k, "burst_margin_threshold": 0,
        "burst_separation_s": 1.5, "stretch_minimum_s": 3,
        "selection": "both branches scan every valid center in each evaluation excerpt",
        "reference_combined_run": str(reference.resolve()) if reference else None,
        "limitations": "Block excerpts were selected by task markers. Scanners receive no markers. This is not an unsegmented full-session evaluation or a cognitive-event accuracy estimate.",
        "input_model_sha256": input_hashes,
        "source_sha256": {str(p.relative_to(root)): file_hash(p)
                          for p in sorted((root / "eeg_moments").glob("*.py"))},
    }
    write_json(out / "integration_manifest.json", manifest)
    write_json(out / "frozen_models.json", {
        "frozen_utc": utc_now(), "stretch_kind": stretch_kind, "input_models": input_hashes,
        "erp_models": {path.name: digest for _, _, _, _, path, _, _, digest in contexts}})

    reports, plot_rows = [], []
    for session, blocks, workload_model, burst_model, burst_path, whash, bhash, saved_hash in contexts:
        events, diagnostics = [], []
        for block in blocks:
            if block.role != "evaluation":
                continue
            assert_heldout(block, workload_model)
            if (block.recording.recording_id in burst_model.model_card["training_recordings"]
                    or hashlib.sha256(block.recording.samples.tobytes()).hexdigest()
                    in burst_model.model_card["training_hashes"]):
                raise ValueError("ERP inference excerpt duplicates calibration data.")
            block_events, diagnostic = detect_combined(block.recording, workload_model, burst_model,
                                                       top_k, block.original_offset_s)
            events.extend(block_events)
            diagnostics.append(diagnostic)
            plot_rows.append((session, block, block_events))
        if joblib.hash(workload_model) != whash or joblib.hash(burst_model) != bhash:
            raise RuntimeError("Inference changed fitted model state.")
        if file_hash(burst_path) != saved_hash:
            raise RuntimeError("Saved ERP model changed during inference.")
        events.sort(key=lambda e: (e["anchor_s"], e["event_id"]))
        # Integration must reproduce the standalone export of the same stretch models exactly.
        previous = json.loads((workload_directory / branch["events"].format(s=session)).read_text())
        current = [e for e in events if e["signal_type"] == "stretch"]
        if ([without(e, ("overlapping_burst_ids",)) for e in current]
                != [without(e, ("overlapping_burst_ids",)) for e in previous]):
            raise RuntimeError("Combined inference changed the standalone stretch output.")
        bursts = [e for e in events if e["signal_type"] == "burst"]
        bursts_match = None
        if reference is not None:
            earlier = json.loads((reference / f"session{session}.events.json").read_text())
            earlier_bursts = [without(e, BURST_LINK_FIELDS) for e in earlier if e["signal_type"] == "burst"]
            if earlier_bursts != [without(e, BURST_LINK_FIELDS) for e in bursts]:
                raise RuntimeError("Burst candidates differ from the reference run; "
                                   "the burst branch must not depend on the stretch model.")
            bursts_match = True
        write_json(out / f"session{session}.events.json", events)
        write_json(out / f"session{session}.diagnostics.json", diagnostics)
        overlapping = sum(d["bursts_overlapping_stretches"] for d in diagnostics)
        reports.append({"session": session, "session_id": workload_model.session_id,
                        "stretch_kind": stretch_kind, "half_life_s": getattr(workload_model, "half_life_s", None),
                        "stretch_events": len(current), "burst_events": len(bursts),
                        "bursts_overlapping_stretches": overlapping,
                        "bursts_outside_stretches": len(bursts) - overlapping,
                        "standalone_stretch_output_reproduced": True,
                        "burst_output_matches_reference": bursts_match, "model_state_unchanged": True})
    if any(file_hash(path) != digest for path, digest in input_hashes.items()):
        raise RuntimeError("An input model file changed during replay.")
    write_json(out / "report.json", {"purpose": manifest["purpose"], "stretch_kind": stretch_kind,
                                     "reference_combined_run": manifest["reference_combined_run"],
                                     "sessions": reports})
    plot_timeline(plot_rows, out / "timeline.png", stretch_kind)
    total_stretches = sum(r["stretch_events"] for r in reports)
    total_bursts = sum(r["burst_events"] for r in reports)
    lines = ["# Combined EEG integration replay", "",
             f"Both detectors scan the same EEG excerpts independently; their accepted events form one chronological list per session. {branch['summary']} Bursts use an ERP mean-amplitude model calibrated on that same session.", "",
             "| Session | Stretch model | Stretches | Burst candidates | Bursts overlapping stretches | Bursts outside stretches |",
             "|---|---|---:|---:|---:|---:|"]
    lines += [f"| {r['session_id']} | {r['stretch_kind']}" + (f" ({r['half_life_s']:g} s half-life)" if r["half_life_s"] else "")
              + f" | {r['stretch_events']} | {r['burst_events']} | {r['bursts_overlapping_stretches']} | {r['bursts_outside_stretches']} |" for r in reports]
    lines += ["", "Counts describe output volume, not accuracy. This reuses previously inspected VP002 data and is an integration check, not fresh validation. Reliable continuous burst detection remains unestablished.", "",
              f"All confirmed stretches are retained. Up to {top_k} positive-margin burst candidates per excerpt survive 1.5-second peak separation. Burst search is never gated by stretches. Overlap creates reciprocal navigation links, without combining scores, labels, or confidence.", "",
              f"The {total_stretches} stretch events equal the standalone `{stretch_kind}` export in `{workload_directory}` apart from navigation links. All fitted model states and saved weights remained unchanged during inference. No weights were transferred between sessions or participants."]
    if reference is not None:
        lines += ["", f"The {total_bursts} burst candidates are identical to those in `{reference}` apart from their stretch links. The burst branch does not depend on which stretch model is loaded."]
    lines += ["", "Each session*.events.json uses its original EEG session clock, with recording IDs and excerpt offsets preserved. Only the last three task-centered excerpts per session were scanned, including 0-back; this is not full-session validation. Colors in timeline.png are review-priority thirds within detector and excerpt, not mental intensity. Confidence remains null.", "",
              "Replay EEG does not measure or corroborate the person in a separately recorded phone video. No insight/confusion labels or combined accuracy are inferred.", ""]
    (out / "RESULTS.md").write_text("\n".join(lines))


def plot_timeline(rows, path, stretch_kind="power"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"high": "#dc4141", "medium": "#c49700", "low": "#208654"}
    fig, axes = plt.subplots(3, 3, figsize=(15, 7), sharey=True)
    for ax, (session, block, events) in zip(axes.flat, rows):
        for event in events:
            offset = block.original_offset_s
            color = colors[event["review_priority"]]
            if event["signal_type"] == "stretch":
                ax.plot([event["start_s"] - offset, event["end_s"] - offset], [1, 1],
                        color=color, linewidth=7, solid_capstyle="butt")
            else:
                ax.scatter(event["anchor_s"] - offset, 0, c=color, s=35)
        ax.set_title(f"Session {session}, excerpt {block.block_index + 1} (offset {block.original_offset_s:.1f}s)", fontsize=9)
        ax.set(xlim=(0, block.recording.duration_s), ylim=(-0.6, 1.6),
               yticks=[0, 1], yticklabels=["Burst", "Stretch"], xlabel="Seconds within excerpt")
        ax.grid(axis="x", alpha=0.2)
    fig.suptitle(f"Replayed EEG: independent stretch ({stretch_kind}) and burst candidates\n"
                 "Color = review priority within detector/excerpt; no cognitive-intensity or accuracy claim", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=150)
    plt.close(fig)
