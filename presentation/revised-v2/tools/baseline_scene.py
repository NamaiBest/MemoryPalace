"""Slide 7: calibration, told as one event seen by two people.

Both wearers rest quietly, then the same moment of overload arrives. A's
response is small, B's is large. Peak to peak is measured from each person's
own resting level, which is the whole reason calibration has to be personal.
Both panels share one y-scale or the comparison would be meaningless.
"""
import numpy as np
from manim import *

BG     = "#f7f4ec"          # very slightly lighter than before, matches the deck
INK    = "#1a1917"
BODY   = "#4e4a42"
MUTE   = "#6e685c"
BRASS  = "#7a6430"
CRIT   = "#a44b3c"
OKG    = "#46683f"
COOLA  = "#2f6d8e"
VIOLB  = "#6e5a85"
PANEL  = "#ece6d8"
EVENT  = "#e6dcc2"

SANS, DISP = "URW Gothic", "Poppins"
config.background_color = BG

REST      = 1.00            # both wearers idle here
A_PEAK    = 1.90            # wearer A's response to the event
B_PEAK    = 3.40            # wearer B's response to the same event
EV_C, EV_W = 15.2, 1.5      # where the event sits on the x axis, and its width


def disp(s, size=38, color=INK):
    return Text(s, font=DISP, font_size=size, color=color, weight=MEDIUM)


def lab(s, size=24, color=BODY):
    return Text(s, font=SANS, font_size=max(size, 20), color=color)


def trace(ax, peak, color, seed=0, x0=0.0, x1=20.0, n=260):
    """A segment of the signal: quiet at REST, with one bump at the event."""
    r = np.random.default_rng(seed)
    x = np.linspace(x0, x1, n)
    y = REST + 0.035 * r.standard_normal(n) + 0.02 * np.sin(x * 7 + seed)
    y = y + (peak - REST) * np.exp(-0.5 * ((x - EV_C) / (EV_W * 0.42)) ** 2)
    p = VMobject(stroke_color=color, stroke_width=3.0)
    p.set_points_as_corners([ax.c2p(a, b) for a, b in zip(x, y)])
    return p


def panel(cx, title, color):
    ax = Axes(
        x_range=[0, 20, 5], y_range=[0, 4.0, 1],
        x_length=5.2, y_length=3.4,
        axis_config={"color": MUTE, "stroke_width": 1.4,
                     "include_ticks": True, "font_size": 20, "include_tip": False},
    ).move_to(np.array([cx, -0.35, 0]))
    bg = Rectangle(width=ax.x_length, height=ax.y_length,
                   fill_color=PANEL, fill_opacity=0.5, stroke_width=0)
    bg.move_to(ax.c2p(10, 2.0))
    name = lab(title, 26, color).next_to(ax, UP, buff=0.24)
    return ax, bg, name


