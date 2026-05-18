# NetSim

Outside-in airline network intelligence — a conversational alternative to spreadsheets for analyzing airlines you don't own.

CS 153 final project. Marquee demo: Spirit Airlines Q1 2023 → Q4 2024.

## What it does

Pick a US airline + a time window. Watch the network evolve on a map. Ask in plain English what happened and why. Run counterfactuals against real downstream demand data.

Built for the people who *watch* airlines — competing carriers' network planners, equity analysts, DOJ/DOT regulators, distressed-asset investors, and aviation consultancies — not the airline's own operations team.

## Stack

- **Frontend:** Next.js 15 + TypeScript + deck.gl + Mapbox GL + Tailwind
- **Backend:** FastAPI + Anthropic SDK (Claude Opus 4.7 + Sonnet 4.6)
- **Data:** DuckDB over Parquet — BTS DB1B (origin-destination tickets, demand & fares), BTS On-Time Marketing Carrier (per-flight records, capacity & cancellations)
- **Sim:** networkx-backed route graph + gravity demand model fit on DB1B

## Layout

```
data/   ingestion scripts, parquet warehouse, references
sim/    route graph, demand model, scenario engine
agents/ Historian / Diagnostician / Strategist / Adjudicator + orchestrator
api/    FastAPI app
web/    Next.js frontend
eval/   held-out events for scoring agent quality
notebooks/  exploratory analysis
```

## Quick start

```bash
# Python env (uv)
uv sync

# Reference data (airports, carriers)
uv run python -m data.ingest.refs

# Pull BTS data (one-time; multi-GB download)
uv run python -m data.ingest.download_db1b   --start 2018-1 --end 2025-3
uv run python -m data.ingest.download_ontime --start 2018-1 --end 2025-12

# Sanity-check the warehouse before doing anything else
uv run python -m data.ingest.verify

# Backend
uv run uvicorn api.main:app --reload

# Frontend
cd web && npm install && npm run dev
```

Set `ANTHROPIC_API_KEY` and `MAPBOX_TOKEN` in `.env` first; see `.env.example`.

## Status

Week 1 scaffold. See the plan in the project root.
