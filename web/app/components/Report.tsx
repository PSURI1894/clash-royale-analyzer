"use client";

import type { AnalysisReport, CardSummary } from "../types";
import { elixirColor, roleColor, scoreColor, severityColor } from "../ui";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span className="stat-v">{value}</span>
      <span className="stat-l">{label}</span>
    </div>
  );
}

export default function Report({
  report,
  byKey,
}: {
  report: AnalysisReport;
  byKey: Record<string, CardSummary>;
}) {
  const m = report.metrics;
  const curveValues = Object.values(m.elixir_curve);
  const maxCurve = Math.max(1, ...curveValues);
  const nameOf = (k: string) => byKey[k]?.name ?? k;

  return (
    <section className="report card">
      <div className="report-head">
        <div>
          <h2>
            {report.archetype.primary} <span className="muted">deck</span>
          </h2>
          <div className="signals">
            {report.archetype.signals.map((s, i) => (
              <span key={i} className="signal">{s}</span>
            ))}
          </div>
        </div>
        <div className="score" style={{ borderColor: scoreColor(report.stability_score) }}>
          <span className="score-num" style={{ color: scoreColor(report.stability_score) }}>
            {report.stability_score}
          </span>
          <span className="score-label">stability</span>
        </div>
      </div>

      <div className="stat-row">
        <Stat label="Avg elixir" value={m.avg_elixir.toFixed(1)} />
        <Stat label="4-card cycle" value={String(m.cycle_cost)} />
        <Stat label="Def. air DPS" value={String(m.air_dps)} />
        <Stat label="Def. ground DPS" value={String(m.ground_dps)} />
        <Stat
          label="Win condition"
          value={report.win_conditions.length ? report.win_conditions.join(", ") : "— none —"}
        />
      </div>

      {report.weak_against.length > 0 && (
        <div className="weak-against">
          <span className="wa-label">No hard answer to</span>
          <div className="wa-chips">
            {report.weak_against.map((k) => (
              <span key={k} className="wa-chip">{nameOf(k)}</span>
            ))}
          </div>
        </div>
      )}

      <div className="report-cols">
        <div className="curve">
          <h3>Elixir curve</h3>
          <div className="bars">
            {Array.from({ length: 9 }, (_, i) => i + 1).map((e) => {
              const n = m.elixir_curve[String(e)] ?? 0;
              return (
                <div key={e} className="bar-col">
                  <span className="bar-n">{n || ""}</span>
                  <div
                    className="bar"
                    style={{ height: `${(n / maxCurve) * 100}%`, background: elixirColor(e) }}
                  />
                  <span className="bar-x">{e}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="vulns">
          <h3>Vulnerabilities</h3>
          {report.vulnerabilities.length === 0 && (
            <p className="muted">No major weaknesses detected — a solid, well-rounded deck.</p>
          )}
          {report.vulnerabilities.map((v) => (
            <div key={v.code} className="vuln" style={{ borderLeftColor: severityColor(v.severity) }}>
              <div className="vuln-head">
                <span className="dot" style={{ background: severityColor(v.severity) }} />
                <strong>{v.title}</strong>
                <span className="sev">{v.severity}</span>
              </div>
              <p>{v.detail}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="deck-chips">
        {report.cards.map((c) => (
          <span key={c.key} className="dchip" style={{ borderLeftColor: roleColor(c.role) }}>
            <span className="elixir sm" style={{ background: elixirColor(c.elixir) }}>
              {c.elixir ?? "–"}
            </span>
            {c.name}
            <span className="role" style={{ color: roleColor(c.role) }}>{c.role}</span>
          </span>
        ))}
      </div>
    </section>
  );
}
