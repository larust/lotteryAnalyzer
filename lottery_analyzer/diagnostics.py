"""Descriptive winner-count diagnostics using leave-one-tier-out inferred sales."""

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from scipy.stats import binom, poisson

from .historical import Draw, load_draws, validate_draw
from .rules import ICELANDIC_LOTTO, LotteryRules


@dataclass(frozen=True)
class WinnerDiagnostic:
    date: str
    tier: str
    observed: int
    minimum_rows: int
    maximum_rows: int
    expected_low: float
    expected_high: float
    predictive_low: int
    predictive_high: int
    pearson_squared: float

    @property
    def outside_envelope(self) -> bool:
        return not self.predictive_low <= self.observed <= self.predictive_high


def diagnose_draw(
    draw: Draw,
    previous: Draw | None = None,
    *,
    rules: LotteryRules = ICELANDIC_LOTTO,
    distribution: str = "binomial",
    coverage: float = 0.95,
) -> tuple[WinnerDiagnostic, ...]:
    """Exclude the tested tier's payout and count when inferring its sales range.

    Other tiers remain dependent observations. Envelopes are reference-model
    diagnostics, not calibrated conditional confidence intervals or p-values.
    Incompatible sales constraints raise rather than silently dropping a draw.
    """
    if distribution not in ("binomial", "poisson"):
        raise ValueError("Choose binomial or poisson.")
    if not 0 < coverage < 1:
        raise ValueError("coverage must lie strictly between zero and one.")
    result = []
    tail = (1 - coverage) / 2
    for i, tier in enumerate(rules.tiers):
        sales = validate_draw(draw, previous, rules=rules, exclude_tiers=(tier.key,))
        if not sales.consistent or sales.minimum_rows <= 0:
            raise ValueError(f"{draw.date}: incompatible sales constraints excluding {tier.key}")
        probability = tier.winning_rows(rules.number_count, rules.draw_count) / rules.combinations
        low, high = sales.minimum_rows, sales.maximum_rows
        expected_low, expected_high = low * probability, high * probability
        mean = (expected_low + expected_high) / 2
        if distribution == "binomial":
            lower = binom.ppf(tail, low, probability)
            upper = binom.ppf(1 - tail, high, probability)
            variance = mean * (1 - probability)
        else:
            lower = poisson.ppf(tail, expected_low)
            upper = poisson.ppf(1 - tail, expected_high)
            variance = mean
        result.append(
            WinnerDiagnostic(
                draw.date.isoformat(),
                tier.key,
                draw.winners[i],
                low,
                high,
                expected_low,
                expected_high,
                int(lower),
                int(upper),
                (draw.winners[i] - mean) ** 2 / variance,
            )
        )
    return tuple(result)


def historical_diagnostics(draws, *, distribution="binomial", coverage=0.95):
    """Diagnose ordered observations; gaps disable the previous-draw constraint."""
    results = []
    for i, draw in enumerate(draws):
        if i and draw.date <= draws[i - 1].date:
            raise ValueError("Draw dates must be unique and in increasing order.")
        previous = draws[i - 1] if i and (draw.date - draws[i - 1].date).days == 7 else None
        results.extend(diagnose_draw(draw, previous, distribution=distribution, coverage=coverage))
    return tuple(results)


def render_report(draws, diagnostics, *, distribution, coverage):
    if not draws:
        raise ValueError("At least one draw is required.")
    accounting = []
    for i, draw in enumerate(draws):
        previous = draws[i - 1] if i and (draw.date - draws[i - 1].date).days == 7 else None
        accounting.append(validate_draw(draw, previous).consistent)
    lines = [
        "# Historical winner-count diagnostics",
        "",
        f"{len(draws)} draws: {draws[0].date} through {draws[-1].date}.",
        "",
        f"Accounting checks: {sum(accounting)}/{len(draws)} draws reconcile "
        "under the assumptions below.",
        "",
        f"Reference: {distribution}; {coverage:.0%} central count envelopes.",
        "",
        "Sales are inferred from prize tables, not independently published sales. For each",
        "tier, its own current winner count and payout are excluded from sales inference.",
        "The expected-count range retains the entire compatible integer sales interval.",
        (
            "The envelope uses the lower quantile at minimum sales and upper "
            "quantile at maximum sales."
        ),
        "",
        (
            "| Tier | Draws | Observed total | Expected total range | Outside "
            "envelope | Mean squared Pearson residual |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tier in ICELANDIC_LOTTO.tiers:
        rows = [r for r in diagnostics if r.tier == tier.key]
        lines.append(
            f"| {tier.label} | {len(rows)} | {sum(r.observed for r in rows):,} | "
            f"{sum(r.expected_low for r in rows):,.2f}–{sum(r.expected_high for r in rows):,.2f} | "
            f"{sum(r.outside_envelope for r in rows)} | "
            f"{sum(r.pearson_squared for r in rows) / len(rows):.2f} |"
        )
    lines += [
        "",
        "Interpretation and limitations:",
        "",
        (
            "- A mean squared Pearson residual near 1 is the independent-row "
            "reference. Larger values describe excess variation or mean mismatch; "
            "they do not identify a cause."
        ),
        (
            "- Residuals use interval-midpoint sales. These are descriptive "
            "diagnostics, not fitted dispersion parameters or formal significance "
            "tests."
        ),
        (
            "- Other tiers share the same draw and ticket population. Leaving out "
            "one tier avoids direct self-calibration but does not create "
            "independent sales measurements."
        ),
        (
            "- Count envelopes are discrete; coverage can exceed the nominal level. "
            "Across many draws and tiers, some exceedances are expected. No "
            "multiple-testing significance claim is made."
        ),
        (
            "- The accounting inversion assumes the configured allocation, no "
            "supplemental funding, and rounded displays of unwon pools. It checks "
            "adjacent pairs, not a continuous prize ledger."
        ),
        (
            "- Duplicate selections, systems, nonuniform number preferences, or "
            "model/data mismatches can affect dispersion. This sample cannot "
            "distinguish these causes."
        ),
        (
            "- These are retrospective counts conditional on inferred sales, not a "
            "backtest of advance sales forecasts or proof of profitable play."
        ),
        "",
        "Per-draw sources and observations are stored in `data/current_rules_draws.json`.",
        "Per-tier intervals and residuals are stored in `data/winner_diagnostics.json`.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--distribution", choices=("binomial", "poisson"), default="binomial")
    parser.add_argument("--coverage", type=float, default=0.95)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    draws = load_draws(args.fixture)
    diagnostics = historical_diagnostics(
        draws, distribution=args.distribution, coverage=args.coverage
    )
    report = render_report(
        draws, diagnostics, distribution=args.distribution, coverage=args.coverage
    )
    if args.json_output:
        args.json_output.write_text(
            json.dumps(
                {
                    "distribution": args.distribution,
                    "coverage": args.coverage,
                    "sales_method": "leave-one-tier-out accounting intervals; not measured sales",
                    "diagnostics": [
                        {**asdict(d), "outside_envelope": d.outside_envelope} for d in diagnostics
                    ],
                },
                indent=2,
            )
            + "\n"
        )
    if args.report:
        args.report.write_text(report)
    else:
        print(report)


if __name__ == "__main__":
    main()
