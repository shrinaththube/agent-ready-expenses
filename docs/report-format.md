# CSV format spec

All CSV exports from the dashboard follow these rules. Golden files in `apps/dashboard/test/golden/` pin the exact bytes.

## General rules

- UTF-8, **no byte-order mark**.
- RFC 4180 quoting: a cell containing `,` `"` CR or LF is wrapped in double quotes and inner quotes are doubled.
- Rows end with CRLF (`\r\n`), including the last row.
- The header row is always present, with the column order fixed below.
- Dates are ISO 8601 `YYYY-MM-DD`; months are `YYYY-MM`.
- Amounts are decimal strings built from integer minor units using **the currency's own minor digits** (`1500 JPY` -> `1500`, `12345 KWD` -> `12.345`, `4200 USD` -> `42.00`). No thousands separators, no currency symbols, no floats.
- **Formula injection:** a text cell that begins with `=`, `+`, `-`, `@`, TAB or CR is prefixed with a single quote (`'`) before quoting.

## Expenses export (`expensesCsv`)

Columns: `expense_id,employee_id,date,category,description,amount,currency,base_amount,base_currency,status`

Rows sorted by `date`, then `expense_id`.

## Monthly report export (`monthlyReportCsv`)

Columns: `month,employee_id,category,count,total,currency`

- One row per `ReportRow` from `GET /reports` (approved spend in the base currency).
- `count` is an integer; `total` is the row's `total` money formatted as above and `currency` is its currency code.
- Rows sorted by `month`, then `employee_id`, then `category` (ascending, plain string comparison).
