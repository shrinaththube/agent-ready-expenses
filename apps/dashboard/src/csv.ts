import type { Expense } from "./contracts.gen";
import { formatAmount } from "./money";

// Format spec: docs/report-format.md (RFC 4180 quoting, CRLF, UTF-8 without BOM,
// fixed header order, ISO dates, amounts with the currency's own minor digits).

const FORMULA_START = /^[=+\-@\t\r]/;

/** Quote one CSV cell and neutralise spreadsheet formula injection. */
export function csvCell(value: string): string {
  let v = value;
  if (FORMULA_START.test(v)) v = `'${v}`;
  return /[",\r\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}

export function toCsv(header: string[], rows: string[][]): string {
  return [header, ...rows].map((r) => r.map(csvCell).join(",")).join("\r\n") + "\r\n";
}

export const EXPENSE_HEADER = [
  "expense_id", "employee_id", "date", "category", "description",
  "amount", "currency", "base_amount", "base_currency", "status",
];

export function expensesCsv(expenses: Expense[]): string {
  const sorted = [...expenses].sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
  return toCsv(
    EXPENSE_HEADER,
    sorted.map((e) => [
      e.id, e.employee_id, e.date, e.category, e.description,
      formatAmount(e.amount), e.amount.currency,
      formatAmount(e.base_amount), e.base_amount.currency, e.status,
    ]),
  );
}
