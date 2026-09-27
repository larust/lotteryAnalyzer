"""Immutable rules for lotteries drawing main numbers and one bonus number."""

from dataclasses import dataclass
from math import comb, isclose, isfinite
from numbers import Integral, Real


def nonnegative(value: float, name: str) -> float:
    """Validate public scalar inputs without accepting booleans or numeric strings."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite, nonnegative number.")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} is too large for numerical evaluation.") from exc
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite, nonnegative number.")
    return value


def _integer(value: int, name: str, minimum: int = 0) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}.")


@dataclass(frozen=True, slots=True)
class PrizeTier:
    """A mutually exclusive tier; bonus=None means either bonus outcome."""

    key: str
    label: str
    matches: int
    bonus: bool | None
    pool_fraction: float
    can_roll_over: bool = False

    def __post_init__(self) -> None:
        if not self.key or not self.label:
            raise ValueError("Prize tiers need a key and label.")
        _integer(self.matches, "matches")
        if self.bonus is not None and type(self.bonus) is not bool:
            raise ValueError("bonus must be True, False, or None.")
        fraction = nonnegative(self.pool_fraction, "pool_fraction")
        if not 0 < fraction <= 1:
            raise ValueError("pool_fraction must be in (0, 1].")

    def winning_rows(self, number_count: int, draw_count: int) -> int:
        """Count tier-winning rows in one complete set of combinations."""
        if self.matches > draw_count:
            return 0
        remaining = draw_count - self.matches
        if self.bonus is None:
            available = number_count - draw_count
        else:
            available = number_count - draw_count - 1
            remaining -= int(self.bonus)
        if remaining < 0 or remaining > available:
            return 0
        return comb(draw_count, self.matches) * comb(available, remaining)


CURRENT_TIERS = (
    PrizeTier("jackpot", "5 correct", 5, None, 0.57, True),
    PrizeTier("four_bonus", "4 + bonus", 4, True, 0.02, True),
    PrizeTier("four", "4 without bonus", 4, False, 0.10),
    PrizeTier("three_bonus", "3 + bonus", 3, True, 0.04),
    PrizeTier("three", "3 without bonus", 3, False, 0.17),
    PrizeTier("two_bonus", "2 + bonus", 2, True, 0.10),
)


@dataclass(frozen=True, slots=True)
class LotteryRules:
    """Defaults: Icelandic Lottó 5/45, rules effective 18 May 2025.

    All monetary values use the same currency. A rounding unit of zero disables
    payout rounding. Changing draw_count requires supplying matching prize tiers.
    """

    name: str = "Icelandic Lottó 5/45"
    number_count: int = 45
    draw_count: int = 5
    row_price: float = 150.0
    payout_fraction: float = 0.45
    tiers: tuple[PrizeTier, ...] = CURRENT_TIERS
    rounding_unit: float = 10.0

    def __post_init__(self) -> None:
        _integer(self.number_count, "number_count", 2)
        _integer(self.draw_count, "draw_count", 1)
        if self.draw_count >= self.number_count:
            raise ValueError("number_count must leave at least one bonus number.")
        if nonnegative(self.row_price, "row_price") == 0:
            raise ValueError("row_price must be positive.")
        if not 0 < nonnegative(self.payout_fraction, "payout_fraction") <= 1:
            raise ValueError("payout_fraction must be in (0, 1].")
        nonnegative(self.rounding_unit, "rounding_unit")
        object.__setattr__(self, "tiers", tuple(self.tiers))
        if not self.tiers or any(not isinstance(tier, PrizeTier) for tier in self.tiers):
            raise ValueError("tiers must contain PrizeTier objects.")
        if len({tier.key for tier in self.tiers}) != len(self.tiers):
            raise ValueError("Prize tier keys must be unique.")
        if not isclose(sum(t.pool_fraction for t in self.tiers), 1, abs_tol=1e-12, rel_tol=0):
            raise ValueError("Prize pool fractions must sum to 1.")
        outcomes: set[tuple[int, bool]] = set()
        for tier in self.tiers:
            if not tier.winning_rows(self.number_count, self.draw_count):
                raise ValueError(f"Tier {tier.key!r} has no possible winning rows.")
            for bonus in (False, True) if tier.bonus is None else (tier.bonus,):
                outcome = (tier.matches, bonus)
                if outcome in outcomes:
                    raise ValueError("Prize tiers must not overlap.")
                outcomes.add(outcome)
        if sum(t.matches == self.draw_count for t in self.tiers) != 1:
            raise ValueError("Exactly one jackpot tier must match all main numbers.")

    @property
    def combinations(self) -> int:
        return comb(self.number_count, self.draw_count)

    @property
    def coverage_cost(self) -> float:
        return self.combinations * self.row_price

    @property
    def jackpot_tier(self) -> PrizeTier:
        return next(t for t in self.tiers if t.matches == self.draw_count)


ICELANDIC_LOTTO = LotteryRules()
