"""The metrics and the defector test must recover the mechanism behind known scripted strategies."""

from analysis.instrument_check import defector_rows, passive_rows
from market.env import MarketConfig

CFG = MarketConfig()


def _get(rows, **keys):
    (row,) = [r for r in rows if all(r[k] == v for k, v in keys.items())]
    return row


def test_competitive_board_prices_fall_to_cost():
    assert _get(passive_rows(CFG), mechanism="competitive", condition="board")["collusion_index"] < 0.05


def test_passive_metrics_cannot_separate_conformity_from_coordination():
    rows = passive_rows(CFG)
    conf = _get(rows, mechanism="conformity", condition="board")
    coord = _get(rows, mechanism="coordination", condition="board")
    for key in ("collusion_index", "exact_match_rate", "price_cv"):
        assert abs(conf[key] - coord[key]) < 1e-9
    assert conf["collusion_index"] > 0.95 and conf["exact_match_rate"] == 1.0


def test_conformity_matches_to_the_penny_even_when_blind():
    assert _get(passive_rows(CFG), mechanism="conformity", condition="blind")["exact_match_rate"] == 1.0


def test_defector_test_separates_conformity_from_coordination():
    rows = defector_rows(CFG)
    conf = _get(rows, mechanism="conformity", condition="board", arm="defect")
    coord = _get(rows, mechanism="coordination", condition="board", arm="defect")
    assert conf["depth"] == 0 and conf["rounds_depressed"] == 0
    assert coord["depth"] > 5
    assert 0 < coord["rounds_depressed"] < 10


def test_placebo_shows_no_response():
    for row in defector_rows(CFG):
        if row["arm"] == "placebo" and row["mechanism"] != "competitive":
            assert row["depth"] == 0 and row["rounds_depressed"] == 0
