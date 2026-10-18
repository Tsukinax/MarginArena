"""HTTP API. One POST runs one Arena and streams its events as Server-Sent Events."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from marginarena.arena import Emit, run_arena
from marginarena.explainer import Language, explain
from marginarena.llm import LLMClient, LLMSettings, first_healthy, served_models
from marginarena.sample import describe_shop, load_shop

# Token Factory's limits (20 requests/min per account) keep the fallback Arena small (spec, ADR 0002).
FALLBACK_CAPS = {"skus": 4, "rounds": 2, "rivals": 2, "strategists": 1}
# Signs each decided SKU when RESULT_SIGNING_KEY is unset. It lives as long as this process, so a deploy that runs
# several processes must set RESULT_SIGNING_KEY.
PROCESS_KEY = secrets.token_bytes(32)
# The default demo: a full 12-SKU run recorded on Token Factory (backend/scripts/record_arena.py), replayed in about
# REPLAY_SECONDS whatever it took live. The package ships its own copy of evidence/runs/token-factory-sample-12sku.sse,
# because a deploy of the backend alone can't see evidence/.
RECORDED_RUN = Path(__file__).resolve().parent / "sample" / "recorded" / "token-factory-sample-12sku.sse"
REPLAY_SECONDS = 20
EVOLUS_URL = "https://api.evolus.ai/api/v1"
# The fictional sample invitation (backend/scripts/make_sample_invitation.py), the only document the extractor is sent.
SAMPLE_INVITATION = Path(__file__).resolve().parent / "sample" / "glow-lab-bkk-invitation.pdf"
# Evolus runs fetched read-only from their execution records (evidence/evolus-*.md): the live site's reading of the
# sample invitation, and the Verdict workflow's run on the recorded Arena's Verdicts. A live read can take minutes,
# and the event workspace expires before judging may end, so these are shown, labelled as recorded.
RECORDED_READING = Path(__file__).resolve().parent / "sample" / "recorded" / "evolus-invitation-reading.json"
RECORDED_WORKFLOW = Path(__file__).resolve().parent / "sample" / "recorded" / "evolus-verdict-workflow.json"
# Gemma's English and Thai explanations of the recorded run's 12 Verdicts (backend/scripts/record_explanations.py),
# each keyed by the fingerprint of the exact Verdict it explains. Judges get them at once, labelled as recorded, even
# while Token Factory is down; asking again with `live` calls the model.
RECORDED_EXPLANATIONS = Path(__file__).resolve().parent / "sample" / "recorded" / "explanations-12sku.json"
# Each server process limits the calls that spend shared quota: Token Factory allows 20 requests a minute per account,
# and every Evolus call leaves an execution in the event workspace. The limits are per client address and, with the
# _ALL ceilings, for everyone together. They hold per process: Vercel may run several. Recorded runs and readings are
# never limited.
LIVE_RUNS_PER_HOUR, LIVE_RUNS_PER_HOUR_ALL = 4, 20
LIVE_READS_PER_HOUR, LIVE_READS_PER_HOUR_ALL = 4, 10
CONFIRMS_PER_HOUR, CONFIRMS_PER_HOUR_ALL = 4, 20
EXPLANATIONS_PER_HOUR, EXPLANATIONS_PER_HOUR_ALL = 40, 200
POLLS_PER_HOUR = 300  # the Confirm step asks Evolus for its run's status every 3 seconds
LIVE_RUN_LEASE_SECONDS = 600  # frees Token Factory for the next live run even if one never reports back
REFUSED_MODEL_SECONDS = 600  # after the route refuses the main model, runs start on the fallback for this long


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
    live: bool = False
    """Ask the model even when an explanation recorded for this exact Verdict exists."""


class ConfirmRequest(BaseModel):
    results: list[dict] = Field(min_length=1, max_length=12)
    """The decided SKUs the Seller confirms, exactly as the Arena returned them."""


class ReadRequest(BaseModel):
    recorded: bool = False
    """Replay the reading the live site made on 15 Oct, labelled "recorded", instead of calling Evolus."""


class Quota:
    """At most `per_hour` uses for each client address, and `all_per_hour` for everyone, in any hour."""

    def __init__(self, per_hour: int, all_per_hour: int | None = None) -> None:
        self.per_hour = per_hour
        self.all_per_hour = all_per_hour
        self.uses: dict[str, deque[float]] = {}

    def take(self, address: str) -> bool:
        if not self._take(address, self.per_hour):
            return False
        return self.all_per_hour is None or self._take("", self.all_per_hour)

    def _take(self, key: str, limit: int) -> bool:
        now = time.monotonic()
        if len(self.uses) > 10_000:  # forget addresses that have not called for an hour
            self.uses = {k: u for k, u in self.uses.items() if now - u[-1] < 3600}
        uses = self.uses.setdefault(key, deque())
        while uses and now - uses[0] >= 3600:
            uses.popleft()
        if len(uses) >= limit:
            return False
        uses.append(now)
        return True


def create_app(
    llm_settings: LLMSettings | None = None,
    llm_transport: httpx.AsyncBaseTransport | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    routes: tuple[LLMSettings, ...] | None = None,
    web_dist: Path | None = None,
    evolus_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """`llm_settings` forces one route; otherwise the first healthy of `routes` (default: from the environment).

    `web_dist` (default: the WEB_DIST environment variable) is the built web app, served at / so one container
    runs everything; without it only /api is served, as in development where Vite serves the web app.
    """
    app = FastAPI(title="MarginArena")
    key = os.environ.get("RESULT_SIGNING_KEY", "").encode() or PROCESS_KEY

    def check_signed(result: dict) -> None:
        # Token Factory may see only our sample data, and every number used must be the engine's (ADR 0001).
        signature = result.get("signature")
        if not isinstance(signature, str) or not hmac.compare_digest(signature, _signature(result, key)):
            raise HTTPException(403, "Only a Verdict this server's Arena produced, unchanged, can be used.")

    def evolus(*ids: str) -> tuple[httpx.AsyncClient, list[str]]:
        """A client for the Evolus workspace, and the values of the resource IDs named in `ids`."""
        missing = [name for name in ("EVOLUS_API_KEY", "EVOLUS_APPLICATION_ID", *ids) if not os.environ.get(name)]
        if missing:
            raise HTTPException(503, f"Evolus is not set up on this server: {', '.join(missing)} missing.")
        headers = {"X-ApiKey": os.environ["EVOLUS_API_KEY"], "X-Application-Id": os.environ["EVOLUS_APPLICATION_ID"]}
        client = httpx.AsyncClient(base_url=EVOLUS_URL, transport=evolus_transport, headers=headers, timeout=300)
        return client, [os.environ[name] for name in ids]

    reading: dict = {}  # this process's last matching reading: the same document reads the same
    live_runs = Quota(LIVE_RUNS_PER_HOUR, LIVE_RUNS_PER_HOUR_ALL)
    live_reads = Quota(LIVE_READS_PER_HOUR, LIVE_READS_PER_HOUR_ALL)
    confirms = Quota(CONFIRMS_PER_HOUR, CONFIRMS_PER_HOUR_ALL)
    explanations = Quota(EXPLANATIONS_PER_HOUR, EXPLANATIONS_PER_HOUR_ALL)
    polls = Quota(POLLS_PER_HOUR)
    lease: dict = {"until": 0.0, "owner": None}  # while a live run holds Token Factory, another would stall both
    explained: dict[tuple[str, str], dict] = {}  # each signed Verdict is written once per language
    recorded_explanations = _recorded_explanations(RECORDED_EXPLANATIONS)
    finished: dict[str, dict] = {}  # Evolus runs that completed or failed: their answer no longer changes

    def release(owner: object | None) -> None:
        if owner is not None and lease["owner"] is owner:  # a run that outlived its lease must not end the next one's
            lease.update(until=0.0, owner=None)

    catalogue: dict = {"read_at": None, "ids": None}  # the route's model catalogue, read at most once a minute
    refused: dict = {"model": None, "until": 0.0}  # a model the route just would not serve, skipped for a while

    def remember(s: LLMSettings, llm: LLMClient) -> None:
        """After a run or an explanation that had to switch models, later ones start on the fallback for a while."""
        if llm.model != s.model:
            refused.update(model=s.model, until=time.monotonic() + REFUSED_MODEL_SECONDS)

    async def settings() -> LLMSettings:
        """The route, starting on its fallback model when the route's catalogue no longer lists the main one."""
        s = llm_settings or await first_healthy(routes or LLMSettings.routes_from_env(), llm_transport)
        if not s.fallback_model:
            return s
        if refused["model"] == s.model and time.monotonic() < refused["until"]:
            return replace(s, model=s.fallback_model)
        if catalogue["read_at"] is None or time.monotonic() - catalogue["read_at"] > 60:
            catalogue.update(read_at=time.monotonic(), ids=await served_models(s, llm_transport))
        ids = catalogue["ids"]
        if ids is not None and s.model not in ids and s.fallback_model in ids:
            return replace(s, model=s.fallback_model)
        return s

    @app.get("/api/health")
    async def health() -> dict:
        s = await settings()
        return {"route": s.route, "model": s.model}

    @app.get("/api/arena/recorded")
    async def recorded_run() -> dict:
        """The recorded run's headline, for the first screen before anyone presses play."""
        return _recorded_summary(RECORDED_RUN)

    @app.get("/api/shops/{shop_id}")
    async def shop(shop_id: Literal["glow-lab-bkk"]) -> dict:
        return describe_shop(load_shop(shop_id))

    @app.post("/api/arena")
    async def arena(request: ArenaRequest, http: Request) -> StreamingResponse:
        owner = None  # the live run's hold on Token Factory; a recorded run holds nothing
        if not request.recorded:
            if time.monotonic() < lease["until"]:
                raise HTTPException(
                    429,
                    "Another live run is using AMD Token Factory right now. "
                    "Watch the recorded run, or try again in about two minutes.",
                )
            if not live_runs.take(_address(http)):
                raise HTTPException(429, "Live runs are used up for this hour. The recorded run is always there.")
            owner = object()
            lease.update(until=time.monotonic() + LIVE_RUN_LEASE_SECONDS, owner=owner)
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
                remember(s, llm)
                release(owner)

        async def produce() -> None:
            try:
                await (_replay(RECORDED_RUN, emit, sleep) if request.recorded else live())
            except Exception as error:  # surface the failure to the client, then end the stream
                await queue.put({"type": "error", "message": f"{type(error).__name__}: {error}"})
            finally:
                await queue.put(None)

        async def stream():
            task = asyncio.create_task(produce())
            try:
                while (event := await queue.get()) is not None:
                    yield f"data: {json.dumps(event, default=str, ensure_ascii=False)}\n\n"
                await task
            finally:
                task.cancel()  # a client that leaves ends its run, which frees Token Factory for the next
                release(owner)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/explain")
    async def explain_verdict(request: ExplainRequest, http: Request) -> dict:
        check_signed(request.result)
        saved = None if request.live else recorded_explanations.get((result_digest(request.result), request.language))
        if saved is not None:
            return {**saved, "recorded": True}
        written = (request.result["signature"], request.language)
        if written in explained:
            return explained[written]
        if not explanations.take(_address(http)):
            raise HTTPException(429, "Explanations are used up for this hour. Try again later.")
        s = await settings()
        llm = LLMClient(s, transport=llm_transport, sleep=sleep)
        try:
            explanation = await explain(request.result, request.language, llm)
        finally:
            await llm.aclose()
            remember(s, llm)
        answer = {**explanation, "route": s.route, "model": llm.model}
        if answer["source"] == "model":  # a template stands in only until the model answers
            explained[written] = answer
        return answer

    @app.post("/api/confirm")
    async def confirm(request: ConfirmRequest, http: Request) -> dict:
        """Runs the Evolus Verdict workflow on the confirmed Verdicts (infra/evolus/evolus_kit.py builds it)."""
        for result in request.results:
            check_signed(result)
        if len({r.get("sku") for r in request.results}) != len(request.results):
            raise HTTPException(422, "Each product can be confirmed only once.")
        if not confirms.take(_address(http)):
            raise HTTPException(429, "Live Evolus runs are used up for this hour. Try again later.")
        shop = load_shop("glow-lab-bkk")
        verdicts = [_confirmed(r) for r in request.results]
        payload = {"shop": shop.name, "campaign": shop.invitation["campaign"], "verdicts": verdicts}
        client, (flow,) = evolus("EVOLUS_WORKFLOW_ID")
        async with client:
            answer = await client.post(
                f"/workflows/{flow}/execute", files={"input": (None, json.dumps(payload, ensure_ascii=False))}
            )
        if not answer.is_success:
            raise HTTPException(502, f"The Evolus workflow did not start (HTTP {answer.status_code}).")
        return {"execution_id": answer.json()["executionId"]}

    @app.get("/api/confirm/recorded")  # declared before /api/confirm/{execution_id}, which would also match it
    async def recorded_confirmation() -> dict:
        """The Verdict workflow's run on the recorded Arena's Verdicts, for when a live run cannot start."""
        saved = json.loads(RECORDED_WORKFLOW.read_text())
        return {**{k: v for k, v in saved.items() if k != "note"}, "recorded": True}

    @app.get("/api/confirm/{execution_id}")
    async def confirmation(http: Request, execution_id: str = PathParam(pattern=r"^[A-Za-z0-9-]{1,64}$")) -> dict:
        if execution_id in finished:
            return finished[execution_id]
        if not polls.take(_address(http)):
            raise HTTPException(429, "Too many status checks from this address this hour. Try again later.")
        client, (flow,) = evolus("EVOLUS_WORKFLOW_ID")
        async with client:
            answer = await client.get(f"/workflows/{flow}/executions/{execution_id}")
        if not answer.is_success:
            raise HTTPException(502, f"Evolus did not report the run (HTTP {answer.status_code}).")
        execution = answer.json()
        output = execution.get("output")
        try:
            result = json.loads(output) if isinstance(output, str) else output
        except ValueError:
            result = output
        steps = execution.get("stepStates") or {}
        status = {
            "status": execution.get("status"),
            "result": result,
            # Evolus's own trail of the run: each step's time, and the credits it used (0 on our own model).
            "step_ms": {n: s.get("durationMs") for n, s in steps.items()} if steps else None,
            "credits": (execution.get("consumption") or {}).get("credits"),
        }
        if status["status"] in ("Completed", "Failed"):
            finished[execution_id] = status
        return status

    @app.get("/api/invitation/sample.pdf")
    async def sample_invitation() -> FileResponse:
        return FileResponse(SAMPLE_INVITATION, media_type="application/pdf", filename=SAMPLE_INVITATION.name)

    @app.post("/api/invitation/read")
    async def read_invitation(http: Request, request: ReadRequest | None = None) -> dict:
        """The Evolus extractor reads the sample invitation; each discount is checked against the one the Arena uses."""
        if request and request.recorded:
            saved = json.loads(RECORDED_READING.read_text())
            return {
                "read": saved["read"],
                **_checked(saved["read"]),
                "execution_id": saved["execution_id"],
                "audit_id": saved["audit_id"],
                "read_at": saved["completed_at"],
                "seconds": saved["seconds"],
                "recorded": True,
                "cached": False,
            }
        if reading:
            return {**reading, "cached": True}
        if not live_reads.take(_address(http)):
            raise HTTPException(429, "Live readings are used up for this hour. Try again later.")
        client, (reader, structure) = evolus("EVOLUS_READER_ID", "EVOLUS_INVITATION_STRUCTURE_ID")
        document = (SAMPLE_INVITATION.name, SAMPLE_INVITATION.read_bytes(), "application/pdf")
        async with client:
            answer = await client.post(
                f"/agents/{reader}/json/{structure}/ask-file", params={"useWebhook": "false"}, files={"file": document}
            )
        if not answer.is_success:
            raise HTTPException(502, f"The Evolus extractor did not read the invitation (HTTP {answer.status_code}).")
        read = answer.json()
        result = {
            "read": read,
            **_checked(read),
            "execution_id": answer.headers.get("X-AskFile-Execution-Id"),
            "audit_id": answer.headers.get("X-AskFile-Audit-Id"),
            "read_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "recorded": False,
        }
        if result["matches"]:  # a misreading is not kept, so the next request reads again
            reading.update(result)
        return {**result, "cached": False}

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


