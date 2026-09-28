"""Compatibility entry points. New code should import lottery_analyzer.

Names and grid orientation are retained; defaults now use current rules and
corrected per-tier payouts. Historical numerical outputs are not preserved.
"""

from lottery_analyzer import ICELANDIC_LOTTO, break_even_contribution, roi_grid
from lottery_analyzer.rules import nonnegative


def lotteryROI(lastWin, addWin, *, rules=ICELANDIC_LOTTO):
    """Return a 2D ROI grid: rows = added contributions, columns = rollovers."""
    return roi_grid(lastWin, addWin, rules=rules)


def breakEven(
    lastWin,
    curWin0,
    curWin1,
    *,
    rules=ICELANDIC_LOTTO,
    money_tolerance=0.01,
    full_output=False,
):
    """Find a profit crossing in *added contribution*, at fixed scalar rollover.

    Returns the evaluated profitable endpoint, preserving the scalar interface.
    full_output=True returns both endpoints and their profits. Rounded payouts
    need not have an exact zero; the result brackets one local crossing.
    """
    rollover = nonnegative(lastWin, "lastWin")
    result = break_even_contribution(
        rollover, (curWin0, curWin1), rules=rules, money_tolerance=money_tolerance
    )
    return result if full_output else result.profitable_value


def plotROIFig(lastWin, addWin, *, rules=ICELANDIC_LOTTO):
    """Return a Matplotlib Axes without showing it."""
    from lottery_analyzer.plotting import plot_roi

    return plot_roi(lastWin, addWin, rules=rules)
