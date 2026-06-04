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
| 2 | Neo4j knowledge graph + curated matchups | ⬜ |
| 3 | Battle-log mining ETL (official API) | ⬜ |
| 4 | RAG tactical advisor (Claude + pgvector) | ⬜ |
| 5 | Deterministic battle engine | ⬜ |
| 6 | Scraping enrichment + productionization | ⬜ |

## Quickstart (local dev — no Docker needed)

Requires **Python 3.11+** and (later) **Node 20+**.

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Ingest card data into a local SQLite DB
.\.venv\Scripts\python.exe -m cr_helper.ingest

# Run the API
.\.venv\Scripts\python.exe -m uvicorn cr_helper.main:app --reload
# -> http://127.0.0.1:8000/docs   (try GET /cards, GET /cards/knight)

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

## Full stack (Docker — Postgres + Neo4j + Redis)

```powershell
docker compose up -d          # start Postgres+pgvector, Neo4j, Redis
# set DATABASE_URL to the Postgres URL in .env, then run ingest + API as above
```

## Layout

```
backend/cr_helper/        FastAPI app, models, ingest pipeline
  ingest/                 cr-api-data download → normalize → load
  routers/                API endpoints
backend/tests/            pytest
web/                      Next.js frontend (Phase 1)
docker-compose.yml        Postgres+pgvector, Neo4j, Redis
data/                     raw downloads (gitignored), curated seeds
```