def _recorded_summary(path: Path) -> dict:
    """What a recorded run found, read from its own events: its run_started, leaders and run_done."""
    events = [json.loads(line[6:]) for line in path.read_text().splitlines() if line.startswith("data: ")]
    started = next(e for e in events if e["type"] == "run_started")
    done = next(e for e in events if e["type"] == "run_done")
    verdicts = {"approve": 0, "revise": 0, "skip": 0, "escalate": 0}
    for r in done["results"]:
        verdicts["skip" if r["skip"] else r["verdict"]] += 1
    changed = [e["sku"] for e in events if e["type"] == "leader" and e["changed"]]
    skips = [r for r in done["results"] if r["skip"]]
    return {
        "recorded_at": started["recorded_at"],
        "route": started["route"],
        "model": started["model"],
        "products": len(done["results"]),
        "margin_protected": done["margin_protected"],
        # The part of Margin Protected that the Skips keep, from the engine's own per-SKU figures.
        "skipped": [r["sku"] for r in skips],
        "margin_protected_by_skips": str(sum((Decimal(r["protected"]) for r in skips), Decimal("0.00"))),
        "verdicts": verdicts,
        "rival_changed": list(dict.fromkeys(changed)),
        "calls_ok": done["telemetry"]["calls_ok"],
        "calls_failed": done["telemetry"]["calls_failed"],
        "elapsed_seconds": done["telemetry"]["elapsed_seconds"],
    }


