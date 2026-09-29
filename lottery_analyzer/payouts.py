"""Shared deterministic prize-pool and payout arithmetic."""

from decimal import Decimal

from .rules import LotteryRules, PrizeTier


def tier_pool(
    total_rows: Decimal,
    rules: LotteryRules,
    tier: PrizeTier,
    rollover: Decimal = Decimal(0),
    supplement: Decimal = Decimal(0),
) -> Decimal:
    return (
        total_rows
        * Decimal(str(rules.row_price))
        * Decimal(str(rules.payout_fraction))
        * Decimal(str(tier.pool_fraction))
        + rollover
        + supplement
    )


def pool_rounding_units(pool: Decimal, rounding_unit: float) -> int:
    """Floor the pool to integer payout units without Decimal division limits."""
    numerator, denominator = pool.as_integer_ratio()
    unit_numerator, unit_denominator = Decimal(str(rounding_unit)).as_integer_ratio()
    return (numerator * unit_denominator) // (denominator * unit_numerator)


def payout_per_winner(pool: Decimal, winners: int, rounding_unit: float) -> Decimal:
    if winners <= 0:
        raise ValueError("A payout per winner requires at least one winning row.")
    if rounding_unit == 0:
        return pool / winners
    return Decimal(pool_rounding_units(pool, rounding_unit) // winners) * Decimal(
        str(rounding_unit)
    )
