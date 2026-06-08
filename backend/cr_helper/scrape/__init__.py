"""Scraping enrichment (Phase 6) — the guarded `scraped` source.

A robots/ToS-respecting, rate-limited, network-gated scraper feeds card meta and
popular counters as a low-weight cross-check into the ensemble, plus a
reconciliation report against mined meta. The offline FixtureScrapeSource (a
clearly-synthetic placeholder) makes the whole path verifiable without touching
any live site; HttpScrapeSource is the real path and stays disabled by default.
"""
