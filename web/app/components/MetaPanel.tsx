"use client";

import { useEffect, useState } from "react";
import { getMetaCards, getMiningStats } from "../api";
import type { CardMeta, MiningStats } from "../types";
import { scoreColor } from "../ui";

export default function MetaPanel() {
  const [stats, setStats] = useState<MiningStats | null>(null);
  const [cards, setCards] = useState<CardMeta[]>([]);
  const [sort, setSort] = useState<"win_rate" | "usage">("win_rate");

  useEffect(() => {
    getMiningStats().then(setStats).catch(() => {});
  }, []);
  useEffect(() => {
    getMetaCards("synthetic", sort, 12).then(setCards).catch(() => setCards([]));
  }, [sort]);

  // Only render once the mining pipeline has produced data.
  if (!stats || stats.battles === 0 || cards.length === 0) return null;

  const maxUsage = Math.max(0.0001, ...cards.map((c) => c.usage));

  return (
    <section className="meta card">
      <div className="meta-head">
        <h3>
          Card meta{" "}
          <span className="muted">
            — mined from {stats.battles.toLocaleString()} battles · {stats.mined_edges.toLocaleString()} edges
          </span>
        </h3>
        <div className="seg">
          <button
            className={sort === "win_rate" ? "seg-b active" : "seg-b"}
            onClick={() => setSort("win_rate")}
          >
            Win rate
          </button>
          <button
            className={sort === "usage" ? "seg-b active" : "seg-b"}
            onClick={() => setSort("usage")}
          >
            Usage
          </button>
        </div>
      </div>

      <div className="meta-rows">
        {cards.map((c, i) => {
          const wr = Math.round(c.win_rate * 100);
          const width = sort === "win_rate" ? wr : Math.round((c.usage / maxUsage) * 100);
          return (
            <div key={c.key} className="meta-row">
              <span className="meta-rank">{i + 1}</span>
              <span className="meta-name">{c.name}</span>
              <div className="meta-bar">
                <div
                  className="meta-fill"
                  style={{
                    width: `${width}%`,
                    background: sort === "win_rate" ? scoreColor(wr) : "var(--accent-2)",
                  }}
                />
              </div>
              <span className="meta-val">
                {sort === "win_rate" ? `${wr}%` : `${(c.usage * 100).toFixed(1)}%`}
              </span>
            </div>
          );
        })}
      </div>

      <p className="muted meta-note">
        Synthetic demo dataset. Supply an IP-whitelisted Clash Royale API token to mine real ladder battles.
      </p>
    </section>
  );
}
