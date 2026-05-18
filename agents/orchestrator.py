"""Orchestrator: classifies the user query and runs the specialist pipeline.

Skeleton only — the streaming version lands in week 3 alongside the SSE endpoint.
"""

from __future__ import annotations

from typing import Literal

from agents import adjudicator, diagnostician, historian, strategist
from agents.runner import run

QueryKind = Literal["describe", "explain", "counterfactual", "compare"]


def classify(_user_message: str) -> QueryKind:
    # TODO Week 3: Claude-classify the user query.
    return "describe"


def handle(user_message: str) -> dict[str, str]:
    kind = classify(user_message)
    history = run(historian.CONFIG, user_message)

    if kind == "describe":
        return {"historian": history["final_text"]}

    if kind == "explain":
        diag = run(diagnostician.CONFIG, user_message, prior_context=history["final_text"])
        return {"historian": history["final_text"], "diagnostician": diag["final_text"]}

    if kind == "counterfactual":
        strat = run(strategist.CONFIG, user_message, prior_context=history["final_text"])
        adj = run(
            adjudicator.CONFIG,
            user_message,
            prior_context=history["final_text"] + "\n\n" + strat["final_text"],
        )
        return {
            "historian": history["final_text"],
            "strategist": strat["final_text"],
            "adjudicator": adj["final_text"],
        }

    # compare — two historian runs, then synthesis; week 3
    return {"historian": history["final_text"]}
