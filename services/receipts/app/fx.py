"""FX conversion from dated rate files in fixtures/fx.

Rules: use the rate on the expense date (never today's), do all math in Decimal,
round half-even exactly once at the end.
"""

import json
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

from .contracts_gen import FxQuote, Money
from .money import minor_digits

MAX_FALLBACK_DAYS = 7


class RateNotFound(LookupError):
    pass


class FxService:
    def __init__(self, rates_dir: Path):
        self._rates: dict[date, dict[str, Decimal]] = {}
        for p in sorted(Path(rates_dir).glob("rates-*.json")):
            doc = json.loads(p.read_text())
            rates = {c: Decimal(v) for c, v in doc["rates"].items()}
            rates[doc["base"]] = Decimal(1)
            self._rates[date.fromisoformat(doc["date"])] = rates

    def rates_on(self, on: date) -> tuple[date, dict[str, Decimal]]:
        """Rates effective on `on`: an exact file, else the latest earlier file within a week
        (weekends and holidays)."""
        for back in range(MAX_FALLBACK_DAYS + 1):
            d = on - timedelta(days=back)
            if d in self._rates:
                return d, self._rates[d]
        raise RateNotFound(f"no FX rates on or within {MAX_FALLBACK_DAYS} days before {on}")

    def convert(self, amount_minor: int, source: str, target: str, on: date) -> FxQuote:
        rate_date, rates = self.rates_on(on)
        for c in (source, target):
            if c not in rates:
                raise RateNotFound(f"no {c} rate for {rate_date}")
        # amount_minor[src] -> minor[tgt], one division/multiplication chain, one rounding.
        scale = Decimal(10) ** minor_digits(target) / Decimal(10) ** minor_digits(source)
        exact = Decimal(amount_minor) * scale * rates[target] / rates[source]
        target_minor = int(exact.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
        return FxQuote(
            source=Money(amount_minor=amount_minor, currency=source),
            target=Money(amount_minor=target_minor, currency=target),
            rate=str(rates[source]),
            rate_date=rate_date.isoformat(),
        )
