"""Expected returns for buying every combination in a main/bonus lottery."""

from .analysis import BreakEvenResult, break_even_contribution, break_even_rollover, roi_grid
from .model import AnalysisResult, TierResult, analyze, rows_from_jackpot_contribution
from .rules import ICELANDIC_LOTTO, LotteryRules, PrizeTier
from .uncertainty import SalesScenario, SalesUncertaintyResult, analyze_sales_uncertainty

__all__ = [
    "ICELANDIC_LOTTO",
    "AnalysisResult",
    "BreakEvenResult",
    "LotteryRules",
    "PrizeTier",
    "SalesScenario",
    "SalesUncertaintyResult",
    "TierResult",
    "analyze",
    "analyze_sales_uncertainty",
    "break_even_contribution",
    "break_even_rollover",
    "roi_grid",
    "rows_from_jackpot_contribution",
]
