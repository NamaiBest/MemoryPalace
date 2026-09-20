"""Figures for Final Presentation/. Palette validated with the dataviz validator:
#9a6b10 / #0a6fae / #a83a2a on surface #faf8f1, all six checks pass."""
import json, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#faf8f1"; INK = "#1a1917"; MUTED = "#6e685c"; GRID = "#e3ded1"
GOLD, BLUE, RED = "#9a6b10", "#0a6fae", "#a83a2a"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "text.color": INK,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": GRID, "font.size": 11,
})

def strip(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRID); ax.spines["bottom"].set_color(GRID)

# ---------------------------------------------------------------- figure 1
g = json.load(open("/tmp/gated.json"))
per, keep, ORDER, SHORT = g["per"], g["keep"], g["order"], g["short"]
means = [(SHORT[k], statistics.mean(per[k][r] for r in keep)) for k in ORDER]
means.sort(key=lambda x: x[1])
names = [m[0] for m in means]; vals = [m[1] * 100 for m in means]
# Colour carries the finding: where the electrodes sit, not how many there are.
cols = [RED if "glasses" in n else GOLD for n in names]

fig, ax = plt.subplots(figsize=(9.5, 5.2))
bars = ax.barh(names, vals, color=cols, height=0.62)
for b, v in zip(bars, vals):
    ax.text(v + 0.7, b.get_y() + b.get_height() / 2, f"{v:.1f}%",
            va="center", fontsize=10.5, color=INK)
ax.axvline(50, color=MUTED, lw=1, ls=(0, (4, 4)))
ax.text(50.5, -0.85, "chance", fontsize=9.5, color=MUTED)
ax.set_xlim(45, 90); ax.set_xlabel("Within-subject AUC, mean over 45 recordings")
ax.set_title("Where the electrodes sit beats how many there are",
             fontsize=14, color=INK, pad=14, loc="left")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); strip(ax)
handles = [plt.Rectangle((0,0),1,1,color=GOLD), plt.Rectangle((0,0),1,1,color=RED)]
ax.legend(handles, ["Scalp positions", "Glasses-reachable positions"],
          frameon=False, loc="lower right", fontsize=10)
fig.tight_layout(); fig.savefig("Final Presentation/figures/electrodes.png", dpi=200)
print("wrote electrodes.png")

# ---------------------------------------------------------------- figure 2
r = json.loads(open("eeg-state-detection/outputs/backtest_state/report.json").read())
rows = []
for pid, p in r["participants"].items():
    for s in p["sessions"]:
        m = s["models"].get("smoothed") or s["models"]["power"]
        rows.append((f"{pid}-s{s['session']}", m["out_of_sample"]["auroc"] * 100,
                     m["null"]["auroc"]["interval_95"][1] * 100,
                     m["null"]["auroc"]["probability_at_least_observed"]))
rows.sort(key=lambda x: x[1])
labels = [x[0] for x in rows]
fig, ax = plt.subplots(figsize=(9.5, 6))
for i, (lab, a, hi, pv) in enumerate(rows):
    ax.plot([0, hi], [i, i], color=GRID, lw=7, solid_capstyle="butt", zorder=1)
    ax.plot(hi, i, marker="|", color=MUTED, ms=11, mew=1.6, zorder=2)
    ax.plot(a, i, "o", color=BLUE if pv <= 0.05 else MUTED, ms=9,
            markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
    ax.text(a + 1.4, i, f"{a:.0f}%", va="center", fontsize=9.5,
            color=INK if pv <= 0.05 else MUTED)
ax.set_yticks(range(len(rows))); ax.set_yticklabels(labels, fontsize=9.5)
ax.axvline(50, color=MUTED, lw=1, ls=(0, (4, 4)))
ax.set_xlim(40, 108); ax.set_xlabel("Out-of-sample AUROC")
ax.set_title("8 of 15 sessions beat their own time-shift null",
             fontsize=14, color=INK, pad=14, loc="left")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); strip(ax)
h = [plt.Line2D([], [], marker="o", ls="", color=BLUE, ms=9),
     plt.Line2D([], [], marker="o", ls="", color=MUTED, ms=9),
     plt.Line2D([], [], color=GRID, lw=7)]
ax.legend(h, ["Beat the null (p ≤ 0.05)", "Did not", "Null 95% ceiling"],
          frameon=False, loc="lower right", fontsize=10)
fig.tight_layout(); fig.savefig("Final Presentation/figures/sessions.png", dpi=200)
print("wrote sessions.png")

# ---------------------------------------------------------------- figure 3
burst = [("xDAWN covariance\nVP001", 6, 3.00, 6, 0.07),
         ("Zigzag homology\nVP005", 6, 3.63, 7, 0.13),
         ("Amplitude bins\nVP001", 4, 3.00, 6, 0.35),
         ("Amplitude bins\nVP002", 3, 3.15, 6, 0.63),
         ("Amplitude bins\nVP005", 2, 3.63, 7, 0.90)]
fig, ax = plt.subplots(figsize=(9.5, 4.6))
x = range(len(burst))
for i, (lab, got, rnd, hi, pv) in enumerate(burst):
    ax.plot([i, i], [0, hi], color=GRID, lw=13, solid_capstyle="butt", zorder=1)
    ax.plot(i, rnd, marker="_", color=MUTED, ms=22, mew=2.2, zorder=2)
    ax.plot(i, got, "o", color=RED, ms=11, markeredgecolor=SURFACE,
            markeredgewidth=2, zorder=3)
    ax.text(i, got + 0.45, f"{got}/36", ha="center", fontsize=10, color=INK)
    ax.text(i, -1.15, f"p = {pv:.2f}", ha="center", fontsize=9.5, color=MUTED)
ax.set_xticks(list(x)); ax.set_xticklabels([b[0] for b in burst], fontsize=9.5)
ax.set_ylim(-1.8, 11.2); ax.set_ylabel("Events matched, of 36")
ax.set_title("Brief bursts: every method lands inside the random range",
             fontsize=14, color=INK, pad=14, loc="left")
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); strip(ax)
h = [plt.Line2D([], [], marker="o", ls="", color=RED, ms=10),
     plt.Line2D([], [], marker="_", ls="", color=MUTED, ms=16, mew=2.2),
     plt.Line2D([], [], color=GRID, lw=10)]
ax.legend(h, ["Detector", "Random mean", "Random 95% range"],
          frameon=False, loc="upper right", fontsize=10)
fig.tight_layout(); fig.savefig("Final Presentation/figures/bursts.png", dpi=200)
print("wrote bursts.png")
