"""Slide 7: why the baseline has to be yours.

The single idea: two people have different peak-to-peak ranges, so the SAME raw
reading is unusual for one and ordinary for the other. Both panels share one
y-scale, otherwise the comparison would be a lie.
"""
import numpy as np
from manim import *

# light palette, matching the deck (PRESENTATION-HANDOFF.md section 3)
BG     = "#f3efe5"
INK    = "#1a1917"
BODY   = "#4e4a42"
MUTE   = "#6e685c"
BRASS  = "#7a6430"
CRIT   = "#a44b3c"
OKG    = "#46683f"
COOLA  = "#2f6d8e"     # wearer A
VIOLB  = "#6e5a85"     # wearer B
PANEL  = "#e9e3d5"

SANS  = "URW Gothic"
DISP  = "Poppins"

config.background_color = BG

READING = 3.0            # the raw value that arrives for both people
A_LO, A_HI = 0.62, 1.42  # wearer A's resting floor and ceiling
B_LO, B_HI = 0.40, 3.40  # wearer B's


def disp(s, size=40, color=INK):
    return Text(s, font=DISP, font_size=size, color=color, weight=MEDIUM)


def lab(s, size=24, color=BODY):
    return Text(s, font=SANS, font_size=max(size, 20), color=color)


def resting_trace(ax, lo, hi, n=340, seed=0, calm=True):
    """A baseline wobble that stays inside [lo, hi] and touches both ends."""
    r = np.random.default_rng(seed)
    t = np.linspace(0, 1, n)
    w = (0.55 * np.sin(t * 34 + seed) + 0.30 * np.sin(t * 71 + seed * 2)
         + 0.18 * np.sin(t * 131 + seed) + 0.22 * r.standard_normal(n))
    w = w / np.max(np.abs(w))                      # normalise to +/-1
    y = (lo + hi) / 2 + w * (hi - lo) / 2          # map onto the person's range
    pts = [ax.c2p(x, v) for x, v in zip(t * 20, y)]
    p = VMobject(stroke_color=COOLA if calm else VIOLB, stroke_width=2.6)
    p.set_points_as_corners(pts)
    return p


def panel(cx, title, color):
    ax = Axes(
        x_range=[0, 20, 5], y_range=[0, 4.0, 1],
        x_length=5.2, y_length=3.4,
        axis_config={"color": MUTE, "stroke_width": 1.4,
                     "include_ticks": True, "font_size": 20, "include_tip": False},
    ).move_to(np.array([cx, -0.35, 0]))
    bg = Rectangle(width=ax.x_length, height=ax.y_length,
                   fill_color=PANEL, fill_opacity=0.55, stroke_width=0)
    bg.move_to(ax.c2p(10, 2.0))
    name = lab(title, 26, color).next_to(ax, UP, buff=0.24)
    return ax, bg, name


