from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.fx import FxService, RateNotFound
from app.money import format_decimal, minor_digits, to_minor

RATES = Path(__file__).resolve().parents[3] / "fixtures" / "fx"
fx = FxService(RATES)


def test_uses_rate_on_expense_date_not_latest():
    # 2024-03-15 EUR rate is 0.92; the latest file (2024-06-14) is 0.933.
    q = fx.convert(10000, "EUR", "USD", date(2024, 3, 15))
    assert q.target.amount_minor == 10870  # 100 / 0.92 = 108.6956... -> 10870
    assert q.rate_date == "2024-03-15"


def test_weekend_uses_previous_business_day():
    q = fx.convert(10000, "EUR", "USD", date(2024, 3, 17))  # Sunday
    assert q.rate_date == "2024-03-15"


def test_no_rate_within_a_week_raises():
    with pytest.raises(RateNotFound):
        fx.convert(100, "EUR", "USD", date(2024, 1, 1))


def test_unknown_currency_raises():
    with pytest.raises(RateNotFound):
        fx.convert(100, "XYZ", "USD", date(2024, 3, 15))


@pytest.mark.parametrize(
    "amount,src,tgt,expected",
    [
        (150000, "JPY", "USD", 1003),  # 1500 JPY / 149.5 = 10.0334 USD
        (12345, "KWD", "USD", 4021),  # 12.345 KWD / 0.307 = 40.2117 USD
        (1000, "USD", "JPY", 1495),  # 10 USD -> 1495 JPY (0 minor digits)
        (1000, "USD", "KWD", 3070),  # 10 USD -> 3.070 KWD (3 minor digits)
        (1000, "USD", "USD", 1000),
        (1000, "USD", "BHD", 3760),  # 10 USD -> 3.760 BHD (3 minor digits)
    ],
)
def test_minor_digit_handling(amount, src, tgt, expected):
    # JPY rows use minor units = yen, so 1500 yen is amount 1500 not 150000.
    if src == "JPY":
        amount = 1500
    assert fx.convert(amount, src, tgt, date(2024, 3, 15)).target.amount_minor == expected


def test_round_trip_display():
    for cur, minor, text in [
        ("JPY", 1500, "1500"),
        ("KWD", 12345, "12.345"),
        ("BHD", 3760, "3.760"),
        ("USD", 5, "0.05"),
    ]:
        assert format_decimal(minor, cur) == text
        assert to_minor(Decimal(text), cur) == minor


def test_bankers_rounding_applied_once(tmp_path):
    (tmp_path / "rates-2024-01-02.json").write_text('{"date":"2024-01-02","base":"USD","rates":{"EUR":"2"}}')
    svc = FxService(tmp_path)
    # 0.05 EUR / 2 = 0.025 USD = 2.5 cents -> half-even -> 2; 0.07 EUR -> 3.5 -> 4
    assert svc.convert(5, "EUR", "USD", date(2024, 1, 2)).target.amount_minor == 2
    assert svc.convert(7, "EUR", "USD", date(2024, 1, 2)).target.amount_minor == 4
    assert svc.convert(9, "EUR", "USD", date(2024, 1, 2)).target.amount_minor == 4  # 4.5 -> 4


def test_digits_table():
    assert (minor_digits("JPY"), minor_digits("KWD"), minor_digits("USD")) == (0, 3, 2)
