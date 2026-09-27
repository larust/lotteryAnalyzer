# Lottery Analyzer

A Python library and optional web calculator for the expected return from buying
**every lottery combination exactly once**. It accounts for your purchases adding
to the prize pools and for sharing prizes with other players. It does not predict
winning numbers or guarantee a profit.

## Install

Requires Python 3.11 or later.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[web,plot,dev]'
```

For library-only use, install with `python -m pip install -e .`. Flask and
Matplotlib are optional extras (`web` and `plot`); neither is imported by the core.

## Current defaults

`ICELANDIC_LOTTO` is an immutable `LotteryRules` instance for Icelandic Lottó 5/45.
The game configuration was checked on 27 September 2026 against the
[2025 amendment, effective 18 May 2025](https://www.reglugerd.is/reglugerdir/eftir-raduneytum/innanrikisraduneyti/nr/24498),
[Getspá's game description](https://games.lotto.is/reglur-og-lei%C3%B0beiningar/lottoleikir/lotto),
and [Articles 8–9 of the underlying regulation](https://www.reglugerd.is/reglugerdir/eftir-raduneytum/dmr/nr/18510).
The underlying page displays historical wording; read it together with its amendments.

| Setting | Default |
| --- | ---: |
| Main numbers drawn / available | 5 / 45 |
| Bonus numbers drawn from remaining balls | 1 |
| Price per row | 150 kr. |
| Sales allocated to prizes | 45% |
| Payout rounding per winning row | Down to 10 kr. |
| Complete set of rows | 1,221,759 |
| Cost of complete set | 183,263,850 kr. |

| Tier key | Prize | Pool share | Winning rows in a complete set | Rollover allowed |
| --- | --- | ---: | ---: | --- |
| `jackpot` | 5 correct | 57% | 1 | Yes |
| `four_bonus` | 4 + bonus | 2% | 5 | Yes |
| `four` | 4 without bonus | 10% | 195 | No |
| `three_bonus` | 3 + bonus | 4% | 390 | No |
| `three` | 3 without bonus | 17% | 7,410 | No |
| `two_bonus` | 2 + bonus | 10% | 7,410 | No |

The configuration is a versioned snapshot, not a live rules feed.

## Library use

```python
from lottery_analyzer import analyze

result = analyze(
    other_rows=500_000,
    rollovers={"jackpot": 100_000_000, "four_bonus": 300_000},
)
print(f"Cost: {result.cost:,.0f} kr.")
print(f"Expected winnings: {result.expected_winnings:,.2f} kr.")
print(f"Expected profit: {result.expected_profit:,.2f} kr.")
print(f"ROI: {result.roi:.2%}")
for tier in result.tiers:
    print(tier.label, tier.winning_rows, tier.expected_winnings)
```

- `other_rows` excludes your complete set of combinations.
- `rollovers` contains actual carried money, by tier. Last week's unwon jackpot
  normally supplies `jackpot`; a jackpot paid out last week supplies no rollover.
  Any nontransferable minimum-prize supplement must be excluded.
- `supplements` optionally specifies additional funds by tier, **after accounting
  for your purchases**. It is not a minimum-pool guarantee. If a guarantee no longer
  applies after your purchases, do not include its hypothetical top-up.
- All amounts must be finite and nonnegative, in the same currency as `row_price`.
  Unknown tier keys and carryovers into non-rollover tiers raise `ValueError`.
- `roi` is a fraction: `0.10` means +10%, `-0.55` means −55%.

If only sales-derived jackpot growth is known:

```python
from lottery_analyzer import rows_from_jackpot_contribution

other_rows = rows_from_jackpot_contribution(20_000_000)
result = analyze(other_rows=other_rows, rollovers={"jackpot": 100_000_000})
```

This inversion assumes growth equals other rows × row price × payout fraction ×
jackpot fraction. Exclude promotions, supplements, and your own purchases. Use
final funds or a clearly identified estimate, rather than assuming an advertised
jackpot forecast is a measured sales total.

## Custom rules

```python
from dataclasses import replace
from lottery_analyzer import ICELANDIC_LOTTO, analyze

