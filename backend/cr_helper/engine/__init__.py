"""Deterministic battle engine (Phase 5).

Reduced-fidelity but fully deterministic combat simulation (no RNG, stable order):
- v0 `duel`: discrete-hit 1v1 trade calculator (winner + leftover HP).
- arena: a spatial sim on a simplified 18x32 grid with movement, targeting,
  splash, towers and river/bridge routing.

Engine outcomes seed `source=simulated` edges into the ensemble graph and power
the /simulate endpoints. Pure Python (small-scale; NumPy-vectorizable later).
"""
