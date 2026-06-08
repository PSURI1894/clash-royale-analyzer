# Clash Royale Helper

A standalone **deck maker, analyzer, RAG tactical advisor, and reduced-fidelity battle simulator** for Clash Royale, built on a decoupled backend where the LLM acts as an *analytical lens over a rigid database* — it never invents numbers.

> Full roadmap & architecture: see the approved build plan. This repo is being built phase by phase.

## Architecture (target)

```
Next.js web  ──►  FastAPI  ──►  LlamaIndex orchestration + Context Fusion
                                  │            │              │
                          Postgres+pgvector  Neo4j      Battle Engine
                          Redis (cache + Celery)        Claude (opus + haiku)
```

**Data sources** (the original case study was wrong about the official API — it has *no* combat stats or win rates):
- **cr-api-data** (static JSON) → combat math: HP, damage, hit speed, range, per-level arrays.
- **Official CR API** → players, **battle logs** (Phase 3 mining). Keys are IP-locked.
- **Curated + mined + scraped + simulated** → the matchup graph, blended as a confidence-weighted ensemble.

## Phase status

| Phase | What | Status |
|---|---|---|
| 0 | Foundation & data spine (ingest cr-api-data → DB, `/cards` API) | ✅ done |
| 1 | Deterministic deck analyzer (`/analyze`) + Next.js deck-builder UI | ✅ done |
| 2 | Knowledge graph + curated matchups + confidence-weighted ensemble (`/matchup`, `/cards/{key}/relations`) | ✅ done |
| 3 | Battle-log mining ETL → empirical `mined` edges + card meta (`/mining/stats`, `/meta/cards`) | ✅ done |
| 4 | RAG tactical advisor: Context Fusion + grounding guardrail (`/advise`) | ✅ done |
| 5 | Deterministic battle engine: duel + arena sim, `simulated` ensemble edges (`/simulate`) | ✅ done |
| 6 | Scraping (4th source) + reconciliation, saved decks, rate-limit/cache/metrics, Docker | ✅ done |

## Quickstart (local dev — no Docker needed)

Requires **Python 3.11+** and (later) **Node 20+**.

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Ingest card data into a local SQLite DB
.\.venv\Scripts\python.exe -m cr_helper.ingest

# Seed the matchup knowledge graph (167 curated counter/synergy edges)
.\.venv\Scripts\python.exe -m cr_helper.graph.seed

# Mine empirical win-rates (offline synthetic source — no API token needed)
.\.venv\Scripts\python.exe -m cr_helper.mining --source synthetic --limit 10000

# Build the RAG index (embed the strategy corpus for the advisor)
.\.venv\Scripts\python.exe -m cr_helper.rag.index

# Seed simulated edges from the battle engine (deterministic duels)
.\.venv\Scripts\python.exe -m cr_helper.engine.simulated

# Seed the scraped cross-check source (offline synthetic fixture)
.\.venv\Scripts\python.exe -m cr_helper.scrape

# Run the API
.\.venv\Scripts\python.exe -m uvicorn cr_helper.main:app --reload
# -> http://127.0.0.1:8000/docs   (try POST /advise, /matchup, /analyze)

# Tests
.\.venv\Scripts\python.exe -m pytest
```

## Front end (Next.js deck builder)

```powershell
cd web
npm install
npm run dev          # http://localhost:3000  (needs the API running on :8000)
```

Pick 8 cards (or load a preset) → **Analyze deck** → archetype, elixir curve, defensive
air/ground DPS, win-condition detection, and a vulnerability report with a stability score.
Once the deck is full, the **Matchup simulator** scores it against a meta archetype
(Lavaloon, Golem Beatdown, X-Bow Siege, …) using the knowledge graph — showing which
threats your deck answers and which it has no response to.

## Full stack (Docker — Postgres + Neo4j + Redis)

```powershell
docker compose up -d          # start Postgres+pgvector, Neo4j, Redis
# set DATABASE_URL to the Postgres URL in .env, then run ingest + API as above

# Optional: store the knowledge graph in Neo4j instead of SQL
#   pip install -e ".[neo4j]"; set NEO4J_URI=bolt://localhost:7687, GRAPH_BACKEND=neo4j
#   then re-run  python -m cr_helper.graph.seed   (seeds SQL + Neo4j)
```

The knowledge graph is **storage-agnostic**: it runs on SQLite/Postgres by default (Docker-free),
with a drop-in **Neo4j adapter** (`cr_helper/graph/neo4j_repo.py`) for the full stack. Every edge
carries provenance `{value, source, confidence, sample_size}`; the **ensemble resolver** blends
curated priors with mined/simulated/scraped evidence via a confidence-weighted average — and
`GET /cards/{key}/relations` exposes the per-source `components` so the blend is auditable.

## Battle-log mining (Phase 3)

```powershell
# Offline synthetic source — deterministic, no token (outcomes biased by the curated graph)
python -m cr_helper.mining --source synthetic --limit 10000

