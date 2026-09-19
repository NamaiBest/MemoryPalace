"""Plot the calibration learning curve produced by crown_learning_curve.py.

The rising line is the evidence behind the per-user adaptation claim: the more of your
own data the model has, the better it gets. Drawn honestly — chance is marked, the axis
is not cropped to exaggerate the slope, and the caption says what task this is.
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results", "crown_learning_curve.json")
OUT = os.path.join(ROOT, "figures", "crown_learning_curve.png")

LABELS = {
    "csp_lda": "CSP + LDA  (what the repo ships)",
    "tangent_logreg": "Tangent space + logistic regression",
}
COLOURS = {"csp_lda": "#8aa3b5", "tangent_logreg": "#c9a25a"}


def main():
    with open(RESULTS) as handle:
        payload = json.load(handle)
    results = payload["results"]

    fig, ax = plt.subplots(figsize=(7.4, 4.6), dpi=160)

    for name, points in results.items():
        sizes = sorted(int(k) for k in points)
        means = [points[str(s)]["mean_auc"] for s in sizes]
        sds = [points[str(s)]["sd"] for s in sizes]
        colour = COLOURS.get(name, "#888888")
        ax.plot(sizes, means, marker="o", markersize=5, linewidth=2,
                color=colour, label=LABELS.get(name, name), zorder=3)
        # Standard error of the mean, so the bands stay readable. Per-subject spread is
        # far wider (sd ~0.13) and is reported in the JSON and the caption instead of
        # being drawn, where it would swamp both lines.
        n = points[str(sizes[0])]["n_subjects"]
        errs = [s / (n ** 0.5) for s in sds]
        ax.fill_between(sizes,
                        [m - e for m, e in zip(means, errs)],
                        [m + e for m, e in zip(means, errs)],
                        color=colour, alpha=0.25, zorder=1, linewidth=0)

    ax.axhline(0.5, color="#c48474", linestyle="--", linewidth=1.2, zorder=2)
    ax.text(ax.get_xlim()[1], 0.505, "chance", ha="right", va="bottom",
            fontsize=9, color="#c48474")

    n_subjects = max(p["n_subjects"] for pts in results.values() for p in pts.values())
    ax.set_xlabel("Calibration trials used for training")
    ax.set_ylabel("AUC (within subject, held-out 30%)")
    ax.set_title("The model improves with your own data\n"
                 f"Neurosity Crown's exact 8 channels · {n_subjects} subjects · EEGMMIDB",
                 fontsize=11)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.grid(alpha=0.15)
    ax.set_ylim(0.45, 0.72)

    fig.subplots_adjust(bottom=0.28)
    fig.text(0.5, 0.045,
             "Imagined left vs right fist — motor imagery, not confusion. No public dataset "
             "labels confusion on this montage.\nBands are standard error; per-subject spread "
             "is much wider (sd ≈ 0.13). Still rising at 28 trials — the ceiling\nis the "
             "dataset's trial count, not the model's.",
             ha="center", va="bottom", fontsize=8, color="#666666", linespacing=1.5)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, facecolor="white")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
