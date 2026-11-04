from datetime import date

import pytest

from app.fx import FxService


@pytest.fixture
def fx(tmp_path):
    (tmp_path / "rates-2024-01-02.json").write_text('{"date":"2024-01-02","base":"USD","rates":{"EUR":"2","GBP":"0.5"}}')
    return FxService(tmp_path)


@pytest.mark.parametrize(
    "minor,expected",
    [(5, 2), (7, 4), (9, 4), (15, 8), (25, 12), (35, 18)],  # EUR minor / 2 -> x.5 cents, half-even
)
def test_hidden_half_even_on_exact_halves(fx, minor, expected):
    assert fx.convert(minor, "EUR", "USD", date(2024, 1, 2)).target.amount_minor == expected


def test_hidden_rounding_happens_once(fx):
    # 1 USD cent -> EUR is 2 cents exactly; GBP 0.5 -> 0.5 cent rounds half-even to 0
    assert fx.convert(1, "USD", "EUR", date(2024, 1, 2)).target.amount_minor == 2
    assert fx.convert(1, "USD", "GBP", date(2024, 1, 2)).target.amount_minor == 0
    assert fx.convert(3, "USD", "GBP", date(2024, 1, 2)).target.amount_minor == 2  # 1.5 -> 2
