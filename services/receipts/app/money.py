"""Integer minor-unit money helpers. No floats: all math is Decimal or int."""

from decimal import ROUND_HALF_EVEN, Decimal

# ISO 4217 minor digits. Unlisted currencies default to 2.
MINOR_DIGITS = {"USD": 2, "EUR": 2, "GBP": 2, "CAD": 2, "INR": 2, "JPY": 0, "KWD": 3}


def minor_digits(currency: str) -> int:
    return MINOR_DIGITS.get(currency, 2)


def to_minor(amount: Decimal, currency: str) -> int:
    """Convert a major-unit Decimal to integer minor units, rounding half-even once."""
    scaled = amount * (Decimal(10) ** minor_digits(currency))
    return int(scaled.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def to_major(minor: int, currency: str) -> Decimal:
    return Decimal(minor) / (Decimal(10) ** minor_digits(currency))


def format_decimal(minor: int, currency: str) -> str:
    """Decimal string with the currency's own minor digits (1500 JPY -> '1500')."""
    digits = minor_digits(currency)
    q = Decimal(1).scaleb(-digits)
    return str(to_major(minor, currency).quantize(q))
