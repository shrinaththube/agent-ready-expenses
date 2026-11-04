import type { Expense } from "../src/contracts.gen";

const base: Expense = {
  id: "exp-0001", employee_id: "e1", manager_id: "m1", category: "meals", description: "Lunch",
  amount: { amount_minor: 4200, currency: "USD" }, base_amount: { amount_minor: 4200, currency: "USD" },
  date: "2024-03-13", has_receipt: true, attendees: 1, region: "domestic", status: "approved", revision: 1,
  created_at: "2024-03-13T10:00:00Z",
};

export const expenses: Expense[] = [
  base,
  { ...base, id: "exp-0002", date: "2024-03-14", description: 'Team "kickoff", Café', amount: { amount_minor: 1500, currency: "JPY" }, base_amount: { amount_minor: 1003, currency: "USD" } },
  { ...base, id: "exp-0003", date: "2024-03-14", category: "travel", description: "=HYPERLINK(\"http://evil.test\",\"x\")", amount: { amount_minor: 12345, currency: "KWD" }, base_amount: { amount_minor: 4021, currency: "USD" }, status: "pending_manager" },
  { ...base, id: "exp-0004", date: "2024-03-15", description: "multi\nline", amount: { amount_minor: 5, currency: "EUR" }, base_amount: { amount_minor: 5, currency: "USD" } },
];
