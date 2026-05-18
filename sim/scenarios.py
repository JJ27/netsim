"""Apply a sequence of Modifications to a baseline NetworkState and return a
new (counterfactual) state suitable for scoring by the Adjudicator.
"""

from __future__ import annotations

from sim.state import Modification, NetworkState

# TODO Week 5: implement apply(state, mods) -> NetworkState.


def apply(state: NetworkState, mods: tuple[Modification, ...]) -> NetworkState:
    raise NotImplementedError("scenarios.apply will land in week 5")
