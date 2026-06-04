"use client";

import { useMemo, useState } from "react";
import type { CardSummary } from "../types";
import { elixirColor } from "../ui";

interface Props {
  cards: CardSummary[];
  deck: string[];
  onAdd: (key: string) => void;
}

const TYPES = ["All", "Troop", "Building", "Spell"];

export default function CardGrid({ cards, deck, onAdd }: Props) {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("All");

  const filtered = useMemo(
    () =>
      cards.filter(
        (c) =>
          (type === "All" || c.type === type) &&
          c.name.toLowerCase().includes(query.toLowerCase())
      ),
    [cards, query, type]
  );

  const full = deck.length >= 8;

  return (
    <section className="grid-wrap card">
      <div className="grid-head">
        <h2>
          Cards <span className="muted">({filtered.length})</span>
        </h2>
        <div className="filters">
          <input
            className="search"
            placeholder="Search cards…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {TYPES.map((t) => (
            <button
              key={t}
              className={`chip ${type === t ? "active" : ""}`}
              onClick={() => setType(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="grid">
        {filtered.map((c) => {
          const inDeck = deck.includes(c.key);
          return (
            <button
              key={c.key}
              className={`card-tile t-${(c.type ?? "").toLowerCase()} ${inDeck ? "in-deck" : ""}`}
              disabled={inDeck || full}
              onClick={() => onAdd(c.key)}
              title={inDeck ? "Already in deck" : full ? "Deck is full" : `Add ${c.name}`}
            >
              <span className="elixir" style={{ background: elixirColor(c.elixir) }}>
                {c.elixir ?? "–"}
              </span>
              <span className="tile-name">{c.name}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
