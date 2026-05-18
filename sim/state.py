"""NetworkState: an immutable snapshot of a carrier's network at a point in time.

A NetworkState is what agents reason over. It's hydrated from the warehouse by
sim.graph.build_network_state and is serializable to JSON for prompt caching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Route:
    origin: str
    dest: str
    seats: int
    departures: int
    passengers: int
    distance_mi: int
    aircraft_types: tuple[int, ...]  # T-100 aircraft type codes


@dataclass(frozen=True)
class FleetEntry:
    aircraft_type: int  # T-100 code
    departures: int
    seats_offered: int


@dataclass(frozen=True)
class NetworkState:
    carrier: str  # IATA, e.g. "NK"
    year: int
    quarter: int
    routes: tuple[Route, ...]
    fleet: tuple[FleetEntry, ...]

    @property
    def period(self) -> str:
        return f"{self.year}Q{self.quarter}"

    @property
    def airports_served(self) -> set[str]:
        return {r.origin for r in self.routes} | {r.dest for r in self.routes}


@dataclass(frozen=True)
class NetworkChange:
    """A diff entry between two NetworkStates."""

    kind: Literal["added", "dropped", "grew", "shrank"]
    origin: str
    dest: str
    delta_departures: int
    delta_seats: int


@dataclass(frozen=True)
class Modification:
    """A proposed change to a baseline network — input to the Adjudicator."""

    kind: Literal["add_route", "drop_route", "resize_route", "ground_aircraft"]
    origin: str | None = None
    dest: str | None = None
    departures: int | None = None
    aircraft_type: int | None = None
    rationale: str = ""


@dataclass(frozen=True)
class ScenarioResult:
    baseline_state: NetworkState
    modifications: tuple[Modification, ...]
    predicted_passengers: dict[tuple[str, str], float] = field(default_factory=dict)
    predicted_revenue: dict[tuple[str, str], float] = field(default_factory=dict)
    notes: str = ""
