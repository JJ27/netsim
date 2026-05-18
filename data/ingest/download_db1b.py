"""Download and normalize BTS DB1B Market data.

DB1B Market is BTS's quarterly origin-destination ticket sample (~10% of US
tickets). One row = one O-D market on one ticket: carrier, fare, passengers,
distance, etc.

URL pattern (verified against 2018Q1, 2023Q1, 2024Q3):
    https://transtats.bts.gov/PREZIP/Origin_and_Destination_Survey_DB1BMarket_YYYY_Q.zip

Real BTS column names are CamelCase (ItinID, OriginAirportID, MktFare, TkCarrier,
etc.). We rename to UPPER_SNAKE_CASE so the rest of the codebase doesn't have to
care about BTS's naming convention.

Usage:
    uv run python -m data.ingest.download_db1b --start 2018-1 --end 2025-3
"""

from __future__ import annotations

import argparse
import io
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx
import polars as pl
from tqdm import tqdm

from data.paths import DB1B_MARKET, RAW, ensure_dirs

BASE_URL = "https://transtats.bts.gov/PREZIP"
FILENAME_TEMPLATE = "Origin_and_Destination_Survey_DB1BMarket_{year}_{quarter}.zip"

# BTS CamelCase → our canonical UPPER_SNAKE.
# Only columns we keep are listed; anything else is dropped.
COLUMN_MAP = {
    "ItinID": "ITIN_ID",
    "MktID": "MKT_ID",
    "MktCoupons": "MKT_COUPONS",
    "Year": "YEAR",
    "Quarter": "QUARTER",
    "OriginAirportID": "ORIGIN_AIRPORT_ID",
    "OriginCityMarketID": "ORIGIN_CITY_MARKET_ID",
    "Origin": "ORIGIN",
    "OriginState": "ORIGIN_STATE",
    "DestAirportID": "DEST_AIRPORT_ID",
    "DestCityMarketID": "DEST_CITY_MARKET_ID",
    "Dest": "DEST",
    "DestState": "DEST_STATE",
    "RPCarrier": "REPORTING_CARRIER",
    "TkCarrier": "TICKET_CARRIER",
    "OpCarrier": "OPERATING_CARRIER",
    "BulkFare": "BULK_FARE",
    "Passengers": "PASSENGERS",
    "MktFare": "MARKET_FARE",
    "MktDistance": "MARKET_DISTANCE",
    "MktMilesFlown": "MARKET_MILES_FLOWN",
    "NonStopMiles": "NONSTOP_MILES",
    "ItinGeoType": "ITIN_GEO_TYPE",
    "MktGeoType": "MARKET_GEO_TYPE",
}


@dataclass
class Quarter:
    year: int
    quarter: int

    def __str__(self) -> str:
        return f"{self.year}Q{self.quarter}"

    def filename(self) -> str:
        return FILENAME_TEMPLATE.format(year=self.year, quarter=self.quarter)

    def url(self) -> str:
        return f"{BASE_URL}/{self.filename()}"

    def raw_path(self) -> Path:
        return RAW / self.filename()

    def parquet_path(self) -> Path:
        return DB1B_MARKET / f"year={self.year}" / f"quarter={self.quarter}" / "data.parquet"


def parse_quarters(start: str, end: str) -> list[Quarter]:
    """Inclusive range from 'YYYY-Q' to 'YYYY-Q'."""
    sy, sq = (int(x) for x in start.split("-"))
    ey, eq = (int(x) for x in end.split("-"))
    quarters: list[Quarter] = []
    y, q = sy, sq
    while (y, q) <= (ey, eq):
        quarters.append(Quarter(y, q))
        q += 1
        if q == 5:
            q = 1
            y += 1
    return quarters


def download(qtr: Quarter, client: httpx.Client, force: bool = False) -> Path:
    out = qtr.raw_path()
    if out.exists() and not force:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    with client.stream("GET", qtr.url(), follow_redirects=True) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"GET {qtr.url()} -> {resp.status_code}")
        total = int(resp.headers.get("content-length", 0))
        with open(out, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=str(qtr), leave=False
        ) as pbar:
            for chunk in resp.iter_bytes(chunk_size=1 << 20):
                f.write(chunk)
                pbar.update(len(chunk))
    return out


def normalize(zip_path: Path, qtr: Quarter) -> Path:
    """Read the CSV inside the zip and write a column-pruned Parquet."""
    out = qtr.parquet_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(csv_name) as f:
            data = f.read()
    df = pl.read_csv(io.BytesIO(data), infer_schema_length=10000, ignore_errors=True)
    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(rename).select(list(rename.values()))
    df.write_parquet(out, compression="zstd", compression_level=6)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and normalize DB1B Market quarters")
    parser.add_argument("--start", required=True, help="Start quarter, e.g. 2018-1")
    parser.add_argument("--end", required=True, help="End quarter, e.g. 2025-3")
    parser.add_argument("--force", action="store_true", help="Re-download even if zip exists")
    parser.add_argument("--keep-zip", action="store_true", help="Keep raw zip files after normalize")
    args = parser.parse_args()

    ensure_dirs()
    quarters = parse_quarters(args.start, args.end)
    print(f"Fetching {len(quarters)} quarters: {quarters[0]} → {quarters[-1]}")

    with httpx.Client(timeout=httpx.Timeout(60.0, read=600.0)) as client:
        for qtr in tqdm(quarters, desc="DB1B"):
            if qtr.parquet_path().exists() and not args.force:
                continue
            try:
                zip_path = download(qtr, client, force=args.force)
                normalize(zip_path, qtr)
                if not args.keep_zip:
                    zip_path.unlink(missing_ok=True)
            except Exception as e:  # noqa: BLE001
                print(f"  ! {qtr} failed: {e}", file=sys.stderr)
                continue
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
