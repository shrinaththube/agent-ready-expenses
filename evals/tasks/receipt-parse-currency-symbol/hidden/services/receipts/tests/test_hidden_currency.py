import pytest

from app.parser import parse_receipt


@pytest.mark.parametrize(
    "text,amount,currency",
    [
        ("Café de Flore\n2024-03-14\nTotal: €45,90\n", 4590, "EUR"),
        ("Hotel Lumière\n14 Mar 2024\nTOTAL EUR 1.234,50\n", 123450, "EUR"),
        ("Pret a Manger\n15 Mar 2024\nSubtotal £10.00\nTotal £12.00\n", 1200, "GBP"),
        ("Tokyo Ramen\n2024-03-15\nTotal ¥1,500\n", 1500, "JPY"),
        ("Tokyo Ramen\n2024-03-15\nTotal JPY 12,000\n", 12000, "JPY"),
        ("Kuwait Cafe\n2024-03-15\nTotal KWD 12.345\n", 12345, "KWD"),
        ("Blue Bottle\n2024-03-13\nTotal $1,234.50\n", 123450, "USD"),
        ("Brasserie\nMar 14, 2024\nAmount due 45,90 EUR\n", 4590, "EUR"),
    ],
)
def test_hidden_amount_and_currency(text, amount, currency):
    r = parse_receipt(text)
    assert (r.total.amount_minor, r.total.currency) == (amount, currency)
    assert r.confidence >= 0.8


def test_hidden_low_confidence_when_currency_and_merchant_unknown():
    assert parse_receipt("Total 45,90\n").confidence < 0.6


def test_hidden_confidence_is_a_probability():
    for t in ["Total €45,90", "x", "Shop\n2024-01-01\nTotal £5.00"]:
        assert 0.0 <= parse_receipt(t).confidence <= 1.0


def test_hidden_date_is_parsed_with_euro_symbol():
    assert parse_receipt("Café\n14 Mar 2024\nTotal €5,00\n").date == "2024-03-14"
