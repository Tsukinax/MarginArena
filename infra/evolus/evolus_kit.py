"""MarginArena's Evolus kit: look at, then set up, the Evolus event workspace from code.

Run from the repo root with the keys from .env:
  uv run --project backend --env-file .env python infra/evolus/evolus_kit.py plan

  uv run --project backend --env-file .env python infra/evolus/evolus_kit.py apply

  plan    read-only: what the workspace holds now, the workflow step catalog and the keys' scopes.
          Prints a summary and saves the raw answers to infra/evolus/.plan/latest.json (gitignored).
  apply   writes: creates what MarginArena needs, finding each resource by name first, so a rerun creates nothing
          new. So far the knowledge library with every document in infra/evolus/library/. Saves the IDs to .env.
          Ask the user before every run.

The extractor, the Campaign Desk agent and the Verdict workflow come next. API notes: docs/api-guide/evolus-api.md.
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
HERE = Path(__file__).resolve().parent
PLAN_DIR = HERE / ".plan"
LIBRARY_DIR = HERE / "library"
ENV_FILE = HERE.parents[1] / ".env"
LIBRARY = "MarginArena Campaign Desk library"
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
    headers = _headers(env)
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


def apply(
    env: dict[str, str],
    transport: httpx.BaseTransport | None = None,
    env_file: Path = ENV_FILE,
) -> dict[str, str]:
    """Create what MarginArena needs, once: each resource is found by name before anything is created."""
    headers = _headers(env)
    with httpx.Client(base_url=BASE_URL, transport=transport, timeout=60) as client:
        ids = {"library": _library(client, headers["user"])}
    _set_env(env_file, "EVOLUS_LIBRARY_ID", ids["library"])
    return ids


def _library(client: httpx.Client, headers: dict[str, str]) -> str:
    """The knowledge library with every document in library/, uploaded in English (Evolus defaults to Italian)."""
    libraries = _ok(client.get("/memories", headers=headers)).json()
    found = [m["id"] for m in libraries if m.get("name") == LIBRARY]
    if found:
        library = found[0]
        print(f"knowledge library {LIBRARY!r}: found")
    else:
        # type 0 = Rag: semantic search over the documents
        body = {"name": LIBRARY, "type": 0}
        response = client.post("/memories/simple", json=body, headers=headers)
        library = _ok(response).json()["id"]
        print(f"knowledge library {LIBRARY!r}: created")
    documents = _ok(client.get(f"/memories/{library}/documents", headers=headers))
    titles = {d.get("title") for d in documents.json()}
    for path in sorted(LIBRARY_DIR.glob("*.md")):
        if path.name in titles:  # Evolus keeps the uploaded file name as the title
            print(f"  {path.name}: already uploaded")
            continue
        _ok(
            client.post(
                f"/memories/{library}/documents",
                params={"language": "en"},
                files={"file": (path.name, path.read_bytes(), "text/markdown")},
                headers=headers,
            )
        )
        print(f"  {path.name}: uploaded (language=en)")
    return library


def _headers(env: dict[str, str]) -> dict[str, dict[str, str]]:
    return {
        "app": {
            "X-ApiKey": env["EVOLUS_API_KEY"],
            "X-Application-Id": env["EVOLUS_APPLICATION_ID"],
        },
        "user": {
            "X-User-ApiKey": env["EVOLUS_USER_API_KEY"],
            "X-Application-Id": env["EVOLUS_APPLICATION_ID"],
        },
    }


def _ok(response: httpx.Response) -> httpx.Response:
    if not response.is_success:
        request = response.request
        raise SystemExit(
            f"{request.method} {request.url.path}: HTTP {response.status_code} "
            f"{response.text[:300]}"
        )
    return response


def _set_env(path: Path, key: str, value: str) -> None:
    """Write key=value into the .env file, replacing an earlier value and keeping every other line."""
    lines = path.read_text().splitlines() if path.exists() else []
    kept = [line for line in lines if not line.startswith(f"{key}=")]
    path.write_text("\n".join([*kept, f"{key}={value}"]) + "\n")


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
    if argv[1:] not in (["plan"], ["apply"]):
        raise SystemExit(__doc__)
    missing = [k for k in KEYS if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")
    env = {k: os.environ[k] for k in KEYS}
    if argv[1] == "apply":
        ids = apply(env)
        print(
            f"Saved to {ENV_FILE.name}: "
            + ", ".join(f"{k} {v}" for k, v in ids.items())
        )
        return
    answers = plan(env)
    PLAN_DIR.mkdir(exist_ok=True)
    (PLAN_DIR / "latest.json").write_text(
        _redact(json.dumps(answers, ensure_ascii=False, indent=1), env) + "\n"
    )
    print(f"Saved the raw answers to {PLAN_DIR / 'latest.json'}")


if __name__ == "__main__":
    main(sys.argv)
