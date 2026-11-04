import { useState } from "react";
import type { Actor, TallyClient } from "../api";
import type { ExpenseCategory, ParsedReceipt } from "../contracts.gen";
import { formatAmount, formatMoney, parseMinor } from "../money";
import { needsConfirmation } from "../receipt";

export function SubmitForm({ client, actor }: { client: TallyClient; actor: Actor }) {
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState<ParsedReceipt | null>(null);
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState<ExpenseCategory>("meals");
  const [confirmed, setConfirmed] = useState(false);
  const [msg, setMsg] = useState("");

  const lowConfidence = parsed ? needsConfirmation(parsed) : false;

  async function parse() {
    try {
      const p = await client.parseReceipt(text);
      setParsed(p);
      setAmount(formatAmount(p.total));
      setConfirmed(false);
      setMsg("");
    } catch (e) {
      setMsg(String(e));
    }
  }

  async function submit() {
    if (!parsed) return;
    const minor = parseMinor(amount, parsed.total.currency);
    if (minor === null) return setMsg("Enter the amount using the currency's decimal digits.");
    try {
      const quote = parsed.total.currency === "USD" ? null : await client.convert(minor, parsed.total.currency, parsed.date);
      const created = await client.createExpense({
        employee_id: actor.id, manager_id: "m1", category, description: parsed.merchant,
        amount: { amount_minor: minor, currency: parsed.total.currency },
        base_amount: quote ? quote.target : { amount_minor: minor, currency: "USD" },
        date: parsed.date, has_receipt: true, attendees: 1, region: "domestic",
      });
      const { decision, expense } = await client.submit(created.id, actor);
      setMsg(`${expense.id}: ${decision.outcome} - ${decision.reason}`);
    } catch (e) {
      setMsg(String(e));
    }
  }

  return (
    <section>
      <h2>Submit an expense</h2>
      <textarea rows={6} cols={60} placeholder="Paste receipt text" value={text} onChange={(e) => setText(e.target.value)} />
      <div><button onClick={parse}>Parse receipt</button></div>
      {parsed && (
        <div>
          <p>
            {parsed.merchant} - {parsed.date} - {formatMoney(parsed.total)} (confidence {parsed.confidence})
          </p>
          <label>Amount <input value={amount} onChange={(e) => setAmount(e.target.value)} /> {parsed.total.currency}</label>{" "}
          <select value={category} onChange={(e) => setCategory(e.target.value as ExpenseCategory)}>
            {["meals", "travel", "lodging", "software", "alcohol", "office", "other"].map((c) => <option key={c}>{c}</option>)}
          </select>
          {lowConfidence && (
            <p role="alert">
              Low-confidence parse. <label><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} /> I confirm these details are correct</label>
            </p>
          )}
          <button disabled={lowConfidence && !confirmed} onClick={submit}>Submit</button>
        </div>
      )}
      {msg && <p>{msg}</p>}
    </section>
  );
}
