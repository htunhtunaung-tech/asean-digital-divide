"""Shared chart styling so every figure (and the dashboard) reads as one system.

Colors come from a validated colorblind-safe categorical palette. Only the first
three slots are used together on one chart, which keeps every pair distinguishable
under common forms of color blindness. Identity is never carried by color alone:
highlighted lines are directly labeled.
"""
import matplotlib as mpl

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"          # secondary text, axis labels
GRID = "#e4e3df"
CONTEXT = "#c9c8c1"        # gray for "all other countries" context lines

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # blue, orange, aqua, yellow

# Sequential (one hue, light -> dark) and diverging (blue <-> gray <-> red)
SEQUENTIAL = ["#f0efec", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f2a3a2", "#e34948", "#a8302f"]


def apply() -> None:
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "lines.linewidth": 2,
        "font.family": "DejaVu Sans",
        "legend.frameon": False,
        "legend.fontsize": 9,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
    })
