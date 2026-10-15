"""OpenAI-compatible chat client for both inference routes (ADR 0002).

It asks for a JSON object, validates it against a pydantic model, paces requests to the route's
limits, and retries 429 and 5xx answers. Invalid output is rejected and counted, never repaired.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel, ValidationError

RETRY_STATUSES = {429, 500, 502, 503}
MAX_ATTEMPTS = 4
# Per-model request quirks on Token Factory (docs/api-guide/tokenfactory-guide.md): Qwen3.8-27B thinks at xhigh unless
# told otherwise, which spends its token budget before it answers.
MODEL_PARAMS = {"Qwen3.8-27B": {"reasoning_effort": "low"}}


@dataclass(frozen=True)
class LLMSettings:
    route: str
    """"mi300x" (our own vLLM endpoint) or "token-factory" (AMD's shared endpoint)."""
    base_url: str
    api_key: str
    model: str
    requests_per_minute: int = 20
    concurrency: int = 8
    fallback_model: str | None = None
    """Answers in place of `model` once the route reports that model has no workers; the run reports the switch."""

    @classmethod
    def routes_from_env(cls) -> tuple[LLMSettings, ...]:
        """Routes in order of preference: our own MI300X endpoint if configured, then Token Factory."""
        token_factory = cls(
            route="token-factory",
            base_url=os.environ.get("TOKEN_FACTORY_BASE_URL", "https://developer.amd.com.cn/radeon/api/v1"),
            api_key=os.environ.get("TOKEN_FACTORY_API_KEY", ""),
            model=os.environ.get("TOKEN_FACTORY_MODEL", "Gemma-4-31B-IT"),
            requests_per_minute=15,  # the account limit is 20/min; leave headroom for other callers
            # DeepSeek-V4-Flash answers JSON without thinking first; Qwen3.8-27B spent our whole token budget thinking
            # on 15 Oct, and Gemma-4-31B-IT left Token Factory's catalogue that night (Q58, Q59).
            fallback_model=os.environ.get("TOKEN_FACTORY_FALLBACK_MODEL", "DeepSeek-V4-Flash"),
        )
        if not os.environ.get("VLLM_BASE_URL"):
            return (token_factory,)
        mi300x = cls(
            route="mi300x",
            base_url=os.environ["VLLM_BASE_URL"],
            api_key=os.environ.get("VLLM_API_KEY", ""),
            model=os.environ.get("VLLM_MODEL", "google/gemma-4-31B-it"),
            requests_per_minute=6000,
            concurrency=128,
        )
        return (mi300x, token_factory)


async def served_models(route: LLMSettings, transport: httpx.AsyncBaseTransport | None = None) -> set[str] | None:
    """The model IDs the route serves now (its /models catalogue), or None when the catalogue can't be read."""
    try:
        async with httpx.AsyncClient(transport=transport, timeout=10) as client:
            response = await client.get(
                route.base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {route.api_key}"}
            )
        if response.status_code == 200:
            return {m["id"] for m in response.json().get("data", [])}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        pass
    return None


async def first_healthy(
    routes: tuple[LLMSettings, ...], transport: httpx.AsyncBaseTransport | None = None
) -> LLMSettings:
    """The first route whose /models answers; the last route is the fallback and is not probed (ADR 0002)."""
    for route in routes[:-1]:
        try:
            async with httpx.AsyncClient(transport=transport, timeout=3) as client:
                response = await client.get(
                    route.base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {route.api_key}"}
                )
            if response.status_code == 200:
                return route
        except httpx.HTTPError:
            pass
    return routes[-1]


@dataclass
class Telemetry:
    model: str = ""
    """The model answering now: the route's model, or its fallback after a switch."""
    calls_ok: int = 0
    calls_invalid: int = 0
    calls_failed: int = 0
    retries: int = 0
    in_flight: int = 0
    completion_tokens: int = 0
    started: float = field(default_factory=time.monotonic)

    def snapshot(self) -> dict:
        elapsed = max(time.monotonic() - self.started, 1e-9)
        return {
            "model": self.model,
            "calls_ok": self.calls_ok,
            "calls_invalid": self.calls_invalid,
            "calls_failed": self.calls_failed,
            "retries": self.retries,
            "in_flight": self.in_flight,
            "completion_tokens": self.completion_tokens,
            "tokens_per_second": round(self.completion_tokens / elapsed, 1),
            "elapsed_seconds": round(elapsed, 2),
        }


class LLMClient:
    def __init__(
        self,
        settings: LLMSettings,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.settings = settings
        self.model = settings.model
        self.telemetry = Telemetry(model=settings.model)
        self._http = httpx.AsyncClient(
            base_url=settings.base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {settings.api_key}"},
            transport=transport,
            timeout=120,
        )
        self._sleep = sleep
        self._slots = asyncio.Semaphore(settings.concurrency)
        self._interval = 60.0 / settings.requests_per_minute
        self._next_start = 0.0
        self._pace = asyncio.Lock()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def json_chat[T: BaseModel](
        self, system: str, user: str, schema: type[T], accept: Callable[[T], bool] | None = None
    ) -> T | None:
        """One validated JSON answer, or None when the model failed or answered out of contract.

        `accept` checks rules that depend on context (for example, limits relative to a price).
        """
        body = {
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0.8,
            "max_tokens": 700,
        }
        async with self._slots:
            data = await self._post_with_retries(body)
        if data is None:
            self.telemetry.calls_failed += 1
            return None
        try:
            content = data["choices"][0]["message"]["content"]
            parsed = schema.model_validate(json.loads(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError):
            self.telemetry.calls_invalid += 1
            return None
        if accept is not None and not accept(parsed):
            self.telemetry.calls_invalid += 1
            return None
        self.telemetry.calls_ok += 1
        self.telemetry.completion_tokens += int(data.get("usage", {}).get("completion_tokens") or 0)
        return parsed

    async def _post_with_retries(self, body: dict) -> dict | None:
        for attempt in range(MAX_ATTEMPTS):
            await self._wait_for_turn()
            self.telemetry.in_flight += 1
            try:
                request = {**body, "model": self.model, **MODEL_PARAMS.get(self.model, {})}
                response = await self._http.post("/chat/completions", json=request)
            except httpx.HTTPError:
                response = None
            finally:
                self.telemetry.in_flight -= 1
            if response is not None and response.status_code == 200:
                return response.json()
            if self._fall_back(response):
                continue  # straight to the fallback model: retrying a model that is not served only waits
            if response is not None and response.status_code not in RETRY_STATUSES:
                return None
            if attempt + 1 < MAX_ATTEMPTS:
                self.telemetry.retries += 1
                retry_after = response.headers.get("Retry-After") if response is not None else None
                await self._sleep(float(retry_after) if retry_after else 2.0**attempt)
        return None

    def _fall_back(self, response: httpx.Response | None) -> bool:
        """Switches the rest of the run to the fallback model when the route says it can't serve the model now.

        Token Factory answers 500 "no_available_workers" while a model is down, and 400 "Requested model ... not
        supported" once it has left the catalogue.
        """
        fallback = self.settings.fallback_model
        if (
            not fallback
            or self.model == fallback
            or response is None
            or not (b"no_available_workers" in response.content or b"not supported" in response.content)
        ):
            return False
        self.model = self.telemetry.model = fallback
        return True

    async def _wait_for_turn(self) -> None:
        """Space request starts evenly so the route's requests-per-minute limit is never exceeded."""
        async with self._pace:
            now = time.monotonic()
            wait = self._next_start - now
            self._next_start = max(now, self._next_start) + self._interval
        if wait > 0:
            await self._sleep(wait)
