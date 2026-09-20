"""MemoryPalace — explanatory scenes for the HackMIT deck.

Every number in these scenes is taken from the repository:
  ds006394 preprocessing + counts .... xueqi-validation/RESULTS.md  §1, §3, §4
  detector config (4 s, k=4, z=2.0) .. confusion-detector/src/config.py + README
  overlap / false-alarm table ........ confusion-detector/README.md
"""
import numpy as np
from manim import *

# --- MemoryPalace palette (app/app/globals.css) ---------------------------
BG       = "#0b0b0c"
PANEL    = "#161617"
IVORY    = "#f3efe6"
DIM      = "#9c968b"
MUTE     = "#6d6860"
BRASS    = "#c9b896"
CRIT     = "#c4746a"
WARM     = "#c9a25a"
COOL     = "#8aa3b5"
OKG      = "#8fad8c"
VIOLET   = "#a691b8"

SANS  = "Geist"
MONO  = "Geist Mono"
SERIF = "Instrument Serif"

config.background_color = BG

rng = np.random.default_rng(7)


def eyebrow(s, color=MUTE):
    t = Text(s.upper(), font=MONO, font_size=17, color=color)
    t.set_opacity(0.95)
    return t


def head(s, size=52):
    return Text(s, font=SERIF, font_size=size, color=IVORY)


def body(s, size=25, color=DIM):
    return Text(s, font=SANS, font_size=size, color=color)


def mono(s, size=21, color=BRASS):
    return Text(s, font=MONO, font_size=size, color=color)


def rule(width=11.0, color=IVORY, op=0.16):
    l = Line(LEFT * width / 2, RIGHT * width / 2, color=color, stroke_width=1.2)
    l.set_opacity(op)
    return l


def eeg_trace(n=900, fs=125.0, seed=0, amp=1.0, spike_at=None):
    """A plausible-looking EEG segment: 1/f-ish background + alpha + mains."""
    r = np.random.default_rng(seed)
    t = np.arange(n) / fs
    x = np.zeros(n)
    for f, a in ((2.0, 1.0), (5.5, 0.55), (10.0, 0.75), (18.0, 0.22), (28.0, 0.12)):
        x += a * np.sin(2 * np.pi * f * t + r.uniform(0, 6.28))
    x += 0.35 * r.standard_normal(n)
    x += 0.30 * np.sin(2 * np.pi * 50.0 * t)          # 50 Hz mains
    if spike_at is not None:
        k = int(spike_at * fs)
        w = np.exp(-0.5 * ((np.arange(n) - k) / (0.05 * fs)) ** 2)
        x += 6.0 * w
    return amp * x / np.max(np.abs(x))


def trace_poly(values, width, height, color, sw=1.6, op=1.0):
    n = len(values)
    xs = np.linspace(-width / 2, width / 2, n)
    ys = np.asarray(values) * (height / 2)
    pts = [np.array([x, y, 0.0]) for x, y in zip(xs, ys)]
    p = VMobject(stroke_color=color, stroke_width=sw)
    p.set_points_smoothly(pts) if n < 60 else p.set_points_as_corners(pts)
    p.set_stroke(opacity=op)
    return p


