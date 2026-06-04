import type { AnalysisReport, CardSummary } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export async function getCards(): Promise<CardSummary[]> {
  const res = await fetch(`${API_BASE}/cards`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load cards (HTTP ${res.status})`);
  return res.json();
}

export async function analyzeDeck(cards: string[]): Promise<AnalysisReport> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cards }),
  });
  if (res.status === 422) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.join("; ") : body.detail;
    throw new Error(detail || "Invalid deck");
  }
  if (!res.ok) throw new Error(`Analyze failed (HTTP ${res.status})`);
  return res.json();
}
