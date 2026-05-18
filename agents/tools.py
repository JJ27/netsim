"""Tool definitions exposed to agents.

Each tool is a Python function plus a JSON-schema description that Claude sees.
The registry pairs them so the orchestrator can give each agent a focused
subset.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import duckdb

from data.paths import DB1B_MARKET, ONTIME
from sim.graph import build_network_state
from sim.state import NetworkState


# ---------- Tool implementations ----------

def get_network_state(carrier: str, year: int, quarter: int) -> dict[str, Any]:
    """Snapshot a carrier's network for a quarter."""
    state: NetworkState = build_network_state(carrier, year, quarter)
    return {
        "carrier": state.carrier,
        "period": state.period,
        "num_routes": len(state.routes),
        "airports_served": sorted(state.airports_served),
        "routes": [
            {
                "o": r.origin,
                "d": r.dest,
                "departures": r.departures,
                "distance_mi": r.distance_mi,
            }
            for r in state.routes
        ],
        "fleet_size": len(state.fleet),
        "total_departures": sum(f.departures for f in state.fleet),
    }


def get_route_demand(origin: str, dest: str, year_start: int, year_end: int) -> dict[str, Any]:
    """DB1B-derived demand and average fare for an O-D over a year range."""
    conn = duckdb.connect(":memory:")
    glob = f"{DB1B_MARKET}/year=*/quarter=*/data.parquet"
    rows = conn.execute(
        f"""
        SELECT
            YEAR, QUARTER,
            SUM(PASSENGERS)::BIGINT AS passengers,
            (SUM(PASSENGERS * MARKET_FARE) / NULLIF(SUM(PASSENGERS), 0))::DOUBLE AS avg_fare
        FROM read_parquet('{glob}')
        WHERE ORIGIN = ? AND DEST = ?
          AND YEAR BETWEEN ? AND ?
          AND MARKET_FARE > 0
          AND BULK_FARE = 0
        GROUP BY YEAR, QUARTER
        ORDER BY YEAR, QUARTER
        """,
        [origin, dest, year_start, year_end],
    ).fetchall()
    return {
        "origin": origin,
        "dest": dest,
        "series": [
            {"year": y, "quarter": q, "passengers": int(p or 0), "avg_fare": float(f or 0)}
            for y, q, p, f in rows
        ],
    }


def get_market_share(origin: str, dest: str, year: int, quarter: int) -> dict[str, Any]:
    """All carriers serving an O-D market and their passenger share (DB1B)."""
    conn = duckdb.connect(":memory:")
    glob = f"{DB1B_MARKET}/year={year}/quarter={quarter}/data.parquet"
    rows = conn.execute(
        f"""
        SELECT
            TICKET_CARRIER,
            SUM(PASSENGERS)::BIGINT AS pax,
            (SUM(PASSENGERS * MARKET_FARE) / NULLIF(SUM(PASSENGERS), 0))::DOUBLE AS avg_fare
        FROM read_parquet('{glob}')
        WHERE ORIGIN = ? AND DEST = ?
          AND MARKET_FARE > 0
          AND BULK_FARE = 0
        GROUP BY TICKET_CARRIER
        ORDER BY pax DESC
        """,
        [origin, dest],
    ).fetchall()
    total = sum(int(p or 0) for _, p, _ in rows) or 1
    return {
        "origin": origin,
        "dest": dest,
        "period": f"{year}Q{quarter}",
        "carriers": [
            {"carrier": c, "passengers": int(p or 0), "share": int(p or 0) / total, "avg_fare": float(f or 0)}
            for c, p, f in rows
        ],
    }


