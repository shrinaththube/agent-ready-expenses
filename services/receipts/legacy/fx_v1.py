"""DEPRECATED - do not use, do not copy, do not fix here.

Superseded by app/fx.py. This module uses floats and today's rate instead of the
expense-date rate. It is kept only until the last importer is removed.
"""

import json
from datetime import date
from pathlib import Path


def convert(amount, source, target, rates_dir):
    rates_file = sorted(Path(rates_dir).glob("rates-*.json"))[-1]  # "today's" (latest) rate
    rates = json.loads(rates_file.read_text())["rates"]
    usd = float(amount) / float(rates.get(source, 1))
    return round(usd * float(rates.get(target, 1)), 2), date.today().isoformat()
