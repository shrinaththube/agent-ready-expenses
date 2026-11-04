import { useState } from "react";
import type { Actor } from "./api";
import { TallyClient } from "./api";
import { ApprovalQueue } from "./components/ApprovalQueue";
import { Reports } from "./components/Reports";
import { SubmitForm } from "./components/SubmitForm";

const client = new TallyClient();

export function App() {
  const [actor, setActor] = useState<Actor>({ id: "e1", role: "employee" });
  const [tab, setTab] = useState<"submit" | "queue" | "reports">("submit");
  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 820, margin: "2rem auto" }}>
      <h1>Tally</h1>
      <label>
        Acting as{" "}
        <input value={actor.id} onChange={(e) => setActor({ ...actor, id: e.target.value })} size={8} />{" "}
        <select value={actor.role} onChange={(e) => setActor({ ...actor, role: e.target.value as Actor["role"] })}>
          <option>employee</option>
          <option>manager</option>
          <option>finance</option>
        </select>
      </label>
      <nav style={{ margin: "1rem 0", display: "flex", gap: 8 }}>
        <button onClick={() => setTab("submit")}>Submit</button>
        <button onClick={() => setTab("queue")}>Approval queue</button>
        <button onClick={() => setTab("reports")}>Reports</button>
      </nav>
      {tab === "submit" && <SubmitForm client={client} actor={actor} />}
      {tab === "queue" && <ApprovalQueue client={client} actor={actor} />}
      {tab === "reports" && <Reports client={client} />}
    </main>
  );
}