class Baseline(Scene):
    def construct(self):
        eyebrow = Text("CALIBRATION", font=SANS, font_size=22, color=BRASS)
        eyebrow.to_edge(UP, buff=0.40)
        title = disp("One event. Two different brains.", 38)
        title.next_to(eyebrow, DOWN, buff=0.24)
        self.play(FadeIn(eyebrow, shift=DOWN * 0.15), run_time=0.5)
        self.play(Write(title), run_time=1.0)

        axA, bgA, nameA = panel(-3.55, "wearer A", COOLA)
        axB, bgB, nameB = panel(+3.55, "wearer B", VIOLB)
        self.play(Create(axA), Create(axB), FadeIn(bgA), FadeIn(bgB),
                  FadeIn(nameA), FadeIn(nameB), run_time=1.0)
        yl = lab("theta / alpha index", 20, MUTE).rotate(PI / 2)
        yl.next_to(axA, LEFT, buff=0.16)
        self.play(FadeIn(yl), run_time=0.4)

        # ---------- the event band, added now so the trace draws over it ----
        def evband(ax):
            lo, hi = ax.c2p(EV_C - EV_W, 0), ax.c2p(EV_C + EV_W, 4.0)
            return Rectangle(width=abs(hi[0] - lo[0]), height=abs(hi[1] - lo[1]),
                             fill_color=EVENT, fill_opacity=0,
                             stroke_color=BRASS, stroke_width=0
                             ).move_to(ax.c2p(EV_C, 2.0))

        bandA, bandB = evband(axA), evband(axB)
        self.add(bandA, bandB)          # behind everything drawn after this

        # ---------- both at rest, no cognitive load ------------------------
        SPLIT = 13.0
        qA = trace(axA, A_PEAK, COOLA, seed=3, x1=SPLIT)
        qB = trace(axB, B_PEAK, VIOLB, seed=9, x1=SPLIT)
        self.play(Create(qA), Create(qB), run_time=2.4, rate_func=linear)

        restNote = lab("resting, no cognitive load", 22, MUTE)
        restNote.move_to(np.array([0, axA.c2p(0, REST)[1] - 0.72, 0]))
        self.play(FadeIn(restNote), run_time=0.5)
        self.wait(0.8)
        self.play(FadeOut(restNote), run_time=0.35)

        # ---------- the same moment of overload arrives --------------------
        evTag = lab("the same moment arrives for both", 22, BRASS)
        evTag.move_to(np.array([0, 2.28, 0]))
        self.play(bandA.animate.set_fill(opacity=0.9).set_stroke(width=1.2),
                  bandB.animate.set_fill(opacity=0.9).set_stroke(width=1.2),
                  FadeIn(evTag), run_time=0.8)

        eA = trace(axA, A_PEAK, COOLA, seed=3, x0=SPLIT)
        eB = trace(axB, B_PEAK, VIOLB, seed=9, x0=SPLIT)
        self.play(Create(eA), Create(eB), run_time=2.2, rate_func=linear)
        self.wait(0.7)

        # ---------- measure each response from its own resting level ------
        def measure(ax, peak, color, value):
            base = DashedLine(ax.c2p(0, REST), ax.c2p(20, REST), color=color,
                              stroke_width=2, dash_length=0.09)
            top = DashedLine(ax.c2p(0, peak), ax.c2p(20, peak), color=color,
                             stroke_width=2, dash_length=0.09)
            arr = DoubleArrow(ax.c2p(18.7, REST), ax.c2p(18.7, peak), color=color,
                              buff=0, stroke_width=4.5,
                              max_tip_length_to_length_ratio=0.22, tip_length=0.14)
            out = lab("peak to peak   " + value, 24, color).next_to(ax, DOWN, buff=0.30)
            return base, top, arr, out

        bA, tA, arrA, outA = measure(axA, A_PEAK, COOLA, "0.9")
        bB, tB, arrB, outB = measure(axB, B_PEAK, VIOLB, "2.4")

        self.play(Create(bA), Create(bB), run_time=0.6)
        self.play(Create(tA), Create(tB), run_time=0.6)
        self.play(GrowFromCenter(arrA), GrowFromCenter(arrB), run_time=0.8)
        self.play(FadeIn(outA), FadeIn(outB), run_time=0.5)
        self.play(Indicate(arrA, scale_factor=1.15, color=COOLA),
                  Indicate(arrB, scale_factor=1.15, color=VIOLB), run_time=1.0)
        self.wait(0.9)

        # ---------- the conclusion ----------------------------------------
        vA = lab("small response", 24, COOLA).next_to(outA, DOWN, buff=0.24)
        vB = lab("nearly three times larger", 24, VIOLB).next_to(outB, DOWN, buff=0.24)
        self.play(FadeIn(vA, shift=UP * 0.1), FadeIn(vB, shift=UP * 0.1), run_time=0.7)
        self.wait(1.0)

        punch = disp("So the threshold has to be yours.", 38, INK)
        punch.move_to(title.get_center())
        self.play(FadeOut(title, shift=UP * 0.2), run_time=0.45)
        self.play(FadeIn(punch, shift=UP * 0.2), run_time=0.75)
        self.wait(2.2)