# =========================================================================
# SCENE 1 — where the numbers come from
# =========================================================================
class DataIn(Scene):
    def construct(self):
        eb = eyebrow("OpenNeuro ds006394  ·  CC0", BRASS).to_edge(UP, buff=0.55)
        ttl = head("Sixteen channels, 125 times a second.", 46).next_to(eb, DOWN, buff=0.34)
        self.play(FadeIn(eb, shift=DOWN * 0.2), run_time=0.6)
        self.play(Write(ttl), run_time=1.1)
        rl = rule(10.6).next_to(ttl, DOWN, buff=0.34)
        self.play(FadeIn(rl), run_time=0.5)

        # 16 stacked traces streaming in
        stack = VGroup()
        names = ["Fp1","Fp2","F7","F3","Fz","F4","F8","T7",
                 "C3","Cz","C4","T8","P3","P4","O1","O2"]
        for i, nm in enumerate(names):
            tr = trace_poly(eeg_trace(600, seed=i, spike_at=3.4 if i in (4,9,13,14) else None),
                            width=8.6, height=0.20,
                            color=BRASS if nm in ("Fz","Cz") else IVORY,
                            sw=1.15, op=1.0 if nm in ("Fz","Cz") else 0.42)
            lab = Text(nm, font=MONO, font_size=13,
                       color=BRASS if nm in ("Fz","Cz") else MUTE)
            lab.next_to(tr, LEFT, buff=0.28)
            stack.add(VGroup(tr, lab))
        stack.arrange(DOWN, buff=0.055).move_to(DOWN * 1.05).shift(RIGHT * 0.35)

        self.play(LaggedStart(*[Create(g[0]) for g in stack],
                              lag_ratio=0.045, run_time=2.4))
        self.play(LaggedStart(*[FadeIn(g[1]) for g in stack],
                              lag_ratio=0.03, run_time=0.8))

        cap = mono("33 participants  ·  56 usable recordings  ·  left-earlobe reference",
                   18, DIM).to_edge(DOWN, buff=0.34)
        self.play(FadeIn(cap, shift=UP * 0.15), run_time=0.7)
        self.wait(1.1)

        # --- collapse to the preprocessing chain --------------------------
        self.play(FadeOut(stack), FadeOut(cap), FadeOut(ttl), FadeOut(rl), run_time=0.7)
        ttl2 = head("Then nothing changes again.", 44).next_to(eb, DOWN, buff=0.34)
        sub = body("Every step below is frozen before any model is fit.", 22, MUTE)
        sub.next_to(ttl2, DOWN, buff=0.28)
        self.play(FadeTransform(ttl.copy(), ttl2), FadeIn(sub), run_time=0.9)

        steps = [
            ("÷ 24", "documented OpenBCI GUI v5.0.1 scale error", IVORY),
            ("1 – 40 Hz", "band-pass", IVORY),
            ("50 Hz notch", "mains", IVORY),
            ("−0.2 → +0.8 s", "epoch, baselined on the first 200 ms", IVORY),
            ("peak-to-peak > 150 µV", "epoch rejected", CRIT),
        ]
        rows = VGroup()
        for val, why, col in steps:
            v = mono(val, 24, col)
            w = body(why, 20, MUTE)
            r = VGroup(v, w).arrange(RIGHT, buff=0.42, aligned_edge=DOWN)
            rows.add(r)
        rows.arrange(DOWN, buff=0.46, aligned_edge=LEFT).move_to(DOWN * 0.35)

        spine_x = rows.get_left()[0] - 0.55
        spine = Line(np.array([spine_x, rows.get_top()[1] - 0.08, 0]),
                     np.array([spine_x, rows.get_bottom()[1] + 0.08, 0]),
                     color=MUTE, stroke_width=1.2)
        spine.set_opacity(0.5)
        nodes = VGroup(*[Dot(np.array([spine_x, r.get_center()[1], 0]),
                             radius=0.055,
                             color=CRIT if i == len(rows) - 1 else BRASS)
                         for i, r in enumerate(rows)])

        self.play(Create(spine), run_time=0.5)
        for i, r in enumerate(rows):
            self.play(FadeIn(nodes[i], scale=0.5), FadeIn(r, shift=RIGHT * 0.25),
                      run_time=0.42)

        note = body("This is the only place “peak-to-peak” appears: it throws an epoch away.\n"
                    "It is not how the detector fires.", 20, WARM)
        note.to_edge(DOWN, buff=0.42)
        self.play(FadeIn(note), run_time=0.8)
        self.wait(1.6)

        self.play(FadeOut(VGroup(rows, spine, nodes, note, sub, ttl2)), run_time=0.7)
        out = VGroup(
            mono("1 025", 62, BRASS), body("surprise epochs", 22, DIM),
            mono("5 865", 62, IVORY), body("time-matched controls", 22, DIM),
        )
        left = VGroup(out[0], out[1]).arrange(DOWN, buff=0.18)
        right = VGroup(out[2], out[3]).arrange(DOWN, buff=0.18)
        pair = VGroup(left, right).arrange(RIGHT, buff=2.2).move_to(DOWN * 0.3)
        self.play(FadeIn(pair, shift=UP * 0.25), run_time=1.0)
        cl = body("Labels are the authors’ own trial_type values. Not recoded.", 20, MUTE)
        cl.to_edge(DOWN, buff=0.55)
        self.play(FadeIn(cl), run_time=0.6)
        self.wait(1.8)


