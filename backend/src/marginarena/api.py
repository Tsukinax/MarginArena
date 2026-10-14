"""HTTP API. One POST runs one Arena and streams its events as Server-Sent Events."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import secrets
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from marginarena.arena import Emit, run_arena
from marginarena.explainer import Language, explain
from marginarena.llm import LLMClient, LLMSettings, first_healthy
from marginarena.sample import describe_shop, load_shop

# Token Factory's limits (20 requests/min per account) keep the fallback Arena small (spec, ADR 0002).
FALLBACK_CAPS = {"skus": 4, "rounds": 2, "rivals": 2, "strategists": 1}
# Signs each decided SKU when RESULT_SIGNING_KEY is unset. It lives as long as this process, so a deploy that runs
# several processes must set RESULT_SIGNING_KEY.
PROCESS_KEY = secrets.token_bytes(32)
# The default demo: a full 12-SKU run recorded on Token Factory (backend/scripts/record_arena.py), replayed in about
# REPLAY_SECONDS whatever it took live.
RECORDED_RUN = Path(__file__).resolve().parents[3] / "evidence" / "runs" / "token-factory-sample-12sku.sse"
REPLAY_SECONDS = 20


class ArenaRequest(BaseModel):
    shop: Literal["glow-lab-bkk"] = "glow-lab-bkk"
    """Only sample shops for now. Token Factory may only see sample data (ADR 0004)."""
    skus: list[str] | None = None
    rounds: int = Field(default=3, ge=1, le=5)
    rivals: int = Field(default=6, ge=1, le=6)
    strategists: int = Field(default=3, ge=0, le=3)
    recorded: bool = False
    """Replay the recorded run, labelled "recorded", instead of calling the model."""


class ExplainRequest(BaseModel):
    result: dict
    """One decided SKU, exactly as the Arena returned it."""
    language: Language = "th"


def create_app(
    llm_settings: LLMSettings | None = None,
    llm_transport: httpx.AsyncBaseTransport | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    routes: tuple[LLMSettings, ...] | None = None,
    web_dist: Path | None = None,
) -> FastAPI:
    """`llm_settings` forces one route; otherwise the first healthy of `routes` (default: from the environment).

    `web_dist` (default: the WEB_DIST environment variable) is the built web app, served at / so one container
    runs everything; without it only /api is served, as in development where Vite serves the web app.
    """
    app = FastAPI(title="MarginArena")
    key = os.environ.get("RESULT_SIGNING_KEY", "").encode() or PROCESS_KEY

    async def settings() -> LLMSettings:
        if llm_settings:
            return llm_settings
        return await first_healthy(routes or LLMSettings.routes_from_env(), llm_transport)

    @app.get("/api/health")
    async def health() -> dict:
        s = await settings()
        return {"route": s.route, "model": s.model}

    @app.get("/api/shops/{shop_id}")
    async def shop(shop_id: Literal["glow-lab-bkk"]) -> dict:
        return describe_shop(load_shop(shop_id))

    @app.post("/api/arena")
    async def arena(request: ArenaRequest) -> StreamingResponse:
        s = await settings()
        shop = load_shop(request.shop)
        skus, rounds, rivals, strategists = request.skus, request.rounds, request.rivals, request.strategists
        if s.route == "token-factory":
            # Q55/Q56: products chosen to show every kind of Verdict, unless the Seller picked products.
            skus = (skus or list(shop.fallback_demo_skus) or [i.sku.id for i in shop.invited])[: FALLBACK_CAPS["skus"]]
            rounds = min(rounds, FALLBACK_CAPS["rounds"])
            rivals = min(rivals, FALLBACK_CAPS["rivals"])
            strategists = min(strategists, FALLBACK_CAPS["strategists"])

        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def emit(event: dict) -> None:
            # /api/explain accepts only results this server's Arena signed, unchanged.
            if event["type"] == "sku_decided":
                event["signature"] = _signature(event, key)
            elif event["type"] == "run_done":
                for result in event["results"]:
                    result["signature"] = _signature(result, key)
            await queue.put(event)

        async def live() -> None:
            llm = LLMClient(s, transport=llm_transport, sleep=sleep)
            try:
                await run_arena(shop, skus, rounds, rivals, strategists, llm, emit)
            finally:
                await llm.aclose()

        async def produce() -> None:
            try:
                await (_replay(RECORDED_RUN, emit, sleep) if request.recorded else live())
            except Exception as error:  # surface the failure to the client, then end the stream
                await queue.put({"type": "error", "message": f"{type(error).__name__}: {error}"})
            finally:
                await queue.put(None)

        async def stream():
            task = asyncio.create_task(produce())
            while (event := await queue.get()) is not None:
                yield f"data: {json.dumps(event, default=str, ensure_ascii=False)}\n\n"
            await task

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/explain")
    async def explain_verdict(request: ExplainRequest) -> dict:
        # Token Factory may see only our sample data, and every number explained must be the engine's (ADR 0001).
        signature = request.result.get("signature")
        if not isinstance(signature, str) or not hmac.compare_digest(signature, _signature(request.result, key)):
            raise HTTPException(403, "Only a Verdict this server's Arena produced, unchanged, can be explained.")
        s = await settings()
        llm = LLMClient(s, transport=llm_transport, sleep=sleep)
        try:
            explanation = await explain(request.result, request.language, llm)
        finally:
            await llm.aclose()
        return {**explanation, "route": s.route, "model": s.model}

    web = web_dist or os.environ.get("WEB_DIST")
    if web:  # mounted last, so every /api route above still wins
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app


async def _replay(path: Path, emit: Emit, sleep: Callable[[float], Awaitable[None]]) -> None:
    """Emits a recorded run's events in order, keeping their rhythm but finishing in about REPLAY_SECONDS."""
    timed: list[tuple[float, dict]] = []
    at = 0.0
    for line in path.read_text().splitlines():
        if line.startswith(": t="):  # the recorder's seconds since the start
            at = float(line[4:])
        elif line.startswith("data: "):
            timed.append((at, json.loads(line[6:])))
    scale = min(1.0, REPLAY_SECONDS / max(timed[-1][0], 1e-9))
    previous = 0.0
    for at, event in timed:
        await sleep((at - previous) * scale)
        previous = at
        await emit(event)


def _signature(result: dict, key: bytes) -> str:
    """HMAC of one decided SKU, over every field except the event type and the signature itself."""
    body = {k: v for k, v in result.items() if k not in ("type", "signature")}
    message = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()
