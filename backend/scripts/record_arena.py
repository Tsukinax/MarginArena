"""Record the sample Arena on every invited SKU, as a Server-Sent Events file the app replays, labelled "recorded".

A live check, not a test: the model proposes different moves on every run. Run from the repo root (Token Factory may
only see sample data, which is all this uses):
    uv run --project backend --env-file .env python backend/scripts/record_arena.py [--expect-route mi300x]

With --expect-route it stops before calling any model unless that route is the healthy one, so a droplet that fails its
health probe can't silently record on Token Factory and overwrite the shipped replay.

Each SKU gets the Arena a live run gets on that route: Token Factory's small one (api.FALLBACK_CAPS), or the full one
on our own MI300X (3 Strategists, 6 Rivals, 3 rounds: api.ArenaRequest's defaults). Every invited SKU runs. Writes
evidence/runs/<route>-sample-12sku.sse with each event's seconds since the start as an SSE comment (": t=12.34"),
which the replay uses for pacing, and the copy the app ships (api.RECORDED_RUN) when the route is Token Factory.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from marginarena.api import FALLBACK_CAPS, RECORDED_RUN, ArenaRequest
from marginarena.arena import run_arena
from marginarena.llm import LLMClient, LLMSettings, first_healthy
from marginarena.sample import load_shop

RUNS = Path(__file__).resolve().parents[2] / "evidence" / "runs"


async def main() -> None:
    settings = await first_healthy(LLMSettings.routes_from_env())
    if "--expect-route" in sys.argv and settings.route != sys.argv[sys.argv.index("--expect-route") + 1]:
        raise SystemExit(f"The healthy route is {settings.route}, not the one expected; nothing was recorded.")
    shop = load_shop("glow-lab-bkk")
    started = time.monotonic()
    recorded_at = datetime.now(UTC).isoformat(timespec="seconds")
    lines: list[str] = []

    async def emit(event: dict) -> None:
        if event["type"] == "run_started":
            event = {**event, "recorded_at": recorded_at}
        line = json.dumps(event, ensure_ascii=False, default=str)
        lines.append(f": t={time.monotonic() - started:.2f}\ndata: {line}\n\n")
        if event["type"] == "sku_decided":
            print(f"{event['sku']}: {event['verdict']}{' (skip)' if event['skip'] else ''}", flush=True)
        if event["type"] in ("run_done", "error"):
            print(json.dumps(event.get("telemetry") or event), flush=True)

    full = ArenaRequest()
    caps = FALLBACK_CAPS if settings.route == "token-factory" else vars(full)
    llm = LLMClient(settings)
    try:
        await run_arena(shop, None, caps["rounds"], caps["rivals"], caps["strategists"], llm, emit)
    finally:
        await llm.aclose()
    out = RUNS / f"{settings.route}-sample-12sku.sse"
    out.write_text("".join(lines))
    if out.name == RECORDED_RUN.name:
        RECORDED_RUN.write_text("".join(lines))
    print(f"Wrote {out} ({len(lines)} events, {time.monotonic() - started:.1f} s)")


if __name__ == "__main__":
    asyncio.run(main())
