from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from itertools import combinations, product
from math import expm1

import numpy as np
import pytest

from lottery_analyzer import (
    ICELANDIC_LOTTO,
    LotteryRules,
    PrizeTier,
    analyze,
    break_even_rollover,
    roi_grid,
    rows_from_jackpot_contribution,
)
from lotteryAnalyzer import breakEven, lotteryROI


def toy_rules(rounding_unit=0.1):
    return LotteryRules(
        name="Exhaustively testable 2/5",
        number_count=5,
        draw_count=2,
        row_price=7.25,
        payout_fraction=0.6,
        tiers=(
            PrizeTier("jackpot", "Two", 2, None, 0.5, True),
            PrizeTier("one_bonus", "One + bonus", 1, True, 0.3, True),
            PrizeTier("one", "One without bonus", 1, False, 0.2),
        ),
        rounding_unit=rounding_unit,
    )


def test_current_rules_and_coverage():
    rules = ICELANDIC_LOTTO
    assert rules.combinations == 1_221_759
    assert rules.coverage_cost == 183_263_850
    assert [t.winning_rows(45, 5) for t in rules.tiers] == [1, 5, 195, 390, 7410, 7410]
    with pytest.raises(FrozenInstanceError):
        rules.row_price = 1


@pytest.mark.parametrize("distribution", ["poisson", "binomial"])
def test_no_other_players_returns_entire_pool(distribution):
    rules = replace(ICELANDIC_LOTTO, rounding_unit=0)
    result = analyze(other_rows=0, rules=rules, distribution=distribution)
    assert result.roi == pytest.approx(-0.55)
    assert result.expected_winnings == pytest.approx(result.cost * 0.45)
    assert result.numerical_error_bound == 0


