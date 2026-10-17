"""Record Gemma's English and Thai explanations of the recorded 12-SKU run's Verdicts, so the app can serve them at
once, labelled as recorded, even while Token Factory is down (api.RECORDED_EXPLANATIONS).

Run from the repo root (Token Factory may only see sample data, which is all this uses):
    uv run --project backend --env-file .env python backend/scripts/record_explanations.py --expect-route token-factory

It replays the recorded run through the app (no model call), then asks /api/explain with `live` for each of the 12
Verdicts in English and Thai: 24 explanations, each up to two drafts. It stops before asking anything unless the
expected route is the healthy one and Gemma-4-31B-IT is the model it starts on. Only drafts Gemma-4-31B-IT wrote that
passed the number check are kept for the app; every answer, kept or not, goes to the evidence file.

Writes backend/src/marginarena/sample/recorded/explanations-12sku.json (what the app serves) and
evidence/explainer-replay-12sku.json and .md (the report).

The number check proves numbers, not labels, so every text is also read by a person. Ask again for the ones that
put a number on the wrong label, keeping the rest: `--only SKU:lang,SKU:lang`. Stop serving one: `--drop SKU:lang`
(the app then asks the model live for it). Both keep every earlier answer in the evidence.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from marginarena import api
from marginarena.api import create_app, result_digest

EVIDENCE = Path(__file__).resolve().parents[2] / "evidence"
MODEL = "Gemma-4-31B-IT"
LANGUAGES = ("en", "th")


def _pairs(flag: str) -> set[str]:
    """The SKU:lang pairs given after `flag`, e.g. {"SS-50:th"}."""
    return set(sys.argv[sys.argv.index(flag) + 1].split(",")) if flag in sys.argv else set()


async def main() -> None:
    only, drop = _pairs("--only"), _pairs("--drop")
    previous = EVIDENCE / "explainer-replay-12sku.json"
    earlier = json.loads(previous.read_text()) if (only or drop) and previous.exists() else None
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://record", timeout=900
    ) as client:
        health = (await client.get("/api/health")).json()
        print(f"route {health['route']}, model {health['model']}", flush=True)
        if "--expect-route" in sys.argv and health["route"] != sys.argv[sys.argv.index("--expect-route") + 1]:
            raise SystemExit("The healthy route is not the one expected; nothing was asked.")
        if health["model"] != MODEL:
            raise SystemExit(f"The route starts on {health['model']}, not {MODEL}; nothing was asked.")
        async with client.stream("POST", "/api/arena", json={"recorded": True}) as response:
            events = [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]
        done = events[-1]
        if done["type"] != "run_done":
            raise SystemExit(f"The replay did not finish: {done}")
        started = next(e for e in events if e["type"] == "run_started")

        answers = []
        for result in done["results"]:
            for language in LANGUAGES:
                if (only or drop) and f"{result['sku']}:{language}" not in only:
                    continue
                t0 = time.monotonic()
                payload = {"result": result, "language": language, "live": True}
                response = await client.post("/api/explain", json=payload)
                response.raise_for_status()
                answer = response.json()
                answers.append(
                    {
                        "digest": result_digest(result),
                        "sku": result["sku"],
                        "verdict": "skip" if result["skip"] else result["verdict"],
                        "language": language,
                        "text": answer["text"],
                        "source": answer["source"],
                        "rejected": answer["rejected"],
                        "route": answer["route"],
                        "model": answer["model"],
                        "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
                        "seconds": round(time.monotonic() - t0, 1),
                    }
                )
                print(
                    f"{result['sku']} {language}: {answer['source']} by {answer['model']}, "
                    f"{len(answer['rejected'])} rejected, {answers[-1]['seconds']} s",
                    flush=True,
                )

    fields = ("digest", "sku", "language", "text", "source", "rejected", "route", "model", "written_at")
    kept = [{k: a[k] for k in fields} for a in answers if a["source"] == "model" and a["model"] == MODEL]
    dropped = list(earlier.get("dropped", [])) if earlier else []
    if earlier:  # keep every other recorded explanation, and every earlier answer in the evidence
        asked_again = {(a["sku"], a["language"]) for a in answers} | {tuple(p.split(":")) for p in drop}
        kept = [e for e in earlier["explanations"] if (e["sku"], e["language"]) not in asked_again] + kept
        dropped += sorted(drop)
        answers = earlier["asked"] + answers
    shipped = {
        "run": api.RECORDED_RUN.name,
        "run_recorded_at": started["recorded_at"],
        "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "explanations": kept,
    }
    api.RECORDED_EXPLANATIONS.write_text(json.dumps(shipped, ensure_ascii=False, indent=1) + "\n")
    record = shipped | {"route": health["route"], "asked": answers, "dropped": dropped}
    (EVIDENCE / "explainer-replay-12sku.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n")
    (EVIDENCE / "explainer-replay-12sku.md").write_text(report(record))
    print(
        f"kept {len(kept)} of {len(answers)}; wrote {api.RECORDED_EXPLANATIONS.name} and evidence/explainer-replay-12sku.md"
    )


def report(r: dict) -> str:
    rows = r["asked"]
    first = sum(1 for a in rows if a["source"] == "model" and not a["rejected"])
    rewritten = sum(1 for a in rows if a["source"] == "model" and a["rejected"])
    template = sum(1 for a in rows if a["source"] == "template")
    other_model = sum(1 for a in rows if a["source"] == "model" and a["model"] != MODEL)
    lines = [
        "# Evidence: Gemma's explanations of the recorded run's 12 Verdicts",
        "",
        "Reproduce: `uv run --project backend --env-file .env python backend/scripts/record_explanations.py "
        "--expect-route token-factory` (sample data only).",
        "",
        f"- **Written:** {r['written_at']} on {r['route']}, for the Verdicts of `{r['run']}` (recorded "
        f"{r['run_recorded_at']}).",
        f"- **Asked:** {len(rows)} explanations (12 Verdicts × English and Thai), through `/api/explain` with `live`.",
        f"- **Passed the number check on the first draft:** {first}; **after one rewrite:** {rewritten}; "
        f"**numbers-only template:** {template}; **written by a model other than {MODEL}:** {other_model}.",
        f"- **Served by the app:** the {len(r['explanations'])} that {MODEL} wrote and that passed the check, each "
        "only for the exact Verdict it explains (`api.result_digest`), labelled as recorded. Any other request asks "
        "the model live.",
        "- **The check proves numbers, not labels:** a right number can still sit next to the wrong words, so a "
        "person reads every text. Asked again after that review: "
        f"{len(rows) - len({(a['sku'], a['language']) for a in rows})}; no longer served: "
        f"{', '.join(r.get('dropped', [])) or 'none'}. Every answer is below, in the order asked.",
        "",
        "| SKU | Verdict | Language | Source | Rejected drafts | Model | Seconds |",
        "|---|---|---|---|---|---|---|",
    ]
    for a in rows:
        lines.append(
            f"| {a['sku']} | {a['verdict']} | {a['language']} | {a['source']} | {len(a['rejected'])} | "
            f"{a['model']} | {a['seconds']} |"
        )
    lines += ["", "## The texts", ""]
    for a in rows:
        lines += [f"**{a['sku']} ({a['verdict']}), {a['language']}, {a['source']}:** {a['text']}", ""]
        for d in a["rejected"]:
            if d["text"]:
                lines += [f"- Rejected draft (cited {', '.join(d['unsupported'])}): {d['text']}", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    asyncio.run(main())
