import type { ParsedReceipt } from "./contracts.gen";

export const CONFIDENCE_THRESHOLD = 0.6;

/** Low-confidence parses must be confirmed by the user before submitting. */
export function needsConfirmation(p: ParsedReceipt): boolean {
  return p.confidence < CONFIDENCE_THRESHOLD;
}