@pytest.mark.parametrize("rounding", [0, 0.1, 10])
def test_binomial_matches_enumeration_of_every_competing_ticket_pair(rounding):
    """An independent oracle: enumerate 100 ordered purchases, with duplicates."""
    rules = toy_rules(rounding)
    rows = list(combinations(range(5), 2))
    main = {0, 1}
    bonus = 2

    def classify(row):
        matches = len(main.intersection(row))
        if matches == 2:
            return 0
        if matches == 1:
            return 1 if bonus in row else 2
        return None

    own = [sum(classify(row) == tier for row in rows) for tier in range(3)]
    assert own == [1, 2, 4]
    pools = [
        Decimal(12) * Decimal("7.25") * Decimal("0.6") * fraction + carry
        for fraction, carry in zip(
            [Decimal("0.5"), Decimal("0.3"), Decimal("0.2")],
            [Decimal("19.1"), Decimal("3.2"), Decimal(0)],
            strict=True,
        )
    ]
    expected = [Decimal(0)] * 3
    for purchased in product(rows, repeat=2):
        for tier, pool in enumerate(pools):
            rivals = sum(classify(row) == tier for row in purchased)
            per_row = pool / (own[tier] + rivals)
            if rounding:
                unit = Decimal(str(rounding))
                per_row = (per_row // unit) * unit
            expected[tier] += own[tier] * per_row / 100
    result = analyze(
        other_rows=2,
        rules=rules,
        distribution="binomial",
        rollovers={"jackpot": 19.1, "one_bonus": 3.2},
    )
    for actual, reference in zip(result.tiers, expected, strict=True):
        assert actual.expected_winnings == pytest.approx(float(reference), abs=1e-10)


@pytest.mark.parametrize("other_rows", [0, 1e-320, 1e-8, 1_221_759, 24_435_180])
def test_poisson_jackpot_has_no_twenty_winner_cutoff(other_rows):
    rules = replace(ICELANDIC_LOTTO, rounding_unit=0)
    result = analyze(other_rows=other_rows, rollovers={"jackpot": 150e6}, rules=rules)
    jackpot = result.tiers[0]
    lam = other_rows / rules.combinations
    expected_share = -expm1(-lam) / lam if lam else 1
    assert jackpot.expected_winnings == pytest.approx(jackpot.pool * expected_share)


def test_rounded_poisson_sum_agrees_with_closed_form_within_rounding_bound():
    rules = ICELANDIC_LOTTO
    rounded = analyze(other_rows=20 * rules.combinations, rules=rules).tiers[0]
    exact = analyze(
        other_rows=20 * rules.combinations, rules=replace(rules, rounding_unit=0)
    ).tiers[0]
    assert 0 <= exact.expected_winnings - rounded.expected_winnings < 10.0001
    assert rounded.numerical_error_bound < 0.01


def test_rounding_at_exact_money_boundary_and_second_prize_carryover():
    rules = toy_rules(0.1)
    # Without other rows, 10 * 7.25 * .6 * .5 = 21.75; a .05 supplement
    # makes exactly 21.80. This must not be rounded to 21.70.
    result = analyze(other_rows=0, rules=rules, supplements={"jackpot": 0.05})
    assert result.tiers[0].expected_winnings == pytest.approx(21.8)
    carried = analyze(other_rows=0, rules=rules, rollovers={"one_bonus": 100})
    base = analyze(other_rows=0, rules=rules)
    assert carried.expected_winnings - base.expected_winnings == pytest.approx(100)


def test_smaller_prizes_include_competing_sales_and_sharing():
    rules = replace(ICELANDIC_LOTTO, rounding_unit=0)
    result = analyze(other_rows=rules.combinations, rules=rules)
    lower = sum(t.expected_winnings for t in result.tiers[1:])
    assert lower == pytest.approx(35_561_242.0955, abs=0.01)
    assert lower > rules.coverage_cost * 0.45 * 0.43


@pytest.mark.parametrize("rounding", [0, 10])
def test_break_even_returns_profitable_side(rounding):
    rules = replace(ICELANDIC_LOTTO, rounding_unit=rounding)
    threshold = break_even_rollover(other_rows=0, rules=rules)
    assert analyze(other_rows=0, rules=rules, rollovers={"jackpot": threshold}).roi >= 0
    assert analyze(other_rows=0, rules=rules, rollovers={"jackpot": threshold - 0.02}).roi < 0
    if rounding == 0:
        assert threshold == pytest.approx(rules.coverage_cost * 0.55, abs=0.01)


def test_grid_orientation_and_legacy_adapters():
    rules = toy_rules(0)
    grid = roi_grid([0, 10, 20], [0, 1], rules=rules)
    assert grid.shape == (2, 3)
    assert np.all(np.diff(grid, axis=1) > 0)
    assert grid[1, 2] == pytest.approx(
        analyze(
            other_rows=rows_from_jackpot_contribution(1, rules),
            rollovers={"jackpot": 20},
            rules=rules,
        ).roi
    )
    assert np.array_equal(lotteryROI([0, 10, 20], [0, 1], rules=rules), grid)
    contribution = breakEven(100, 0, 1000, rules=rules)
    assert lotteryROI(100, contribution, rules=rules)[0, 0] == pytest.approx(0, abs=1e-5)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"other_rows": -1},
        {"other_rows": float("nan")},
        {"other_rows": float("inf")},
        {"other_rows": True},
        {"other_rows": 1.5, "distribution": "binomial"},
        {"other_rows": 1, "distribution": "normal"},
        {"other_rows": 1, "rollovers": {"unknown": 1}},
        {"other_rows": 1, "rollovers": {"four": 10}},
        {"other_rows": 1, "rollovers": {"jackpot": -1}},
        {"other_rows": 1, "supplements": {"jackpot": float("nan")}},
        {"other_rows": 1, "tail_probability": 0},
    ],
)
def test_invalid_scenarios(kwargs):
    with pytest.raises(ValueError):
        analyze(**kwargs)


@pytest.mark.parametrize(
    "changes",
    [
        {"number_count": 5},
        {"draw_count": 0},
        {"number_count": 45.5},
        {"row_price": 0},
        {"payout_fraction": 1.1},
        {"rounding_unit": -10},
        {"tiers": ICELANDIC_LOTTO.tiers[:-1]},
        {"tiers": (PrizeTier("a", "A", 5, None, 0.5), PrizeTier("b", "B", 5, None, 0.5))},
    ],
)
def test_invalid_rules(changes):
    with pytest.raises(ValueError):
        replace(ICELANDIC_LOTTO, **changes)


def test_invalid_axes_and_root_brackets():
    for values in ([], [[1, 2]], [float("nan")], [-1]):
        with pytest.raises(ValueError):
            roi_grid(values, [1])
    with pytest.raises(ValueError, match="Bracket"):
        break_even_rollover(other_rows=0, bracket=(0, 1))
    with pytest.raises(ValueError, match="lastWin"):
        breakEven([1, 2], 0, 1)
    with pytest.raises(ValueError, match="bracket"):
        breakEven(0, 0, 1)


@pytest.mark.parametrize("distribution", ["poisson", "binomial"])
def test_unsupported_sales_counts_raise_validation_errors(distribution):
    with pytest.raises(ValueError, match="numeric range"):
        analyze(other_rows=1e20, distribution=distribution)


def test_large_rollover_does_not_overflow_decimal_rounding():
    result = analyze(other_rows=0, rollovers={"jackpot": 1e100})
    assert result.expected_winnings == pytest.approx(1e100)
