"""Expected pari-mutuel payouts, with bounded numerical tail omission."""

from decimal import Decimal
from math import expm1, log1p
from typing import Literal

import numpy as np
from scipy.stats import binom, poisson

from .payouts import pool_rounding_units

Distribution = Literal["poisson", "binomial"]
DEFAULT_TAIL_PROBABILITY = 1e-12
MAX_SUPPORT_SIZE = 1_000_000


def expected_payout(
    *,
    pool: Decimal,
    own_winners: int,
    combinations: int,
    other_rows: float,
    distribution: Distribution,
    rounding_unit: float,
    tail_probability: float,
) -> tuple[float, float]:
    """Return (expected receipt, upper bound on omitted receipt).

    The bound covers omitted probability tails, not floating-point error or
    modeling uncertainty. No independence between tiers is needed for their
    expectations to add. Other rows are assumed independent and uniform.
    """
    pool_value = float(pool)
    if pool_value == 0:
        return 0.0, 0.0
    probability = own_winners / combinations
    mean = other_rows * probability

    # Full closed form for the jackpot, when rounding is disabled.
    if own_winners == 1 and rounding_unit == 0:
        if mean == 0:
            share = 1.0
        elif distribution == "poisson":
            share = -expm1(-mean) / mean
        elif probability == 1:
            share = 1 / (other_rows + 1)
        else:
            share = -expm1((other_rows + 1) * log1p(-probability)) / (
                (other_rows + 1) * probability
            )
        return pool_value * share, 0.0

    law = poisson(mean) if distribution == "poisson" else binom(int(other_rows), probability)
    lower_quantile = law.ppf(tail_probability / 2)
    upper_quantile = law.isf(tail_probability / 2)
    if not np.isfinite(lower_quantile) or not np.isfinite(upper_quantile):
        raise ValueError("Competing row count is too large for numerical payout evaluation.")
    low = max(0, int(lower_quantile))
    high = int(upper_quantile)
    if high - low + 1 > MAX_SUPPORT_SIZE or high > np.iinfo(np.int64).max - own_winners:
        raise ValueError("Competing row count is too large for numerical payout evaluation.")
    winners = np.arange(low, high + 1, dtype=np.int64)
    weights = law.pmf(winners)
    if rounding_unit:
        # Integer division avoids binary floating-point rounding down an exact
        # monetary boundary (e.g. an exact 10 kr. payout becoming zero).
        units = pool_rounding_units(pool, rounding_unit)
        row_units = np.fromiter((units // (own_winners + int(k)) for k in winners), dtype=float)
        receipts = row_units * rounding_unit * own_winners
    else:
        receipts = pool_value * (own_winners / (own_winners + winners))
    missing_mass = float(law.cdf(low - 1) + law.sf(high))
    return float(np.dot(weights, receipts)), pool_value * missing_mass
