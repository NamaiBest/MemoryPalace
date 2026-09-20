"""Walk-forward view of the state-change detector, with a circular time-shift null.

Saved models only; nothing is fitted. For each participant and session the first six
blocks are the calibration (in-sample) period and the last three the out-of-sample
period, exactly as in the original experiments. Every block is rescanned with the
frozen model so the in-sample region can be drawn next to the out-of-sample one,
the way a backtest shows both. The null keeps each out-of-sample score trace intact
and circularly shifts it against the task/rest labels, preserving autocorrelation.
"""
import json
from pathlib import Path

import joblib
import numpy as np

from .data import write_json
from .shin import correct_ocular_from_pretask, load_session
from .workload import labels_for_times, workload_metrics
from .workload_benchmark import file_hash, interval_assessment, utc_now

SOURCES = {
    "VP002": {"smoothed": "outputs/smoothing_vp002/session{s}.power_ema.joblib", "power_is_base": True,
              "eye": ("outputs/workload_vp002/session{s}.report.json", ("classification", "task_rest", "eog_power", "auroc")),
              "saved": ("outputs/smoothing_vp002/session{s}.report.json", {"power": ("classification", "power", "auroc"), "smoothed": ("classification", "power_ema", "auroc")})},
    "VP003": {"power": "outputs/volatility_vp003/session{s}.task_rest.power.joblib",
              "eye": ("outputs/volatility_vp003/session{s}.report.json", ("classification", "task_rest", "eog_power", "auroc")),
              "saved": ("outputs/volatility_vp003/session{s}.report.json", {"power": ("classification", "task_rest", "power", "auroc")})},
    "VP004": {"power": "outputs/fourier_vp004/session{s}.task_rest.power.joblib",
              "eye": ("outputs/fourier_vp004/session{s}.report.json", ("classification", "task_rest", "eog_power", "auroc")),
              "saved": ("outputs/fourier_vp004/session{s}.report.json", {"power": ("classification", "task_rest", "power", "auroc")})},
    "VP005": {"power": "outputs/dynamic_tda_vp005/session{s}.stretch.power.joblib",
              "smoothed": "outputs/dynamic_tda_vp005/session{s}.stretch.ema.joblib",
              "eye": ("outputs/dynamic_tda_vp005/session{s}.report.json", ("workload", "eog_power", "auroc")),
              "saved": ("outputs/dynamic_tda_vp005/session{s}.report.json", {"power": ("workload", "power", "auroc"), "smoothed": ("workload", "ema", "auroc")})},
    "VP006": {"power": "outputs/background_vp006/session{s}.stretch.power.joblib",
              "smoothed": "outputs/background_vp006/session{s}.stretch.power_ema.joblib", "eye": None,
              "saved": ("outputs/background_vp006/session{s}.report.json", {"power": ("stretch", "power", "auroc"), "smoothed": ("stretch", "power_ema", "auroc")})},
}
DRAWS = 2000
# Validated default palette (dataviz reference): slot 1 blue, slot 2 orange; neutrals for context.
BLUE, ORANGE, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#8a8a86", "#0b0b0b", "#52514e"


def dig(value, keys):
    for key in keys:
        value = value[key]
    return value


def load_models(spec, session):
    models, hashes = {}, {}
    if spec.get("smoothed"):
        path = spec["smoothed"].format(s=session)
        models["smoothed"] = joblib.load(path)
        hashes[path] = file_hash(path)
    if spec.get("power_is_base"):
        models["power"] = models["smoothed"].base_model
    else:
        path = spec["power"].format(s=session)
        models["power"] = joblib.load(path)
        hashes[path] = file_hash(path)
    for model in models.values():
        if model.target != "task_rest" or model.kind.startswith("eog_"):
            raise ValueError("Backtest expects EEG task/rest models.")
    return models, hashes


