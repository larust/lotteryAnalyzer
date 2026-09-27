"""Compatibility entry points. New code should import lottery_analyzer.

Names and grid orientation are retained; defaults now use current rules and
corrected per-tier payouts. Historical numerical outputs are not preserved.
"""

from scipy.optimize import brentq

from lottery_analyzer import ICELANDIC_LOTTO, roi_grid
from lottery_analyzer.rules import nonnegative


def lotteryROI(lastWin, addWin, *, rules=ICELANDIC_LOTTO):
    """Return a 2D ROI grid: rows = added contributions, columns = rollovers."""
    return roi_grid(lastWin, addWin, rules=rules)


def breakEven(lastWin, curWin0, curWin1, *, rules=ICELANDIC_LOTTO):
    """Find a break-even *added contribution*, with fixed scalar rollover.

    With payout rounding this is a numerical crossing, not necessarily an exact
    zero. Prefer lottery_analyzer.break_even_rollover for a profitable threshold
    at fixed competing sales.
    """
    rollover = nonnegative(lastWin, "lastWin")
    low = nonnegative(curWin0, "curWin0")
    high = nonnegative(curWin1, "curWin1")
    if low >= high:
        raise ValueError("Contribution bounds must be increasing.")

    def roi(contribution):
        return float(lotteryROI(rollover, contribution, rules=rules)[0, 0])

    if roi(low) * roi(high) > 0:
        raise ValueError("Contribution bounds must bracket a break-even crossing.")
    return brentq(roi, low, high, xtol=0.01)


def plotROIFig(lastWin, addWin, *, rules=ICELANDIC_LOTTO):
    """Return a Matplotlib Axes without showing it."""
    from lottery_analyzer.plotting import plot_roi

    return plot_roi(lastWin, addWin, rules=rules)
