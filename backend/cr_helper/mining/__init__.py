"""Battle-log mining ETL (Phase 3).

Extract battles -> parse to catalog keys -> dedupe -> store -> aggregate empirical
win-rates -> write `source=mined` edges into the ensemble graph and per-card meta
stats. Pluggable sources: an offline `SyntheticSource` (dev/test/demo) and a real
`OfficialApiSource` (needs an IP-whitelisted developer.clashroyale.com token).
"""
