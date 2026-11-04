# 0001: Money is integer minor units plus a currency code

Status: accepted

Floats cannot represent most decimal amounts exactly, and a rounding error in money is a correctness bug, not a cosmetic one. Every amount is `{amount_minor: integer, currency: ISO 4217}`. Go uses `int64`, Python uses `Decimal` for FX math and converts back to an integer once, TypeScript uses integers and formats only at display. Currencies differ in minor digits (JPY 0, USD 2, KWD 3), so formatting and parsing go through a per-currency digits table. The contract generator rejects JSON-Schema `number` on money-like property names, and the eval grader scans diffs for float money.

Consequence: some code is more verbose than `amount * 1.1`. That is the point.