# =========================================================================
# SCENE 2 — why calibration is personal
# =========================================================================
class WhyCalibrate(Scene):
    def construct(self):
        eb = eyebrow("Calibration", BRASS).to_edge(UP, buff=0.55)
        ttl = head("The threshold is universal. The baseline is not.", 44)
        ttl.next_to(eb, DOWN, buff=0.32)
        self.play(FadeIn(eb, shift=DOWN * 0.2), run_time=0.5)
        self.play(Write(ttl), run_time=1.2)
        self.wait(0.3)
        self.play(VGroup(eb, ttl).animate.scale(0.92).to_edge(UP, buff=0.42), run_time=0.6)

        ax = Axes(x_range=[0, 20, 5], y_range=[0, 1.35, 0.5],
                  x_length=9.6, y_length=3.0,
                  axis_config={"color": MUTE, "stroke_width": 1.4,
                               "include_ticks": True, "font_size": 18,
                               "tip_length": 0.14},
                  ).move_to(DOWN * 0.35)
        xlab = body("seconds of quiet work", 18, MUTE).next_to(ax, DOWN, buff=0.16)
        ylab = Text("frontal θ/α load index", font=MONO, font_size=16, color=MUTE)
        ylab.rotate(PI / 2).next_to(ax, LEFT, buff=0.22)
        self.play(Create(ax), FadeIn(xlab), FadeIn(ylab), run_time=1.0)

        # --- person A: a tight baseline
        muA, sdA = 0.42, 0.11
        n = 260
        xs = np.linspace(0, 20, n)
        yA = muA + sdA * rng.standard_normal(n)
        curveA = VMobject(stroke_color=COOL, stroke_width=2.0)
        curveA.set_points_as_corners([ax.c2p(x, float(np.clip(y, 0, 1.3)))
                                      for x, y in zip(xs, yA)])
        nameA = mono("wearer A", 20, COOL).next_to(ax, UP, buff=0.18).align_to(ax, LEFT)
        self.play(Create(curveA), FadeIn(nameA), run_time=2.0)

        loA, hiA = max(0.0, muA - 2 * sdA), min(1.3, muA + 2 * sdA)
        bandA = Rectangle(width=ax.x_length,
                          height=abs(ax.c2p(0, hiA)[1] - ax.c2p(0, loA)[1]),
                          fill_color=COOL, fill_opacity=0.14, stroke_width=0)
        bandA.move_to(ax.c2p(10, (loA + hiA) / 2))
        meanA = DashedLine(ax.c2p(0, muA), ax.c2p(20, muA), color=COOL, stroke_width=1.6)
        statA = mono("µ = 0.42   σ = 0.11", 21, COOL)
        statA.next_to(ax.c2p(20, muA), RIGHT, buff=0.24)
        self.play(FadeIn(bandA), Create(meanA), FadeIn(statA), run_time=1.0)
        self.wait(0.6)

        # --- the formula
        z = MathTex(r"z \;=\; \frac{x-\mu}{\sigma}",
                    color=IVORY, font_size=42).to_edge(DOWN, buff=0.28)
        self.play(Write(z), run_time=1.0)
        self.wait(0.7)

        # --- the same raw value arrives
        x_raw = 0.87
        ev = Line(ax.c2p(14.2, 0), ax.c2p(14.2, x_raw), color=BRASS, stroke_width=3.0)
        dot = Dot(ax.c2p(14.2, x_raw), color=BRASS, radius=0.075)
        evlab = mono("x = 0.87", 20, BRASS).next_to(dot, UP, buff=0.16)
        self.play(Create(ev), FadeIn(dot), FadeIn(evlab), run_time=0.8)

        zA = mono("z = +4.1", 30, CRIT).next_to(statA, DOWN, buff=0.30).align_to(statA, LEFT)
        self.play(FadeIn(zA, shift=LEFT * 0.2), run_time=0.7)
        fires = body("fires", 20, CRIT).next_to(zA, DOWN, buff=0.12).align_to(zA, LEFT)
        self.play(FadeIn(fires), run_time=0.4)
        self.wait(1.0)

        # --- person B: same event, wider baseline
        self.play(FadeOut(VGroup(curveA, bandA, meanA, statA, zA, fires, nameA)), run_time=0.6)
        muB, sdB = 0.55, 0.38
        yB = muB + sdB * rng.standard_normal(n)
        curveB = VMobject(stroke_color=VIOLET, stroke_width=2.0)
        curveB.set_points_as_corners([ax.c2p(x, float(np.clip(y, 0, 1.3)))
                                      for x, y in zip(xs, yB)])
        nameB = mono("wearer B", 20, VIOLET).next_to(ax, UP, buff=0.18).align_to(ax, LEFT)
        loB, hiB = max(0.0, muB - 2 * sdB), min(1.3, muB + 2 * sdB)
        bandB = Rectangle(width=ax.x_length,
                          height=abs(ax.c2p(0, hiB)[1] - ax.c2p(0, loB)[1]),
                          fill_color=VIOLET, fill_opacity=0.14, stroke_width=0)
        bandB.move_to(ax.c2p(10, (loB + hiB) / 2))
        meanB = DashedLine(ax.c2p(0, muB), ax.c2p(20, muB), color=VIOLET, stroke_width=1.6)
        statB = mono("µ = 0.55   σ = 0.38", 21, VIOLET)
        statB.next_to(ax.c2p(20, muB), RIGHT, buff=0.24)
        self.play(Create(curveB), FadeIn(nameB), run_time=1.6)
        self.play(FadeIn(bandB), Create(meanB), FadeIn(statB), run_time=0.9)

        zB = mono("z = +0.8", 30, OKG).next_to(statB, DOWN, buff=0.30).align_to(statB, LEFT)
        self.play(FadeIn(zB, shift=LEFT * 0.2), run_time=0.7)
        quiet = body("ordinary", 20, OKG).next_to(zB, DOWN, buff=0.12).align_to(zB, LEFT)
        self.play(FadeIn(quiet), run_time=0.4)
        self.wait(1.2)

        self.play(FadeOut(VGroup(ax, xlab, ylab, curveB, bandB, meanB, statB, zB,
                                 quiet, nameB, ev, dot, evlab, z)), run_time=0.8)

        punch = VGroup(
            head("Identical amplitude.", 42),
            head("Opposite conclusion.", 42),
        ).arrange(DOWN, buff=0.18)
        punch[1].set_color(BRASS)
        self.play(FadeIn(punch[0], shift=UP * 0.2), run_time=0.7)
        self.play(FadeIn(punch[1], shift=UP * 0.2), run_time=0.7)
        sub = body("Spatial filters are tied to electrode positions and impedances, so weights\n"
                   "do not transfer between people, sessions or headsets. Retraining on the\n"
                   "wearer, on the day, is mandatory — which is why we built the product around it.",
                   21, DIM)
        sub.next_to(punch, DOWN, buff=0.55)
        self.play(FadeIn(sub), run_time=1.0)
        self.wait(2.2)


