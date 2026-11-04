import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { ReportRow } from "../src/contracts.gen";
import { monthlyReportCsv } from "../src/csv";

const r = (month: string, employee_id: string, category: string, count: number, amount_minor: number, currency = "USD"): ReportRow => ({
  month, employee_id, category, count, total: { amount_minor, currency },
});

describe("monthlyReportCsv (hidden)", () => {
  it("matches the golden file: sorted, RFC 4180, per-currency digits, formula-safe", () => {
    const rows = [
      r("2024-02", "e1", "travel", 1, 700),
      r("2024-01", "e2", "meals", 1, 1500, "JPY"),
      r("2024-02", "e1", "meals", 10, 9999999),
      r("2024-01", "=SUM(A1)", "meals", 4, 5),
      r("2024-01", "e,1", "travel", 2, 12345, "KWD"),
    ];
    const golden = readFileSync(new URL("./golden/hidden-monthly.csv", import.meta.url), "utf8");
    expect(monthlyReportCsv(rows)).toBe(golden);
  });

  it("has no BOM, CRLF endings and a header even with no rows", () => {
    const out = monthlyReportCsv([]);
    expect(out).toBe("month,employee_id,category,count,total,currency\r\n");
    expect(out.charCodeAt(0)).not.toBe(0xfeff);
  });
});
