"use client";

import { useEffect, useState } from "react";
import { getArchetypes, getMatchup } from "../api";
import type { CardSummary, MatchupReport } from "../types";
import { scoreColor } from "../ui";

export default function Matchup({
  deck,
  byKey,
}: {
  deck: string[];
  byKey: Record<string, CardSummary>;
}) {
  const [archetypes, setArchetypes] = useState<string[]>([]);
  const [opponent, setOpponent] = useState("Lavaloon");
  const [report, setReport] = useState<MatchupReport | null>(null);
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

  const nameOf = (k: string) => byKey[k]?.name ?? k;

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setReport(await getMatchup(deck, opponent));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="matchup card">
      <div className="matchup-head">
        <h3>
          Matchup simulator <span className="muted">— graph-driven</span>
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
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <button className="btn primary" onClick={run} disabled={loading}>
            {loading ? "Simulating…" : "Check matchup"}
          </button>
        </div>
      </div>

      {error && <div className="banner error">{error}</div>}

      {report && (
        <div className="matchup-body">
          <div className="matchup-score">
            <div className="score" style={{ borderColor: scoreColor(report.score) }}>
              <span className="score-num" style={{ color: scoreColor(report.score) }}>
                {report.score}
              </span>
              <span className="score-label">matchup</span>
            </div>
            <div className="verdict">
              <strong>vs {report.opponent}</strong>
              <br />
              {report.verdict}
            </div>
          </div>

          <div className="threats">
            {report.threats.map((t) => {
              const pct = Math.round(t.coverage * 100);
              return (
                <div key={t.threat} className="threat">
                  <div className="threat-head">
                    <strong>{nameOf(t.threat)}</strong>
                    <span className="cov" style={{ color: scoreColor(pct) }}>
                      {pct}%
                    </span>
                  </div>
                  <div className="cov-bar">
                    <div
                      className="cov-fill"
                      style={{ width: `${pct}%`, background: scoreColor(pct) }}
                    />
                  </div>
                  <p className="muted">
                    {t.answers.length
                      ? `Answered by ${t.answers.map(nameOf).join(", ")}`
                      : "⚠ No answer in your deck"}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