def scan_block(model, block):
    scan = model.scan(block.recording)
    times = np.asarray(scan["times"], float)
    scores = np.asarray(scan["scores"], float)
    valid = np.asarray(scan["valid"], bool)
    labels = labels_for_times(block, times, "task_rest")
    step = float(np.median(np.diff(times))) if len(times) > 1 else 0.25
    every = max(1, round(2.0 / step))
    use = valid & (np.arange(len(times)) % every == 0) & (labels >= 0)
    return {"times": times, "scores": scores, "valid": valid, "labels": labels, "use": use,
            "stretches": scan["stretches"], "intervals": interval_assessment(block, scan["stretches"])}


def shifted(scores, valid, rng):
    """Circularly shift the finite scores among the valid positions; gaps are jumped over."""
    out = scores.copy()
    finite = scores[valid]
    if len(finite) > 1:
        out[valid] = np.roll(finite, int(rng.integers(1, len(finite))))
    return out


def null_distribution(blocks, rng, draws):
    labels = np.concatenate([b["labels"][b["use"]] for b in blocks])
    auroc, balanced = np.full(draws, np.nan), np.full(draws, np.nan)
    if len(np.unique(labels)) != 2:
        return auroc, balanced
    for d in range(draws):
        scores = np.concatenate([shifted(b["scores"], b["valid"], rng)[b["use"]] for b in blocks])
        metrics = workload_metrics(labels, scores)
        auroc[d], balanced[d] = metrics["auroc"], metrics["balanced_accuracy"]
    return auroc, balanced


def pooled(blocks):
    labels = np.concatenate([b["labels"][b["use"]] for b in blocks])
    scores = np.concatenate([b["scores"][b["use"]] for b in blocks])
    return workload_metrics(labels, scores) if len(labels) else None


def summarize_null(values, observed):
    values = values[np.isfinite(values)]
    if not len(values) or observed is None:
        return None
    return {"mean": float(values.mean()), "interval_95": [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))],
            "probability_at_least_observed": float((values >= observed).mean()), "draws": int(len(values))}


def run_backtest(data_root, out, draws=DRAWS, seed=19, participants=tuple(SOURCES)):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory is not empty; preserve previous results.")
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    started = utc_now()
    report = {"purpose": "walk-forward display and circular time-shift null for the saved task/rest state detectors; nothing fitted",
              "started_utc": started, "draws": draws, "seed": seed, "participants": {}, "input_sha256": {}}
    for participant in participants:
        spec = SOURCES[participant]
        directory = Path(data_root) / participant
        sessions = []
        for session in (1, 2, 3):
            print(f"{participant} session {session}: rescan all nine blocks with the frozen models", flush=True)
            blocks, audit = load_session(directory, session)
            blocks, audit = correct_ocular_from_pretask(directory, session, blocks, audit)
            models, hashes = load_models(spec, session)
            report["input_sha256"].update(hashes)
            rng = np.random.default_rng(seed + session)
            record = {"session": session, "session_id": blocks[0].recording.session_id, "models": {},
                      "blocks": [{"block_index": b.block_index, "condition": b.condition, "role": b.role,
                                  "offset_s": b.original_offset_s, "task_start_s": b.task_start_s, "task_end_s": b.task_end_s,
                                  "rest_intervals_s": b.baseline_intervals_s, "duration_s": b.recording.duration_s} for b in blocks],
                      "half_life_s": getattr(models.get("smoothed"), "half_life_s", None)
                                     or (models["smoothed"].model_card.get("temporal_setting") if "smoothed" in models else None)}
            saved_path, saved_keys = spec["saved"]
            saved_report = json.loads(Path(saved_path.format(s=session)).read_text())
            for name, model in models.items():
                scans = [scan_block(model, b) for b in blocks]
                calibration = [s for s, b in zip(scans, blocks) if b.role == "calibration"]
                evaluation = [s for s, b in zip(scans, blocks) if b.role == "evaluation"]
                observed = pooled(evaluation)
                null_auroc, null_ba = null_distribution(evaluation, rng, draws)
                intervals = [s["intervals"] for s in evaluation]
                record["models"][name] = {
                    "kind": model.kind,
                    "in_sample": pooled(calibration),
                    "out_of_sample": observed,
                    "saved_report_out_of_sample_auroc": dig(saved_report, saved_keys[name]) if name in saved_keys else None,
                    "null": {"auroc": summarize_null(null_auroc, observed["auroc"] if observed else None),
                             "balanced_accuracy": summarize_null(null_ba, observed["balanced_accuracy"] if observed else None)},
                    "out_of_sample_intervals": {key: sum(i[key] for i in intervals) for key in
                                                ("returned", "true_positives", "truth_stretches", "task_covered_s", "task_total_s", "rest_covered_s", "rest_total_s")},
                    "traces": [{"times": s["times"].tolist(),
                                "scores": [float(x) if np.isfinite(x) else None for x in s["scores"]],
                                "stretches": s["stretches"]} for s in scans]}
            eye = spec.get("eye")
            record["eye_only_out_of_sample_auroc"] = dig(json.loads(Path(eye[0].format(s=session)).read_text()), eye[1]) if eye else None
            sessions.append(record)
        report["participants"][participant] = {"sessions": sessions, "chosen_model": "smoothed" if spec.get("smoothed") else "power"}
        plot_walkforward(participant, report["participants"][participant], out / f"walkforward_{participant}.png")
    report["completed_utc"] = utc_now()
    report["source_sha256"] = {str(p.relative_to(root)): file_hash(p) for p in sorted((root / "eeg_moments").glob("*.py"))}
    write_json(out / "report.json", report)
    plot_summary(report, out / "summary.png")
    write_results(report, out)
    return report


