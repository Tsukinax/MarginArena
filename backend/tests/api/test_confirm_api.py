"""Seam 2 for Confirm: POST /api/confirm runs the Evolus Verdict workflow, with Evolus faked at the network edge.

The Verdicts come from the recorded Arena replay, so they carry the server's signatures without calling a model.
"""

import json
import re

import httpx
import pytest

from marginarena.api import create_app
from marginarena.llm import LLMSettings

SETTINGS = LLMSettings(route="token-factory", base_url="http://model.test/v1", api_key="test", model="Gemma-4-31B-IT")
WORKFLOW_RESULT = {"upload": [{"sku": "NT-200"}], "approval_request": "Subject: VC-30 needs your call"}


@pytest.fixture(autouse=True)
def evolus_env(monkeypatch):
    monkeypatch.setenv("EVOLUS_API_KEY", "app-key")
    monkeypatch.setenv("EVOLUS_APPLICATION_ID", "app-1")
    monkeypatch.setenv("EVOLUS_WORKFLOW_ID", "wf-1")


class FakeEvolus:
    """Execute answers 202 with an executionId; the execution answers its status and the Output step's text."""

    def __init__(self):
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "POST" and request.url.path == "/api/v1/workflows/wf-1/execute":
            return httpx.Response(202, json={"executionId": "ex-1"})
        if request.method == "GET" and request.url.path == "/api/v1/workflows/wf-1/executions/ex-1":
            return httpx.Response(200, json={"status": "Completed", "output": json.dumps(WORKFLOW_RESULT)})
        return httpx.Response(404, json={"title": "Not Found"})

    def sent_verdicts(self) -> list[dict]:
        field = re.search(rb'name="input"\r\n\r\n(.*?)\r\n--', self.requests[0].content, re.S)[1]
        return json.loads(field)["verdicts"]


async def no_sleep(_seconds: float) -> None:
    return None


async def confirm(evolus: FakeEvolus, change=lambda results: results) -> tuple[httpx.Response, httpx.Response | None]:
    app = create_app(llm_settings=SETTINGS, evolus_transport=httpx.MockTransport(evolus.handle), sleep=no_sleep)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/api/arena", json={"recorded": True}) as response:
            events = [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]
        started = await client.post("/api/confirm", json={"results": change(events[-1]["results"])})
        if started.status_code != 200:
            return started, None
        return started, await client.get(f"/api/confirm/{started.json()['execution_id']}")


async def test_confirm_runs_the_evolus_verdict_workflow_on_the_confirmed_verdicts():
    evolus = FakeEvolus()

    started, done = await confirm(evolus)

    verdicts = {v["sku"]: v for v in evolus.sent_verdicts()}
    assert started.json()["execution_id"] == "ex-1"
    assert evolus.requests[0].headers["X-ApiKey"] == "app-key"
    assert len(verdicts) == 12
    assert verdicts["SS-50"]["verdict"] == "revise" and verdicts["SS-50"]["plan"] == "฿157.50 off"
    assert verdicts["VC-30"]["failed_checks"] == ["below the Margin Floor"]
    assert done.json() == {"status": "Completed", "result": WORKFLOW_RESULT}


async def test_confirm_refuses_verdicts_changed_after_the_arena():
    evolus = FakeEvolus()

    def deeper_cut(results):
        return [{**r, "chosen_plan": "฿300.00 off"} if r["sku"] == "SS-50" else r for r in results]

    started, _ = await confirm(evolus, deeper_cut)

    assert started.status_code == 403
    assert evolus.requests == []


async def test_confirming_nothing_is_refused_without_starting_a_workflow():
    evolus = FakeEvolus()

    started, _ = await confirm(evolus, lambda results: [])

    assert started.status_code == 422
    assert evolus.requests == []
