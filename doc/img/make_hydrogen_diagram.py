"""Schematic of the hydrogen subsystem, for doc/img/HydrogenSubsystem.png."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ELEC, H2, HEAT, GREY, BAL = "#2E6DA4", "#C0504D", "#E8A33D", "#666666", "#F4F4F4"
fig, ax = plt.subplots(figsize=(10.0, 6.4))
ax.set_xlim(0, 110); ax.set_ylim(0, 82); ax.axis("off")

def band(y, h, colour, title, sub):
    ax.add_patch(FancyBboxPatch((2, y), 100, h, boxstyle="round,pad=0.5",
                                linewidth=1.6, edgecolor=colour, facecolor=BAL))
    ax.text(5.5, y + h/2 + 1.4, title, fontsize=10, color=colour, va="center", weight="bold")
    ax.text(5.5, y + h/2 - 2.4, sub, fontsize=6.8, color=GREY, style="italic", va="center")

def box(x, y, w, h, label, sub, colour):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.45",
                                linewidth=1.3, edgecolor=colour, facecolor="white"))
    ax.text(x + w/2, y + h/2 + 1.6, label, ha="center", va="center", fontsize=8.4)
    ax.text(x + w/2, y + h/2 - 2.5, sub, ha="center", va="center", fontsize=5.7,
            style="italic", color=GREY)

def arrow(x1, y1, x2, y2, colour, label=None, side=1, dashed=False):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10,
                                 linewidth=1.25, color=colour, linestyle="--" if dashed else "-"))
    if label:
        ax.text(x1 + 1.6*side, (y1 + y2)/2, label, fontsize=6.2, color=colour,
                ha="left" if side > 0 else "right", va="center")

band(60, 9, ELEC, "electricity balance", "always built")
band(32, 9, H2,   "hydrogen balance   eBalanceH2", "built only with the carrier on")
band(2,  8, HEAT, "heat balance", "built with the heat files")

XS, W = (8, 32, 56, 80), 20
box(XS[0], 45, W, 10, "electrolyser",      "ProductionFunctionH2",        ELEC)
box(XS[1], 45, W, 10, "reformer / import", "MaximumProductionH2",         H2)
box(XS[2], 45, W, 10, "H$_2$ turbine",     "ProductionFunctionH2ToPower", H2)
box(XS[3], 45, W, 10, "H$_2$ boiler",      "ProductionFunctionH2ToHeat",  H2)

arrow(18, 60, 18, 55, ELEC, "electricity")
arrow(18, 45, 18, 41, H2,   "H$_2$")
arrow(42, 45, 42, 41, H2,   "H$_2$")
arrow(66, 41, 66, 45, H2,   "fuel")
arrow(66, 55, 66, 60, ELEC, "electricity")
arrow(90, 41, 90, 45, H2,   "fuel")
ax.plot([100, 106], [50, 50], color=HEAT, lw=1.25)                       # boiler out to the right
ax.add_patch(FancyArrowPatch((106, 50), (106, 10), arrowstyle="-|>", mutation_scale=10,
                             linewidth=1.25, color=HEAT))
ax.text(107.4, 30, "heat", fontsize=6.2, color=HEAT, rotation=90, va="center")

box(XS[0], 17, W, 10, "H$_2$ store",         "MaximumStorageH2",       H2)
box(XS[1], 17, W, 10, "H$_2$ demand",        "oT_Data_DemandHydrogen", H2)
box(XS[2], 17, W, 10, "not served / excess", "HNSCost / H2ExcCost",    GREY)
box(XS[3], 17, W, 10, "H$_2$ pipeline",      "NetworkHydrogen",        H2)

arrow(15, 32, 15, 27, H2, "charge", side=-1)
arrow(21, 27, 21, 32, H2, "discharge")
arrow(42, 32, 42, 27, H2)
arrow(66, 32, 66, 27, GREY, dashed=True)
arrow(90, 32, 90, 27, H2, dashed=True)
ax.text(90, 29.5, "to other nodes", fontsize=6.0, color=H2, ha="right")

ax.text(55, 79.5, "Hydrogen subsystem in openTEPES", ha="center", fontsize=12, weight="bold")
ax.text(55, 75.6, "the hydrogen balance is the only carrier balance holding consumers, so a case omitting it burns fuel for nothing",
        ha="center", fontsize=7.0, style="italic", color=GREY)
fig.savefig("doc/img/HydrogenSubsystem.png", dpi=200, bbox_inches="tight")
print("wrote doc/img/HydrogenSubsystem.png")
