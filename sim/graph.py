"""Build NetworkState snapshots from the DuckDB warehouse.

Capacity-side source: BTS On-Time Marketing Carrier Performance (one row per
flight). We aggregate to O-D-quarter per carrier.

Demand-side data (DB1B) is layered on by other tools, not this one.
"""

from __future__ import annotations

from functools import lru_cache

import duckdb

from data.paths import ONTIME
from sim.state import FleetEntry, NetworkState, Route


@lru_cache(maxsize=1)
def _conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


def build_network_state(carrier: str, year: int, quarter: int) -> NetworkState:
    """Snapshot a carrier's served network for a quarter from On-Time data.

    `carrier` is the IATA code of the *marketing* carrier (e.g. 'NK' for Spirit).
    """
    conn = _conn()
    glob = f"{ONTIME}/year={year}/month=*/data.parquet"
    months = {1: (1, 2, 3), 2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12)}[quarter]
    month_list = ",".join(str(m) for m in months)

    routes_df = conn.execute(
        f"""
        SELECT
            ORIGIN AS origin,
            DEST AS dest,
            COUNT(*)::BIGINT AS departures_scheduled,
            SUM(CASE WHEN CANCELLED < 0.5 THEN 1 ELSE 0 END)::BIGINT AS departures_performed,
            SUM(CASE WHEN CANCELLED >= 0.5 THEN 1 ELSE 0 END)::BIGINT AS cancellations,
            MAX(DISTANCE)::BIGINT AS distance_mi
        FROM read_parquet('{glob}')
        WHERE MARKETING_IATA = ?
          AND MONTH IN ({month_list})
        GROUP BY ORIGIN, DEST
        HAVING departures_performed > 0
        ORDER BY departures_performed DESC
        """,
        [carrier],
    ).fetchall()

    routes = tuple(
        Route(
            origin=o,
            dest=d,
            seats=0,  # On-Time does not report seats; demand-side fills this in.
            departures=int(dep_perf or 0),
            passengers=0,
            distance_mi=int(dist or 0),
            aircraft_types=(),
        )
        for o, d, _dep_sched, dep_perf, _cancel, dist in routes_df
    )

    # Fleet from On-Time: tail numbers operated by the carrier.
    # Aircraft type requires a join to the FAA registry (planned for week 4).
    fleet_df = conn.execute(
        f"""
        SELECT
            TAIL_NUMBER,
            COUNT(*)::BIGINT AS departures
        FROM read_parquet('{glob}')
        WHERE MARKETING_IATA = ?
          AND MONTH IN ({month_list})
          AND CANCELLED < 0.5
          AND TAIL_NUMBER IS NOT NULL
          AND TAIL_NUMBER != ''
        GROUP BY TAIL_NUMBER
        ORDER BY departures DESC
        """,
        [carrier],
    ).fetchall()

    fleet = tuple(
        FleetEntry(aircraft_type=0, departures=int(dep), seats_offered=0)
        for _tail, dep in fleet_df
    )

    return NetworkState(
        carrier=carrier, year=year, quarter=quarter, routes=routes, fleet=fleet
    )