# =========================================================================
# SCENE 3 — four in a row, and why windows must not overlap
# =========================================================================
class Persistence(Scene):
    def construct(self):
        eb = eyebrow("The persistence filter", BRASS).to_edge(UP, buff=0.55)
        ttl = head("One loud window is noise. Four in a row is a state.", 42)
        ttl.next_to(eb, DOWN, buff=0.32)
        self.play(FadeIn(eb, shift=DOWN * 0.2), run_time=0.5)
        self.play(Write(ttl), run_time=1.2)
        self.play(VGroup(eb, ttl).animate.scale(0.9).to_edge(UP, buff=0.42), run_time=0.6)

        # z-score bar stream
        zs = [0.4, 1.1, 2.4, 0.7, -0.3, 0.9, 2.2, 2.6, 2.1, 2.9, 1.4, 0.6, 0.2, 1.0]
        bars = VGroup()
        bw, gap = 0.52, 0.20
        for v in zs:
            h = max(abs(v), 0.05) * 0.62
            col = CRIT if v >= 2.0 else MUTE
            r = Rectangle(width=bw, height=h, fill_color=col, fill_opacity=0.9, stroke_width=0)
            bars.add(r)
        bars.arrange(RIGHT, buff=gap, aligned_edge=DOWN).move_to(DOWN * 0.7)
        base = Line(bars.get_left() + LEFT * 0.35, bars.get_right() + RIGHT * 0.35,
                    color=MUTE, stroke_width=1.2).align_to(bars, DOWN)
        thr_y = bars.get_bottom()[1] + 2.0 * 0.62
        thr = DashedLine(np.array([base.get_left()[0], thr_y, 0]),
                         np.array([base.get_right()[0], thr_y, 0]),
                         color=BRASS, stroke_width=1.6)
        thrlab = mono("z = 2.0", 19, BRASS).next_to(thr, RIGHT, buff=0.18)
        wlab = mono("one bar = one 4-second window", 18, MUTE).next_to(bars, DOWN, buff=0.34)

        self.play(Create(base), run_time=0.4)
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars],
                              lag_ratio=0.10, run_time=2.0))
        self.play(Create(thr), FadeIn(thrlab), FadeIn(wlab), run_time=0.7)
        self.wait(0.5)

        # lone spike rejected
        lone = SurroundingRectangle(bars[2], color=MUTE, stroke_width=1.6, buff=0.10)
        lonelab = body("one window — ignored", 19, MUTE).next_to(lone, UP, buff=0.22)
        self.play(Create(lone), FadeIn(lonelab), run_time=0.7)
        self.wait(0.9)
        self.play(FadeOut(lone), FadeOut(lonelab), run_time=0.4)

        run = SurroundingRectangle(VGroup(*bars[6:10]), color=CRIT, stroke_width=2.0, buff=0.12)
        runlab = body("four consecutive — capture", 20, CRIT).next_to(run, UP, buff=0.22)
        self.play(Create(run), FadeIn(runlab), run_time=0.8)
        self.wait(1.4)

        self.play(FadeOut(VGroup(bars, base, thr, thrlab, wlab, run, runlab)), run_time=0.7)

        # --- the overlap bug ------------------------------------------------
        ttl2 = head("“Four in a row” only counts if the four are independent.", 38)
        ttl2.next_to(eb, DOWN, buff=0.30)
        self.play(FadeTransform(ttl, ttl2), run_time=0.8)

        def window_row(hop_frac, color, label, y):
            g = VGroup()
            span = 7.4
            wlen = 1.55
            for i in range(4):
                r = Rectangle(width=wlen, height=0.40, stroke_color=color,
                              stroke_width=1.6, fill_color=color, fill_opacity=0.16)
                r.move_to(np.array([-span / 2 + wlen / 2 + i * wlen * hop_frac, y, 0]))
                g.add(r)
            lab = mono(label, 19, color).next_to(g, LEFT, buff=0.4)
            lab.align_to(g, DOWN).shift(UP * 0.08)
            return VGroup(g, lab)

        r_over = window_row(0.25, CRIT, "hop 1 s", 0.55)
        r_ind = window_row(1.00, OKG, "hop 4 s", -0.85)
        cap_over = body("75 % shared data — four looks, two of them independent", 19, DIM)
        cap_over.next_to(r_over, DOWN, buff=0.20).align_to(r_over[0], LEFT)
        cap_ind = body("no shared data — four genuinely independent looks", 19, DIM)
        cap_ind.next_to(r_ind, DOWN, buff=0.20).align_to(r_ind[0], LEFT)

        self.play(FadeIn(r_over), FadeIn(cap_over), run_time=0.9)
        self.play(FadeIn(r_ind), FadeIn(cap_ind), run_time=0.9)
        self.wait(1.0)

        fa1 = mono("30.3", 44, CRIT).next_to(r_over, RIGHT, buff=0.75)
        fa1s = body("false alarms / hour", 17, DIM).next_to(fa1, DOWN, buff=0.06)
        fa2 = mono("1.3", 44, OKG).next_to(r_ind, RIGHT, buff=0.75)
        fa2s = body("false alarms / hour", 17, DIM).next_to(fa2, DOWN, buff=0.06)
        VGroup(fa2, fa2s).align_to(VGroup(fa1, fa1s), LEFT)
        self.play(FadeIn(fa1), FadeIn(fa1s), run_time=0.6)
        self.play(FadeIn(fa2), FadeIn(fa2s), run_time=0.6)
        self.wait(0.8)

        punch = body("Same code. Same threshold. 24× fewer false alarms.", 26, BRASS)
        punch.to_edge(DOWN, buff=0.55)
        self.play(FadeIn(punch, shift=UP * 0.2), run_time=0.9)
        self.wait(2.0)
