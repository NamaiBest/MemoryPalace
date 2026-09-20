"""Independent stretch and ERP scans of the same calibrated EEG recording."""
import numpy as np

from .model import export_events, select_events
from .smoothing import export_smoothed_events
from .workload import export_workload_events


def export_stretches(recording, model, scan, offset_s=0.0):
    """Export with the model's own score definition; smoothed margins are not raw margins."""
    if model.kind == "power_ema":
        return export_smoothed_events(recording, model, scan, offset_s)
    return export_workload_events(recording, model, scan, offset_s)


def detect_combined(recording, workload_model, burst_model, top_k=5, offset_s=0.0):
    """Return the union of accepted events. Inference receives no task/trial labels.

    top_k limits bursts only. Scores/ranks remain specific to each detector and
    recording excerpt; temporal links neither gate candidates nor boost scores.
    """
    recording.validate()
    if not isinstance(top_k, int) or top_k < 0:
        raise ValueError("top_k must be a nonnegative integer.")
    if not np.isfinite(offset_s) or offset_s < 0:
        raise ValueError("Clock offset must be finite and nonnegative.")
    # Validate both branches before scanning either; never transfer session weights.
    workload_model.validate_recording(recording)
    burst_model.validate_recording(recording)
    stretch_kinds = {workload_model.kind, getattr(workload_model, "base_model", workload_model).kind}
    if any(kind.startswith("eog_") for kind in stretch_kinds) or burst_model.kind.startswith("eog_"):
        raise ValueError("Eye-only controls cannot export combined EEG events.")
    if workload_model.target != "task_rest":
        raise ValueError("The stretch branch requires a task/rest model.")

    workload_scan = workload_model.scan(recording)
    times, scores, rejected = burst_model.scan(recording)
    selected = select_events(times, scores, np.ones(len(times), dtype=bool),
                             burst_model.config, top_k)
    stretches = export_stretches(recording, workload_model, workload_scan, offset_s)
    bursts = export_events(recording, burst_model, selected, offset_s=offset_s, scope="all")
    for burst in bursts:
        onset = burst["eeg_anchor_s"]
        burst.update({
            "event_type": "eeg_evoked_response_candidate",
            "start_s": max(0, onset - 0.1) + offset_s,
            "end_s": min(recording.duration_s, onset + 1.0) + offset_s,
            "anchor_definition": "proposed stimulus onset; not the peak latency of a P300",
            "evidence": "Frozen within-session ERP classifier ranked this EEG window as target-like; cognitive meaning unverified.",
            "model_version": f"real-shin2018-{burst_model.kind}-v1",
        })
        nearest = min(stretches, key=lambda s: abs(s["anchor_s"] - burst["anchor_s"]), default=None)
        delta = burst["anchor_s"] - nearest["anchor_s"] if nearest else None
        burst.update({
            "nearest_stretch_onset_s": nearest["anchor_s"] if nearest else None,
            "offset_from_stretch_onset_s": delta,
            "within_onset_gate": abs(delta) <= burst_model.config.gate_radius_s if nearest else False,
            "overlapping_stretch_ids": [s["event_id"] for s in stretches
                                        if burst["start_s"] < s["end_s"] and burst["end_s"] > s["start_s"]],
        })
    for stretch in stretches:
        stretch["overlapping_burst_ids"] = [b["event_id"] for b in bursts
                                            if stretch["event_id"] in b["overlapping_stretch_ids"]]
    events = sorted(stretches + bursts, key=lambda e: (e["anchor_s"], e["event_id"]))
    diagnostics = {
        "source": recording.source, "recording_id": recording.recording_id,
        "session_id": recording.session_id, "offset_s": offset_s,
        "search_scope": "all valid centers in this excerpt; no onset gating",
        "combination": "union; overlap links only; no score fusion or confidence boost",
        "rank_scope": "each detector within this recording excerpt",
        "stretch_model_kind": workload_model.kind,
        "stretch_half_life_s": getattr(workload_model, "half_life_s", None),
        "burst_budget": top_k,
        "event_counts": {"stretch": len(stretches), "burst": len(bursts)},
        "bursts_overlapping_stretches": sum(bool(b["overlapping_stretch_ids"]) for b in bursts),
        "workload_windows": len(workload_scan["times"]),
        "workload_rejected_windows": int((~workload_scan["valid"]).sum()),
        "burst_windows": len(times) + rejected, "burst_rejected_windows": int(rejected),
    }
    return events, diagnostics
