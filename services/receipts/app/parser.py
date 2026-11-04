"""Rule-based receipt parsing: regex plus small heuristics. No ML.

Confidence is the sum of independent signals (max 1.0). Below 0.6 the dashboard
asks the user to confirm the parse.
"""

import re
from datetime import date
from decimal import Decimal

from .contracts_gen import Money, ParsedReceipt
from .money import to_minor

MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
    )
}
TOTAL_LABEL = re.compile(r"\b(grand\s+total|total\s+due|amount\s+due|balance\s+due|total)\b", re.I)
SUBTOTAL = re.compile(r"sub\s*-?\s*total", re.I)
NUMBER = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")

W_TOTAL, W_DATE, W_CURRENCY, W_MERCHANT = 0.4, 0.2, 0.2, 0.2


def parse_date(text: str) -> date | None:
    if m := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        return _safe(int(m[1]), int(m[2]), int(m[3]))
    if m := re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text):
        return _safe(int(m[3]), int(m[1]), int(m[2]))  # US month/day/year
    if m := re.search(r"\b(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?,?\s+(\d{4})\b", text):
        return _safe(int(m[3]), MONTHS.get(m[2].lower(), 0), int(m[1]))
    if m := re.search(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b", text):
        return _safe(int(m[3]), MONTHS.get(m[1].lower(), 0), int(m[2]))
    return None


def _safe(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def detect_currency(line: str) -> str | None:
    """Currency named on the line: a `$` symbol or the code USD."""
    if re.search(r"\bUSD\b", line) or "$" in line:
        return "USD"
    return None


def parse_amount(token: str, currency: str) -> int:
    return to_minor(Decimal(token.replace(",", "")), currency)


def parse_merchant(lines: list[str]) -> str | None:
    for ln in lines[:3]:
        if re.search(r"[A-Za-z]{3}", ln) and not parse_date(ln) and not TOTAL_LABEL.search(ln):
            return ln.strip()
    return None


def parse_receipt(text: str) -> ParsedReceipt:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    confidence = 0.0

    merchant = parse_merchant(lines)
    if merchant:
        confidence += W_MERCHANT

    when = parse_date(text)
    if when:
        confidence += W_DATE

    currency, amount_token, labelled = None, None, False
    for ln in reversed(lines):
        if TOTAL_LABEL.search(ln) and not SUBTOTAL.search(ln):
            nums = NUMBER.findall(ln)
            if nums:
                amount_token, labelled = nums[-1], True
                currency = detect_currency(ln)
                break
    if amount_token is None:  # fall back to the largest number in the document
        nums = [n for ln in lines for n in NUMBER.findall(ln) if "." in n]
        amount_token = max(nums, key=lambda n: Decimal(n.replace(",", "")), default="0")
    if labelled:
        confidence += W_TOTAL
    if currency is None:
        currency = next((c for ln in lines if (c := detect_currency(ln))), None)
    if currency:
        confidence += W_CURRENCY

    cur = currency or "USD"
    return ParsedReceipt(
        merchant=merchant or "Unknown",
        date=when.isoformat() if when else "1970-01-01",
        total=Money(amount_minor=parse_amount(amount_token, cur), currency=cur),
        confidence=round(confidence, 2),
    )
