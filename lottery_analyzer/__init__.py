"""Expected returns for buying every combination in a main/bonus lottery."""

from .analysis import break_even_rollover, roi_grid
from .model import AnalysisResult, TierResult, analyze, rows_from_jackpot_contribution
from .rules import ICELANDIC_LOTTO, LotteryRules, PrizeTier

__all__ = [
    "ICELANDIC_LOTTO",
    "AnalysisResult",
    "LotteryRules",
    "PrizeTier",
    "TierResult",
    "analyze",
    "break_even_rollover",
    "roi_grid",
    "rows_from_jackpot_contribution",
]
