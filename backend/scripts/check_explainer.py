"""Live check of the explainer: run the sample Arena on the configured route, then explain every Verdict in
Thai and English, and record how many drafts passed the number check.

Run from the repo root (Token Factory may only see sample data, which is all this uses):
    uv run --project backend --env-file .env python backend/scripts/check_explainer.py

Writes evidence/explainer-<route>.json (everything) and evidence/explainer-<route>.md (the report).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from marginarena.api import create_app

EVIDENCE = Path(__file__).resolve().parents[2] / "evidence"
LANGUAGES = ("th", "en")


async def main() -> None:
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://check", timeout=900
    ) as client:
        health = (await client.get("/api/health")).json()
        print(f"route {health['route']}, model {health['model']}", flush=True)
        started = time.monotonic()
        async with client.stream("POST", "/api/arena", json={"shop": "glow-lab-bkk"}) as response:
            events = [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]
        arena_seconds = round(time.monotonic() - started, 1)
        done = events[-1]
        if done["type"] != "run_done":
            raise SystemExit(f"The Arena did not finish: {done}")
        print(f"Arena: {len(done['results'])} SKUs in {arena_seconds} s", flush=True)

        explanations = []
        for result in done["results"]:
            for language in LANGUAGES:
                t0 = time.monotonic()
                response = await client.post("/api/explain", json={"result": result, "language": language})
                response.raise_for_status()
                answer = response.json() | {
                    "sku": result["sku"],
                    "verdict": "skip" if result["skip"] else result["verdict"],
                    "seconds": round(time.monotonic() - t0, 1),
                }
                explanations.append(answer)
                print(f"{result['sku']} {language}: {answer['source']}, {len(answer['rejected'])} rejected", flush=True)

    record = {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "route": health["route"],
        "model": health["model"],
        "arena_seconds": arena_seconds,
        "results": done["results"],
        "explanations": explanations,
    }
    name = f"explainer-{health['route']}"
    (EVIDENCE / f"{name}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n")
    (EVIDENCE / f"{name}.md").write_text(report(record))
    print(f"wrote evidence/{name}.md and .json", flush=True)


def report(r: dict) -> str:
    rows = r["explanations"]
    first = sum(1 for e in rows if e["source"] == "model" and not e["rejected"])
    rewritten = sum(1 for e in rows if e["source"] == "model" and e["rejected"])
    template = sum(1 for e in rows if e["source"] == "template")
    lines = [
        "# Evidence: Verdict explanations checked number by number",
        "",
        "Reproduce: `uv run --project backend --env-file .env python backend/scripts/check_explainer.py`, which writes this file "
        f"and `explainer-{r['route']}.json`.",
        "",
        f"- **Measured:** {r['measured_at']} on route `{r['route']}`, model `{r['model']}`, sample shop Glow Lab BKK.",
        f"- **Arena:** {len(r['results'])} SKUs decided in {r['arena_seconds']} s.",
        f"- **Explanations:** {len(rows)} ({len(r['results'])} SKUs × Thai and English). {first} passed the number check "
        f"on the first draft, {rewritten} passed after a rewrite, and {template} fell back to the numbers-only template.",
        "- **What the check proves:** every number in a shown explanation is a figure from the engine's fact sheet "
        "(rounding allowed). It does not prove that each number is attached to the right label, so the explanation "
        "is shown next to the engine's own table of figures.",
        "",
        "| SKU | Verdict | Language | Source | Drafts rejected | Seconds |",
        "|---|---|---|---|---|---|",
    ]
    for e in rows:
        rejected = "; ".join(", ".join(d["unsupported"]) or "no answer" for d in e["rejected"]) or "none"
        lines.append(f"| {e['sku']} | {e['verdict']} | {e['language']} | {e['source']} | {rejected} | {e['seconds']} |")
    lines += ["", "## The explanations, as shown", ""]
    for e in rows:
        lines += [f"**{e['sku']} ({e['language']}, {e['source']})**", "", f"> {e['text']}", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    asyncio.run(main())
