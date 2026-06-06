"use client";

import { useEffect, useState } from "react";
import { getAdvice, getArchetypes } from "../api";
import type { AdviceReport } from "../types";

export default function Advisor({ deck }: { deck: string[] }) {
  const [archetypes, setArchetypes] = useState<string[]>([]);
  const [opponent, setOpponent] = useState("Lavaloon");
  const [report, setReport] = useState<AdviceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getArchetypes()
      .then((a) => {
        setArchetypes(a);
        if (a.length && !a.includes(opponent)) setOpponent(a[0]);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setReport(await getAdvice(deck, opponent));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="advisor card">
      <div className="advisor-head">
        <h3>
          AI coach <span className="muted">— RAG, every number grounded</span>
        </h3>
        <div className="matchup-controls">
          <select
            className="select"
            value={opponent}
            onChange={(e) => {
              setOpponent(e.target.value);
              setReport(null);
            }}
          >
            {archetypes.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
          <button className="btn primary" onClick={run} disabled={loading}>
            {loading ? "Thinking…" : "Get coaching"}
          </button>
        </div>
      </div>

      {error && <div className="banner error">{error}</div>}

      {report && (
        <div className="advice">
          <div className="advice-verdict">
            <strong>{report.verdict}</strong>
            <span className={report.grounding.ok ? "ground ok" : "ground warn"}>
              {report.grounding.ok
                ? "✓ grounded"
                : `⚠ ${report.grounding.unverified_numbers.length} unverified`}
              <span className="ground-engine">{report.grounding.engine}</span>
            </span>
          </div>

          <div className="advice-grid">
            <div>
              <h4>Key facts</h4>
              <ul>{report.key_facts.map((f, i) => <li key={i}>{f}</li>)}</ul>
              <h4>Game plan</h4>
              <ul>{report.game_plan.map((f, i) => <li key={i}>{f}</li>)}</ul>
            </div>
            <div>
              <h4>Defensive routine</h4>
              <ol>{report.defensive_routine.map((f, i) => <li key={i}>{f}</li>)}</ol>
              <h4>Placements</h4>
              <ul className="placements">
                {report.placements.map((p, i) => (
                  <li key={i}><strong>{p.card}:</strong> {p.note}</li>
                ))}
              </ul>
            </div>
          </div>

          {report.sources.length > 0 && (
            <div className="advice-sources">
              <span className="muted">Sources:</span>{" "}
              {report.sources.map((s) => (
                <span key={s.id} className="cite" title={s.title}>{s.id}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
