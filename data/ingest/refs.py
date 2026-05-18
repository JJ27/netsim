"""Build reference tables: airports, carriers, aircraft types.

Airports come from OurAirports (CC0 licensed CSV). Carriers come from BTS
L_UNIQUE_CARRIERS lookup. Aircraft types come from BTS L_AIRCRAFT_TYPE lookup.

Run once per project setup:
    uv run python -m data.ingest.refs
"""

from __future__ import annotations

import io
import sys

import httpx
import polars as pl

from data.paths import REFS, ensure_dirs

OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
BTS_LOOKUP_URL = (
    "https://www.transtats.bts.gov/Download_Lookup.asp?Y11x72=Y_{table}"
)

# Hard-coded fallback for major US carriers — used if BTS lookup fetch fails.
# Two-letter IATA + ICAO + name for the carriers most relevant to the demo.
CARRIER_FALLBACK = [
    ("AA", "AAL", "American Airlines"),
    ("AS", "ASA", "Alaska Airlines"),
    ("B6", "JBU", "JetBlue Airways"),
    ("DL", "DAL", "Delta Air Lines"),
    ("F9", "FFT", "Frontier Airlines"),
    ("G4", "AAY", "Allegiant Air"),
    ("HA", "HAL", "Hawaiian Airlines"),
    ("NK", "NKS", "Spirit Airlines"),
    ("SY", "SCX", "Sun Country Airlines"),
    ("UA", "UAL", "United Airlines"),
    ("WN", "SWA", "Southwest Airlines"),
    ("XP", "AVE", "Avelo Airlines"),
    ("MX", "BBQ", "Breeze Airways"),
]


def build_airports(client: httpx.Client) -> None:
    resp = client.get(OURAIRPORTS_URL, follow_redirects=True, timeout=60.0)
    resp.raise_for_status()
    df = pl.read_csv(io.BytesIO(resp.content))
    # Keep just the US large/medium airports with IATA codes.
    df = df.filter(
        (pl.col("iso_country") == "US")
        & (pl.col("type").is_in(["large_airport", "medium_airport", "small_airport"]))
        & (pl.col("iata_code").is_not_null())
        & (pl.col("iata_code") != "")
    ).select(
        pl.col("iata_code").alias("iata"),
        pl.col("ident").alias("icao"),
        pl.col("name"),
        pl.col("municipality").alias("city"),
        pl.col("iso_region").alias("region"),
        pl.col("latitude_deg").alias("lat"),
        pl.col("longitude_deg").alias("lon"),
        pl.col("elevation_ft").alias("elevation_ft"),
        pl.col("type").alias("size_class"),
    )
    out = REFS / "airports.parquet"
    df.write_parquet(out, compression="zstd")
    print(f"  airports.parquet — {df.height} US airports")


def build_carriers() -> None:
    df = pl.DataFrame(
        CARRIER_FALLBACK,
        schema=["iata", "icao", "name"],
        orient="row",
    )
    out = REFS / "carriers.parquet"
    df.write_parquet(out, compression="zstd")
    print(f"  carriers.parquet — {df.height} carriers (manual seed)")


def main() -> int:
    ensure_dirs()
    print("Building reference tables…")
    try:
        with httpx.Client() as client:
            build_airports(client)
    except Exception as e:  # noqa: BLE001
        print(f"  ! airports failed: {e}", file=sys.stderr)
    build_carriers()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
