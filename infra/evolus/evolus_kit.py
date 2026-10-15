"""MarginArena's Evolus kit: look at, then set up, the Evolus event workspace from code.

Run from the repo root with the keys from .env:
  uv run --project backend --env-file .env python infra/evolus/evolus_kit.py plan

  uv run --project backend --env-file .env python infra/evolus/evolus_kit.py apply [--model own/<alias>
                                                                              [--fallback own/<alias>]]

  plan    read-only: what the workspace holds now, the workflow step catalog and the keys' scopes.
          Prints a summary and saves the raw answers to infra/evolus/.plan/latest.json (gitignored).
  apply   writes: creates what MarginArena needs, finding each resource by name first, so a rerun creates nothing
          new: the knowledge library with every document in infra/evolus/library/, and with --model (one of the
          workspace's own models from "Your models") the Campaign Desk agent and the Verdict workflow; --fallback
          names the model the agent falls back to. Saves the IDs to .env. Ask the user before every run.

The Campaign Invitation extractor comes next. API notes: docs/api-guide/evolus-api.md.
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
AGENT = "MarginArena Campaign Desk"
AGENT_PROMPT = (
    "You are the Campaign Desk of Glow Lab BKK, a Thai skincare Seller on Shopee Thailand. MarginArena's pricing "
    "engine decides every Verdict on a Campaign Invitation and computes every number: never compute prices, fees or "
    "profit yourself, and quote only numbers you are given. Use the knowledge library (Shopee Thailand fees and "
    "Campaign rules, the HydraLab reseller agreement) to say where a fee or a rule comes from. Answer in the "
    "language you are asked in, briefly."
)
WORKFLOW = "MarginArena Verdict"
# Runs after the Seller confirms. The input is the confirmed Verdicts as JSON; the scripts only sort and pass
# through the engine's figures, they compute none.
SPLIT_SCRIPT = """
const v = (data && data.verdicts) || [];
const upload = v.filter(r => !r.skip && r.verdict !== 'escalate').map(r => ({
  sku: r.sku, product: r.name, promo_plan: r.plan, campaign_price: r.selling_price, voucher: r.voucher,
  verdict: r.verdict
}));
const escalations = v.filter(r => r.verdict === 'escalate').map(r => ({
  sku: r.sku, product: r.name, invited_plan: r.invited_plan, failed_checks: r.failed_checks,
  worst_case_as_invited: r.invited_worst_total, worst_case_not_joining: r.dont_join_total
}));
const skipped = v.filter(r => r.skip).map(r => r.sku);
return {
  shop: data.shop, campaign: data.campaign, upload, escalations, skipped,
  counts: { joining: upload.length, escalations: escalations.length, skipped: skipped.length }
};
"""
APPROVAL_PROMPT = (
    "The JSON below is what MarginArena's engine decided for a Campaign Invitation. If its escalations list is "
    "empty, reply exactly: No approval needed. Otherwise draft a short approval request email to the shop owner: a "
    "subject line, then 3 to 6 sentences asking the owner to decide each escalated product and saying why it was "
    "escalated (its failed checks). Quote only numbers that appear in the JSON. This is a draft; nothing is sent."
)
ASSEMBLE_SCRIPT = """
const split = sources[0].data || {};
const draft = ((sources[1] && sources[1].text) || '').trim();
return {
  shop: split.shop, campaign: split.campaign, upload: split.upload || [], escalations: split.escalations || [],
  skipped: split.skipped || [], counts: split.counts || {},
  approval_request: (split.escalations || []).length ? draft : null
};
"""
# The bulk-upload columns are MarginArena's own: Seller Centre's template is not public.
UPLOAD_FILE = {
    "format": "csv",
    "fileNamePattern": "marginarena-campaign-upload_{{timestamp}}.{{format}}",
    "csv": {
        "delimiter": ",",
        "quoting": "minimal",
        "rowsFrom": "upload",
        "columns": [
            {"name": "SKU", "from": "sku"},
            {"name": "Product", "from": "product"},
            {"name": "Campaign price (THB)", "from": "campaign_price"},
            {"name": "Shop voucher (THB)", "from": "voucher"},
            {"name": "Promo Plan", "from": "promo_plan"},
            {"name": "Verdict", "from": "verdict"},
        ],
    },
}
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
    model: str | None = None,
    fallback: str | None = None,
) -> dict[str, str]:
    """Create what MarginArena needs, once: each resource is found by name before anything is created.

    `model` is the key of one of the workspace's own models ("own/<alias>"); without it only the library is made.
    `fallback` is the model the agent turns to when `model` fails.
    """
    headers = _headers(env)
    with httpx.Client(base_url=BASE_URL, transport=transport, timeout=60) as client:
        ids = {"library": _library(client, headers["user"])}
        if model:
            ids["agent"] = _agent(client, headers, model, fallback, ids["library"])
            ids["workflow"] = _workflow(client, headers["app"], ids["agent"])
    for name, value in ids.items():
        _set_env(env_file, f"EVOLUS_{name.upper()}_ID", value)
    return ids


def _agent(
    client: httpx.Client, headers: dict, model: str, fallback: str | None, library: str
) -> str:
    """The Campaign Desk agent on our own model, with the knowledge library attached."""
    found = [
        a
        for a in _ok(client.get("/agents", headers=headers["app"])).json()
        if a.get("name") == AGENT
    ]
    if found:
        agent = found[0].get("agentId") or found[0]["id"]
        print(f"agent {AGENT!r}: found")
    else:
        body = {
            "name": AGENT,
            "prompt": AGENT_PROMPT,
            "language": "en",
            "modelKey": model,
            "isChatVisible": True,
        }
        if fallback:
            body["fallbackModelKeys"] = [fallback]
        agent = _ok(client.post("/agents", json=body, headers=headers["app"])).json()[
            "agentId"
        ]
        print(f"agent {AGENT!r}: created on {model}")
    attached = _ok(
        client.get(f"/agents/{agent}/memories", headers=headers["user"])
    ).json()
    if library not in {m.get("id") for m in attached}:
        _ok(
            client.post(
                f"/agents/{agent}/memories",
                json={"memoryId": library},
                headers=headers["user"],
            )
        )
        print("  knowledge library: attached")
    return agent


def _workflow(client: httpx.Client, headers: dict[str, str], agent: str) -> str:
    """The Verdict workflow, turned on at creation (a workflow that is off answers 409), with every step."""
    found = [
        w
        for w in _ok(client.get("/workflows", headers=headers)).json()
        if w.get("name") == WORKFLOW
    ]
    if found:
        flow = found[0]["id"]
        print(f"workflow {WORKFLOW!r}: found")
    else:
        body = {
            "name": WORKFLOW,
            "description": "Carries out the Verdicts a Seller confirmed in MarginArena.",
            "isActive": True,
        }
        flow = _ok(client.post("/workflows", json=body, headers=headers)).json()["id"]
        print(f"workflow {WORKFLOW!r}: created")
    steps = [
        {
            "name": "Split the Verdicts",
            "stepType": "Script",
            "stepConfigJson": json.dumps({"script": SPLIT_SCRIPT}),
        },
        {
            "name": "Bulk-upload file",
            "stepType": "CreateFile",
            "links": ["Split the Verdicts"],
            "stepConfigJson": json.dumps(UPLOAD_FILE),
        },
        {
            "name": "Approval request",
            "stepType": "AgentCall",
            "links": ["Split the Verdicts"],
            "agentId": agent,
            "prompt": APPROVAL_PROMPT,
        },
        {
            "name": "Assemble the result",
            "stepType": "Script",
            "links": ["Split the Verdicts", "Approval request"],
            "stepConfigJson": json.dumps({"script": ASSEMBLE_SCRIPT}),
        },
        {"name": "Result", "stepType": "Output", "links": ["Assemble the result"]},
    ]
    for step in steps:
        existing = {
            s["name"]: s["id"]
            for s in _ok(client.get(f"/workflows/{flow}", headers=headers)).json()[
                "steps"
            ]
        }
        if step["name"] in existing:
            continue
        body = {k: v for k, v in step.items() if k != "links"}
        body["inputStepIds"] = [existing[name] for name in step.get("links", [])]
        _ok(client.post(f"/workflows/{flow}/steps", json=body, headers=headers))
        print(f"  step {step['name']!r}: added")
    return flow


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
    command = argv[1:]
    options = (
        dict(zip(command[1::2], command[2::2], strict=False))
        if command[:1] == ["apply"]
        else {}
    )
    model, fallback = options.get("--model"), options.get("--fallback")
    if command not in (["plan"], ["apply"]) and not (
        model and set(options) <= {"--model", "--fallback"}
    ):
        raise SystemExit(__doc__)
    missing = [k for k in KEYS if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")
    env = {k: os.environ[k] for k in KEYS}
    if argv[1] == "apply":
        ids = apply(env, model=model, fallback=fallback)
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
