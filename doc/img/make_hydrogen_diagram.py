"""Schematic of the hydrogen subsystem, for doc/img/HydrogenSubsystem.png.

Colours are Okabe-Ito, so the three carriers stay distinct under the common colour deficiencies.
Every arrow starts and ends on a box edge; the boiler routes to heat as an elbow round the right.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ELEC, H2, HEAT, GREY, BAL = "#0072B2", "#009E73", "#D55E00", "#666666", "#F4F4F4"
PAD = 0.45

fig, ax = plt.subplots(figsize=(9.6, 5.8))
ax.set_xlim(0, 112); ax.set_ylim(0, 74); ax.axis("off")

def band(y, h, colour, title, sub):
    ax.add_patch(FancyBboxPatch((2, y), 100, h, boxstyle=f"round,pad={PAD}",
                                linewidth=1.6, edgecolor=colour, facecolor=BAL))
    ax.text(5.5, y + h/2 + 1.3, title, fontsize=10, color=colour, va="center", weight="bold")
    ax.text(5.5, y + h/2 - 2.2, sub, fontsize=6.6, color=GREY, style="italic", va="center")

def box(x, y, w, h, label, sub, colour):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={PAD}",
                                linewidth=1.3, edgecolor=colour, facecolor="white"))
    ax.text(x + w/2, y + h/2 + 1.6, label, ha="center", va="center", fontsize=9)
    ax.text(x + w/2, y + h/2 - 2.4, sub, ha="center", va="center", fontsize=5.8,
            style="italic", color=GREY)

def arrow(x, y1, y2, colour, label=None, side=1, dashed=False, both=False):
    """Vertical, from edge to edge: y1 and y2 are the box edges, padding included."""
    y1 += PAD if y2 > y1 else -PAD
    y2 -= PAD if y2 > y1 else -PAD
    ax.add_patch(FancyArrowPatch((x, y1), (x, y2), mutation_scale=10, linewidth=1.3,
                                 arrowstyle="<|-|>" if both else "-|>",
                                 color=colour, linestyle="--" if dashed else "-"))
    if label:
        ax.text(x + 1.5*side, (y1 + y2)/2, label, fontsize=6.3, color=colour,
                ha="left" if side > 0 else "right", va="center")

def elbow(pts, colour, label=None):
    """Polyline with the arrowhead on the final segment."""
    for a, b in zip(pts, pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=colour, lw=1.3, solid_capstyle="round")
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=10,
                                 linewidth=1.3, color=colour))
    if label:
        ax.text(pts[1][0] + 1.5, (pts[1][1] + pts[2][1])/2, label, fontsize=6.3,
                color=colour, va="center")

band(58, 8, ELEC, "electricity", "always built")
band(31, 8, H2,   "hydrogen", "built if the case has any hydrogen")
band(2,  7, HEAT, "heat", "built if the case has heat")

XS, W, H = (8, 32, 56, 80), 20, 9
box(XS[0], 44, W, H, "electrolyser", "power to H$_2$", ELEC)
box(XS[1], 44, W, H, "reformer",     "gas to H$_2$, or import", H2)
box(XS[2], 44, W, H, "turbine",      "H$_2$ to power", H2)
box(XS[3], 44, W, H, "boiler",       "H$_2$ to heat",  H2)

arrow(18, 58, 53, ELEC, "takes power")            # grid  -> electrolyser
arrow(18, 44, 39, H2,   "makes H$_2$")            # electrolyser -> balance
arrow(42, 44, 39, H2,   "makes H$_2$")            # reformer -> balance
arrow(66, 39, 44, H2,   "burns H$_2$")             # balance -> turbine
arrow(66, 53, 58, ELEC, "gives power")            # turbine -> grid
arrow(90, 39, 44, H2,   "burns H$_2$")             # balance -> boiler
elbow([(100 + PAD, 48.5), (107, 48.5), (107, 5.5), (102 + PAD, 5.5)], HEAT, "heat")

box(XS[0], 17, W, H, "store",    "holds H$_2$ between hours", H2)
box(XS[1], 17, W, H, "demand",   "industrial H$_2$ to serve", H2)
box(XS[2], 17, W, H, "unserved / excess", "priced as a penalty", GREY)
box(XS[3], 17, W, H, "pipeline", "moves H$_2$ between nodes", H2)

arrow(14, 31, 26, H2, "fill", side=-1)
arrow(22, 26, 31, H2, "empty")
arrow(42, 31, 26, H2, "serves")
arrow(66, 31, 26, GREY, "too little, too much", dashed=True, both=True)
arrow(90, 31, 26, H2, "to and from", dashed=True, both=True)

ax.text(56, 71, "Hydrogen subsystem in openTEPES", ha="center", fontsize=12, weight="bold")
ax.text(56, 67.6, "Hydrogen is the only carrier with units that burn it. Leave this balance out and their fuel costs nothing.",
        ha="center", fontsize=7.2, style="italic", color=GREY)
fig.savefig("doc/img/HydrogenSubsystem.png", dpi=200, bbox_inches="tight")
print("wrote doc/img/HydrogenSubsystem.png")
