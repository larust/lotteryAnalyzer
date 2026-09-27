from dataclasses import replace

import matplotlib
import pytest

matplotlib.use("Agg")

from lottery_analyzer import ICELANDIC_LOTTO  # noqa: E402
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


def test_validation_is_icelandic_and_preserves_entered_values():
    client = create_app().test_client()
    response = client.post("/calculate", data={"other_rows": "1.5", "distribution": "binomial"})
    text = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "Fjöldi raða verður að vera heiltala" in text
    assert 'value="1.5"' in text
    assert 'value="binomial" selected' in text


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
