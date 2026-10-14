"""MarginArena's Evolus kit: look at, then set up, the Evolus event workspace from code.

Run from the repo root with the keys from .env:
  uv run --project backend --env-file .env python infra/evolus/evolus_kit.py plan

  plan    read-only: what the workspace holds now, the workflow step catalog and the keys' scopes.
          Prints a summary and saves the raw answers to infra/evolus/.plan/latest.json (gitignored).

Creating resources (the knowledge library from infra/evolus/library/, the extractor, the Campaign Desk agent and the
workflow) comes next, written against what `plan` returns. Ask the user before running anything that writes.
API notes: docs/api-guide/evolus-api.md.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

BASE_URL = "https://api.evolus.ai/api/v1"
KEYS = ("EVOLUS_API_KEY", "EVOLUS_APPLICATION_ID", "EVOLUS_USER_API_KEY")
SECRETS = ("EVOLUS_API_KEY", "EVOLUS_USER_API_KEY")
PLAN_DIR = Path(__file__).resolve().parent / ".plan"
# (label, path, which key). Web services, extractors, memories and skills need the personal User API Key.
LOOKS = (
    ("agents", "/agents", "app"),
    ("knowledge libraries", "/memories", "user"),
    ("workflows", "/workflows", "app"),
    ("workflow step catalog", "/workflows/step-catalog", "app"),
    ("web services", "/webservices", "user"),
    ("user key scopes", "/user/api-keys/scopes", "user"),
    ("own model connections", "/own-models/connections", "user"),
    ("AI tools", "/ai-tools", "app"),
)
# Workflow steps and catalog topics whose docs `apply` is written against; plan reads every part.
DOCS = (
    *("AgentCall", "Webhook", "Email", "CreateFile", "LlmCall", "Switch"),
    *("DataExtractor", "Output", "AiTool", "Script"),
    *("fields", "input", "links", "placeholders", "parameters", "default-model"),
)


def plan(env: dict[str, str], transport: httpx.BaseTransport | None = None) -> dict:
    """GET each resource list once and report what is there. Nothing in the workspace changes."""
    headers = {
        "app": {
            "X-ApiKey": env["EVOLUS_API_KEY"],
            "X-Application-Id": env["EVOLUS_APPLICATION_ID"],
        },
        "user": {
            "X-User-ApiKey": env["EVOLUS_USER_API_KEY"],
            "X-Application-Id": env["EVOLUS_APPLICATION_ID"],
        },
    }
    answers = {}
    with httpx.Client(base_url=BASE_URL, transport=transport, timeout=30) as client:
        for label, path, key in LOOKS:
            response = client.get(path, headers=headers[key])
            body = _json(response)
            answers[label] = {
                "path": path,
                "status": response.status_code,
                "body": body,
            }
            print(
                _redact(
                    f"{label} (GET {path}): HTTP {response.status_code}, {_summary(body)}",
                    env,
                )
            )
        catalog = answers["workflow step catalog"]["body"]
        entries = (
            catalog.get("steps", []) + catalog.get("topics", [])
            if isinstance(catalog, dict)
            else []
        )
        docs = {}
        for entry in (e for e in entries if e.get("key") in DOCS):
            for part in range(1, entry.get("parts", 1) + 1):
                response = client.get(
                    f"/workflows/step-catalog/{entry['key']}",
                    params={"part": part},
                    headers=headers["app"],
                )
                docs[f"{entry['key']}#{part}"] = _json(response, limit=None)
        answers["step docs"] = docs
        print(f"step docs (GET /workflows/step-catalog/{{key}}): {len(docs)} parts")
    return answers


def _json(response: httpx.Response, limit: int | None = 2000):
    try:
        return response.json()
    except ValueError:
        return response.text[:limit]


def _summary(body) -> str:
    items = body.get("items") or body.get("data") if isinstance(body, dict) else body
    if isinstance(items, list):
        names = [
            str(
                i.get("name")
                or i.get("title")
                or i.get("key")
                or i.get("slug")
                or i.get("id")
            )
            for i in items
            if isinstance(i, dict)
        ]
        return f"{len(items)} entries" + (f": {', '.join(names[:12])}" if names else "")
    if isinstance(body, dict):
        return f"fields {', '.join(list(body)[:12])}"
    return f"{str(body)[:200]!r}"


def _redact(text: str, env: dict[str, str]) -> str:
    for name in SECRETS:
        if env.get(name):
            text = text.replace(env[name], f"<{name}>")
    return text


def main(argv: list[str]) -> None:
    if argv[1:] != ["plan"]:
        raise SystemExit(__doc__)
    missing = [k for k in KEYS if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")
    env = {k: os.environ[k] for k in KEYS}
    answers = plan(env)
    PLAN_DIR.mkdir(exist_ok=True)
    (PLAN_DIR / "latest.json").write_text(
        _redact(json.dumps(answers, ensure_ascii=False, indent=1), env) + "\n"
    )
    print(f"Saved the raw answers to {PLAN_DIR / 'latest.json'}")


if __name__ == "__main__":
    main(sys.argv)
