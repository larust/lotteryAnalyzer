"""Scenario grids and break-even thresholds, independent of presentation."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

import numpy as np
from numpy.typing import NDArray

from .model import analyze, rows_from_jackpot_contribution
from .probability import Distribution
from .rules import ICELANDIC_LOTTO, LotteryRules, nonnegative


@dataclass(frozen=True, slots=True)
class BreakEvenResult:
    """A local sign-changing bracket, or an evaluated exact zero.

    lower/upper describe contribution amounts; profits use the game's currency.
    No global monotonicity or uniqueness is assumed for rounded contributions.
    """

    lower: float
    upper: float
    lower_profit: float
    upper_profit: float

    @property
    def profitable_value(self) -> float:
        return self.lower if self.lower_profit >= 0 else self.upper

    @property
    def exact_zero(self) -> bool:
        return self.lower == self.upper and self.lower_profit == 0


def _crossing_bracket(
    profit: Callable[[float], float], bracket: tuple[float, float], tolerance: float
) -> BreakEvenResult:
    low, high = (nonnegative(value, "bracket endpoint") for value in bracket)
    tolerance = nonnegative(tolerance, "money_tolerance")
    if low >= high or tolerance == 0:
        raise ValueError("Use an increasing bracket and a positive money_tolerance.")

    def evaluate(value: float) -> float:
        result = profit(value)
        if not isfinite(result):
            raise ValueError("Expected profit must be finite throughout the bracket.")
        return result

    left, right = evaluate(low), evaluate(high)
    if left == 0:
        return BreakEvenResult(low, low, left, left)
    if right == 0:
        return BreakEvenResult(high, high, right, right)
    if (left < 0) == (right < 0):
        raise ValueError("Bounds must bracket a loss and a nonnegative expected profit.")
    while high - low > tolerance:
        middle = low + (high - low) / 2
        if middle in (low, high):
            raise ValueError("money_tolerance is below floating-point resolution at this bracket.")
        value = evaluate(middle)
        if value == 0:
            return BreakEvenResult(middle, middle, value, value)
        if (value < 0) == (left < 0):
            low, left = middle, value
        else:
            high, right = middle, value
    return BreakEvenResult(low, high, left, right)


def break_even_contribution(
    jackpot_rollover: float,
    bracket: tuple[float, float],
    *,
    rules: LotteryRules = ICELANDIC_LOTTO,
    rollovers: Mapping[str, float] | None = None,
    supplements: Mapping[str, float] | None = None,
    money_tolerance: float = 0.01,
) -> BreakEvenResult:
    """Bracket one Poisson profit crossing as other players' contribution varies.

    Accepts either sign orientation and discontinuous rounded payouts. It does
    not claim an exact root, a unique crossing, or that all values on one side
    remain profitable. Same-sign endpoints are rejected even if interior
    crossings exist. The jackpot entry in rollovers is replaced by the argument.
    """
    carried = dict(rollovers or {})
    carried[rules.jackpot_tier.key] = nonnegative(jackpot_rollover, "jackpot_rollover")

    def profit(contribution: float) -> float:
        return analyze(
            other_rows=rows_from_jackpot_contribution(contribution, rules),
            rollovers=carried,
            supplements=supplements,
            rules=rules,
        ).expected_profit

    return _crossing_bracket(profit, bracket, money_tolerance)


def _axis(values: float | Sequence[float], name: str) -> NDArray[np.float64]:
    try:
        axis = np.atleast_1d(np.asarray(values, dtype=float))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain finite, nonnegative numbers.") from exc
    if axis.ndim != 1 or not axis.size or not np.all(np.isfinite(axis)) or np.any(axis < 0):
        raise ValueError(f"{name} must be a nonempty 1D array of finite, nonnegative numbers.")
    return axis


def roi_grid(
    jackpot_rollovers: float | Sequence[float],
    jackpot_contributions: float | Sequence[float],
    *,
    rules: LotteryRules = ICELANDIC_LOTTO,
    rollovers: Mapping[str, float] | None = None,
    supplements: Mapping[str, float] | None = None,
) -> NDArray[np.float64]:
    """Poisson ROI grid: rows = contributions, columns = jackpot rollovers.

    Contributions are from other players' sales only. Values on the rollover
    axis replace any jackpot value in rollovers; other tiers are preserved.
    """
    carried = _axis(jackpot_rollovers, "jackpot_rollovers")
    added = _axis(jackpot_contributions, "jackpot_contributions")
    output = np.empty((len(added), len(carried)))
    for row, contribution in enumerate(added):
        for column, rollover in enumerate(carried):
            tier_rollovers = dict(rollovers or {})
            tier_rollovers[rules.jackpot_tier.key] = rollover
            output[row, column] = analyze(
                other_rows=rows_from_jackpot_contribution(contribution, rules),
                rollovers=tier_rollovers,
                supplements=supplements,
                rules=rules,
            ).roi
    return output


def break_even_rollover(
    *,
    other_rows: float,
    bracket: tuple[float, float] = (0, 1_000_000_000),
    rules: LotteryRules = ICELANDIC_LOTTO,
    rollovers: Mapping[str, float] | None = None,
    supplements: Mapping[str, float] | None = None,
    distribution: Distribution = "poisson",
    money_tolerance: float = 0.01,
) -> float:
    """Find a jackpot rollover with nonnegative modeled profit.

    Returns the profitable side of the boundary, within money_tolerance in
    rollover currency. Bisection supports the steps introduced by payout
    rounding; an exact zero may not exist. Other players' sales stay fixed.
    The jackpot entry in rollovers is replaced by the searched value.
    """
    low, high = (nonnegative(value, "bracket endpoint") for value in bracket)
    tolerance = nonnegative(money_tolerance, "money_tolerance")
    if low >= high or tolerance == 0:
        raise ValueError("Use an increasing bracket and a positive money_tolerance.")

    def profit(rollover: float) -> float:
        carried = dict(rollovers or {})
        carried[rules.jackpot_tier.key] = rollover
        return analyze(
            other_rows=other_rows,
            rollovers=carried,
            supplements=supplements,
            rules=rules,
            distribution=distribution,
        ).expected_profit

    left_profit, right_profit = profit(low), profit(high)
    if left_profit == 0:
        return low
    if left_profit > 0 or right_profit < 0:
        raise ValueError("Bracket must span a loss and a nonnegative expected profit.")
    while high - low > tolerance:
        middle = low + (high - low) / 2
        if middle in (low, high):
            break
        if profit(middle) >= 0:
            high = middle
        else:
            low = middle
    return high
