import { useEffect, useState } from "react";
import type { TallyClient } from "../api";
import type { Report } from "../contracts.gen";
import { expensesCsv } from "../csv";
import { monthLabel } from "../month";
import { formatMoney } from "../money";

export function Reports({ client }: { client: TallyClient }) {
  const [report, setReport] = useState<Report | null>(null);
  useEffect(() => { client.report().then(setReport).catch(() => setReport(null)); }, []);

  async function exportCsv() {
    const csv = expensesCsv(await client.listExpenses());
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "expenses.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!report) return <p>Loading report...</p>;
  return (
    <section>
      <h2>Approved spend (USD)</h2>
      <table>
        <thead><tr><th>Month</th><th>Employee</th><th>Category</th><th>Count</th><th>Total</th></tr></thead>
        <tbody>
          {report.rows.map((r) => (
            <tr key={`${r.month}${r.employee_id}${r.category}`}>
              <td>{monthLabel(r.month)}</td><td>{r.employee_id}</td><td>{r.category}</td><td>{r.count}</td><td>{formatMoney(r.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>{report.status_counts.map((s) => `${s.status}: ${s.count}`).join(" | ")}</p>
      <button onClick={exportCsv}>Export expenses CSV</button>
    </section>
  );
}
