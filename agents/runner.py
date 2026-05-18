"""Shared agent-loop runner: handles tool use against Anthropic's API.

Each specialized agent (historian, diagnostician, etc.) is just a config:
a system prompt + a tool subset + a model choice. The runner is the engine.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, AsyncIterator

from anthropic import Anthropic

from agents.tools import anthropic_tool_specs, call_tool

# Model IDs locked in the plan.
MODEL_OPUS = "claude-opus-4-7"
MODEL_SONNET = "claude-sonnet-4-6"

MAX_TOOL_ITERATIONS = 8


@dataclass
class AgentConfig:
    name: str
    system_prompt: str
    tool_names: list[str]
    model: str = MODEL_SONNET
    max_tokens: int = 2048


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def run(agent: AgentConfig, user_message: str, prior_context: str | None = None) -> dict[str, Any]:
    """Synchronous run: returns {final_text, transcript} after the agent stops.

    Implements a standard tool-use loop with a safety cap on iterations.
    """
    client = _client()
    messages: list[dict[str, Any]] = []
    if prior_context:
        messages.append({"role": "user", "content": f"Context:\n{prior_context}"})
        messages.append({"role": "assistant", "content": "Understood. Awaiting the question."})
    messages.append({"role": "user", "content": user_message})

    tool_specs = anthropic_tool_specs(agent.tool_names)
    transcript: list[dict[str, Any]] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = client.messages.create(
            model=agent.model,
            max_tokens=agent.max_tokens,
            system=[
                {
                    "type": "text",
                    "text": agent.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=tool_specs,
            messages=messages,
        )
        transcript.append({"stop_reason": resp.stop_reason, "content": [b.model_dump() for b in resp.content]})
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    try:
                        result = call_tool(block.name, block.input)
                        tool_results.append(
                            {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}
                        )
                    except Exception as e:  # noqa: BLE001
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "is_error": True,
                                "content": f"Tool error: {e}",
                            }
                        )
            messages.append({"role": "user", "content": tool_results})
            continue
        # end_turn or stop_sequence — collect text
        final = "".join(b.text for b in resp.content if b.type == "text")
        return {"final_text": final, "transcript": transcript}

    return {"final_text": "(agent hit tool iteration cap)", "transcript": transcript}


async def stream(agent: AgentConfig, user_message: str) -> AsyncIterator[dict[str, Any]]:
    """Streaming variant — emits {type, agent, payload} events for the UI.

    TODO Week 3: implement using Anthropic streaming API + SSE.
    """
    raise NotImplementedError("Streaming runner lands in week 3.")
    yield  # pragma: no cover
