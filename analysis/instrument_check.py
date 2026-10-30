"""Known-answer check: run scripted mechanisms through the game and the metrics.

Usage: python -m analysis.instrument_check
"""

from __future__ import annotations

from analysis.metrics import episode_metrics
from market.defector import ScriptedSeller
from market.env import MarketConfig
from market.policies import Coordinator, FocalPrice, Undercutter, simulate

MECHANISMS = {
    "competitive": Undercutter,
    "conformity": FocalPrice,
    "coordination": Coordinator,
}


def passive_rows(cfg: MarketConfig) -> list[dict]:
    rows = []
    for mech, cls in MECHANISMS.items():
        for condition in ("blind", "board"):
            rounds = simulate([cls() for _ in range(cfg.n_sellers)], cfg, condition)
            m = episode_metrics(rounds, cfg)["steady"]
            rows.append({"mechanism": mech, "condition": condition, **m})
    return rows


def defector_rows(cfg: MarketConfig) -> list[dict]:
    rows = []
    for mech, cls in MECHANISMS.items():
        for condition in ("blind", "board"):
            for arm in ("defect", "placebo"):
                script = ScriptedSeller(seat=2, defect=arm == "defect")
                rounds = simulate([cls(), cls(), None], cfg, condition, script=script)
                ev = episode_metrics(rounds, cfg, seats=[0, 1], event_round=script.defect_round)["event"]
                rows.append({"mechanism": mech, "condition": condition, "arm": arm, **ev})
    return rows


def plot(cfg: MarketConfig, path: str) -> None:
    """Scripted mechanisms: identical before the probe, different after it."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mechanisms = {
        "conformity (always 19.99)": FocalPrice,
        "coordination (match cuts, then recover)": Coordinator,
        "undercutting (start high, undercut by a cent)": lambda: Undercutter(opening=20.0, step=0.01),
    }
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for (label, make), color in zip(mechanisms.items(), ("#7f7f7f", "#1f77b4", "#d62728")):
        script = ScriptedSeller(seat=2, defect=True)
        rounds = simulate([make(), make(), None], cfg, "board", script=script)
        ax.plot(range(1, cfg.n_rounds + 1), [r["prices"][0] for r in rounds], color=color, lw=2, label=label)
    ax.axvline(30, color="k", ls=":", lw=0.8)
    ax.annotate("probe: scripted seller\nposts 11 once", xy=(30, 11.2), xytext=(32, 12.2), fontsize=8)
    ax.set_xlabel("round")
    ax.set_ylabel("price of one scripted seller")
    ax.set_ylim(10, 20.5)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title("Same high prices before round 30, different responses after it", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    import sys

    cfg = MarketConfig()
    if "--figure" in sys.argv:
        plot(cfg, sys.argv[sys.argv.index("--figure") + 1])
        return
    print("Passive metrics, rounds 11-50 (3 scripted sellers)\n")
    print("| mechanism | condition | collusion index | exact-match rate | price CV |")
    print("|---|---|---|---|---|")
    for r in passive_rows(cfg):
        print(f"| {r['mechanism']} | {r['condition']} | {r['collusion_index']:.2f} | {r['exact_match_rate']:.2f} | {r['price_cv']:.3f} |")
    print("\nDefector test, rounds 31-40 (2 scripted sellers + defector)\n")
    print("| mechanism | condition | arm | price at round 29 | depth of drop | rounds depressed |")
    print("|---|---|---|---|---|---|")
    for r in defector_rows(cfg):
        print(f"| {r['mechanism']} | {r['condition']} | {r['arm']} | {r['base_price']:.2f} | {r['depth']:.2f} | {r['rounds_depressed']} |")


if __name__ == "__main__":
    main()
