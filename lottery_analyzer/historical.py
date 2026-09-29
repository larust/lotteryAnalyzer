"""Reconcile historical prize tables without mistaking payouts for exact pools.

This is a deterministic accounting check, not validation of the winner-count
distribution. Integer row counts are inferred constraints, not measured sales.
"""

import argparse
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction
from math import ceil, floor
from pathlib import Path

from .payouts import payout_per_winner, tier_pool
from .rules import ICELANDIC_LOTTO, LotteryRules


@dataclass(frozen=True)
class Draw:
    date: date
    source: str
    winners: tuple[int, ...]
    amounts: tuple[int, ...]


@dataclass(frozen=True)
class Validation:
    draw: Draw
    minimum_rows: int
    maximum_rows: int
    checked_tiers: tuple[str, ...]
    skipped_tiers: tuple[str, ...]
    forward_matches: bool

    @property
    def consistent(self) -> bool:
        return self.minimum_rows <= self.maximum_rows and self.forward_matches


def _bounds(winners: int, amount: int, unit: Fraction) -> tuple[Fraction, Fraction]:
    # For zero winners, interpret the displayed pool as rounded down to the
    # same unit. This is an explicit hypothesis about the website's display.
    multiplier = max(1, winners)
    return Fraction(multiplier * amount), multiplier * (Fraction(amount) + unit)


def validate_draw(
    draw: Draw,
    previous: Draw | None = None,
    *,
    rules: LotteryRules = ICELANDIC_LOTTO,
    exact_displayed_carryover: bool = False,
    exclude_tiers: tuple[str, ...] = (),
) -> Validation:
    """Check pairwise accounting consistency, assuming no extra prize funding.

    Pools lie in [w*p, w*(p+unit)), where w is observed winning rows and p is
    published per-row payout. Non-rollover tiers have zero carryover. Eligible
    tiers need the previous weekly result; otherwise they are skipped.
    Unwon displayed pools are treated as [display, display+unit), not as exact
    carryover balances. exact_displayed_carryover=True tests the stricter reading.
    Each pair is checked independently; this is not a full ledger reconstruction.
    exclude_tiers omits both the count and payout constraints for those tiers.
    """
    if set(exclude_tiers) - {t.key for t in rules.tiers}:
        raise ValueError("Unknown excluded tier.")
    if rules.rounding_unit <= 0:
        raise ValueError("Historical rounded tables require a positive rounding unit.")
    for observation in (draw, previous):
        if observation is None:
            continue
        if len(observation.winners) != len(rules.tiers) or len(observation.amounts) != len(
            rules.tiers
        ):
            raise ValueError("Historical observations must contain every configured tier.")
        if any(type(v) is not int or v < 0 for v in (*observation.winners, *observation.amounts)):
            raise ValueError("Historical counts and amounts must be nonnegative integers.")
        if any(Fraction(v) % Fraction(str(rules.rounding_unit)) for v in observation.amounts):
            raise ValueError("Published amounts must be multiples of the rounding unit.")
    if previous is not None and (draw.date - previous.date).days != 7:
        raise ValueError("Provide the immediately preceding weekly draw.")
    unit = Fraction(str(rules.rounding_unit))
    low, high = 0, None
    constraints = []
    skipped = []
    for i, tier in enumerate(rules.tiers):
        if tier.key in exclude_tiers or (tier.can_roll_over and previous is None):
            skipped.append(tier.key)
            continue
        carry_low = carry_high = Fraction(0)
        if tier.can_roll_over and previous.winners[i] == 0:
            carry_low = Fraction(previous.amounts[i])
            carry_high = carry_low if exact_displayed_carryover else carry_low + unit
        observed_low, observed_high = _bounds(draw.winners[i], draw.amounts[i], unit)
        rate = (
            Fraction(str(rules.row_price))
            * Fraction(str(rules.payout_fraction))
            * Fraction(str(tier.pool_fraction))
        )
        lower = (observed_low - carry_high) / rate
        tier_low = ceil(lower) if carry_low == carry_high else floor(lower) + 1
        tier_high = ceil((observed_high - carry_low) / rate) - 1
        low = max(low, tier_low)
        high = tier_high if high is None else min(high, tier_high)
        constraints.append((i, carry_low, carry_high, observed_low, observed_high))
    if high is None:
        raise ValueError("No tiers have known carryover constraints.")

    # Forward-check a witness using the same pool and rounding arithmetic as
    # the ROI engine. The interval inversion above uses independent exact
    # rational arithmetic. No hypothetical complete set is added to history.
    matched = low <= high
    if matched:
        for i, carry_low, carry_high, observed_low, observed_high in constraints:
            base = tier_pool(Decimal(low), rules, rules.tiers[i])
            witness_low = max(Fraction(base) + carry_low, observed_low)
            witness_high = min(Fraction(base) + carry_high, observed_high)
            pool = base + Decimal(carry_low.numerator) / Decimal(carry_low.denominator)
            if carry_low != carry_high:
                witness = (witness_low + witness_high) / 2
                pool = Decimal(witness.numerator) / Decimal(witness.denominator)
            divisor = max(1, draw.winners[i])
            matched &= payout_per_winner(pool, divisor, rules.rounding_unit) == draw.amounts[i]
    return Validation(
        draw, low, high, tuple(rules.tiers[c[0]].key for c in constraints), tuple(skipped), matched
    )


def load_draws(path: Path) -> tuple[Draw, ...]:
    data = json.loads(path.read_text())
    if data["tier_order"] != [t.key for t in ICELANDIC_LOTTO.tiers]:
        raise ValueError("Fixture tier order does not match current rules.")
    effective = date.fromisoformat(data["rules_effective_from"])
    draws = tuple(
        Draw(date.fromisoformat(d["date"]), d["source"], tuple(d["winners"]), tuple(d["amounts"]))
        for d in data["draws"]
    )
    if any(d.date < effective for d in draws):
        raise ValueError("Fixture contains a draw before these rules became effective.")
    if any(a.date >= b.date for a, b in zip(draws, draws[1:], strict=False)):
        raise ValueError("Draw dates must be unique and in increasing order.")
    return draws


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    draws = load_draws(args.fixture)
    print("| Draw | Accounting check | Compatible row counts | Tiers checked | Exact carryover? |")
    print("| --- | --- | ---: | ---: | --- |")
    failed = False
    for i, draw in enumerate(draws):
        previous = draws[i - 1] if i else None
        result = validate_draw(draw, previous)
        strict = validate_draw(draw, previous, exact_displayed_carryover=True)
        counts = f"{result.minimum_rows:,}–{result.maximum_rows:,}" if result.consistent else "none"
        print(
            f"| [{draw.date}]({draw.source}) | {'consistent' if result.consistent else 'FAIL'} "
            f"| {counts} | {len(result.checked_tiers)} "
            f"| {'consistent' if strict.consistent else 'FAIL'} |"
        )
        failed |= not result.consistent
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