class Baseline(Scene):
    def construct(self):
        # ---------------------------------------------------------- title
        eyebrow = Text("CALIBRATION", font=SANS, font_size=22, color=BRASS)
        eyebrow.to_edge(UP, buff=0.40)
        title = disp("Your range is not my range.", 38)
        title.next_to(eyebrow, DOWN, buff=0.24)
        self.play(FadeIn(eyebrow, shift=DOWN * 0.15), run_time=0.5)
        self.play(Write(title), run_time=1.1)

        axA, bgA, nameA = panel(-3.55, "wearer A", COOLA)
        axB, bgB, nameB = panel(+3.55, "wearer B", VIOLB)

        self.play(Create(axA), Create(axB), FadeIn(bgA), FadeIn(bgB),
                  FadeIn(nameA), FadeIn(nameB), run_time=1.1)
        yl = lab("theta / alpha index", 20, MUTE).rotate(PI / 2)
        yl.next_to(axA, LEFT, buff=0.16)
        self.play(FadeIn(yl), run_time=0.4)

        def band(ax, lo, hi, color):
            return (DashedLine(ax.c2p(0, hi), ax.c2p(20, hi), color=color,
                               stroke_width=2, dash_length=0.09),
                    DashedLine(ax.c2p(0, lo), ax.c2p(20, lo), color=color,
                               stroke_width=2, dash_length=0.09))

        def p2p_arrow(ax, lo, hi, color):
            # the measured span itself, drawn just inside the right edge
            return DoubleArrow(ax.c2p(18.6, lo), ax.c2p(18.6, hi), color=color,
                               buff=0, stroke_width=4.5,
                               max_tip_length_to_length_ratio=0.2, tip_length=0.15)

        def readout(ax, value, color):
            # lives BELOW the panel, so nothing ever sits on the trace
            t = lab("peak to peak   " + value, 24, color)
            t.next_to(ax, DOWN, buff=0.30)
            return t

        # ------------------------------------------- A: a narrow resting band
        trA = resting_trace(axA, A_LO, A_HI, seed=3, calm=True)
        self.play(Create(trA), run_time=1.8, rate_func=linear)
        hiA, loA = band(axA, A_LO, A_HI, COOLA)
        self.play(Create(hiA), Create(loA), run_time=0.7)
        arrA = p2p_arrow(axA, A_LO, A_HI, COOLA)
        outA = readout(axA, "0.8", COOLA)
        self.play(GrowFromCenter(arrA), run_time=0.6)
        self.play(FadeIn(outA), run_time=0.45)
        self.wait(0.5)

        # ------------------------------------------- B: a much wider one
        trB = resting_trace(axB, B_LO, B_HI, seed=11, calm=False)
        self.play(Create(trB), run_time=1.8, rate_func=linear)
        hiB, loB = band(axB, B_LO, B_HI, VIOLB)
        self.play(Create(hiB), Create(loB), run_time=0.7)
        arrB = p2p_arrow(axB, B_LO, B_HI, VIOLB)
        outB = readout(axB, "3.0", VIOLB)
        self.play(GrowFromCenter(arrB), run_time=0.6)
        self.play(FadeIn(outB), run_time=0.45)

        # the two spans side by side is the whole argument, so hold on it
        self.play(Indicate(arrA, scale_factor=1.15, color=COOLA),
                  Indicate(arrB, scale_factor=1.15, color=VIOLB), run_time=1.0)
        self.wait(0.8)

        # ------------------------------------------- one reading, both panels
        rdA = Line(axA.c2p(0, READING), axA.c2p(20, READING), color=BRASS, stroke_width=3.4)
        rdB = Line(axB.c2p(0, READING), axB.c2p(20, READING), color=BRASS, stroke_width=3.4)
        # a chip in the gap between the panels: the only place nothing is drawn
        ry = axA.c2p(0, READING)[1]
        chip = RoundedRectangle(width=0.98, height=0.52, corner_radius=0.12,
                                fill_color=BG, fill_opacity=1.0,
                                stroke_color=BRASS, stroke_width=2)
        chip.move_to(np.array([0, ry, 0]))
        tag = lab("3.0", 24, BRASS).move_to(chip.get_center())
        self.play(Create(rdA), Create(rdB), run_time=0.9)
        self.play(FadeIn(chip), FadeIn(tag), run_time=0.45)
        self.wait(0.7)

        # ------------------------------------------- the two verdicts
        vA = lab("far outside A's range", 24, CRIT).next_to(outA, DOWN, buff=0.24)
        vB = lab("inside B's range", 24, OKG).next_to(outB, DOWN, buff=0.24)
        self.play(FadeIn(vA, shift=UP * 0.12), run_time=0.55)
        self.play(FadeIn(vB, shift=UP * 0.12), run_time=0.55)
        self.wait(1.3)

        # ------------------------------------------- punchline
        # the punchline takes the title's place, so it cannot crowd the verdicts
        punch = disp("Same reading. Different meaning.", 38, INK)
        punch.move_to(title.get_center())
        self.play(FadeOut(title, shift=UP * 0.2), run_time=0.45)
        self.play(FadeIn(punch, shift=UP * 0.2), run_time=0.75)
        self.wait(2.2)
