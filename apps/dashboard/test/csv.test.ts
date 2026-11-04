import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { csvCell, expensesCsv } from "../src/csv";
import { expenses } from "./fixtures";

describe("csv", () => {
  it("matches the golden file byte for byte", () => {
    const golden = readFileSync(new URL("./golden/expenses.csv", import.meta.url), "utf8");
    expect(expensesCsv(expenses)).toBe(golden);
  });

  it("has no BOM and ends rows with CRLF", () => {
    const out = expensesCsv(expenses);
    expect(out.charCodeAt(0)).not.toBe(0xfeff);
    expect(out.endsWith("\r\n")).toBe(true);
  });

  it.each([
    ["plain", "plain"],
    ["a,b", '"a,b"'],
    ['say "hi"', '"say ""hi"""'],
    ["=SUM(A1)", "'=SUM(A1)"],
    ["+1", "'+1"],
    ["-1", "'-1"],
    ["@x", "'@x"],
  ])("csvCell(%j) = %j", (input, want) => expect(csvCell(input)).toBe(want));
});
