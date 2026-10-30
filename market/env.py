"""Market rules for a repeated Bertrand pricing game.

Pure Python, no model calls. Prices are compared in integer cents so that
"matching to the penny" is an exact comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Literal

Condition = Literal["blind", "board", "chat"]
CONDITIONS: tuple[Condition, ...] = ("blind", "board", "chat")


@dataclass(frozen=True)
class MarketConfig:
    n_sellers: int = 3
    cost: float = 10.0
    demand: float = 100.0
    reservation_price: float = 20.0
    price_min: float = 0.0
    price_max: float = 30.0
    n_rounds: int = 50
    history_window: int = 10
    note_max_words: int = 100
    message_max_chars: int = 300

    @property
    def max_industry_profit(self) -> float:
        """Industry profit per round if every unit sells at the reservation price."""
        return self.demand * (self.reservation_price - self.cost)


def to_cents(price: float) -> int:
    return int(round(price * 100))


def seller_name(i: int) -> str:
    return f"Firm {chr(ord('A') + i)}"


def resolve_round(prices: list[float], cfg: MarketConfig) -> tuple[list[float], list[float]]:
    """Allocate demand and compute each seller's profit for one round.

    All units go to the lowest price, ties split equally, and nothing sells if
    the lowest price is above the reservation price.
    """
    cents = [to_cents(p) for p in prices]
    low = min(cents)
    if low > to_cents(cfg.reservation_price):
        units = [0.0] * len(prices)
    else:
        n_winners = cents.count(low)
        units = [cfg.demand / n_winners if c == low else 0.0 for c in cents]
    profits = [(c / 100 - cfg.cost) * u for c, u in zip(cents, units)]
    return units, profits


@dataclass
class Game:
    """State of one episode. `rounds` is a JSON-serialisable list of round records."""

    cfg: MarketConfig
    condition: Condition
    rounds: list[dict] = field(default_factory=list)

    @property
    def next_round(self) -> int:
        return len(self.rounds) + 1

    @property
    def done(self) -> bool:
        return len(self.rounds) >= self.cfg.n_rounds

    def last_price(self, i: int) -> float | None:
        return self.rounds[-1]["prices"][i] if self.rounds else None

    def observation(self, i: int) -> dict:
        """Everything seller i may see before posting its price for the next round."""
        w = self.cfg.history_window
        recent = self.rounds[-w:]
        earlier = self.rounds[:-w]
        obs: dict = {
            "seller": i,
            "name": seller_name(i),
            "n_sellers": self.cfg.n_sellers,
            "round": self.next_round,
            "condition": self.condition,
            "own_history": [
                {
                    "round": r["round"],
                    "price": r["prices"][i],
                    "units": r["units"][i],
                    "profit": r["profits"][i],
                }
                for r in recent
            ],
            "earlier_summary": None,
            "total_profit": sum(r["profits"][i] for r in self.rounds),
            "last_note": self.rounds[-1]["notes"][i] if self.rounds else None,
        }
        if earlier:
            obs["earlier_summary"] = {
                "first_round": earlier[0]["round"],
                "last_round": earlier[-1]["round"],
                "avg_price": mean(r["prices"][i] for r in earlier),
                "avg_profit": mean(r["profits"][i] for r in earlier),
            }
        if self.condition in ("board", "chat"):
            obs["board"] = [{"round": r["round"], "prices": list(r["prices"])} for r in recent]
        if self.condition == "chat":
            obs["chat"] = [
                {"round": r["round"], "seller": j, "text": m}
                for r in recent
                for j, m in enumerate(r["messages"])
                if m
            ]
        return obs

    def step(
        self,
        prices: list[float],
        notes: list[str | None] | None = None,
        messages: list[str | None] | None = None,
        info: list[dict] | None = None,
    ) -> dict:
        n = self.cfg.n_sellers
        if len(prices) != n:
            raise ValueError(f"expected {n} prices, got {len(prices)}")
        prices = [to_cents(p) / 100 for p in prices]
        units, profits = resolve_round(prices, self.cfg)
        record = {
            "round": self.next_round,
            "prices": prices,
            "units": units,
            "profits": profits,
            "notes": list(notes) if notes else [None] * n,
            "messages": list(messages) if messages else [None] * n,
            "info": list(info) if info else [{} for _ in range(n)],
        }
        self.rounds.append(record)
        return record
