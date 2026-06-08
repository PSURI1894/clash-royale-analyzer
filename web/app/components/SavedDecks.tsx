"use client";

import { useEffect, useState } from "react";
import { deleteDeck, getDecks, saveDeck } from "../api";
import type { SavedDeck } from "../types";

export default function SavedDecks({
  deck,
  onLoad,
}: {
  deck: string[];
  onLoad: (cards: string[]) => void;
}) {
  const [decks, setDecks] = useState<SavedDeck[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => getDecks().then(setDecks).catch(() => setDecks([]));
  useEffect(() => {
    refresh();
  }, []);

  async function save() {
    setError(null);
    try {
      await saveDeck(name.trim() || `Deck ${decks.length + 1}`, deck);
      setName("");
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function remove(id: number) {
    await deleteDeck(id).catch(() => {});
    refresh();
  }

  return (
    <section className="saved card">
      <div className="saved-head">
        <h3>Saved decks</h3>
        <div className="saved-save">
          <input
            className="search"
            placeholder="Deck name"
            value={name}
            maxLength={40}
            onChange={(e) => setName(e.target.value)}
          />
          <button className="btn" onClick={save} disabled={deck.length !== 8}>
            Save current
          </button>
        </div>
      </div>

      {error && <div className="banner error">{error}</div>}

      {decks.length === 0 ? (
        <p className="muted">No saved decks yet — build a full 8-card deck and save it.</p>
      ) : (
        <div className="saved-list">
          {decks.map((d) => (
            <div key={d.id} className="saved-item">
              <button className="chip" onClick={() => onLoad(d.cards)} title="Load deck">
                {d.name}
              </button>
              <button className="saved-del" onClick={() => remove(d.id)} title="Delete deck">
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
