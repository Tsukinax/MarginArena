"""HTTP API. One POST runs one Arena and streams its events as Server-Sent Events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from marginarena.arena import run_arena
from marginarena.llm import LLMClient, LLMSettings
from marginarena.sample import load_shop

# Token Factory's limits (20 requests/min per account) keep the fallback Arena small (spec, ADR 0002).
FALLBACK_CAPS = {"skus": 3, "rounds": 2, "rivals": 2, "strategists": 1}


class ArenaRequest(BaseModel):
    shop: Literal["glow-lab-bkk"] = "glow-lab-bkk"
    """Only sample shops for now. Token Factory may only see sample data (ADR 0004)."""
    skus: list[str] | None = None
    rounds: int = Field(default=3, ge=1, le=5)
    rivals: int = Field(default=6, ge=1, le=6)
    strategists: int = Field(default=3, ge=0, le=3)


def create_app(
    llm_settings: LLMSettings | None = None,
    llm_transport: httpx.AsyncBaseTransport | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> FastAPI:
    app = FastAPI(title="MarginArena")

    def settings() -> LLMSettings:
        return llm_settings or LLMSettings.from_env()

    @app.get("/api/health")
    async def health() -> dict:
        s = settings()
        return {"route": s.route, "model": s.model}

    @app.post("/api/arena")
    async def arena(request: ArenaRequest) -> StreamingResponse:
        s = settings()
        shop = load_shop(request.shop)
        skus, rounds, rivals, strategists = request.skus, request.rounds, request.rivals, request.strategists
        if s.route == "token-factory":
            skus = (skus or [i.sku.id for i in shop.invited])[: FALLBACK_CAPS["skus"]]
            rounds = min(rounds, FALLBACK_CAPS["rounds"])
            rivals = min(rivals, FALLBACK_CAPS["rivals"])
            strategists = min(strategists, FALLBACK_CAPS["strategists"])

        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def produce() -> None:
            llm = LLMClient(s, transport=llm_transport, sleep=sleep)
            try:
                await run_arena(shop, skus, rounds, rivals, strategists, llm, queue.put)
            except Exception as error:  # surface the failure to the client, then end the stream
                await queue.put({"type": "error", "message": f"{type(error).__name__}: {error}"})
            finally:
                await llm.aclose()
                await queue.put(None)

        async def stream():
            task = asyncio.create_task(produce())
            while (event := await queue.get()) is not None:
                yield f"data: {json.dumps(event, default=str, ensure_ascii=False)}\n\n"
            await task

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app
