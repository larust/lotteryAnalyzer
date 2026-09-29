from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from lottery_analyzer.historical import load_draws, validate_draw
from lottery_analyzer.payouts import payout_per_winner, tier_pool
from lottery_analyzer.rules import ICELANDIC_LOTTO

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "historical_draws.json"


def test_published_september_results_reconcile_with_current_rules():
    draws = load_draws(FIXTURE)
    expected = [
        (476032, 476165),
        (593928, 593928),
        (731725, 731725),
        (890596, 890596),
        (281154, 281154),
    ]
    for i, (draw, counts) in enumerate(zip(draws, expected, strict=True)):
        result = validate_draw(draw, draws[i - 1] if i else None)
        assert result.consistent
        assert (result.minimum_rows, result.maximum_rows) == counts
        assert len(result.checked_tiers) == (6 if i else 4)
    assert validate_draw(draws[0]).skipped_tiers == ("jackpot", "four_bonus")


def test_displayed_jackpot_is_not_silently_treated_as_exact_carryover():
    draws = load_draws(FIXTURE)
    for i in (1, 2):
        assert not validate_draw(draws[i], draws[i - 1], exact_displayed_carryover=True).consistent
        assert validate_draw(draws[i], draws[i - 1]).consistent


def test_one_feasible_unrounded_ledger_reproduces_all_four_september_draws():
    # 43,965,721 is one possible opening carryover inside the published
    # [43,965,720, 43,965,730) display interval; it is NOT an observed balance.
    draws = load_draws(FIXTURE)[1:]
    carry = Decimal("43965721")
    for draw, rows in zip(draws, [593928, 731725, 890596, 281154], strict=True):
        for i, tier in enumerate(ICELANDIC_LOTTO.tiers):
            pool = tier_pool(Decimal(rows), ICELANDIC_LOTTO, tier, carry if i == 0 else Decimal(0))
            assert payout_per_winner(pool, max(1, draw.winners[i]), 10) == draw.amounts[i]
            if i == 0:
                next_carry = pool if draw.winners[i] == 0 else Decimal(0)
        carry = next_carry
    assert carry == 0


def test_inconsistent_payout_is_detected():
    draws = load_draws(FIXTURE)
    changed = list(draws[-1].amounts)
    changed[2] += 1000
    corrupted = replace(draws[-1], amounts=tuple(changed))
    assert not validate_draw(corrupted, draws[-2]).consistent


def test_changed_allocation_does_not_silently_fit():
    draws = load_draws(FIXTURE)
    tiers = list(ICELANDIC_LOTTO.tiers)
    tiers[0] = replace(tiers[0], pool_fraction=0.56)
    tiers[1] = replace(tiers[1], pool_fraction=0.03)
    rules = replace(ICELANDIC_LOTTO, tiers=tuple(tiers))
    assert not validate_draw(draws[-1], draws[-2], rules=rules).consistent


def test_payout_rounding_uses_half_open_intervals():
    assert payout_per_winner(Decimal("99.999"), 2, 10) == 40
    assert payout_per_winner(Decimal("100"), 2, 10) == 50
    with pytest.raises(ValueError):
        payout_per_winner(Decimal(100), 0, 10)


def test_rejects_malformed_or_nonconsecutive_history():
    draws = load_draws(FIXTURE)
    with pytest.raises(ValueError, match="preceding"):
        validate_draw(draws[-1], replace(draws[-2], date=draws[-2].date - timedelta(days=7)))
    with pytest.raises(ValueError, match="every configured"):
        validate_draw(replace(draws[-1], amounts=(10,)))
    with pytest.raises(ValueError, match="multiples"):
        validate_draw(replace(draws[-1], amounts=(11, *draws[-1].amounts[1:])))
    with pytest.raises(ValueError, match="nonnegative integers"):
        validate_draw(replace(draws[-1], winners=(-1, *draws[-1].winners[1:])))
