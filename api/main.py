"""FastAPI entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat, network

app = FastAPI(title="NetSim", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(network.router, prefix="/network", tags=["network"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
