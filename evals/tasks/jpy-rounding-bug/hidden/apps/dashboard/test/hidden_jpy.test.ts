import { describe, expect, it } from "vitest";
import { expensesCsv } from "../src/csv";
import { formatAmount, formatMoney } from "../src/money";
import type { Expense } from "../src/contracts.gen";

const jpy: Expense = {
  id: "exp-9", employee_id: "e1", manager_id: "m1", category: "meals", description: "Ramen",
  amount: { amount_minor: 1500, currency: "JPY" }, base_amount: { amount_minor: 1003, currency: "USD" },
  date: "2024-03-15", has_receipt: true, attendees: 1, region: "international", status: "approved", revision: 1,
  created_at: "2024-03-15T00:00:00Z",
};

describe("currencies with non-2 minor digits", () => {
  it("shows JPY with no decimals and KWD with three", () => {
    expect(formatAmount({ amount_minor: 1500, currency: "JPY" })).toBe("1500");
    expect(formatMoney({ amount_minor: 1500, currency: "JPY" })).toBe("1500 JPY");
    expect(formatAmount({ amount_minor: 12345, currency: "KWD" })).toBe("12.345");
    expect(formatAmount({ amount_minor: 7, currency: "JPY" })).toBe("7");
  });

  it("exports JPY amounts without decimals", () => {
    const lines = expensesCsv([jpy]).split("\r\n");
    expect(lines[1]).toBe("exp-9,e1,2024-03-15,meals,Ramen,1500,JPY,10.03,USD,approved");
  });
});
