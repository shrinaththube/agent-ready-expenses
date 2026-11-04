#!/usr/bin/env node
// Seeds demo expenses into a running policy service. CommonJS on purpose:
// it requires the pinned `nanoid@3` (see docs/decisions/0004-pin-nanoid-commonjs.md).
const { nanoid } = require("nanoid");
const base = process.env.POLICY_URL || "http://localhost:8081";

const demo = [
  ["e1", "meals", 4200, "2024-03-13"],
  ["e1", "lodging", 45000, "2024-03-14"],
  ["e2", "software", 9900, "2024-03-16"],
  ["e3", "office", 120000, "2024-03-15"],
];

async function main() {
  for (const [emp, category, usd, date] of demo) {
    const body = {
      employee_id: emp, manager_id: "m1", category, description: `demo ${nanoid(6)}`,
      amount: { amount_minor: usd, currency: "USD" }, base_amount: { amount_minor: usd, currency: "USD" },
      date, has_receipt: true, attendees: 1, region: "domestic",
    };
    const res = await fetch(`${base}/expenses`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const e = await res.json();
    await fetch(`${base}/expenses/${e.id}/submit`, { method: "POST", headers: { "X-Actor-ID": emp, "X-Actor-Role": "employee" } });
    console.log("seeded", e.id);
  }
}
main().catch((err) => { console.error(err); process.exit(1); });
