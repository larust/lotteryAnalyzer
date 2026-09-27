"""Optional Matplotlib presentation. Importing the core does not import it."""

from collections.abc import Sequence

from .analysis import _axis, roi_grid
from .rules import ICELANDIC_LOTTO, LotteryRules


def plot_roi(
    jackpot_rollovers: Sequence[float],
    jackpot_contributions: Sequence[float],
    *,
    rules: LotteryRules = ICELANDIC_LOTTO,
    ax=None,
):
    """Return an Axes containing a contour plot; never show or save implicitly."""
    import matplotlib.pyplot as plt
    import numpy as np

    carried = _axis(jackpot_rollovers, "jackpot_rollovers")
    added = _axis(jackpot_contributions, "jackpot_contributions")
    if any(len(axis) < 2 or np.any(np.diff(axis) <= 0) for axis in (carried, added)):
        raise ValueError("Plot axes need at least two strictly increasing values.")
    if ax is None:
        _, ax = plt.subplots()
    values = roi_grid(carried, added, rules=rules) * 100
    if np.ptp(values) == 0:
        raise ValueError("ROI is constant over this grid; no contours can be drawn.")
    contours = ax.contour(carried, added, values, levels=10)
    ax.clabel(contours, fmt="%.1f%%")
    ax.set(
        xlabel="Jackpot rollover",
        ylabel="Jackpot contribution from other players",
        title=f"Expected return on investment — {rules.name}",
    )
    return ax
