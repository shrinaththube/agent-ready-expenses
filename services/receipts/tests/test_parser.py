import base64
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.parser import parse_receipt
from app.pdf import pdf_text

RECEIPTS = Path(__file__).resolve().parents[3] / "fixtures" / "receipts"
client = TestClient(app)


def read(name):
    return (RECEIPTS / name).read_text()


def test_coffee_receipt():
    r = parse_receipt(read("coffee-usd.txt"))
    assert (r.merchant, r.date, r.total.amount_minor, r.total.currency) == (
        "Blue Bottle Coffee",
        "2024-03-13",
        845,
        "USD",
    )
    assert r.confidence >= 0.8


def test_dinner_receipt_us_date_and_code():
    r = parse_receipt(read("dinner-usd.txt"))
    assert (r.date, r.total.amount_minor, r.total.currency) == ("2024-03-15", 8235, "USD")


def test_subtotal_is_not_the_total():
    assert parse_receipt("Shop\n2024-01-01\nSubtotal 10.00\nTotal 11.50\n").total.amount_minor == 1150


def test_low_confidence_when_unclear():
    r = parse_receipt(read("unclear.txt"))
    assert r.confidence < 0.6


def test_pdf_receipt():
    data = (RECEIPTS / "taxi-usd.pdf").read_bytes()
    assert "Total: $23.40" in pdf_text(data)
    r = client.post("/receipts/parse", json={"pdf_base64": base64.b64encode(data).decode()}).json()
    assert r["merchant"] == "Metro Taxi" and r["total"] == {"amount_minor": 2340, "currency": "USD"}


def test_injection_text_is_just_text():
    r = parse_receipt(read("malicious-injection.txt"))
    assert r.total.amount_minor == 1200 and r.merchant == "Corner Cafe"


def test_api_convert_and_errors():
    ok = client.post("/fx/convert", json={"amount_minor": 10000, "source": "EUR", "date": "2024-03-15"})
    assert ok.status_code == 200 and ok.json()["target"] == {"amount_minor": 10870, "currency": "USD"}
    assert (
        client.post(
            "/fx/convert", json={"amount_minor": 1, "source": "EUR", "date": "2020-01-01"}
        ).status_code
        == 422
    )
    assert client.post("/receipts/parse", json={}).status_code == 400
