"""Publication/demo figures. Reads cached arrays and result JSON."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C  # noqa: E402
from src.io_utils import ensure_dirs, read_json, setup_logging  # noqa: E402

plt.rcParams.update(
    {
        "figure.dpi": 140,
        "savefig.dpi": 200,
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.facecolor": "white",
        "figure.facecolor": "white",
    }
)


def _save(fig, name: str) -> Path:
    path = C.FIGURES_DIR / name
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_erp_waveforms() -> None:
    z = np.load(C.CACHE_DIR / "erp_grand_average.npz")
    t = z["times"]
    ch = [str(x) for x in z["ch_names"]]
    s = z["erp_surprise"]
    c = z["erp_control"]
    d = z["erp_diff"]
    plot_ch = [x for x in ("Fz", "Cz", "F3", "F4", "P3", "P4") if x in ch]
    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.2), sharex=True, sharey=True)
    for ax, name in zip(axes.ravel(), plot_ch):
        i = ch.index(name)
        ax.axvline(0, color="0.6", lw=0.8)
        ax.axhline(0, color="0.85", lw=0.6)
        ax.plot(t, c[i], color="#4C78A8", lw=1.4, label="dummy-surprises (control)")
        ax.plot(t, s[i], color="#E45756", lw=1.4, label="surprises")
        ax.set_title(name)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("µV")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False)
    fig.suptitle("Grand-average surprise-related EEG response", y=1.02)
    _save(fig, "erp_waveforms.png")

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for name, color in (("Fz", "#F58518"), ("Cz", "#E45756"), ("P3", "#54A24B")):
        if name not in ch:
            continue
        i = ch.index(name)
        ax.plot(t, d[i], color=color, lw=1.6, label=f"{name} surprise−control")
    ax.axvline(0, color="0.6", lw=0.8)
    ax.axhline(0, color="0.85", lw=0.6)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Difference (µV)")
    ax.set_title("Event-related difference (surprises − dummy-surprises)")
    ax.legend(frameon=False)
    _save(fig, "erp_difference.png")


def fig_tfr() -> None:
    z = np.load(C.CACHE_DIR / "tfr_midline.npz")
    freqs = z["freqs"]
    times = z["tfr_times"]
    diff = z["diff_induced"]
    chans = [str(x) for x in z["channels"]]
    fig, axes = plt.subplots(1, len(chans), figsize=(10, 3.6), sharey=True)
    if len(chans) == 1:
        axes = [axes]
    vmax = np.percentile(np.abs(diff), 98)
    for ax, name, img in zip(axes, chans, diff):
        im = ax.pcolormesh(times, freqs, img, shading="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        ax.axvline(0, color="k", lw=0.8)
        ax.set_title(name)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Hz")
    fig.colorbar(im, ax=axes, shrink=0.8, label="|STFT| surprise − control")
    fig.suptitle("Time-frequency difference (induced STFT)", y=1.04)
    path = C.FIGURES_DIR / "tfr_difference.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_channel_bars() -> None:
    ev = read_json(C.RESULTS_DIR / "event_analysis.json")
    items = sorted(ev["channel_window_diff_uv"].items(), key=lambda kv: kv[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    colors = ["#E45756" if v >= 0 else "#4C78A8" for v in vals]
    ax.bar(names, vals, color=colors)
    ax.axhline(0, color="0.5", lw=0.8)
    ax.set_ylabel("Mean amplitude difference (µV)")
    ax.set_title("Channel-level surprise−control difference, 0.25–0.55 s")
    ax.tick_params(axis="x", rotation=45)
    _save(fig, "channel_difference.png")


def fig_topomap() -> None:
    z = np.load(C.CACHE_DIR / "erp_grand_average.npz")
    t = z["times"]
    ch = [str(x) for x in z["ch_names"]]
    d = z["erp_diff"]
    m = (t >= 0.25) & (t <= 0.55)
    vals = d[:, m].mean(axis=1)
    try:
        import mne
        info = mne.create_info(ch, sfreq=C.EXPECTED_SFREQ, ch_types="eeg")
        montage = mne.channels.make_standard_montage("standard_1020")
        info.set_montage(montage)
        fig, ax = plt.subplots(figsize=(4.4, 3.8))
        mne.viz.plot_topomap(vals, info, axes=ax, show=False, cmap="RdBu_r", contours=4)
        ax.set_title("0.25–0.55 s difference")
        _save(fig, "topomap_difference.png")
    except Exception:
        fig, ax = plt.subplots(figsize=(6.5, 3.4))
        ax.bar(ch, vals)
        ax.set_title("0.25–0.55 s difference (no montage available)")
        ax.tick_params(axis="x", rotation=45)
        _save(fig, "topomap_difference.png")


def fig_loso_and_ablation() -> None:
    clf = read_json(C.RESULTS_DIR / "classification.json")
    key = "features_event_all16_logreg"
    if key not in clf:
        keys = [k for k in clf if k.endswith("_logreg")]
        key = keys[0] if keys else None
    if key:
        rows = clf[key]["per_subject"]
        fig, ax = plt.subplots(figsize=(8.8, 3.6))
        xs = np.arange(len(rows))
        ax.bar(xs, [r["balanced_accuracy"] for r in rows], color="#4C78A8")
        ax.axhline(0.5, color="0.4", ls="--", lw=1, label="chance")
        ax.set_xticks(xs, [r["subject"].replace("sub-", "") for r in rows], rotation=90, fontsize=8)
        ax.set_ylabel("Balanced accuracy")
        ax.set_xlabel("Held-out subject")
        ax.set_title("LOSO logistic regression, all 16 channels")
        ax.legend(frameon=False)
        _save(fig, "loso_balanced_accuracy.png")

        fig, ax = plt.subplots(figsize=(4.2, 3.6))
        cm = clf[key]["pooled"]["confusion_matrix"]
        mat = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
        im = ax.imshow(mat, cmap="Blues")
        for (i, j), v in np.ndenumerate(mat):
            ax.text(j, i, str(v), ha="center", va="center")
        ax.set_xticks([0, 1], ["pred control", "pred surprise"])
        ax.set_yticks([0, 1], ["true control", "true surprise"])
        ax.set_title("Pooled confusion (LOSO logreg)")
        fig.colorbar(im, ax=ax, shrink=0.8)
        _save(fig, "confusion_logreg.png")

    abl = read_json(C.RESULTS_DIR / "electrode_ablation.json")
    order = [k for k in ("all16", "half8", "ganglion4", "glasses2") if k in abl]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = np.arange(len(order))
    ba = [abl[k]["balanced_accuracy_mean"] for k in order]
    auc = [abl[k]["roc_auc_mean"] or 0 for k in order]
    ax.bar(x - 0.18, ba, 0.36, label="balanced acc", color="#4C78A8")
    ax.bar(x + 0.18, auc, 0.36, label="ROC-AUC", color="#F58518")
    ax.axhline(0.5, color="0.4", ls="--", lw=0.8)
    ax.set_xticks(x, [f"{k}\n({abl[k]['n_channels']} ch)" for k in order])
    ax.set_ylim(0.4, 1.0)
    ax.set_ylabel("LOSO mean")
    ax.set_title("Electrode ablation (logistic regression)")
    ax.legend(frameon=False)
    _save(fig, "electrode_ablation.png")


def fig_trigger() -> None:
    p = C.RESULTS_DIR / "continuous_trigger.json"
    if not p.exists():
        return
    tr = read_json(p)
    rows = [r for r in tr["folds"] if r.get("test")]
    if not rows:
        return
    det = [r["test"]["pooled_detection_rate"] for r in rows]
    fp = [r["test"]["false_per_hour"] for r in rows]
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    ax.scatter(fp, det, c="#E45756", s=36)
    ax.set_xlabel("False triggers per hour")
    ax.set_ylabel("Event detection rate")
    ax.set_title("Continuous trigger, held-out subjects")
    ax.set_ylim(-0.05, 1.05)
    ax.axhline(np.mean(det), color="0.6", ls=":", lw=0.8)
    _save(fig, "trigger_detection_vs_false.png")


def run() -> None:
    log = setup_logging("figures")
    ensure_dirs()
    fig_erp_waveforms()
    fig_tfr()
    fig_channel_bars()
    fig_topomap()
    fig_loso_and_ablation()
    fig_trigger()
    log.info("figures written to %s", C.FIGURES_DIR)


def main() -> None:
    run()


if __name__ == "__main__":
    main()
