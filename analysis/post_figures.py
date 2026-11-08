"""Figures for the research post: a company logo and a model name per row, two columns of 0-100% bars, few words.

What each result means goes in the post's text, not in the figure.

    python -m analysis.post_figures --data data --logs logs --out figures/post
"""

from __future__ import annotations

import argparse
import functools
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.transforms import blended_transform_factory
from PIL import Image

from analysis import style
from analysis.addendum import MIN_MOMENTS, copies_by_model, law_split, load_replays, mechanism
from analysis.blog_figures import PHASE4_LABELS
from analysis.style import BASE, CLAY, CLAY_DARK, GRID, INK, MUTED, SKY, TEXT, Canvas

LOGOS = Path(__file__).resolve().parent.parent / "figures" / "logos"
COMPANY = {
    "opus-5.5": "anthropic", "sonnet-5.5": "anthropic", "haiku-5.5": "anthropic", "opus-5": "anthropic",
    "astra": "openai", "sol": "openai", "luna": "openai", "argon": "google-color", "grok-4.7": "xai",
    "deepseek-v4-pro": "deepseek-color", "qwen-3.5": "qwen-color",
}
ROW_IN, GAP_IN, HEAD_IN, BOTTOM_IN, LOGO_IN, RAISE_IN = 0.44, 0.24, 0.58, 0.3, 0.24, 0.14
BAR, COL_GAP = 0.6, 0.34
DARK = {CLAY: CLAY_DARK, SKY: "#3F6E9E", BASE: MUTED}


