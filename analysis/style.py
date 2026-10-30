"""Figure style for the blog and README: a warm background, one accent colour, direct labels, takeaway titles."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BG = "#FAF9F5"
INK = "#141413"
TEXT = "#3D3D3A"
MUTED = "#87867F"
GRID = "#E8E6DC"
BASE = "#B0AEA5"
CLAY = "#D97757"
CLAY_DARK = "#B4532F"
CLAY_LIGHT = "#F0C7B5"
SKY = "#6A9BCC"
OLIVE = "#788C5D"

FONTS = ["Inter", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def use() -> None:
    available = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams.update({
        "font.family": [f for f in FONTS if f in available] or ["DejaVu Sans"],
        "font.size": 10,
        "text.color": TEXT,
        "axes.labelcolor": MUTED,
        "axes.edgecolor": BASE,
        "axes.facecolor": BG,
        "figure.facecolor": BG,
        "savefig.facecolor": BG,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": False,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.major.pad": 6,
        "ytick.major.pad": 6,
        "legend.frameon": False,
        "lines.solid_capstyle": "round",
    })


class Canvas:
    """A figure with a left-aligned takeaway title, a subtitle, a source line, and axes placed in inches."""

    def __init__(self, width: float, height: float, title: str, subtitle: str = "", source: str = ""):
        self.w, self.h = width, height
        self.fig = plt.figure(figsize=(width, height))
        self.pad = 0.38
        self.fig.text(self.pad / width, 1 - 0.5 / height, title, fontsize=15, weight="bold", color=INK, ha="left", va="baseline")
        lines = subtitle.count("\n") + 1 if subtitle else 0
        if subtitle:
            self.fig.text(self.pad / width, 1 - 0.68 / height, subtitle, fontsize=10, color=MUTED, ha="left", va="top", linespacing=1.4)
        if source:
            self.fig.text(self.pad / width, 0.2 / height, source, fontsize=7.5, color=MUTED, ha="left", va="bottom")
        self.top = 0.68 + 0.21 * lines + 0.35

    def axes(self, left: float, bottom: float, width: float | None = None, height: float | None = None, top: float | None = None):
        """Axes at `left`, `bottom` inches; by default they fill the space below the title block."""
        top = self.top if top is None else top
        width = self.w - left - 0.4 if width is None else width
        height = self.h - top - bottom if height is None else height
        return self.fig.add_axes((left / self.w, bottom / self.h, width / self.w, height / self.h))

    def save(self, path: str | Path, dpi: int = 220) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(path, dpi=dpi)
        plt.close(self.fig)


def pct_axis(ax, axis: str = "x", ticks=(0, 0.25, 0.5, 0.75, 1.0)) -> None:
    labels = [f"{t:.0%}" for t in ticks]
    if axis == "x":
        ax.set_xticks(ticks, labels)
    else:
        ax.set_yticks(ticks, labels)
