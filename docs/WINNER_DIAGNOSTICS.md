# Historical winner-count diagnostics

71 draws: 2025-05-24 through 2026-09-26.

Accounting checks: 71/71 draws reconcile under the assumptions below.

Reference: binomial; 95% central count envelopes.

Sales are inferred from prize tables, not independently published sales. For each
tier, its own current winner count and payout are excluded from sales inference.
The expected-count range retains the entire compatible integer sales interval.
The envelope uses the lower quantile at minimum sales and upper quantile at maximum sales.

| Tier | Draws | Observed total | Expected total range | Outside envelope | Mean squared Pearson residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5 correct | 71 | 27 | 28.97–28.97 | 0 | 0.91 |
| 4 + bonus | 71 | 124 | 144.84–144.84 | 1 | 1.07 |
| 4 without bonus | 71 | 5,434 | 5,648.66–5,648.73 | 23 | 3.69 |
| 3 + bonus | 71 | 11,048 | 11,297.36–11,297.39 | 37 | 10.00 |
| 3 without bonus | 71 | 213,852 | 214,649.89–214,650.33 | 59 | 64.39 |
| 2 + bonus | 71 | 209,374 | 214,649.89–214,650.33 | 60 | 77.21 |

Interpretation and limitations:

- A mean squared Pearson residual near 1 is the independent-row reference. Larger values describe excess variation or mean mismatch; they do not identify a cause.
- Residuals use interval-midpoint sales. These are descriptive diagnostics, not fitted dispersion parameters or formal significance tests.
- Other tiers share the same draw and ticket population. Leaving out one tier avoids direct self-calibration but does not create independent sales measurements.
- Count envelopes are discrete; coverage can exceed the nominal level. Across many draws and tiers, some exceedances are expected. No multiple-testing significance claim is made.
- The accounting inversion assumes the configured allocation, no supplemental funding, and rounded displays of unwon pools. It checks adjacent pairs, not a continuous prize ledger.
- Duplicate selections, systems, nonuniform number preferences, or model/data mismatches can affect dispersion. This sample cannot distinguish these causes.
- These are retrospective counts conditional on inferred sales, not a backtest of advance sales forecasts or proof of profitable play.

Per-draw sources and observations are stored in `data/current_rules_draws.json`.
Per-tier intervals and residuals are stored in `data/winner_diagnostics.json`.
