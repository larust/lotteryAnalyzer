# Working on Lottery Analyzer

## Purpose and scope

This project estimates the return from buying every lottery combination exactly
once. It is a reusable Python library with an optional Icelandic Flask interface
and compatibility wrappers for the original code. It does not predict winning
numbers or guarantee profit.

Read [README.md](README.md) for the public API, rule sources, mathematical
assumptions, and limitations. Treat rule defaults and website-derived scenario
defaults as dated snapshots, not live information.

## Development workflow

- Inspect `git status` and relevant code before editing. Preserve existing work.
- Keep changes focused on the requested task; do not commit or push unless asked.
- Support Python 3.11 and later. CI currently checks Python 3.11 and 3.14.
- Reuse `.venv` when available. To set up a new environment:

  ```sh
  python3 -m venv .venv
  .venv/bin/python -m pip install -e '.[web,plot,dev]'
  ```

- Use typed public APIs, validated inputs, and immutable configuration/result
  objects where consistent with the surrounding code.
- Keep calculations independent of presentation. Flask and Matplotlib are
  optional extras and must not become imports required by the core library.
- Keep Python identifiers and library documentation in English. User-facing web
  text, validation messages, and number formatting must remain Icelandic.
- Preserve documented legacy signatures, array shapes, and solver semantics in
  `lotteryAnalyzer.py` unless the task explicitly changes compatibility.

## Code map

Paths below are relative to `lottery_analyzer/` unless otherwise specified.

| Location | Responsibility |
| --- | --- |
| `rules.py` | Immutable rules, tier validation, exact combination counts |
| `payouts.py` | Shared deterministic prize-pool and rounding arithmetic |
| `probability.py` | Competing-winner distributions and payout expectations |
| `model.py` | Per-tier analysis, result objects, sales conversion |
| `analysis.py` | ROI grids and break-even searches |
| `uncertainty.py` | Probability-weighted competing-sales scenarios |
| `defaults.py` | Dated, sourced web-form scenario defaults |
| `web.py`, `templates/`, `static/` | Flask app factory and Icelandic interface |
| `plotting.py` | Optional plotting without implicit display or saving |
| `historical.py` | Historical payout reconciliation and inferred sales bounds |
| `diagnostics.py` | Descriptive historical winner-count diagnostics |
| Root `scripts/collect_history.py` | Collection of official historical results |
| Root `data/`, `docs/`, `tests/` | Observations, generated diagnostics, reports, tests |

## Calculation invariants

- `other_rows` excludes the user's complete set. Add that set's purchases to
  current prize-pool funding exactly once.
- Keep actual carryovers, sales-derived contributions, advertised jackpot
  forecasts, and explicit supplements distinct. A paid jackpot contributes no
  rollover. A forecast is not an observed sales count.
- Parameterize calculations through `LotteryRules`; do not scatter current-game
  constants through the engine. Use exact combinatorics for tier probabilities.
- Round payouts down **per winning row**, then multiply by the user's winning
  rows. Preserve decimal/exact arithmetic at monetary rounding boundaries.
- Reject invalid, nonfinite, negative, or unsupported inputs rather than quietly
  coercing them. Binomial competing-sales counts must be whole numbers.
- Preserve adaptive probability support and the omitted-tail winnings bound.
  Numerical truncation error is not model uncertainty or a profit interval.
- Evaluate each uncertain-sales scenario separately before weighting results.
  Evaluating at average sales is generally not equivalent.
- Payout rounding creates discontinuities. Break-even searches must preserve
  opposite-sign brackets and return an evaluated nonnegative-profit endpoint;
  do not assume an exact root or a globally unique crossing.
- The Poisson and binomial references do not model arbitrary correlated or
  nonuniform ticket choices. Do not present expected ROI as a probability of
  making a profit.

## Historical evidence and updates

Read [the accounting report](docs/HISTORICAL_VALIDATION.md) and
[the winner-count report](docs/WINNER_DIAGNOSTICS.md) before changing historical
inference or interpreting diagnostic results.

- Preserve published observations separately from inferred quantities, including
  source URLs, observation dates, tier order, and applicable rule dates.
- Keep the manually checked five-draw fixture as a separate regression reference.
- Historical draws contain actual participants only: never add the hypothetical
  complete set used by the ROI model to historical accounting.
- Rounded displayed unwon pools are not independently observed exact balances.
  Retain the documented interval assumption and distinguish adjacent-pair
  feasibility from a complete continuous ledger reconstruction.
- Exclude a tested tier's own count and payout from its sales inference. Other
  tiers remain dependent, so this is not independent statistical validation.
- Do not silently discard inconsistent observations or fit model defaults to
  diagnostics and then describe the same sample as independent validation.
- Refresh source data only as part of a task that calls for it. Check returned
  dates and prize categories. Keep tests offline and deterministic.
- When changing game rules or scenario defaults, verify official sources and
  amendments, record the effective/observation dates, and update relevant tests
  and documentation. Do not apply current rules to older draws by assumption.

Reproduce historical checks from the repository root:

```sh
.venv/bin/python -m lottery_analyzer.historical data/historical_draws.json
.venv/bin/python -m lottery_analyzer.historical data/current_rules_draws.json
.venv/bin/python -m lottery_analyzer.diagnostics data/current_rules_draws.json \
  --json-output data/winner_diagnostics.json --report docs/WINNER_DIAGNOSTICS.md
```

Regenerate derived reports when their inputs or diagnostic logic change. The
README documents the separate network-dependent collection command.

## Verification

For code changes, run relevant tests while iterating and these checks before
handing off:

```sh
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
git diff --check
```

CI invokes the `pytest` console script. When changing test imports or pytest
configuration, check both invocation forms; module invocation alone can mask
missing repository paths.

Run `.venv/bin/python -m build` for packaging/dependency changes and before
shipping a release. CI also runs it. Keep templates and static assets in wheels;
keep historical fixtures, reports, and the collector in the source distribution
through `MANIFEST.in`.

For mathematical changes, use independent expected results or small exhaustive
enumerations. Cover relevant zero-sales limits, rounding boundaries, rollover
resets, high competition, invalid inputs, and solver brackets. Do not merely
duplicate the implementation in a test. Documentation-only edits need link/path
and whitespace checks rather than a full test run.

Summarize what changed, what was checked, and any remaining numerical or modeling
limitations. Keep accounting consistency distinct from evidence about player
behavior or forecast accuracy.
