import type {
  AdviceReport,
  AnalysisReport,
  CardMeta,
  CardSummary,
  MatchupReport,
  MiningStats,
  SavedDeck,
  SimResult,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

/** Opaque per-browser identity for saved decks (no account/password). */
function userToken(): string {
  if (typeof window === "undefined") return "server";
  let t = localStorage.getItem("cr_user_token");
  if (!t) {
    t = "u-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("cr_user_token", t);
  }
  return t;
}

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

export async function getSimulation(
  attacker: string[],
  defender: string[],
  lane: "left" | "right" = "left"
): Promise<SimResult> {
  const res = await fetch(`${API_BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ attacker, defender, lane }),
  });
  if (res.status === 422) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.join("; ") : body.detail;
    throw new Error(detail || "Invalid simulation request");
  }
  if (!res.ok) throw new Error(`Simulation failed (HTTP ${res.status})`);
  return res.json();
}

export async function getDecks(): Promise<SavedDeck[]> {
  const res = await fetch(`${API_BASE}/decks`, {
    headers: { "X-User-Token": userToken() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to load decks (HTTP ${res.status})`);
  return res.json();
}

export async function saveDeck(name: string, cards: string[]): Promise<SavedDeck> {
  const res = await fetch(`${API_BASE}/decks`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Token": userToken() },
    body: JSON.stringify({ name, cards }),
  });
  if (res.status === 422) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.join("; ") : body.detail;
    throw new Error(detail || "Invalid deck");
  }
  if (!res.ok) throw new Error(`Save failed (HTTP ${res.status})`);
  return res.json();
}

export async function deleteDeck(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/decks/${id}`, {
    method: "DELETE",
    headers: { "X-User-Token": userToken() },
  });
  if (!res.ok) throw new Error(`Delete failed (HTTP ${res.status})`);
}