# Real ladder battles — needs an IP-whitelisted token from developer.clashroyale.com
#   set CLASH_ROYALE_API_TOKEN in .env, then crawl from seed player tags:
python -m cr_helper.mining --source api --seed-tags "#2PP0" "#9YJUPU9LV" --limit 5000
```

The pipeline parses battle logs → resolves cards to catalog keys → dedupes → stores → aggregates
empirical win-rates into `source=mined` edges (level/sample/margin-guarded). As real battles
accumulate, mined evidence **outweighs and refines** the curated prior — e.g. the expert
`inferno-tower ⟶ golem` "hard counter" (0.90) is pulled to the observed deck-level win-rate (~0.68).
Keys are **IP-locked**: run the harvester on a static-IP host (or proxy), never serverless.
Scheduling: wrap `run_mining` with Celery beat (`cr_helper/mining/tasks.py`, needs Redis).

## RAG tactical advisor (Phase 4)

`POST /advise` returns a structured, **grounded** coaching report for a deck + matchup.

- **Context Fusion** assembles an evidence pack — hard facts from the analyzer (elixir, DPS,
  anti-air), the graph (matchup score, threat coverage) and mining (card win-rates), plus the
  top retrieved strategy notes.
- **Grounding guardrail (the anti-hallucination spine):** every number in the output must
  appear in the evidence or it is flagged. Each report carries `grounding.ok` + `engine`.
- **Two clients, one interface:** an offline **Stub** (deterministic, grounded by construction —
  runs with no key) and **Claude** (`opus` synthesis, prompt-cached system prompt + tool-use
  structured output) when `ANTHROPIC_API_KEY` is set (`pip install -e ".[llm]"`).
- **Embeddings:** offline feature-hashing by default; `EMBED_BACKEND=voyage` for production.
  Vector search is Python cosine on SQLite — swap in **pgvector** at scale.

The corpus (`data/curated/strategy.json`) is original, paraphrased guidance — not copyrighted text.

## Battle engine (Phase 5)

Deterministic, reduced-fidelity combat — pure Python, no API key or Docker.

- **v0 duel** (`POST /simulate/duel`): discrete-hit 1v1 trade calculator (winner + leftover HP).
- **Arena sim** (`POST /simulate`): movement, targeting, splash, towers and river/bridge routing
  on a simplified 18×32 grid; reports tower damage, survivors and final unit positions.
- **`simulated` edges:** `python -m cr_helper.engine.simulated` runs a duel for every fighter pair
  and writes decisive wins as low-weight `source=simulated` counter edges — completing the
  **curated + mined + simulated** ensemble (visible in `/cards/{key}/relations` `components`).
- Frontend: an SVG arena board visualising the push outcome.

## Scraping & productionization (Phase 6)

- **Scraped source** (`python -m cr_helper.scrape`): a robots/ToS-respecting, network-gated
  scraper feeds card meta + popular counters as a low-weight `scraped` cross-check — the 4th
  and final ensemble source. The offline `FixtureScrapeSource` (a clearly-synthetic placeholder)
  makes it verifiable without touching any live site; `HttpScrapeSource` is the real path,
  disabled unless `SCRAPE_ALLOW_NETWORK=true` and you've confirmed the site's terms.
- **Reconciliation** (`GET /meta/reconcile`): scraped vs mined card win-rates (mean |Δ| + agreement).
- **Saved decks** (`/decks`): per-browser token — no accounts or passwords — with validated CRUD.
- **Hardening:** per-client rate limiting, an analyze response cache, and `/healthz` + `/stats`
  (uptime, request counts, cache hits).

### Deploy (full stack)

```powershell
docker compose up -d --build          # Postgres+pgvector, Neo4j, Redis, and the API image
docker compose exec api python -m cr_helper.ingest
docker compose exec api python -m cr_helper.graph.seed
# web -> Vercel (set NEXT_PUBLIC_API_BASE); API/harvester -> a static-IP host (the CR API is IP-locked)
```

## Layout

```
backend/cr_helper/        FastAPI app, models, ingest pipeline
  ingest/                 cr-api-data download → normalize → load
  analyzer/               deterministic deck metrics + archetype/vulnerabilities
  graph/                  matchup graph: ensemble resolver, SQL + Neo4j repos, seed
  mining/                 battle-log ETL: sources (api/synthetic), parse, aggregate
  rag/                    advisor: embed, vector store, retrieve, fusion, guardrail, clients
  engine/                 battle engine: units, duel, arena, scenario, simulated edges
  scrape/                 guarded scraper, reconciliation, scraped-edge seeder
  runtime.py              rate limiter, metrics, TTL cache
  routers/                cards, analyze, graph, mining, advise, simulate, decks, system
backend/tests/            pytest (56 tests)
web/                      Next.js (deck builder + matchup + meta + coach + sim + saved decks)
docker-compose.yml        Postgres+pgvector, Neo4j, Redis, API
Dockerfile                backend API image
data/curated/             curated matchup edges + strategy corpus + scraped fixture
data/fixtures/            sample official-API battle log (parser tests)
```