def _address(http: Request) -> str:
    """The client's address: Vercel overwrites X-Forwarded-For with it, so it can't be spoofed there; without the
    header (local runs) it is the socket's peer. A deployment behind another proxy should overwrite the header too."""
    forwarded = http.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (http.client.host if http.client else "unknown")


def _checked(read: dict) -> dict:
    """Each minimum discount the extractor read, checked against the invitation the Arena uses."""
    expected = {i.sku.id: i.required_discount * 100 for i in load_shop("glow-lab-bkk").invited}
    found = {str(i.get("sku", "")).strip(): _number(i.get("minimum_discount_pct")) for i in read.get("items", [])}
    checks = [
        {
            "sku": sku,
            "read_discount_pct": None if found.get(sku) is None else f"{found[sku]:f}",
            "expected_discount_pct": f"{pct.normalize():f}",
            "matches": found.get(sku) == pct,
        }
        for sku, pct in expected.items()
    ]
    extra = sorted(set(found) - set(expected))
    return {"checks": checks, "extra_skus": extra, "matches": all(c["matches"] for c in checks) and not extra}


def _number(value) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None and str(value).strip() != "" else None
    except InvalidOperation:
        return None


def _confirmed(r: dict) -> dict:
    """One confirmed Verdict as the Evolus workflow reads it: the engine's figures, passed through unchanged."""
    w = r["waterfall"]
    return {
        "sku": r["sku"],
        "name": r["name"],
        "verdict": r["verdict"],
        "skip": r["skip"],
        "plan": r["chosen_plan"],
        "selling_price": w["selling_price"],
        "voucher": w["voucher"],
        "invited_plan": r["invited_plan"],
        "failed_checks": r["invited_failed_checks"],
        "invited_worst_total": r["invited_worst_total"],
        "dont_join_total": r["dont_join_total"],
    }


def _canonical(result: dict) -> bytes:
    """One decided SKU as stable bytes: every field except the event type and the signature itself."""
    body = {k: v for k, v in result.items() if k not in ("type", "signature")}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def _signature(result: dict, key: bytes) -> str:
    """HMAC of one decided SKU, over the same fields as its fingerprint."""
    return hmac.new(key, _canonical(result), hashlib.sha256).hexdigest()


def result_digest(result: dict) -> str:
    """The fingerprint of one decided SKU: a recorded explanation is served only for the exact Verdict it explains."""
    return hashlib.sha256(_canonical(result)).hexdigest()


def _recorded_explanations(path: Path) -> dict[tuple[str, str], dict]:
    """Recorded explanations that passed the number check, by (fingerprint, language); none without the file."""
    if not path.exists():
        return {}
    entries = json.loads(path.read_text())["explanations"]
    return {
        (e["digest"], e["language"]): {k: v for k, v in e.items() if k not in ("digest", "sku")}
        for e in entries
        if e.get("source") == "model"
    }
