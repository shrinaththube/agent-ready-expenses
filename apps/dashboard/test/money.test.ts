import { describe, expect, it } from "vitest";
import { formatAmount, formatMoney, minorDigits, parseMinor } from "../src/money";

describe("money", () => {
  it.each([
    [{ amount_minor: 7500, currency: "USD" }, "75.00"],
    [{ amount_minor: 5, currency: "USD" }, "0.05"],
    [{ amount_minor: 1500, currency: "JPY" }, "1500"],
    [{ amount_minor: 12345, currency: "KWD" }, "12.345"],
    [{ amount_minor: -250, currency: "EUR" }, "-2.50"],
  ])("formats %j as %s", (m, want) => expect(formatAmount(m)).toBe(want));

  it("formats with currency code", () => expect(formatMoney({ amount_minor: 1500, currency: "JPY" })).toBe("1500 JPY"));

  it("round-trips parse and format for every currency digit count", () => {
    for (const [cur, text] of [["JPY", "1500"], ["KWD", "12.345"], ["USD", "0.05"]] as const) {
      const minor = parseMinor(text, cur)!;
      expect(formatAmount({ amount_minor: minor, currency: cur })).toBe(text);
    }
  });

  it("rejects too many digits and garbage", () => {
    expect(parseMinor("1.234", "USD")).toBeNull();
    expect(parseMinor("12.5", "JPY")).toBeNull();
    expect(parseMinor("abc", "USD")).toBeNull();
    expect(minorDigits("JPY")).toBe(0);
  });
});
