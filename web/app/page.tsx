"use client";

import { useEffect, useMemo, useState } from "react";
import { analyzeDeck, getCards } from "./api";
import Advisor from "./components/Advisor";
import CardGrid from "./components/CardGrid";
import DeckTray from "./components/DeckTray";
import Matchup from "./components/Matchup";
import MetaPanel from "./components/MetaPanel";
import Report from "./components/Report";
import { PRESETS } from "./presets";
import type { AnalysisReport, CardSummary } from "./types";

export default function Home() {
  const [cards, setCards] = useState<CardSummary[]>([]);
  const [deck, setDeck] = useState<string[]>([]);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    getCards()
      .then(setCards)
      .catch((e) => setLoadError(String(e?.message ?? e)));
  }, []);

  const byKey = useMemo(
    () => Object.fromEntries(cards.map((c) => [c.key, c])),
    [cards]
  );

  function add(key: string) {
    setReport(null);
    setDeck((d) => (d.includes(key) || d.length >= 8 ? d : [...d, key]));
  }
  function remove(key: string) {
    setReport(null);
    setDeck((d) => d.filter((k) => k !== key));
  }
  function clear() {
    setReport(null);
    setError(null);
    setDeck([]);
  }
  function loadPreset(keys: string[]) {
    setReport(null);
    setError(null);
    setDeck(keys);
  }

  async function analyze() {
    setLoading(true);
    setError(null);
    try {
      setReport(await analyzeDeck(deck));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <header className="topbar">
        <h1>
          ⚔️ Clash Royale <span className="accent">Helper</span>
        </h1>
        <p className="subtitle">
          Deterministic deck analyzer — every number is computed from the card database, not guessed.
        </p>
      </header>

      {loadError && (
        <div className="banner error">
          Couldn&apos;t reach the API ({loadError}). Start the backend:{" "}
          <code>uvicorn cr_helper.main:app</code> on port 8000.
        </div>
      )}

      <DeckTray
        deck={deck.map((k) => byKey[k]).filter(Boolean) as CardSummary[]}
        count={deck.length}
        onRemove={remove}
        onClear={clear}
        onAnalyze={analyze}
        loading={loading}
        presets={PRESETS}
        onPreset={loadPreset}
      />

      {error && <div className="banner error">{error}</div>}

      {report && <Report report={report} byKey={byKey} />}

      {deck.length === 8 && (
        <Matchup key={deck.join(",")} deck={deck} byKey={byKey} />
      )}

      {deck.length === 8 && <Advisor key={`adv-${deck.join(",")}`} deck={deck} />}

      <MetaPanel />

      <CardGrid cards={cards} deck={deck} onAdd={add} />
    </main>
  );
}
