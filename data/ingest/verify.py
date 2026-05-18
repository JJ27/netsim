"""Sanity-check the warehouse after ingest.

Runs known-answer queries and reports pass/fail. Designed to fail loudly with
specific diagnostics if the parquet schema, column names, or data coverage are
off, so problems surface before you spend hours debugging downstream agents.

Usage:
    uv run python -m data.ingest.verify
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import duckdb

from data.paths import DB1B_MARKET, ONTIME, REFS


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def _conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


def check_files_exist() -> Check:
    issues = []
    if not DB1B_MARKET.exists() or not any(DB1B_MARKET.rglob("data.parquet")):
        issues.append("DB1B Market parquet missing — run download_db1b.py")
    if not ONTIME.exists() or not any(ONTIME.rglob("data.parquet")):
        issues.append("On-Time parquet missing — run download_ontime.py")
    if not (REFS / "airports.parquet").exists():
        issues.append("airports.parquet missing — run refs.py")
    if not (REFS / "carriers.parquet").exists():
        issues.append("carriers.parquet missing — run refs.py")
    return Check(
        "warehouse files exist",
        passed=not issues,
        detail="OK" if not issues else " / ".join(issues),
    )


def check_db1b_columns() -> Check:
    conn = _conn()
    glob = f"{DB1B_MARKET}/year=*/quarter=*/data.parquet"
    try:
        cols = {r[0] for r in conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{glob}') LIMIT 0").fetchall()}
    except Exception as e:
        return Check("DB1B schema", False, f"could not read: {e}")
    required = {"YEAR", "QUARTER", "ORIGIN", "DEST", "TICKET_CARRIER", "PASSENGERS", "MARKET_FARE"}
    missing = required - cols
    return Check(
        "DB1B has expected UPPER_SNAKE columns",
        passed=not missing,
        detail=f"all present" if not missing else f"missing: {sorted(missing)}",
    )


def check_ontime_columns() -> Check:
    conn = _conn()
    glob = f"{ONTIME}/year=*/month=*/data.parquet"
    try:
        cols = {r[0] for r in conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{glob}') LIMIT 0").fetchall()}
    except Exception as e:
        return Check("On-Time schema", False, f"could not read: {e}")
    required = {"YEAR", "MONTH", "ORIGIN", "DEST", "MARKETING_IATA", "TAIL_NUMBER", "CANCELLED", "DISTANCE"}
    missing = required - cols
    return Check(
        "On-Time has expected UPPER_SNAKE columns",
        passed=not missing,
        detail=f"all present" if not missing else f"missing: {sorted(missing)}",
    )


def check_spirit_route_count() -> Check:
    """Spirit's quarterly route count should:
    - drop noticeably in 2020 (COVID)
    - decline in 2024 (GTF + restructuring)
    - never be 0 in our window
    """
    conn = _conn()
    glob = f"{ONTIME}/year=*/month=*/data.parquet"
    try:
        rows = conn.execute(
            f"""
            SELECT YEAR, QUARTER, COUNT(DISTINCT ORIGIN || '-' || DEST) AS routes
            FROM read_parquet('{glob}')
            WHERE MARKETING_IATA = 'NK' AND CANCELLED < 0.5
            GROUP BY YEAR, QUARTER ORDER BY YEAR, QUARTER
            """
        ).fetchall()
    except Exception as e:
        return Check("Spirit quarterly route count", False, f"query failed: {e}")
    if not rows:
        return Check("Spirit quarterly route count", False, "no Spirit data found")
    by_period = {(int(y), int(q)): int(r) for y, q, r in rows}
    # Soft checks: 2024 Q3 routes should be less than 2023 Q3 (capacity contraction)
    a = by_period.get((2023, 3))
    b = by_period.get((2024, 3))
    note = f"2023Q3={a} routes, 2024Q3={b} routes"
    if a and b and b >= a:
        return Check(
            "Spirit 2024Q3 < 2023Q3 (GTF contraction)",
            False,
            f"{note} — expected decline; check ingest coverage",
        )
    return Check("Spirit 2024Q3 < 2023Q3 (GTF contraction)", True, note)


def check_spirit_cancellation_spike() -> Check:
    """Spirit's monthly cancellation rate in 2024 should peak above ~3%
    (well above industry baseline of ~1-2%)."""
    conn = _conn()
    glob = f"{ONTIME}/year=2024/month=*/data.parquet"
    try:
        rows = conn.execute(
            f"""
            SELECT MONTH,
                   COUNT(*)::BIGINT AS sched,
                   SUM(CASE WHEN CANCELLED >= 0.5 THEN 1 ELSE 0 END)::BIGINT AS canc
            FROM read_parquet('{glob}')
            WHERE MARKETING_IATA = 'NK'
            GROUP BY MONTH ORDER BY MONTH
            """
        ).fetchall()
    except Exception as e:
        return Check("Spirit 2024 cancellation rate", False, f"query failed: {e}")
    if not rows:
        return Check("Spirit 2024 cancellation rate", False, "no 2024 data")
    rates = [(int(m), c / s if s else 0.0) for m, s, c in rows]
    peak_month, peak = max(rates, key=lambda x: x[1])
    detail = f"peak month {peak_month}: {peak:.1%} (industry baseline ~1-2%)"
    # Just informational — don't fail on this. Some quarters won't spike.
    return Check("Spirit 2024 cancellation rate observable", True, detail)


def check_db1b_spirit_passengers() -> Check:
    """Spirit (NK) should have meaningful passenger counts in DB1B."""
    conn = _conn()
    glob = f"{DB1B_MARKET}/year=*/quarter=*/data.parquet"
    try:
        rows = conn.execute(
            f"""
            SELECT YEAR, QUARTER, SUM(PASSENGERS)::BIGINT AS pax
            FROM read_parquet('{glob}')
            WHERE TICKET_CARRIER = 'NK'
            GROUP BY YEAR, QUARTER ORDER BY YEAR, QUARTER
            """
        ).fetchall()
    except Exception as e:
        return Check("DB1B Spirit passengers", False, f"query failed: {e}")
    if not rows:
        return Check("DB1B Spirit passengers", False, "no Spirit data in DB1B")
    total = sum(int(p) for _, _, p in rows)
    first = rows[0]
    last = rows[-1]
    detail = (
        f"{len(rows)} quarters of NK data, total sample={total:,} pax "
        f"(first {first[0]}Q{first[1]}={first[2]:,}, last {last[0]}Q{last[1]}={last[2]:,})"
    )
    return Check("DB1B Spirit passengers", total > 100_000, detail)


def main() -> int:
    print("Verifying NetSim data warehouse…\n")
    checks = [
        check_files_exist(),
        check_db1b_columns(),
        check_ontime_columns(),
        check_db1b_spirit_passengers(),
        check_spirit_route_count(),
        check_spirit_cancellation_spike(),
    ]
    pad = max(len(c.name) for c in checks) + 2
    for c in checks:
        mark = "PASS" if c.passed else "FAIL"
        print(f"  [{mark}] {c.name:<{pad}} {c.detail}")
    failed = sum(1 for c in checks if not c.passed)
    print(f"\n{len(checks) - failed} / {len(checks)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
