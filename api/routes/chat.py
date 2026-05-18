"""Chat endpoint — SSE streaming agent responses.

Week 1 skeleton: synchronous POST that runs the orchestrator. The streaming
SSE version lands in week 3.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from agents.orchestrator import handle

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    carrier: str | None = None
    year: int | None = None
    quarter: int | None = None


@router.post("")
def chat(req: ChatRequest) -> dict:
    return handle(req.message)