custom = replace(
    ICELANDIC_LOTTO,
    name="Hypothetical 5/40 at 130 kr. with current prize tiers",
    number_count=40,
    row_price=130,
    rounding_unit=0,  # Disable payout rounding for theoretical comparisons.
)
result = analyze(other_rows=500_000, rules=custom)
```

This example changes two parameters; it does **not** reconstruct all historical
Icelandic rules. Supply the appropriate `PrizeTier` objects to change allocations
or matching conditions. `bonus=True` requires the bonus, `False` excludes it, and
`None` accepts either outcome. Tiers must be mutually exclusive, possible under
the draw rules, and allocate exactly 100% of the prize pool. Changing the number
of main balls drawn also requires supplying compatible tiers.

The model supports one bonus ball drawn without replacement from the remaining
numbers. It does not model separate star-number pools, fixed-cash prize tiers,
partial coverage, or purchases with duplicate rows in your own complete set.

## Probability model and numerical accuracy

The default `distribution="poisson"` retains the original model's assumption.
For tier `j`, you hold exactly `m_j` winning rows out of `M` combinations, and the
number of competing winners is Poisson with mean `other_rows * m_j / M`.

For a fixed whole-number count of independent, uniformly selected competing rows,
use `distribution="binomial"`. This uses the binomial marginal distribution for
each tier. Tier counts need not be mutually independent to add their expectations.

Each pool includes current sales from **both** other players and your complete
set, plus the relevant rollover and supplement. For `k` competing winners, the
receipt is:

```text
without rounding: pool * m_j / (m_j + k)
with rounding:    m_j * unit * floor(pool / ((m_j + k) * unit))
```

Monetary pools use decimal arithmetic before per-row rounding. The unrounded
jackpot expectation uses a closed form, including a stable zero-sales limit.
Other expectations use a probability-adaptive support, replacing the original
fixed cutoff of 20 competing winners. The default omitted-tail tolerance is
`1e-12`; `result.numerical_error_bound` bounds omitted winnings in currency units.
It does not bound floating-point error or uncertainty in the sales model.
Very large supports are rejected rather than allocating unbounded arrays.
Competing row counts above `2**53 - 1` are rejected to avoid losing integer
precision in floating-point calculations.

Actual players may choose nonuniform or correlated rows, including systems.
Neither probability option models that behavior. The calculator also excludes
financing, purchase logistics, automatic promotions/free rows, and automatic
minimum-prize supplements. Payout-rounding reserves returned in later draws can
be supplied as explicit supplements for those draws. Under exhaustive coverage
each configured tier has a winner, so no tier rolls forward from the modeled draw.

## Break-even and plotting

```python
from lottery_analyzer import break_even_rollover, roi_grid

required_rollover = break_even_rollover(
    other_rows=500_000,
    rollovers={"four_bonus": 300_000},
    bracket=(0, 500_000_000),
)
grid = roi_grid([0, 50_000_000, 100_000_000], [10_000_000, 20_000_000])
# Shape (2, 3): contributions on rows, jackpot rollovers on columns.
```

The break-even search holds competing sales fixed and returns the nonnegative-
profit side of the boundary within 0.01 kr. of rollover by default. Payout rounding
creates steps, so an exact zero-profit point need not exist. A bracket that does
not span the threshold raises `ValueError`.

```python
import matplotlib.pyplot as plt
from lottery_analyzer.plotting import plot_roi

ax = plot_roi([0, 50_000_000, 100_000_000], [10_000_000, 20_000_000])
ax.figure.savefig("roi.png")
plt.show()
```

Plotting returns an `Axes`, accepts an existing `ax=`, and never displays or saves
implicitly. The vertical axis is the contribution from other players, not the
total current jackpot.

## Web interface

```sh
python app.py
# Open http://127.0.0.1:5000
```

The interface is in Icelandic, including validation messages and number formatting
(for example, `183.263.850,00`). The Python API remains in English.
The form accepts other players' row count, eligible carryovers, and the probability
model. It displays per-tier expected receipts and ROI. To configure a different
game, call `lottery_analyzer.web.create_app(custom_rules)`. Templates and CSS are
packaged with the library. The development server runs locally without debug mode.

## Compatibility and project layout

`lotteryAnalyzer.lotteryROI`, `breakEven`, and `plotROIFig` remain available.
They now use the current defaults and corrected per-tier calculations; historical
numerical outputs are not preserved. `lotteryROI` retains its two-dimensional
output even for scalar inputs. `breakEven` still searches for an **added jackpot
contribution**, whereas the new `break_even_rollover` searches for a **carryover**.
The legacy solver returns an approximate crossing when payouts are rounded.

| Module | Responsibility |
| --- | --- |
| `rules.py` | Validated immutable rules and exact combination counts |
| `probability.py` | Prize-sharing distributions and payout expectations |
| `model.py` | Per-tier pools, structured results, sales conversion |
| `analysis.py` | Scenario grids and break-even thresholds |
| `plotting.py` | Optional Matplotlib presentation |
| `web.py` | Optional Flask app factory |

## Development

```sh
pytest
ruff check .
ruff format --check .
python -m build
```

Tests include exhaustive competing-ticket enumeration for a small game, no-sales
boundaries, high-competition jackpot expectations, rounding boundaries, carryovers,
break-even thresholds, compatibility wrappers, plots, and Flask form requests.
CI runs the suite on Python 3.11 and 3.14.
