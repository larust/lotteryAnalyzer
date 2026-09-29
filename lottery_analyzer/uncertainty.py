"""Finite probability distributions over competing sales volumes."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import fsum, isclose

from .model import AnalysisResult, TierResult, analyze
from .probability import DEFAULT_TAIL_PROBABILITY, Distribution
from .rules import ICELANDIC_LOTTO, LotteryRules, nonnegative


@dataclass(frozen=True, slots=True)
class SalesScenario:
    other_rows: float
    probability: float

    def __post_init__(self) -> None:
        nonnegative(self.other_rows, "other_rows")
        if not 0 < nonnegative(self.probability, "probability") <= 1:
            raise ValueError("Scenario probability must be in (0, 1].")


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    probability: float
    analysis: AnalysisResult


@dataclass(frozen=True, slots=True)
class SalesUncertaintyResult:
    scenarios: tuple[ScenarioResult, ...]
    average: AnalysisResult


def analyze_sales_uncertainty(
    scenarios: Sequence[SalesScenario],
    *,
    rollovers: Mapping[str, float] | None = None,
    supplements: Mapping[str, float] | None = None,
    rules: LotteryRules = ICELANDIC_LOTTO,
    distribution: Distribution = "poisson",
    tail_probability: float = DEFAULT_TAIL_PROBABILITY,
) -> SalesUncertaintyResult:
    """Average conditional results, not the sales inputs.

    Probabilities must sum to one. Each scenario recalculates sales-funded pools,
    competing winner counts, and payout rounding. Carryovers and supplements are
    held fixed across scenarios. average.other_rows is the mean sales count;
    average's payouts are expectations over scenarios, not a run at that count.
    Scenario variation is NOT the distribution of realized lottery profits.
    """
    scenarios = tuple(scenarios)
    if not scenarios or any(not isinstance(s, SalesScenario) for s in scenarios):
        raise ValueError("Provide at least one SalesScenario.")
    total = fsum(s.probability for s in scenarios)
    if not isclose(total, 1, abs_tol=1e-12, rel_tol=0):
        raise ValueError("Scenario probabilities must sum to one.")
    results = tuple(
        ScenarioResult(
            s.probability / total,
            analyze(
                other_rows=s.other_rows,
                rollovers=rollovers,
                supplements=supplements,
                rules=rules,
                distribution=distribution,
                tail_probability=tail_probability,
            ),
        )
        for s in scenarios
    )
    tiers = tuple(
        TierResult(
            tier.key,
            tier.label,
            tier.winning_rows,
            fsum(s.probability * s.analysis.tiers[i].pool for s in results),
            fsum(s.probability * s.analysis.tiers[i].expected_competing_winners for s in results),
            fsum(s.probability * s.analysis.tiers[i].expected_winnings for s in results),
            fsum(s.probability * s.analysis.tiers[i].numerical_error_bound for s in results),
        )
        for i, tier in enumerate(results[0].analysis.tiers)
    )
    average = AnalysisResult(
        rules, fsum(s.probability * s.analysis.other_rows for s in results), distribution, tiers
    )
    return SalesUncertaintyResult(results, average)
