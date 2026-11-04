import type { Money } from "./contracts.gen";

// Money is integer minor units + ISO currency code. No floats: amounts are
// formatted from integers by string manipulation, and parsed from strings.
const MINOR_DIGITS: Record<string, number> = { USD: 2, EUR: 2, GBP: 2, CAD: 2, INR: 2, JPY: 0, KWD: 3 };

export function minorDigits(currency: string): number {
  return MINOR_DIGITS[currency] ?? 2;
}

/** Decimal string with the currency's own digits: 1500 JPY -> "1500", 12345 KWD -> "12.345". */
export function formatAmount(m: Money): string {
  const digits = minorDigits(m.currency);
  const neg = m.amount_minor < 0;
  let s = String(Math.abs(m.amount_minor));
  if (digits > 0) {
    s = s.padStart(digits + 1, "0");
    s = `${s.slice(0, -digits)}.${s.slice(-digits)}`;
  }
  return neg ? `-${s}` : s;
}

/** Display string, e.g. "75.00 USD". */
export function formatMoney(m: Money): string {
  return `${formatAmount(m)} ${m.currency}`;
}

/** Parse a user-typed decimal string ("12.5", "1500") into minor units. Rejects excess digits. */
export function parseMinor(text: string, currency: string): number | null {
  const digits = minorDigits(currency);
  const m = /^(\d+)(?:\.(\d+))?$/.exec(text.trim());
  if (!m) return null;
  const frac = m[2] ?? "";
  if (frac.length > digits) return null;
  return Number(m[1] + frac.padEnd(digits, "0"));
}
