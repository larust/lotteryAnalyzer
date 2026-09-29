from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from scipy.stats import binom, poisson

from lottery_analyzer.diagnostics import diagnose_draw, historical_diagnostics
from lottery_analyzer.historical import load_draws, validate_draw
from lottery_analyzer.rules import ICELANDIC_LOTTO
from scripts.collect_history import NAMES, parse_draw

DATA = Path(__file__).resolve().parents[1] / "data"


def test_complete_current_period_and_overlap_with_manual_observations():
    draws = load_draws(DATA / "current_rules_draws.json")
    assert len(draws) == 71
    assert draws[0].date == date(2025, 5, 24)
    assert draws[-1].date == date(2026, 9, 26)
    assert all((b.date - a.date).days == 7 for a, b in zip(draws, draws[1:], strict=False))
    assert draws[-5:] == load_draws(DATA / "historical_draws.json")
    assert all(
        validate_draw(d, draws[i - 1] if i else None).consistent for i, d in enumerate(draws)
    )
    assert len(historical_diagnostics(draws)) == 426


def test_tested_tier_does_not_set_its_own_sales_estimate():
    draws = load_draws(DATA / "historical_draws.json")
    draw = draws[-1]
    baseline = diagnose_draw(draw, draws[-2])
    for i in range(6):
        winners, amounts = list(draw.winners), list(draw.amounts)
        winners[i] += 100
        amounts[i] += 1000
        changed = replace(draw, winners=tuple(winners), amounts=tuple(amounts))
        # Other tiers may now fail reconciliation, so inspect the exclusion directly.
        result = validate_draw(changed, draws[-2], exclude_tiers=(ICELANDIC_LOTTO.tiers[i].key,))
        assert (result.minimum_rows, result.maximum_rows) == (
            baseline[i].minimum_rows,
            baseline[i].maximum_rows,
        )


@pytest.mark.parametrize("distribution", ["binomial", "poisson"])
def test_envelopes_match_reference_quantiles(distribution):
    draws = load_draws(DATA / "historical_draws.json")
    for d, tier in zip(
        diagnose_draw(draws[0], distribution=distribution), ICELANDIC_LOTTO.tiers, strict=True
    ):
        p = tier.winning_rows(45, 5) / ICELANDIC_LOTTO.combinations
        if distribution == "binomial":
            low, high = binom.ppf(0.025, d.minimum_rows, p), binom.ppf(0.975, d.maximum_rows, p)
        else:
            low, high = (
                poisson.ppf(0.025, d.minimum_rows * p),
                poisson.ppf(0.975, d.maximum_rows * p),
            )
        assert (d.predictive_low, d.predictive_high) == (low, high)
        assert d.expected_low == d.minimum_rows * p
        assert d.expected_high == d.maximum_rows * p


def test_invalid_diagnostics_and_gaps():
    draws = load_draws(DATA / "historical_draws.json")
    for kwargs in ({"coverage": 1}, {"coverage": float("nan")}, {"distribution": "normal"}):
        with pytest.raises(ValueError):
            diagnose_draw(draws[0], **kwargs)
    assert historical_diagnostics((draws[0], draws[2]))[6:] == diagnose_draw(draws[2])
    with pytest.raises(ValueError):
        historical_diagnostics(tuple(reversed(draws)))
    with pytest.raises(ValueError):
        validate_draw(draws[0], exclude_tiers=("typo",))


def test_collector_rejects_stale_dates_and_category_changes():
    expected = date(2025, 5, 24)
    result = {
        "gameId": "lotto",
        "status": "resulted",
        "drawDate": "2025-05-24T00:00:00Z",
        "results": {
            "lottoWins": [{"name": n, "winners": 1, "amount": 100} for n in NAMES],
            "lottoNumbers": ["1", "2", "3", "4", "5"],
            "bonusNumbers": ["6"],
        },
    }
    payload = {"results": [result]}
    assert parse_draw(payload, expected, "source")["winners"] == [1] * 6
    with pytest.raises(ValueError, match="Missing"):
        parse_draw(payload, date(2025, 5, 31), "source")
    result["results"]["lottoWins"][0]["name"] = "old-rule-tier"
    with pytest.raises(ValueError, match="categories"):
        parse_draw(payload, expected, "source")
