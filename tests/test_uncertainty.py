from dataclasses import replace

import pytest

from lottery_analyzer import (
    ICELANDIC_LOTTO,
    LotteryRules,
    PrizeTier,
    SalesScenario,
    analyze,
    analyze_sales_uncertainty,
    break_even_contribution,
    rows_from_jackpot_contribution,
)
from lotteryAnalyzer import breakEven


def jump_rules():
    return LotteryRules(
        number_count=2,
        draw_count=1,
        row_price=1,
        payout_fraction=0.45,
        tiers=(PrizeTier("jackpot", "One", 1, None, 1, True),),
        rounding_unit=10,
    )


def test_legacy_solver_brackets_a_rounding_jump_without_inventing_a_zero():
    rules = jump_rules()
    result = breakEven(9, 0, 0.2, rules=rules, full_output=True, money_tolerance=1e-6)
    # Pool = 9 + .9 + contribution; first payout appears at contribution .1.
    assert result.lower < 0.1 <= result.upper
    assert result.upper - result.lower <= 1e-6
    assert result.lower_profit == -2
    assert result.upper_profit > 6
    assert not result.exact_zero
    assert result.profitable_value == result.upper
    assert breakEven(9, 0, 0.2, rules=rules, money_tolerance=1e-6) == result.upper


def test_decreasing_crossing_returns_profitable_lower_endpoint():
    rules = jump_rules()
    result = break_even_contribution(12, (0, 100), rules=rules)
    assert result.lower_profit >= 0 > result.upper_profit
    assert result.profitable_value == result.lower
    for contribution, expected in [
        (result.lower, result.lower_profit),
        (result.upper, result.upper_profit),
    ]:
        actual = analyze(
            other_rows=rows_from_jackpot_contribution(contribution, rules),
            rollovers={"jackpot": 12},
            rules=rules,
        )
        assert actual.expected_profit == expected


def test_exact_zero_endpoint_and_invalid_brackets():
    rules = replace(jump_rules(), payout_fraction=0.5, rounding_unit=0)
    exact = break_even_contribution(1, (0, 1), rules=rules)
    assert exact.exact_zero and exact.profitable_value == 0
    for bracket, tolerance in [((0, 0), 0.01), ((2, 1), 0.01), ((0, 1), 0), ((0, 1), float("nan"))]:
        with pytest.raises(ValueError):
            break_even_contribution(0, bracket, rules=rules, money_tolerance=tolerance)


@pytest.mark.parametrize("distribution", ["poisson", "binomial"])
def test_single_scenario_is_identical_to_fixed_sales(distribution):
    expected = analyze(other_rows=100, distribution=distribution)
    result = analyze_sales_uncertainty([SalesScenario(100, 1)], distribution=distribution)
    assert result.average == expected


def test_weighted_sales_recalculates_pools_and_is_not_analysis_at_mean():
    rules = replace(ICELANDIC_LOTTO, rounding_unit=0)
    scenarios = [SalesScenario(0, 0.25), SalesScenario(1_000_000, 0.75)]
    options = dict(
        rules=rules,
        rollovers={"jackpot": 150e6, "four_bonus": 1000},
        supplements={"four": 3000},
        distribution="binomial",
    )
    result = analyze_sales_uncertainty(scenarios, **options)
    first, second = (analyze(other_rows=s.other_rows, **options) for s in scenarios)
    expected = 0.25 * first.expected_winnings + 0.75 * second.expected_winnings
    assert result.average.other_rows == 750_000
    assert result.average.cost == rules.coverage_cost
    assert result.average.expected_winnings == pytest.approx(expected)
    assert result.average.expected_profit == pytest.approx(expected - rules.coverage_cost)
    assert result.scenarios[0].analysis.tiers[0].pool < result.scenarios[1].analysis.tiers[0].pool
    assert result.average.roi != pytest.approx(analyze(other_rows=750_000, **options).roi)
    assert result.average.numerical_error_bound == pytest.approx(
        0.25 * first.numerical_error_bound + 0.75 * second.numerical_error_bound
    )


def test_weighted_rounded_payouts_against_two_deterministic_sales_outcomes():
    # With binomial sales and a fixed draw, enumerate both possible competing
    # rows in this 1/2 lottery. No simulation or probability code is the oracle.
    rules = jump_rules()
    # At N=0 pool=10.4 => receipt=10; at N=1 pool=10.85 =>
    # one competing winner pays 0, no competing winner pays 10, equally likely.
    result = analyze_sales_uncertainty(
        [SalesScenario(0, 0.4), SalesScenario(1, 0.6)],
        rules=rules,
        distribution="binomial",
        rollovers={"jackpot": 9.5},
    )
    assert result.average.expected_winnings == pytest.approx(0.4 * 10 + 0.6 * 5)
    assert result.average.expected_profit == pytest.approx(5)


@pytest.mark.parametrize("scenarios", [[], [SalesScenario(1, 0.2)], [SalesScenario(1, 0.7)] * 2])
def test_invalid_probability_totals(scenarios):
    with pytest.raises(ValueError):
        analyze_sales_uncertainty(scenarios)


@pytest.mark.parametrize("rows,weight", [(-1, 1), (1, 0), (1, -1), (1, 2), (1, float("nan"))])
def test_invalid_scenario(rows, weight):
    with pytest.raises(ValueError):
        SalesScenario(rows, weight)


def test_binomial_requires_integer_sales_in_every_scenario():
    with pytest.raises(ValueError, match="integer"):
        analyze_sales_uncertainty([SalesScenario(1.5, 1)], distribution="binomial")
