import type { Expense, FxQuote, ParsedReceipt, PolicyDecision, Report } from "./contracts.gen";

export interface Actor {
  id: string;
  role: "employee" | "manager" | "finance";
}

type Fetch = typeof fetch;

/** Thin client for the policy and receipts services. */
export class TallyClient {
  constructor(
    private policyBase = "/api/policy",
    private receiptsBase = "/api/receipts",
    private f: Fetch = (...a) => fetch(...a),
  ) {}

  private async req<T>(url: string, init: RequestInit = {}, actor?: Actor): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (actor) {
      headers["X-Actor-ID"] = actor.id;
      headers["X-Actor-Role"] = actor.role;
    }
    const res = await this.f(url, { ...init, headers });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error ?? body.detail ?? `HTTP ${res.status}`);
    return body as T;
  }

  parseReceipt(text: string): Promise<ParsedReceipt> {
    return this.req(`${this.receiptsBase}/receipts/parse`, { method: "POST", body: JSON.stringify({ text }) });
  }

  convert(amountMinor: number, source: string, date: string): Promise<FxQuote> {
    return this.req(`${this.receiptsBase}/fx/convert`, {
      method: "POST",
      body: JSON.stringify({ amount_minor: amountMinor, source, target: "USD", date }),
    });
  }

  createExpense(e: Omit<Expense, "id" | "status" | "revision" | "created_at">): Promise<Expense> {
    return this.req(`${this.policyBase}/expenses`, { method: "POST", body: JSON.stringify(e) });
  }

  submit(id: string, actor: Actor): Promise<{ expense: Expense; decision: PolicyDecision }> {
    return this.req(`${this.policyBase}/expenses/${id}/submit`, { method: "POST" }, actor);
  }

  listExpenses(status = ""): Promise<Expense[]> {
    return this.req(`${this.policyBase}/expenses${status ? `?status=${status}` : ""}`);
  }

  decide(id: string, action: "approve" | "reject" | "reimburse", actor: Actor, reason = ""): Promise<Expense> {
    return this.req(`${this.policyBase}/expenses/${id}/${action}`, { method: "POST", body: JSON.stringify({ reason }) }, actor);
  }

  report(): Promise<Report> {
    return this.req(`${this.policyBase}/reports`);
  }
}
