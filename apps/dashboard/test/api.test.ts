import { describe, expect, it, vi } from "vitest";
import { TallyClient } from "../src/api";
import { needsConfirmation } from "../src/receipt";
import { monthLabel } from "../src/month";

describe("TallyClient", () => {
  it("sends actor headers and surfaces server errors", async () => {
    const f = vi.fn(async () => new Response(JSON.stringify({ error: "forbidden" }), { status: 403 }));
    const c = new TallyClient("/p", "/r", f as unknown as typeof fetch);
    await expect(c.decide("exp-1", "approve", { id: "m1", role: "manager" })).rejects.toThrow("forbidden");
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/p/expenses/exp-1/approve");
    expect((init.headers as Record<string, string>)["X-Actor-ID"]).toBe("m1");
  });

  it("converts using the expense date", async () => {
    const f = vi.fn(async () => new Response("{}", { status: 200 }));
    await new TallyClient("/p", "/r", f as unknown as typeof fetch).convert(1500, "JPY", "2024-03-15");
    const body = JSON.parse(((f.mock.calls[0] as unknown as [string, RequestInit])[1].body) as string);
    expect(body).toEqual({ amount_minor: 1500, source: "JPY", target: "USD", date: "2024-03-15" });
  });
});

describe("receipt confirmation", () => {
  const p = (confidence: number) => ({ merchant: "x", date: "2024-01-01", total: { amount_minor: 1, currency: "USD" }, confidence });
  it("asks below 0.6 only", () => {
    expect(needsConfirmation(p(0.59))).toBe(true);
    expect(needsConfirmation(p(0.6))).toBe(false);
  });
});

describe("month", () => {
  it("labels months", () => expect(monthLabel("2024-03")).toBe("Mar 2024"));
});
