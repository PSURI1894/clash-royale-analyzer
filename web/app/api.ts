import type {
  AdviceReport,
  AnalysisReport,
  CardMeta,
  CardSummary,
  MatchupReport,
  MiningStats,
} from "./types";

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

export async function getArchetypes(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/archetypes`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load archetypes (HTTP ${res.status})`);
  return res.json();
}

export async function getMatchup(cards: string[], opponent: string): Promise<MatchupReport> {
  const res = await fetch(`${API_BASE}/matchup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cards, opponent }),
  });
  if (res.status === 422) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.join("; ") : body.detail;
    throw new Error(detail || "Invalid matchup request");
  }
  if (!res.ok) throw new Error(`Matchup failed (HTTP ${res.status})`);
  return res.json();
}

export async function getMiningStats(): Promise<MiningStats> {
  const res = await fetch(`${API_BASE}/mining/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load mining stats (HTTP ${res.status})`);
  return res.json();
}

export async function getMetaCards(
  dataset = "synthetic",
  sort: "win_rate" | "usage" = "win_rate",
  limit = 12
): Promise<CardMeta[]> {
  const params = new URLSearchParams({ dataset, sort, limit: String(limit) });
  const res = await fetch(`${API_BASE}/meta/cards?${params}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load meta cards (HTTP ${res.status})`);
  return res.json();
}

export async function getAdvice(cards: string[], opponent: string): Promise<AdviceReport> {
  const res = await fetch(`${API_BASE}/advise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cards, opponent }),
  });
  if (res.status === 422) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.join("; ") : body.detail;
    throw new Error(detail || "Invalid advice request");
  }
  if (!res.ok) throw new Error(`Advice failed (HTTP ${res.status})`);
  return res.json();
}
