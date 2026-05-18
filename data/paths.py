"""Shared path constants for the data warehouse layout."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WAREHOUSE = Path(os.environ.get("NETSIM_WAREHOUSE_DIR", REPO_ROOT / "data" / "warehouse"))
RAW = WAREHOUSE / "raw"
REFS = REPO_ROOT / "data" / "refs"

# Partitioned parquet roots (hive-style year=YYYY/quarter=Q or year=YYYY/month=MM)
DB1B_MARKET = WAREHOUSE / "db1b_market"
ONTIME = WAREHOUSE / "ontime"


def ensure_dirs() -> None:
    """Create warehouse subdirectories if missing."""
    for p in (WAREHOUSE, RAW, REFS, DB1B_MARKET, ONTIME):
        p.mkdir(parents=True, exist_ok=True)