def compare_periods(carrier: str, year_a: int, quarter_a: int, year_b: int, quarter_b: int) -> dict[str, Any]:
    """Diff a carrier's network between two quarters."""
    a = build_network_state(carrier, year_a, quarter_a)
    b = build_network_state(carrier, year_b, quarter_b)
    a_map = {(r.origin, r.dest): r for r in a.routes}
    b_map = {(r.origin, r.dest): r for r in b.routes}
    added = [k for k in b_map if k not in a_map]
    dropped = [k for k in a_map if k not in b_map]
    resized = []
    for k in a_map.keys() & b_map.keys():
        d_dep = b_map[k].departures - a_map[k].departures
        if abs(d_dep) >= max(5, 0.1 * a_map[k].departures):
            resized.append({"o": k[0], "d": k[1], "delta_departures": d_dep})
    return {
        "carrier": carrier,
        "from": a.period,
        "to": b.period,
        "added_routes": [{"o": o, "d": d} for o, d in added],
        "dropped_routes": [{"o": o, "d": d} for o, d in dropped],
        "resized_routes": resized,
        "summary": {
            "routes_before": len(a.routes),
            "routes_after": len(b.routes),
            "added": len(added),
            "dropped": len(dropped),
            "resized": len(resized),
            "departures_before": sum(r.departures for r in a.routes),
            "departures_after": sum(r.departures for r in b.routes),
        },
    }


def get_cancellation_rate(carrier: str, year: int, quarter: int) -> dict[str, Any]:
    """Cancellation rate for a carrier in a quarter, overall and by month.

    The GTF story shows up here: large carriers' baseline cancellation rate is
    ~1-2%; sustained elevation above ~4% suggests a structural problem.
    """
    conn = duckdb.connect(":memory:")
    glob = f"{ONTIME}/year={year}/month=*/data.parquet"
    months = {1: (1, 2, 3), 2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12)}[quarter]
    month_list = ",".join(str(m) for m in months)
    rows = conn.execute(
        f"""
        SELECT
            MONTH,
            COUNT(*)::BIGINT AS scheduled,
            SUM(CASE WHEN CANCELLED >= 0.5 THEN 1 ELSE 0 END)::BIGINT AS cancelled
        FROM read_parquet('{glob}')
        WHERE MARKETING_IATA = ?
          AND MONTH IN ({month_list})
        GROUP BY MONTH
        ORDER BY MONTH
        """,
        [carrier],
    ).fetchall()
    by_month = [
        {
            "month": int(m),
            "scheduled": int(s),
            "cancelled": int(c),
            "rate": float(c) / float(s) if s else 0.0,
        }
        for m, s, c in rows
    ]
    total_sched = sum(b["scheduled"] for b in by_month)
    total_canc = sum(b["cancelled"] for b in by_month)
    return {
        "carrier": carrier,
        "period": f"{year}Q{quarter}",
        "overall_rate": total_canc / total_sched if total_sched else 0.0,
        "by_month": by_month,
    }


def get_fleet_composition(carrier: str, year: int, quarter: int) -> dict[str, Any]:
    """Distinct tail numbers operated by a carrier in a quarter.

    Aircraft-type lookup (FAA registry join) lands in week 4. For now we report
    raw tail counts and the top tail numbers by departures.
    """
    conn = duckdb.connect(":memory:")
    glob = f"{ONTIME}/year={year}/month=*/data.parquet"
    months = {1: (1, 2, 3), 2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12)}[quarter]
    month_list = ",".join(str(m) for m in months)
    rows = conn.execute(
        f"""
        SELECT
            TAIL_NUMBER,
            COUNT(*)::BIGINT AS departures
        FROM read_parquet('{glob}')
        WHERE MARKETING_IATA = ?
          AND MONTH IN ({month_list})
          AND TAIL_NUMBER IS NOT NULL AND TAIL_NUMBER != ''
          AND CANCELLED < 0.5
        GROUP BY TAIL_NUMBER
        ORDER BY departures DESC
        """,
        [carrier],
    ).fetchall()
    return {
        "carrier": carrier,
        "period": f"{year}Q{quarter}",
        "distinct_tails": len(rows),
        "top_tails": [{"tail": t, "departures": int(d)} for t, d in rows[:20]],
        "total_departures": sum(int(d) for _, d in rows),
    }