def fmt(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def write_results(report, out):
    lines = ["# Walk-forward view of the state-change detector", "",
             "Saved frozen models rescanned on all nine blocks of every session: the first six blocks are the calibration "
             "(in-sample) period, the last three the out-of-sample period, as in the original experiments. AUROC and balanced "
             "accuracy use non-overlapping accepted labeled windows. The null circularly shifts each out-of-sample score trace "
             f"against the labels ({report['draws']} draws per session), preserving autocorrelation; the probability is the fraction "
             "of shifts scoring at least the observed value.", "",
             "| Participant | Session | Model | In-sample AUROC | Out-of-sample AUROC | Saved report | Null 95% interval | P(null ≥ observed) | Out-of-sample BA | Whole-task matches | Rest included | Eye-only AUROC |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for participant, p in report["participants"].items():
        for s in p["sessions"]:
            for name, m in s["models"].items():
                n = m["null"]["auroc"]
                iv = m["out_of_sample_intervals"]
                lines.append(f"| {participant} | {s['session']} | {name} ({m['kind']}) | {fmt(m['in_sample']['auroc'] if m['in_sample'] else None)} | "
                             f"{fmt(m['out_of_sample']['auroc'] if m['out_of_sample'] else None)} | {fmt(m['saved_report_out_of_sample_auroc'])} | "
                             f"[{fmt(n['interval_95'][0], 2) if n else 'n/a'}, {fmt(n['interval_95'][1], 2) if n else 'n/a'}] | {fmt(n['probability_at_least_observed']) if n else 'n/a'} | "
                             f"{fmt(m['out_of_sample']['balanced_accuracy'] if m['out_of_sample'] else None)} | {iv['true_positives']}/{iv['truth_stretches']} | "
                             f"{iv['rest_covered_s']:.1f}/{iv['rest_total_s']:.0f} s | {fmt(s['eye_only_out_of_sample_auroc'])} |")
    lines += ["", "## Per participant, chosen model, out of sample", "",
              "| Participant | Model | Mean AUROC | Sessions with P ≤ 0.05 | Whole-task matches | Rest included | Mean eye-only AUROC |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for participant, p in report["participants"].items():
        name = p["chosen_model"]
        ms = [s["models"][name] for s in p["sessions"]]
        aurocs = [m["out_of_sample"]["auroc"] for m in ms if m["out_of_sample"] and m["out_of_sample"]["auroc"] is not None]
        sig = sum(m["null"]["auroc"]["probability_at_least_observed"] <= 0.05 for m in ms if m["null"]["auroc"])
        tp = sum(m["out_of_sample_intervals"]["true_positives"] for m in ms)
        truth = sum(m["out_of_sample_intervals"]["truth_stretches"] for m in ms)
        rest = sum(m["out_of_sample_intervals"]["rest_covered_s"] for m in ms)
        rest_total = sum(m["out_of_sample_intervals"]["rest_total_s"] for m in ms)
        eyes = [s["eye_only_out_of_sample_auroc"] for s in p["sessions"] if s["eye_only_out_of_sample_auroc"] is not None]
        lines.append(f"| {participant} | {name} ({ms[0]['kind']}) | {np.mean(aurocs):.3f} | {sig}/3 | {tp}/{truth} | {rest:.1f}/{rest_total:.0f} s | "
                     f"{fmt(float(np.mean(eyes)) if eyes else None)} |")
    lines += ["", "The saved-report column is each original experiment's own out-of-sample AUROC; small differences for VP003 and VP004 come from their "
              "experiments' own window-selection rules. Whole-task matches require IoU ≥ 0.5 with the task interval. Rest included is labeled rest "
              "inside returned intervals, out of 72 s per participant. Eye-only AUROC is the saved eye-channel control of the same experiment; VP006 had none.", "",
              "Figures: `walkforward_<participant>.png` (score trace over the session clock, calibration then out-of-sample, ground truth shaded, "
              "returned intervals as bars) and `summary.png` (out-of-sample AUROC per session against the shift-null interval and the eye-only control).", ""]
    (out / "RESULTS.md").write_text("\n".join(lines))


def plot_walkforward(participant, data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    name = data["chosen_model"]
    fig, axes = plt.subplots(3, 1, figsize=(16, 9.5), sharex=False, layout="constrained")
    for ax, session in zip(axes, data["sessions"]):
        model = session["models"][name]
        blocks = session["blocks"]
        split = next(b for b in blocks if b["role"] == "evaluation")["offset_s"] - 3.0
        ymax = 0.0
        for block, trace in zip(blocks, model["traces"]):
            off = block["offset_s"]
            ax.axvspan(off + block["task_start_s"], off + block["task_end_s"], color="#edece8", lw=0, zorder=0)
            for start, end in block["rest_intervals_s"]:
                ax.axvspan(off + start, off + end, facecolor="none", edgecolor="#b9b8b3", hatch="///", lw=0, zorder=0)
            times = np.asarray(trace["times"]) + off
            scores = np.array([np.nan if v is None else v for v in trace["scores"]])
            color = BLUE if block["role"] == "evaluation" else GRAY
            ax.plot(times, scores, color=color, lw=1.4, zorder=3)
            finite = scores[np.isfinite(scores)]
            if len(finite):
                ymax = max(ymax, float(np.nanpercentile(np.abs(finite), 99)))
            for stretch in trace["stretches"]:
                ax.plot([off + stretch["start_s"], off + stretch["end_s"]], [0.985, 0.985], color=color, lw=5,
                        solid_capstyle="butt", transform=ax.get_xaxis_transform(), clip_on=False, zorder=4)
        ax.axhline(0, color="#c9c8c3", lw=0.8, zorder=1)
        ax.axvline(split, color=INK, lw=1.0, zorder=5)
        ax.text(split + 2, 0.91, "out of sample →", transform=ax.get_xaxis_transform(), fontsize=9, color=INK, va="top")
        ax.text(split - 2, 0.91, "← calibration (in sample)", transform=ax.get_xaxis_transform(), fontsize=9, color=MUTED, va="top", ha="right")
        oos, null = model["out_of_sample"], model["null"]["auroc"]
        iv = model["out_of_sample_intervals"]
        label = (f"session {session['session']}: out-of-sample AUROC {oos['auroc']:.2f}"
                 + (f", shift-null P = {null['probability_at_least_observed']:.3f}" if null else "")
                 + f"; whole-task {iv['true_positives']}/{iv['truth_stretches']}; rest included {iv['rest_covered_s']:.1f}/{iv['rest_total_s']:.0f} s")
        ax.set_title(label, loc="left", fontsize=10, color=INK)
        ax.set_ylim(-1.15 * ymax if ymax else -1, 1.15 * ymax if ymax else 1)
        ax.set_ylabel("detector margin", color=MUTED)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(colors=MUTED)
        ax.set_xlabel("session clock (s)", color=MUTED)
    handles = [Line2D([], [], color=BLUE, lw=1.6, label="detector margin, out of sample"),
               Line2D([], [], color=GRAY, lw=1.6, label="detector margin, in sample"),
               Line2D([], [], color=BLUE, lw=5, label="returned interval (top bar)"),
               Patch(facecolor="#edece8", label="task period (ground truth)"),
               Patch(facecolor="none", edgecolor="#b9b8b3", hatch="///", label="labeled rest (ground truth)")]
    fig.legend(handles=handles, loc="outside lower center", ncol=5, fontsize=9, frameon=False)
    kind = data["sessions"][0]["models"][name]["kind"]
    fig.suptitle(f"{participant}: task/rest state detector ({kind}), walk-forward by session. Nine blocks per session, the first six calibrate, "
                 "the last three are scored.\nLabels are task versus rest, a proxy for a state change; models were frozen before scoring.",
                 fontsize=11, x=0.01, ha="left")
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_summary(report, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(14, 5.2), layout="constrained")
    x, ticks, ticklabels, group_centres = 0, [], [], []
    for participant, p in report["participants"].items():
        name = p["chosen_model"]
        start = x
        for s in p["sessions"]:
            m = s["models"][name]
            null = m["null"]["auroc"]
            if null:
                ax.plot([x, x], null["interval_95"], color="#cfcecb", lw=8, solid_capstyle="butt", zorder=1)
            if "power" in s["models"] and name != "power" and s["models"]["power"]["out_of_sample"]:
                ax.scatter([x], [s["models"]["power"]["out_of_sample"]["auroc"]], s=70, facecolors="white", edgecolors=BLUE, linewidths=1.6, zorder=3)
            ax.scatter([x], [m["out_of_sample"]["auroc"]], s=80, color=BLUE, zorder=4)
            if s["eye_only_out_of_sample_auroc"] is not None:
                ax.scatter([x], [s["eye_only_out_of_sample_auroc"]], s=70, color=ORANGE, marker="D", zorder=3)
            ticks.append(x)
            ticklabels.append(f"s{s['session']}")
            x += 1
        aurocs = [s["models"][name]["out_of_sample"]["auroc"] for s in p["sessions"]]
        centre = (start + x - 1) / 2
        group_centres.append((centre, participant, float(np.mean(aurocs))))
        x += 1
    ax.axhline(0.5, color="#c9c8c3", lw=0.8, zorder=0)
    ax.text(x - 1.2, 0.505, "chance", color=MUTED, fontsize=8, ha="right", va="bottom")
    for centre, participant, mean in group_centres:
        ax.text(centre, 1.07, f"{participant}\nmean {mean:.2f}", ha="center", va="bottom", fontsize=9, color=INK, clip_on=False)
    ax.set_xticks(ticks, ticklabels, color=MUTED, fontsize=8)
    ax.set_ylim(0.15, 1.05)
    ax.set_ylabel("out-of-sample AUROC, task vs rest", color=MUTED)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED)
    handles = [Line2D([], [], marker="o", color=BLUE, lw=0, markersize=9, label="EEG detector, chosen model (smoothed where calibrated)"),
               Line2D([], [], marker="o", markerfacecolor="white", markeredgecolor=BLUE, lw=0, markersize=9, label="EEG detector, raw margins"),
               Line2D([], [], marker="D", color=ORANGE, lw=0, markersize=8, label="eye-channel-only control"),
               Line2D([], [], color="#cfcecb", lw=8, label="circular time-shift null, 95% interval")]
    fig.legend(handles=handles, loc="outside lower center", fontsize=8, frameon=False, ncol=4)
    fig.suptitle("Signal against noise: out-of-sample state detection per session, five participants, models frozen before scoring", fontsize=11, x=0.01, ha="left")
    fig.savefig(path, dpi=130)
    plt.close(fig)


def replot(out):
    """Regenerate the figures from a saved report without rescanning."""
    out = Path(out)
    report = json.loads((out / "report.json").read_text())
    for participant, data in report["participants"].items():
        plot_walkforward(participant, data, out / f"walkforward_{participant}.png")
    plot_summary(report, out / "summary.png")
