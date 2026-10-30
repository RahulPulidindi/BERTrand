"""The public release: logs are portable across machines, and the tables and figures rebuild from the committed logs."""

import pandas as pd
import pytest

from analysis import blog_figures, export, style
from analysis.load import PROJECT_ROOT, log_key

LOGS = PROJECT_ROOT / "logs"


def test_log_key_is_machine_independent():
    rel = "logs/run2/ladder/sonnet-minimal/x.eval"
    assert log_key(f"file:///Users/someone/BERTrand/{rel}") == rel
    assert log_key(f"/home/ci/work/BERTrand/{rel}") == rel
    assert log_key(PROJECT_ROOT / rel) == rel
    assert log_key(rel) == rel


@pytest.fixture(scope="module")
def tables(tmp_path_factory):
    """The data/ tables, exported from the logs (data/ itself is generated, not committed)."""
    if not (LOGS / "run4").exists():
        pytest.skip("raw logs not present")
    out = tmp_path_factory.mktemp("data")
    frames = {
        "phase2_prices": export.phase2_prices(LOGS / "run2" / "ladder"),
        "phase3_decisions": export.phase3_decisions(LOGS / "run3" / "replay" / "decisions"),
        "phase3_interviews": export.phase3_interviews(LOGS / "run3" / "replay" / "interviews"),
        **export.phase4_tables(LOGS / "run4"),
    }
    for name, df in frames.items():
        df.to_csv(out / f"{name}.csv", index=False)
    return out


def test_export_has_every_record(tables):
    rows = {p.stem: len(pd.read_csv(p)) for p in tables.glob("*.csv")}
    assert rows["phase3_decisions"] == 3136 and rows["phase3_interviews"] == 1088
    assert rows["phase4_markets"] == 245 and rows["phase4_prices"] == 245 * 20
    assert rows["phase4_replays"] == 1470 and rows["phase4_stated"] == 660


def test_blog_figures_build(tables, tmp_path):
    style.use()
    for make in blog_figures.FIGURES:
        make(tables, tmp_path)
    assert len(list(tmp_path.glob("*.png"))) == len(blog_figures.FIGURES)
