# Historical payout validation

Checked on **28 September 2026** against the official lotto.is Lottó result tables.
Five consecutive draws were transcribed; the first provides carryover context
for the four September draws. The observations and source URLs are in
[`data/historical_draws.json`](../data/historical_draws.json).

## Findings

All six published tier amounts for each September draw can be reproduced using
the configured allocations and per-winning-row rounding. Where a tier has zero
winners, its published amount is an unwon pool display, not a payment to anyone.
The first observation checks only the four non-rollover tiers: the preceding
draw was not collected, so its jackpot and second-prize carryovers are unknown.

| Draw | Scenario | Compatible integer row counts | Tiers checked |
| --- | --- | ---: | ---: |
| [29 August](https://games.lotto.is/urslit/lotto?year=2026&week=35) | Opening observation, jackpot unwon | 476,032–476,165 | 4 |
| [5 September](https://games.lotto.is/urslit/lotto?year=2026&week=36) | Jackpot rolls forward | 593,928 | 6 |
| [12 September](https://games.lotto.is/urslit/lotto?year=2026&week=37) | Jackpot rolls forward again | 731,725 | 6 |
| [19 September](https://games.lotto.is/urslit/lotto?year=2026&week=38) | Accumulated jackpot won | 890,596 | 6 |
| [26 September](https://games.lotto.is/urslit/lotto?year=2026&week=39) | Ordinary draw after the jackpot was won | 281,154 | 6 |

**These are inferred row counts, not independently published sales figures.**
They assume the configured row price and allocations, no additional prize funding,
and that the unwon jackpot display is rounded down to the nearest 10 kr. Actual
sales ledger data would be needed to confirm the inferred counts independently.

## Why displayed rollover amounts cannot be treated as exact

Treating the 29 August and 5 September displayed jackpots as exact carried
balances leaves no integer row count that satisfies the following week's jackpot
display. Allowing an unreported remainder below 10 kr. resolves both discrepancies.

One feasible ledger illustrates the distinction:

| Draw | Unrounded jackpot in this example | Published display/payout |
| --- | ---: | ---: |
| 29 August | 43,965,721.000 kr. | 43,965,720 kr. |
| 5 September | 66,817,100.800 kr. | 66,817,100 kr. |
| 12 September | 94,970,220.175 kr. | 94,970,220 kr. |
| 19 September | 129,235,901.275 kr. | 129,235,900 kr. |
| 26 September | 10,817,400.150 kr. | 10,817,400 kr. |

The opening 43,965,721 kr. is an arbitrary feasible value inside the display
interval, **not a recovered official balance**. The following amounts result
from adding the inferred sales contributions, and resetting the carryover after
the 19 September win. A regression test reproduces all tier amounts using this
single feasible ledger. This establishes consistency with the rounding hypothesis;
it does not prove the website's undisclosed internal accounting precision.

## Method

For a tier with `w > 0` winning rows, reported payout `p`, and rounding unit `u`,
the unrounded pool must satisfy:

```text
w * p <= pool < w * (p + u)
pool = rows * row_price * payout_fraction * tier_fraction + carryover
```

For an unwon tier, the display is modeled as `display <= pool < display + u`.
The checker intersects the compatible integer-sales ranges from all tiers whose
carryover is constrained. A previous winner means zero carryover; an unwon
previous tier contributes its display interval. No unknown adjustment is fitted
to force a match. Additional funding, promotions, or a different display convention
could change the interpretation and must be investigated if a draw fails.

The interval inversion uses exact rational arithmetic. A forward replay then
uses the same Decimal prize-pool and payout-rounding helpers as the ROI engine.
It uses the historical participating rows and observed winning-row counts;
**it does not add a hypothetical purchase of every combination**.

## What this validates—and what it does not

The observations support the current payout allocations, per-row rounding, and
jackpot accumulation/reset arithmetic under the listed assumptions. They do not
independently validate the 5/45 combination counts, Poisson/binomial winner model,
uniform ticket-selection assumption, sales forecasts, or expected investment ROI.
Those require separate checks and a larger dataset, ideally including exact sales.

No zero-winner second-prize draw occurs in this sample. Second-prize rollover
accounting therefore remains covered by synthetic tests rather than this historical
sample. No pre-May-2025 draw or special additional-funding draw was tested.

## Reproduce

```sh
.venv/bin/python -m lottery_analyzer.historical data/historical_draws.json
.venv/bin/python -m pytest tests/test_historical.py -q
```

The CLI reports pairwise consistency and also tests the stricter interpretation
that displayed carryovers are exact. Its exit status depends on the interval-based
check; expected strict-check failures remain visible in its output. Sources are
offline fixtures so regression tests do not depend on a changing website.