def simulate_scenario(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Placeholder; full impl in week 5–6."""
    return {"status": "not_implemented", "note": "scenario simulation lands in week 5–6"}


# ---------- Tool registry ----------

@dataclass
class Tool:
    name: str
    description: str
    schema: dict[str, Any]
    func: Callable[..., Any]


TOOLS: dict[str, Tool] = {
    "get_network_state": Tool(
        name="get_network_state",
        description="Return a carrier's served route network for one quarter (On-Time derived). "
        "Carrier is the IATA marketing code, e.g. 'NK' for Spirit.",
        schema={
            "type": "object",
            "properties": {
                "carrier": {"type": "string", "description": "IATA marketing carrier code."},
                "year": {"type": "integer"},
                "quarter": {"type": "integer", "enum": [1, 2, 3, 4]},
            },
            "required": ["carrier", "year", "quarter"],
        },
        func=get_network_state,
    ),
    "get_route_demand": Tool(
        name="get_route_demand",
        description="DB1B-derived passengers and average fare for an O-D market over a year range.",
        schema={
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Origin airport IATA code."},
                "dest": {"type": "string", "description": "Destination airport IATA code."},
                "year_start": {"type": "integer"},
                "year_end": {"type": "integer"},
            },
            "required": ["origin", "dest", "year_start", "year_end"],
        },
        func=get_route_demand,
    ),
    "get_market_share": Tool(
        name="get_market_share",
        description="All carriers serving an O-D in a quarter, with passenger share and avg fare.",
        schema={
            "type": "object",
            "properties": {
                "origin": {"type": "string"},
                "dest": {"type": "string"},
                "year": {"type": "integer"},
                "quarter": {"type": "integer", "enum": [1, 2, 3, 4]},
            },
            "required": ["origin", "dest", "year", "quarter"],
        },
        func=get_market_share,
    ),
    "compare_periods": Tool(
        name="compare_periods",
        description="Diff a carrier's network between two quarters: added/dropped/resized routes plus departure totals.",
        schema={
            "type": "object",
            "properties": {
                "carrier": {"type": "string"},
                "year_a": {"type": "integer"},
                "quarter_a": {"type": "integer", "enum": [1, 2, 3, 4]},
                "year_b": {"type": "integer"},
                "quarter_b": {"type": "integer", "enum": [1, 2, 3, 4]},
            },
            "required": ["carrier", "year_a", "quarter_a", "year_b", "quarter_b"],
        },
        func=compare_periods,
    ),
    "get_cancellation_rate": Tool(
        name="get_cancellation_rate",
        description="Cancellation rate (overall and by month) for a carrier in a quarter. Elevated, "
        "sustained rates suggest structural issues (e.g. aircraft groundings).",
        schema={
            "type": "object",
            "properties": {
                "carrier": {"type": "string"},
                "year": {"type": "integer"},
                "quarter": {"type": "integer", "enum": [1, 2, 3, 4]},
            },
            "required": ["carrier", "year", "quarter"],
        },
        func=get_cancellation_rate,
    ),
    "get_fleet_composition": Tool(
        name="get_fleet_composition",
        description="Distinct tail numbers and top operating tails for a carrier in a quarter. "
        "Aircraft-type resolution is planned for week 4 once the FAA registry is loaded.",
        schema={
            "type": "object",
            "properties": {
                "carrier": {"type": "string"},
                "year": {"type": "integer"},
                "quarter": {"type": "integer", "enum": [1, 2, 3, 4]},
            },
            "required": ["carrier", "year", "quarter"],
        },
        func=get_fleet_composition,
    ),
    "simulate_scenario": Tool(
        name="simulate_scenario",
        description="Run a counterfactual modification against the demand model. (Week 5+)",
        schema={
            "type": "object",
            "properties": {
                "baseline_carrier": {"type": "string"},
                "baseline_year": {"type": "integer"},
                "baseline_quarter": {"type": "integer"},
                "modifications": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["baseline_carrier", "baseline_year", "baseline_quarter", "modifications"],
        },
        func=simulate_scenario,
    ),
}


def anthropic_tool_specs(names: list[str]) -> list[dict[str, Any]]:
    """Render a subset of tools in Anthropic's tool-use format."""
    return [
        {"name": TOOLS[n].name, "description": TOOLS[n].description, "input_schema": TOOLS[n].schema}
        for n in names
    ]


def call_tool(name: str, args: dict[str, Any]) -> Any:
    """Dispatch a tool call by name."""
    return TOOLS[name].func(**args)
