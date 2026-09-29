from dataclasses import replace

import matplotlib
import pytest

matplotlib.use("Agg")

from lottery_analyzer import ICELANDIC_LOTTO  # noqa: E402
from lottery_analyzer.defaults import LOTTO_IS_SNAPSHOT  # noqa: E402
from lottery_analyzer.plotting import plot_roi  # noqa: E402
from lottery_analyzer.web import create_app  # noqa: E402


def test_web_form_calculates_and_serves_assets():
    app = create_app()
    app.testing = True
    client = app.test_client()
    page = client.get("/")
    assert page.status_code == 200
    assert b'action="/calculate"' in page.data
    assert b'lang="is"' in page.data
    assert b"183.263.850,00" in page.data
    assert client.get("/static/style.css").status_code == 200
    result = client.post(
        "/calculate",
        data={
            "other_rows": "0",
            "rollover_jackpot": "100000000",
            "rollover_four_bonus": "1000",
            "distribution": "binomial",
        },
    )
    assert result.status_code == 200
    assert "Vænt ávöxtun" in result.get_data(as_text=True)
    assert "4 réttar og bónustala" in result.get_data(as_text=True)


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"other_rows": "-1"},
        {"other_rows": "nan"},
        {"other_rows": "inf"},
        {"other_rows": "abc"},
        {"other_rows": "1", "rollover_jackpot": "-1"},
        {"other_rows": "1.5", "distribution": "binomial"},
        {"other_rows": "1", "distribution": "invalid"},
    ],
)
def test_bad_web_inputs_are_user_errors(data):
    app = create_app()
    app.testing = True
    result = app.test_client().post("/calculate", data=data)
    assert result.status_code == 400
    assert b'role="alert"' in result.data


def test_app_factory_accepts_custom_rules():
    rules = replace(ICELANDIC_LOTTO, name="Custom lottery", row_price=200)
    page = create_app(rules).test_client().get("/")
    assert b"Custom lottery" in page.data
    assert b"244.351.800,00" in page.data
    assert b"www.lotto.is" not in page.data
    assert b'value="259909"' not in page.data


def test_sourced_defaults_distinguish_forecast_from_carryover():
    snapshot = LOTTO_IS_SNAPSHOT
    assert snapshot.estimated_other_rows == 259_909
    values = snapshot.form_values()
    assert values["rollover_jackpot"] == values["rollover_four_bonus"] == "0"
    client = create_app().test_client()
    text = client.get("/").get_data(as_text=True)
    assert 'value="259909"' in text
    assert "28.09.2026" in text
    assert "10.000.000 kr." in text
    assert "Þetta er ekki birt sölutala" in text
    assert snapshot.forecast_url in text and snapshot.results_url in text
    assert client.post("/calculate", data=values).status_code == 200


def test_validation_is_icelandic_and_preserves_entered_values():
    client = create_app().test_client()
    response = client.post("/calculate", data={"other_rows": "1.5", "distribution": "binomial"})
    text = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "Fjöldi raða verður að vera heiltala" in text
    assert 'value="1.5"' in text
    assert 'value="binomial" selected' in text


def test_uncertain_sales_form_shows_weighted_scenarios():
    client = create_app().test_client()
    response = client.post(
        "/calculate",
        data={
            "other_rows": "100",
            "sales_uncertainty": "on",
            "sales_spread": "20",
            "distribution": "binomial",
        },
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "80,00" in text and "120,00" in text
    assert "Veginn meðalfjöldi" in text
    assert "ekki líkur á hagnaði eða tapi" in text
    invalid = client.post(
        "/calculate",
        data={
            "other_rows": "100",
            "sales_uncertainty": "on",
            "sales_spread": "101",
        },
    )
    assert invalid.status_code == 400
    assert "má ekki vera meira en 100" in invalid.get_data(as_text=True)


def test_plot_returns_reusable_axes_and_correct_labels(tmp_path):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    assert plot_roi([0, 1e8], [0, 1e7], ax=ax) is ax
    assert "contribution" in ax.get_ylabel()
    fig.savefig(tmp_path / "roi.png")
    assert (tmp_path / "roi.png").stat().st_size > 0
    plt.close(fig)
    with pytest.raises(ValueError, match="increasing"):
        plot_roi([0], [1, 2])
