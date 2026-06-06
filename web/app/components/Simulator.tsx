"use client";

import { useMemo, useState } from "react";
import { getSimulation } from "../api";
import type { CardSummary, SimResult } from "../types";

const SCALE = 10;
const W = 18 * SCALE;
const H = 32 * SCALE;
const sx = (x: number) => x * SCALE;
const sy = (y: number) => (32 - y) * SCALE;
const ATT = "#ef4444";
const DEF = "#38bdf8";

const PUSHES: { label: string; cards: string[] }[] = [
  { label: "Hog Rider", cards: ["hog-rider"] },
  { label: "Hog + Ice Golem", cards: ["hog-rider", "ice-golem"] },
  { label: "Giant + Musketeer", cards: ["giant", "musketeer"] },
  { label: "Balloon", cards: ["balloon"] },
  { label: "Golem + Mega Minion", cards: ["golem", "mega-minion"] },
  { label: "P.E.K.K.A + Bandit", cards: ["pekka", "bandit"] },
  { label: "Royal Giant", cards: ["royal-giant"] },
];

function Board({ result }: { result: SimResult }) {
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="arena" role="img" aria-label="arena">
      <rect x={0} y={0} width={W} height={H} fill="#0c1326" rx={8} />
      <rect x={0} y={sy(16.5)} width={W} height={SCALE} fill="#16324a" />
      <rect x={sx(3.5) - 12} y={sy(16.5)} width={24} height={SCALE} fill="#3b2f1a" />
      <rect x={sx(14.5) - 12} y={sy(16.5)} width={24} height={SCALE} fill="#3b2f1a" />

      {result.towers.map((t, i) => {
        const c = t.side === "attacker" ? ATT : DEF;
        const w = t.kind === "king" ? 20 : 16;
        return (
          <g key={i} opacity={t.alive ? 1 : 0.25}>
            <rect x={sx(t.x) - w / 2} y={sy(t.y) - w / 2} width={w} height={w} rx={3}
              fill="none" stroke={c} strokeWidth={2} />
            <rect x={sx(t.x) - w / 2} y={sy(t.y) - w / 2 - 5} width={w} height={3} fill="#1c2845" />
            <rect x={sx(t.x) - w / 2} y={sy(t.y) - w / 2 - 5}
              width={(w * Math.max(0, t.hp)) / t.max_hp} height={3} fill={c} />
          </g>
        );
      })}

      {result.units.map((u, i) => (
        <circle key={i} cx={sx(u.x)} cy={sy(u.y)} r={4.5}
          fill={u.side === "attacker" ? ATT : DEF} opacity={0.35 + 0.65 * u.hp_pct} />
      ))}
    </svg>
  );
}

export default function Simulator({
  deck,
  byKey,
}: {
  deck: string[];
  byKey: Record<string, CardSummary>;
}) {
  const defendable = useMemo(
    () => deck.filter((k) => byKey[k]?.type !== "Spell"),
    [deck, byKey]
  );
  const [push, setPush] = useState(0);
  const [defenders, setDefenders] = useState<string[]>(defendable.slice(0, 4));
  const [lane, setLane] = useState<"left" | "right">("left");
  const [result, setResult] = useState<SimResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(k: string) {
    setResult(null);
    setDefenders((d) => (d.includes(k) ? d.filter((x) => x !== k) : [...d, k]));
  }

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setResult(await getSimulation(PUSHES[push].cards, defenders, lane));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  const winColor = (w: string) => (w === "defender" ? "#22c55e" : w === "attacker" ? "#ef4444" : "#eab308");

  return (
    <section className="simulator card">
      <div className="advisor-head">
        <h3>Battle simulator <span className="muted">— deterministic engine</span></h3>
      </div>

      <div className="sim-controls">
        <label>
          <span>Incoming push</span>
          <select className="select" value={push} onChange={(e) => { setPush(+e.target.value); setResult(null); }}>
            {PUSHES.map((p, i) => <option key={p.label} value={i}>{p.label}</option>)}
          </select>
        </label>
        <div className="sim-lane">
          <span>Lane</span>
          <button className={lane === "left" ? "chip active" : "chip"} onClick={() => { setLane("left"); setResult(null); }}>Left</button>
          <button className={lane === "right" ? "chip active" : "chip"} onClick={() => { setLane("right"); setResult(null); }}>Right</button>
        </div>
        <button className="btn primary" onClick={run} disabled={loading || defenders.length === 0}>
          {loading ? "Simulating…" : "Simulate defence"}
        </button>
      </div>

      <div className="sim-defenders">
        <span className="muted">Your defenders:</span>
        {defendable.map((k) => (
          <button key={k} className={defenders.includes(k) ? "chip active" : "chip"} onClick={() => toggle(k)}>
            {byKey[k]?.name ?? k}
          </button>
        ))}
      </div>

      {error && <div className="banner error">{error}</div>}

      {result && (
        <div className="sim-result">
          <Board result={result} />
          <div className="sim-readout">
            <div className="sim-winner" style={{ color: winColor(result.winner) }}>
              {result.winner === "defender" ? "Defended ✓" : result.winner === "attacker" ? "Push got through ✗" : "Stalemate"}
            </div>
            <p>{result.summary}</p>
            <ul className="sim-stats">
              <li>Duration: <strong>{result.duration}s</strong></li>
              <li>Tower damage taken: <strong>{result.defender_tower_damage}</strong></li>
              <li>Survivors: <strong>{result.defender_survivors.join(", ") || "none"}</strong></li>
              {result.attacker_survivors.length > 0 && (
                <li>Enemy survivors: <strong>{result.attacker_survivors.join(", ")}</strong></li>
              )}
            </ul>
            {result.warnings.length > 0 && (
              <p className="muted sim-warn">{result.warnings.join("; ")}</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