@functools.cache
def logo(company: str, px: int = 96) -> np.ndarray:
    """The company's logo cropped to its mark and centred on a transparent square, so every logo looks the same size."""
    im = Image.open(LOGOS / f"{company}.png").convert("RGBA")
    im = im.crop(im.getbbox())
    side = max(im.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return np.asarray(square.resize((px, px), Image.LANCZOS))


def chart(path: Path, title: str, subtitle: str, rows: list[dict], cols: tuple[str, str], colours: tuple[str, str],
          bold: tuple[bool, bool] = (False, True), arrow: bool = True, breaks: tuple[int, ...] = ()) -> None:
    """rows: {"model", "a", "b"}. `breaks` are the row indices that start a new group, with a little space before them."""
    ys, y = [], 0.0
    for i in range(len(rows)):
        y += GAP_IN / ROW_IN if i in breaks else 0.0
        ys.append(y)
        y += 1.0
    head = HEAD_IN / ROW_IN
    c = Canvas(8.2, 1.24 - RAISE_IN + HEAD_IN + y * ROW_IN + BOTTOM_IN, title, subtitle)
    ax = c.axes(2.5, BOTTOM_IN, top=c.top - RAISE_IN)
    ax.set_xlim(0, 2 + COL_GAP + 0.25)
    ax.set_ylim(y - 0.5, -0.5 - head)
    ax.axis("off")
    for k, name in enumerate(cols):
        ax.text(k * (1 + COL_GAP), -0.5 - head / 2, name, fontsize=11, weight="bold", color=INK, ha="left", va="center", linespacing=1.25)
    if arrow:
        ax.text(1 + COL_GAP / 2, -0.5 - head / 2, "\u2192", fontsize=16, color=MUTED, ha="center", va="center")
    side = blended_transform_factory(c.fig.transFigure, ax.transData)
    for y_row, r in zip(ys, rows):
        mark = OffsetImage(logo(COMPANY[r["model"]]), zoom=LOGO_IN * 72 / 96)
        ax.add_artist(AnnotationBbox(mark, (c.pad / c.w, y_row), xycoords=side, box_alignment=(0, 0.5), frameon=False, pad=0,
                                     annotation_clip=False))
        ax.text((c.pad + LOGO_IN + 0.14) / c.w, y_row, PHASE4_LABELS[r["model"]], transform=side, fontsize=11, color=TEXT,
                ha="left", va="center")
        for k, key in enumerate(("a", "b")):
            x0, v = k * (1 + COL_GAP), r[key]
            ax.barh(y_row, 1.0, left=x0, height=BAR, color=GRID, alpha=0.6, lw=0, zorder=1)
            ax.barh(y_row, max(v, 0.005), left=x0, height=BAR, color=colours[k], lw=0, zorder=2)
            ax.text(x0 + v + 0.03, y_row, f"{v:.0%}", va="center", ha="left", fontsize=10.5, zorder=3,
                    color=DARK[colours[k]] if bold[k] else MUTED, weight="bold" if bold[k] else "normal")
    c.save(path)


def group_breaks(flags) -> tuple[int, ...]:
    return tuple(i for i in range(1, len(flags)) if flags[i] != flags[i - 1])


def fig_ask(data: Path, out: Path) -> None:
    """Phase 4: says it would join a proposed cartel (stated test) against joins one in the market (explicit arm)."""
    m, s = pd.read_csv(data / "phase4_markets.csv"), pd.read_csv(data / "phase4_stated.csv")
    rows = []
    for model in PHASE4_LABELS:
        said = s[(s.model == model) & (s["item"] == "explicit") & s.answer.isin(["yes", "no"])].answer
        joined = m[(m.model == model) & (m.arm == "explicit")].judge_response == "accepts"
        rows.append({"model": model, "a": (said == "yes").mean(), "b": joined.mean()})
    rows.sort(key=lambda r: (-r["b"], -r["a"]))
    chart(out / "fig1_ask.png", "Asked, AIs refuse cartels. In the market, many join them.", "When a rival proposes a cartel", rows,
          ("Says it would join", "Actually joins"), (BASE, CLAY), breaks=group_breaks([r["b"] > 0 for r in rows]))


def fig_purpose(data: Path, logs: Path, out: Path) -> None:
    m, _ = mechanism(data, logs)
    m = m.sort_values("final")
    rows = [{"model": k, "a": r.future, "b": r.final} for k, r in m.iterrows()]
    chart(out / "fig2_purpose.png", "Frontier AIs collude on purpose", "Share of decisions that keep prices high", rows,
          ("Cheating can be punished", "Cheating cannot be punished"), (BASE, CLAY),
          breaks=group_breaks((m.future - m.final >= 0.5).to_numpy()))


def fig_copies(logs: Path, out: Path) -> None:
    t = copies_by_model(load_replays(logs / "run5" / "copies"))
    t = t[t.n >= 5].sort_values("copies", ascending=False)
    rows = [{"model": k, "a": r.others, "b": r.copies} for k, r in t.iterrows()]
    chart(out / "fig3_copies.png", "AI copies collude even when cheating cannot be punished",
          "Share of decisions that keep prices high, in the final round", rows,
          ("Rivals are other AIs", "Rivals are its copies"), (BASE, CLAY),
          breaks=group_breaks(((t.copies - t.others >= 0.1) & (t.p < 0.05)).to_numpy()))


def fig_warnings(logs: Path, out: Path) -> None:
    t = law_split(load_replays(logs / "run5" / "law"))
    t = t[t.n_law >= MIN_MOMENTS].sort_values(["claim_law", "dropped_law"], ascending=[False, True])
    rows = [{"model": k, "a": r.claim_law, "b": r.dropped_law} for k, r in t.iterrows()]
    chart(out / "fig4_warnings.png", "Warnings change what AIs say, not what they do", "After being told that price-fixing is illegal",
          rows, ("Keeps colluding,\nsays it complies", "Stops colluding"), (CLAY, SKY), bold=(True, True), arrow=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--out", default="figures/post")
    args = ap.parse_args()
    data, logs, out = Path(args.data), Path(args.logs), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    style.use()
    fig_ask(data, out)
    fig_purpose(data, logs, out)
    fig_copies(logs, out)
    fig_warnings(logs, out)
    print(f"wrote 4 figures to {out}")


if __name__ == "__main__":
    main()
