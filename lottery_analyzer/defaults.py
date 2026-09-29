"""Dated, manually verified lotto.is snapshot for the default web scenario.

The advertised jackpot is a forecast, not a rollover or a measured sales total.
Both rollover-eligible prizes were won in the 26 September 2026 results.
"""

from dataclasses import dataclass
from datetime import date

from .model import rows_from_jackpot_contribution


@dataclass(frozen=True, slots=True)
class LottoSnapshot:
    checked_on: date
    previous_draw: date
    advertised_jackpot: int
    jackpot_rollover: int
    second_prize_rollover: int
    forecast_url: str = "https://games.lotto.is/"
    results_url: str = "https://games.lotto.is/urslit/lotto"

    @property
    def estimated_other_rows(self) -> int:
        """Assume forecast minus carryover comes entirely from ordinary sales."""
        return round(
            rows_from_jackpot_contribution(self.advertised_jackpot - self.jackpot_rollover)
        )

    def form_values(self) -> dict[str, str]:
        return {
            "other_rows": str(self.estimated_other_rows),
            "rollover_jackpot": str(self.jackpot_rollover),
            "rollover_four_bonus": str(self.second_prize_rollover),
            "distribution": "poisson",
        }


LOTTO_IS_SNAPSHOT = LottoSnapshot(
    checked_on=date(2026, 9, 28),
    previous_draw=date(2026, 9, 26),
    advertised_jackpot=10_000_000,
    jackpot_rollover=0,
    second_prize_rollover=0,
)
