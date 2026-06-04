"use client";

import type { CardSummary } from "../types";
import type { Preset } from "../presets";
import { elixirColor } from "../ui";

interface Props {
  deck: CardSummary[];
  count: number;
  onRemove: (key: string) => void;
  onClear: () => void;
  onAnalyze: () => void;
  loading: boolean;
  presets: Preset[];
  onPreset: (cards: string[]) => void;
}

export default function DeckTray({
  deck, count, onRemove, onClear, onAnalyze, loading, presets, onPreset,
}: Props) {
  const slots: (CardSummary | null)[] = [...deck];
  while (slots.length < 8) slots.push(null);

  return (
    <section className="tray card">
      <div className="tray-head">
        <h2>
          Your Deck <span className="muted">({count}/8)</span>
        </h2>
        <div className="presets">
          <span className="muted" style={{ fontSize: 12.5, alignSelf: "center" }}>Load:</span>
          {presets.map((p) => (
            <button key={p.name} className="chip" onClick={() => onPreset(p.cards)}>
              {p.name}
            </button>
          ))}
        </div>
      </div>

      <div className="slots">
        {slots.map((c, i) =>
          c ? (
            <button key={c.key} className="slot filled" onClick={() => onRemove(c.key)} title="Click to remove">
              <span className="elixir" style={{ background: elixirColor(c.elixir) }}>{c.elixir ?? "–"}</span>
              <span className="slot-name">{c.name}</span>
              <span className="slot-type">{c.type}</span>
            </button>
          ) : (
            <div key={`empty-${i}`} className="slot empty">+</div>
          )
        )}
      </div>

      <div className="tray-actions">
        <button className="btn primary" disabled={count !== 8 || loading} onClick={onAnalyze}>
          {loading ? "Analyzing…" : count === 8 ? "Analyze deck" : `Pick ${8 - count} more`}
        </button>
        <button className="btn ghost" onClick={onClear} disabled={count === 0}>
          Clear
        </button>
      </div>
    </section>
  );
}
