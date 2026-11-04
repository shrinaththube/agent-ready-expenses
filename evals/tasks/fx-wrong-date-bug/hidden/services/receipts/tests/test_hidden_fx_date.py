from datetime import date
from pathlib import Path

from app.fx import FxService

RATES = Path(__file__).resolve().parents[3] / "fixtures" / "fx"
fx = FxService(RATES)


def test_hidden_rate_follows_expense_date():
    # EUR per USD: 03-15 -> 0.92, 03-18 -> 0.917, latest file (06-14) -> 0.933
    assert fx.convert(10000, "EUR", "USD", date(2024, 3, 15)).target.amount_minor == 10870
    assert fx.convert(10000, "EUR", "USD", date(2024, 3, 18)).target.amount_minor == 10905
    assert fx.convert(10000, "EUR", "USD", date(2024, 3, 15)).rate_date == "2024-03-15"


def test_hidden_other_currencies_by_date():
    assert fx.convert(1500, "JPY", "USD", date(2024, 3, 15)).target.amount_minor == 1003
    assert fx.convert(1500, "JPY", "USD", date(2024, 3, 11)).target.amount_minor == 1012  # 1500/148.20


def test_hidden_weekend_uses_previous_file():
    assert fx.convert(10000, "EUR", "USD", date(2024, 3, 16)).rate_date == "2024-03-15"
