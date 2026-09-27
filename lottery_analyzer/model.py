"""Reusable analysis of purchasing every lottery combination exactly once."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from math import isfinite

from .probability import DEFAULT_TAIL_PROBABILITY, Distribution, expected_payout
from .rules import ICELANDIC_LOTTO, LotteryRules, nonnegative


@dataclass(frozen=True, slots=True)
class TierResult:
    key: str
    label: str
    winning_rows: int
    pool: float
    expected_competing_winners: float
    expected_winnings: float
    numerical_error_bound: float


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    rules: LotteryRules
    other_rows: float
    distribution: Distribution
    tiers: tuple[TierResult, ...]

    @property
    def cost(self) -> float:
        return self.rules.coverage_cost

    @property
    def expected_winnings(self) -> float:
        return sum(tier.expected_winnings for tier in self.tiers)

    @property
    def expected_profit(self) -> float:
        return self.expected_winnings - self.cost

    @property
    def roi(self) -> float:
        """Expected profit divided by cost; 0.10 means +10%."""
        return self.expected_profit / self.cost

    @property
    def numerical_error_bound(self) -> float:
        return sum(tier.numerical_error_bound for tier in self.tiers)


def _amounts(
    values: Mapping[str, float] | None, rules: LotteryRules, name: str
) -> dict[str, float]:
    result = dict(values or {})
    allowed = {tier.key for tier in rules.tiers}
    if result.keys() - allowed:
        raise ValueError(f"Unknown tier in {name}: {sorted(result.keys() - allowed)}")
    for key, value in result.items():
        result[key] = nonnegative(value, f"{name}[{key}]")
    return result


def analyze(
    *,
    other_rows: float,
    rollovers: Mapping[str, float] | None = None,
    supplements: Mapping[str, float] | None = None,
    rules: LotteryRules = ICELANDIC_LOTTO,
    distribution: Distribution = "poisson",
    tail_probability: float = DEFAULT_TAIL_PROBABILITY,
) -> AnalysisResult:
    """Estimate returns from one full set of combinations.

    other_rows excludes your complete set. Poisson accepts an estimated fractional
    count; binomial requires an integer count of independent uniform rows.
    rollovers are actual carried funds, not last week's paid-out jackpot.
    supplements are extra funds awarded in this draw, after your purchases.
    Minimum-pool guarantees are not automatically inferred from advertised sums.
    """
    other_rows = nonnegative(other_rows, "other_rows")
    if other_rows > 2**53 - 1:
        raise ValueError("other_rows exceeds the supported numeric range (2**53 - 1).")
    if distribution not in ("poisson", "binomial"):
        raise ValueError("distribution must be 'poisson' or 'binomial'.")
    if distribution == "binomial" and not other_rows.is_integer():
        raise ValueError("The binomial model requires an integer other_rows count.")
    tail_probability = nonnegative(tail_probability, "tail_probability")
    if not 1e-15 <= tail_probability <= 1e-6:
        raise ValueError("tail_probability must be between 1e-15 and 1e-6.")
    carried = _amounts(rollovers, rules, "rollovers")
    additions = _amounts(supplements, rules, "supplements")
    for tier in rules.tiers:
        if carried.get(tier.key, 0) and not tier.can_roll_over:
            raise ValueError(f"Tier {tier.key!r} does not allow rollovers.")
    prize_pool = (
        (Decimal(rules.combinations) + Decimal(str(other_rows)))
        * Decimal(str(rules.row_price))
        * Decimal(str(rules.payout_fraction))
    )
    if not isfinite(float(prize_pool) + sum(carried.values()) + sum(additions.values())):
        raise ValueError("Total prize money is too large for numerical evaluation.")
    results = []
    for tier in rules.tiers:
        pool = (
            prize_pool * Decimal(str(tier.pool_fraction))
            + Decimal(str(carried.get(tier.key, 0)))
            + Decimal(str(additions.get(tier.key, 0)))
        )
        if not isfinite(float(pool)):
            raise ValueError("Prize pool is too large for numerical evaluation.")
        own_winners = tier.winning_rows(rules.number_count, rules.draw_count)
        receipt, error = expected_payout(
            pool=pool,
            own_winners=own_winners,
            combinations=rules.combinations,
            other_rows=other_rows,
            distribution=distribution,
            rounding_unit=rules.rounding_unit,
            tail_probability=tail_probability,
        )
        results.append(
            TierResult(
                tier.key,
                tier.label,
                own_winners,
                float(pool),
                other_rows * own_winners / rules.combinations,
                receipt,
                error,
            )
        )
    return AnalysisResult(rules, other_rows, distribution, tuple(results))


def rows_from_jackpot_contribution(
    contribution: float, rules: LotteryRules = ICELANDIC_LOTTO
) -> float:
    """Infer other rows from sales-derived jackpot growth, excluding supplements."""
    return nonnegative(contribution, "contribution") / (
        rules.row_price * rules.payout_fraction * rules.jackpot_tier.pool_fraction
    )
