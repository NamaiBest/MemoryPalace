"""Two simple figures for Final Presentation/. Palette validated with the dataviz
checker (#9a6b10 / #0a6fae / #a83a2a on #faf8f1): all six checks pass."""
import json, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE, INK, MUTED, GRID = "#faf8f1", "#1a1917", "#6e685c", "#e3ded1"
GOLD, BLUE, RED = "#9a6b10", "#0a6fae", "#a83a2a"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "savefig.facecolor": SURFACE, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "font.size": 12})

def bare(ax):
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(left=False)

# ---- 1. electrodes -------------------------------------------------------
n38 = json.load(open("/tmp/n38.json"))
rows = sorted(n38["rows"], key=lambda r: r["mean"])
fig, ax = plt.subplots(figsize=(9, 4.8))
cols = [RED if r["glasses"] else GOLD for r in rows]
bars = ax.barh([r["montage"] for r in rows], [r["mean"] for r in rows],
               color=cols, height=0.6)
for b, r in zip(bars, rows):
    ax.text(r["mean"] + 0.8, b.get_y() + b.get_height()/2, f"{r['mean']:.0f}%",
            va="center", fontsize=12, color=INK, fontweight="medium")
ax.axvline(50, color=MUTED, lw=1, ls=(0, (3, 3)))
ax.text(50.6, len(rows) - 0.4, "chance", fontsize=10, color=MUTED)
ax.set_xlim(45, 92); ax.set_xticks([50, 60, 70, 80, 90])
ax.set_xlabel("Accuracy at spotting a surprise (AUC)")
ax.set_title("Fewer electrodes costs little. Moving them to glasses costs a lot.",
             fontsize=14, pad=16, loc="left")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); bare(ax)
fig.tight_layout(); fig.savefig("Final Presentation/figures/electrodes.png", dpi=200)
print("electrodes.png")

# ---- 2. participants -----------------------------------------------------
r = json.loads(open("eeg-state-detection/outputs/backtest_state/report.json").read())
pp = []
for pid, p in r["participants"].items():
    a = [(s["models"].get("smoothed") or s["models"]["power"])["out_of_sample"]["auroc"]
         for s in p["sessions"]]
    pp.append((pid, statistics.mean(a) * 100))
pp.sort(key=lambda x: x[1])
fig, ax = plt.subplots(figsize=(9, 3.9))
bars = ax.barh([x[0] for x in pp], [x[1] for x in pp], color=BLUE, height=0.58)
for b, (_, v) in zip(bars, pp):
    ax.text(v + 0.8, b.get_y() + b.get_height()/2, f"{v:.0f}%", va="center",
            fontsize=12, color=INK, fontweight="medium")
ax.axvline(50, color=MUTED, lw=1, ls=(0, (3, 3)))
ax.text(50.6, len(pp) - 0.45, "chance", fontsize=10, color=MUTED)
ax.set_xlim(45, 100); ax.set_xticks([50, 60, 70, 80, 90, 100])
ax.set_xlabel("Accuracy at spotting a focused state (AUC)")
ax.set_title("Every person is different, which is why the model is trained per person",
             fontsize=14, pad=16, loc="left")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); bare(ax)
fig.tight_layout(); fig.savefig("Final Presentation/figures/participants.png", dpi=200)
print("participants.png")
