"""Read Inspect logs into plain episode records for analysis."""

from __future__ import annotations

from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log

from analysis.metrics import episode_metrics
from market.env import MarketConfig

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def log_key(name: str | Path) -> str:
    """A machine-independent name for a log file, e.g. "logs/run2/ladder/sonnet-minimal/<file>.eval".

    Judge and monitor outputs identify markets by (log, sample id). Older outputs store absolute file URIs from the
    machine that ran them, so both sides of every join go through this function.
    """
    path = Path(str(name).removeprefix("file://"))
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        parts = path.parts
        if "logs" in parts:
            last = len(parts) - 1 - parts[::-1].index("logs")
            return Path(*parts[last:]).as_posix()
        return path.as_posix()


def log_paths(log_dir: str | Path) -> list[str]:
    return [info.name for info in list_eval_logs(str(log_dir))]


def load_episodes(paths: list[str | Path]) -> list[dict]:
    """One record per episode. `model` names what was selling: the model, or "mixed" for a mixed market.

    Metrics are recomputed from the raw rounds, so every log is analysed with the current metric code.
    A paired sample becomes two records, its defect and placebo branches, with the same `pair_id`.
    """
    episodes = []
    for path in paths:
        log = read_eval_log(str(path))
        reasoning = (log.eval.task_args or {}).get("reasoning_effort")
        for s in log.samples or []:
            if not s.store or "rounds" not in s.store:
                continue
            usage = {m: u.model_dump() for m, u in (s.model_usage or {}).items()}
            cfg = MarketConfig(**s.store["market_config"])
            md = s.metadata
            seats = s.store["llm_seats"]
            interviews = s.store.get("interview") or {}
            if s.store.get("paired"):
                branches = [("defect", s.store["rounds"]), ("placebo", s.store["rounds_placebo"])]
            else:
                branches = [(md.get("defector", "none"), s.store["rounds"])]
            for k, (arm, rounds) in enumerate(branches):
                episodes.append(
                    {
                        "log": log_key(path),
                        "id": s.id,
                        **md,
                        "defector": arm,
                        "paired": bool(s.store.get("paired")),
                        "pair_id": f"{path}#{s.id}" if s.store.get("paired") else None,
                        "model": md.get("composition") or log.eval.model,
                        "reasoning_effort": reasoning,
                        "seat_models": s.store.get("seat_models"),
                        "rounds": rounds,
                        "cfg": cfg,
                        "llm_seats": seats,
                        "metrics": episode_metrics(
                            rounds, cfg, seats, event_round=md["defect_round"] if arm != "none" else None
                        ),
                        "interview": interviews.get(arm if s.store.get("paired") else "main"),
                        "usage": usage if k == 0 else {},
                        "seconds": s.total_time if k == 0 else 0,
                    }
                )
    return episodes
