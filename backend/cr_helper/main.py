"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import __version__
from .db import init_db
from .routers import advise, analyze, cards, graph, mining, simulate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist. Production uses Alembic migrations.
    init_db()
    yield


app = FastAPI(
    title="Clash Royale Helper API",
    version=__version__,
    summary="Deck maker, analyzer, RAG advisor & battle simulator — data spine.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-friendly; tighten to the web origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cards.router)
app.include_router(analyze.router)
app.include_router(graph.router)
app.include_router(mining.router)
app.include_router(advise.router)
app.include_router(simulate.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")
