import { useEffect, useState } from "react";
import type { Actor, TallyClient } from "../api";
import type { Expense } from "../contracts.gen";
import { formatMoney } from "../money";

export function ApprovalQueue({ client, actor }: { client: TallyClient; actor: Actor }) {
  const [items, setItems] = useState<Expense[]>([]);
  const [err, setErr] = useState("");
  const wanted = actor.role === "finance" ? "pending_finance" : "pending_manager";

  const load = () => client.listExpenses(wanted).then(setItems).catch((e) => setErr(String(e)));
  useEffect(() => { void load(); }, [wanted]);

  async function act(id: string, action: "approve" | "reject") {
    try {
      await client.decide(id, action, actor);
      setErr("");
      await load();
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <section>
      <h2>Queue: {wanted}</h2>
      {err && <p role="alert">{err}</p>}
      <ul>
        {items.map((e) => (
          <li key={e.id}>
            {e.id} {e.employee_id} {e.category} {formatMoney(e.amount)} ({formatMoney(e.base_amount)}){" "}
            <button onClick={() => act(e.id, "approve")}>Approve</button>{" "}
            <button onClick={() => act(e.id, "reject")}>Reject</button>
          </li>
        ))}
      </ul>
    </section>
  );
}
