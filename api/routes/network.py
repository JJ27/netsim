"""Network state endpoints — read-only views the frontend uses to render maps."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sim.graph import build_network_state

router = APIRouter()


@router.get("/{carrier}")
def get_network(carrier: str, year: int, quarter: int) -> dict:
    if quarter not in (1, 2, 3, 4):
        raise HTTPException(400, "quarter must be 1-4")
    try:
        state = build_network_state(carrier.upper(), year, quarter)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(404, f"could not build state: {e}") from e
    return {
        "carrier": state.carrier,
        "period": state.period,
        "routes": [
            {
                "o": r.origin,
                "d": r.dest,
                "seats": r.seats,
                "departures": r.departures,
                "passengers": r.passengers,
                "distance_mi": r.distance_mi,
            }
            for r in state.routes
        ],
        "fleet": [
            {"aircraft_type": f.aircraft_type, "departures": f.departures, "seats": f.seats_offered}
            for f in state.fleet
        ],
    }
