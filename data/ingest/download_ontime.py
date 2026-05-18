"""Download and normalize the BTS On-Time Marketing Carrier Performance dataset.

This dataset has per-flight records (year/month) for all US domestic flights
reported by major carriers from January 2018 onward. It includes tail numbers,
scheduled vs actual times, cancellations, and origin/dest — which is what we
use as the capacity-side ground truth (replacing T-100).

URL pattern (verified across multiple months):
    https://transtats.bts.gov/PREZIP/On_Time_Marketing_Carrier_On_Time_Performance_Beginning_January_2018_YYYY_M.zip

Compressed ~33 MB/month. 96 months (Jan 2018 → Dec 2025) ≈ 3 GB.

Real BTS column names are CamelCase; we rename to UPPER_SNAKE for downstream
queries. We also drop the Div1..Div5 diversion columns to save space — they're
nearly always empty.

Usage:
    uv run python -m data.ingest.download_ontime --start 2018-1 --end 2025-12
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

from data.paths import ONTIME, RAW, ensure_dirs

BASE_URL = "https://transtats.bts.gov/PREZIP"
FILENAME_TEMPLATE = (
    "On_Time_Marketing_Carrier_On_Time_Performance_Beginning_January_2018_{year}_{month}.zip"
)

# Subset of On-Time columns we keep. Diversion fields and most delay-cause
# breakdowns are dropped to keep parquet size manageable.
COLUMN_MAP = {
    "Year": "YEAR",
    "Quarter": "QUARTER",
    "Month": "MONTH",
    "DayofMonth": "DAY_OF_MONTH",
    "FlightDate": "FLIGHT_DATE",
    "Marketing_Airline_Network": "MARKETING_CARRIER",
    "IATA_Code_Marketing_Airline": "MARKETING_IATA",
    "Flight_Number_Marketing_Airline": "MARKETING_FLIGHT_NUMBER",
    "Operating_Airline ": "OPERATING_CARRIER",  # NB trailing space in source
    "Operating_Airline": "OPERATING_CARRIER",   # tolerated if trimmed
    "IATA_Code_Operating_Airline": "OPERATING_IATA",
    "Tail_Number": "TAIL_NUMBER",
    "Flight_Number_Operating_Airline": "OPERATING_FLIGHT_NUMBER",
    "OriginAirportID": "ORIGIN_AIRPORT_ID",
    "OriginCityMarketID": "ORIGIN_CITY_MARKET_ID",
    "Origin": "ORIGIN",
    "OriginState": "ORIGIN_STATE",
    "DestAirportID": "DEST_AIRPORT_ID",
    "DestCityMarketID": "DEST_CITY_MARKET_ID",
    "Dest": "DEST",
    "DestState": "DEST_STATE",
    "CRSDepTime": "CRS_DEP_TIME",
    "DepTime": "DEP_TIME",
    "DepDelay": "DEP_DELAY",
    "DepDelayMinutes": "DEP_DELAY_MINUTES",
    "CRSArrTime": "CRS_ARR_TIME",
    "ArrTime": "ARR_TIME",
    "ArrDelay": "ARR_DELAY",
    "ArrDelayMinutes": "ARR_DELAY_MINUTES",
    "Cancelled": "CANCELLED",
    "CancellationCode": "CANCELLATION_CODE",
    "Diverted": "DIVERTED",
    "CRSElapsedTime": "CRS_ELAPSED_TIME",
    "ActualElapsedTime": "ACTUAL_ELAPSED_TIME",
    "AirTime": "AIR_TIME",
    "Flights": "FLIGHTS",
    "Distance": "DISTANCE",
    "CarrierDelay": "CARRIER_DELAY",
    "WeatherDelay": "WEATHER_DELAY",
    "NASDelay": "NAS_DELAY",
    "SecurityDelay": "SECURITY_DELAY",
    "LateAircraftDelay": "LATE_AIRCRAFT_DELAY",
}


@dataclass
class Month:
    year: int
    month: int

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d}"

    def filename(self) -> str:
        return FILENAME_TEMPLATE.format(year=self.year, month=self.month)

    def url(self) -> str:
        return f"{BASE_URL}/{self.filename()}"

    def raw_path(self) -> Path:
        return RAW / self.filename()

    def parquet_path(self) -> Path:
        return ONTIME / f"year={self.year}" / f"month={self.month:02d}" / "data.parquet"


def parse_months(start: str, end: str) -> list[Month]:
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    out: list[Month] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(Month(y, m))
        m += 1
        if m == 13:
            m = 1
            y += 1
    return out


def download(mo: Month, client: httpx.Client, force: bool = False) -> Path:
    out = mo.raw_path()
    if out.exists() and not force:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    with client.stream("GET", mo.url(), follow_redirects=True) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"GET {mo.url()} -> {resp.status_code}")
        total = int(resp.headers.get("content-length", 0))
        with open(out, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=str(mo), leave=False
        ) as pbar:
            for chunk in resp.iter_bytes(chunk_size=1 << 20):
                f.write(chunk)
                pbar.update(len(chunk))
    return out


def normalize(zip_path: Path, mo: Month) -> Path:
    out = mo.parquet_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(csv_name) as f:
            data = f.read()
    df = pl.read_csv(io.BytesIO(data), infer_schema_length=10000, ignore_errors=True)
    # Strip trailing whitespace on column names (BTS has 'Operating_Airline ' with a space).
    df = df.rename({c: c.strip() for c in df.columns if c != c.strip()})
    rename = {k.strip(): v for k, v in COLUMN_MAP.items() if k.strip() in df.columns}
    df = df.rename(rename).select(sorted(set(rename.values())))
    df.write_parquet(out, compression="zstd", compression_level=6)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and normalize On-Time Marketing Carrier months")
    parser.add_argument("--start", required=True, help="Start month, e.g. 2018-1")
    parser.add_argument("--end", required=True, help="End month, e.g. 2025-12")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--keep-zip", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    months = parse_months(args.start, args.end)
    print(f"Fetching {len(months)} months: {months[0]} → {months[-1]}")

    with httpx.Client(timeout=httpx.Timeout(60.0, read=600.0)) as client:
        for mo in tqdm(months, desc="OnTime"):
            if mo.parquet_path().exists() and not args.force:
                continue
            try:
                zip_path = download(mo, client, force=args.force)
                normalize(zip_path, mo)
                if not args.keep_zip:
                    zip_path.unlink(missing_ok=True)
            except Exception as e:  # noqa: BLE001
                print(f"  ! {mo} failed: {e}", file=sys.stderr)
                continue
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
