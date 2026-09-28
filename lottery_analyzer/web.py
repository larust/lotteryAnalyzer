"""Optional Flask interface to the public analysis API."""

from flask import Flask, render_template, request

from .defaults import LOTTO_IS_SNAPSHOT
from .model import analyze
from .rules import ICELANDIC_LOTTO, LotteryRules, nonnegative
from .uncertainty import SalesScenario, analyze_sales_uncertainty

_LABELS = {
    "Icelandic Lottó 5/45": "Íslenskt Lottó 5/45",
    "5 correct": "5 réttar",
    "4 + bonus": "4 réttar og bónustala",
    "4 without bonus": "4 réttar án bónustölu",
    "3 + bonus": "3 réttar og bónustala",
    "3 without bonus": "3 réttar án bónustölu",
    "2 + bonus": "2 réttar og bónustala",
}


def format_number(value: float, decimals: int = 0) -> str:
    """Use Icelandic separators without changing process-wide locale settings."""
    return format(value, f",.{decimals}f").translate(str.maketrans(",.", ".,"))


def _form_number(value: str, label: str) -> float:
    try:
        return nonnegative(float(value), label)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{label} verður að vera gild tala, núll eða hærri.") from exc


def create_app(rules: LotteryRules = ICELANDIC_LOTTO) -> Flask:
    app = Flask(__name__)
    snapshot = LOTTO_IS_SNAPSHOT if rules == ICELANDIC_LOTTO else None

    @app.context_processor
    def source_context():
        return {"lotto_snapshot": snapshot}

    app.jinja_env.filters["is_label"] = lambda label: _LABELS.get(label, label)
    app.jinja_env.filters["is_number"] = format_number
    app.jinja_env.filters["is_percent"] = lambda value: (
        ("+" if value > 0 else "") + format_number(value * 100, 2) + " %"
    )

    @app.get("/")
    def index():
        return render_template(
            "index.html", rules=rules, values=snapshot.form_values() if snapshot else {}
        )

    @app.post("/calculate")
    def calculate():
        values = request.form
        try:
            other_rows = _form_number(values.get("other_rows", ""), "Fjöldi raða annarra spilara")
            rollovers = {
                tier.key: _form_number(
                    values.get(f"rollover_{tier.key}", "0"),
                    f"Yfirfærð vinningsupphæð ({_LABELS.get(tier.label, tier.label)})",
                )
                for tier in rules.tiers
                if tier.can_roll_over
            }
            distribution = values.get("distribution", "poisson")
            if distribution not in ("poisson", "binomial"):
                raise ValueError("Veldu Poisson-nálgun eða tvíkostadreifingu.")
            if distribution == "binomial" and not other_rows.is_integer():
                raise ValueError(
                    "Fjöldi raða verður að vera heiltala þegar tvíkostadreifing er valin."
                )
            if other_rows > 2**53 - 1:
                raise ValueError("Fjöldi raða er of mikill fyrir útreikninginn.")
            uncertain = values.get("sales_uncertainty") == "on"
            spread = 0.0
            if uncertain:
                spread = _form_number(values.get("sales_spread", "20"), "Frávik í sölu") / 100
                if spread > 1:
                    raise ValueError("Frávik í sölu má ekki vera meira en 100 %.")
        except ValueError as exc:
            return render_template("index.html", rules=rules, values=values, error=str(exc)), 400
        try:
            uncertainty = None
            if uncertain:
                counts = [other_rows * (1 - spread), other_rows, other_rows * (1 + spread)]
                if distribution == "binomial":
                    counts = [round(count) for count in counts]
                uncertainty = analyze_sales_uncertainty(
                    [
                        SalesScenario(count, weight)
                        for count, weight in zip(counts, (0.25, 0.5, 0.25), strict=True)
                    ],
                    rollovers=rollovers,
                    rules=rules,
                    distribution=distribution,
                )
                result = uncertainty.average
            else:
                result = analyze(
                    other_rows=other_rows,
                    rollovers=rollovers,
                    rules=rules,
                    distribution=distribution,
                )
        except (ValueError, OverflowError):
            return render_template(
                "index.html",
                rules=rules,
                values=values,
                error=(
                    "Gildin eru of stór fyrir útreikninginn. "
                    "Prófaðu lægri upphæðir eða færri raðir."
                ),
            ), 400
        return render_template("results.html", result=result, uncertainty=uncertainty)

    return app
