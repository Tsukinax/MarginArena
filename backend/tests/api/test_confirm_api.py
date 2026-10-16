"""Seam 2 for Confirm: POST /api/confirm runs the Evolus Verdict workflow, with Evolus faked at the network edge.

The Verdicts come from the recorded Arena replay, so they carry the server's signatures without calling a model.
"""

import json
import re

import httpx
import pytest

from marginarena import api
from marginarena.api import create_app
from marginarena.llm import LLMSettings

SETTINGS = LLMSettings(route="token-factory", base_url="http://model.test/v1", api_key="test", model="Gemma-4-31B-IT")
WORKFLOW_RESULT = {"upload": [{"sku": "NT-200"}], "approval_request": "Subject: VC-30 needs your call"}
# What Evolus reported for the live run ffdb5077 on 17 Oct (evidence/evolus-workspace-usage.md): each step's time and
# the credits the run used.
EXECUTION = {
    "status": "Completed",
    "output": json.dumps(WORKFLOW_RESULT),
    "stepStates": {
        "1": {"status": "done", "durationMs": 3},
        "2": {"status": "done", "durationMs": 18},
        "3": {"status": "done", "durationMs": 2978},
        "4": {"status": "done", "durationMs": 1},
        "5": {"status": "done", "durationMs": 0},
    },
    "consumption": {"credits": 0.0, "pendingEntries": 0},
}


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
            return httpx.Response(200, json=EXECUTION)
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
    assert done.json()["status"] == "Completed" and done.json()["result"] == WORKFLOW_RESULT


async def test_a_finished_run_shows_each_steps_time_and_the_credits_it_used():
    # Evolus's own trail of the run, so the Seller (and a judge) sees what each step did and that it cost no credits.
    _, done = await confirm(FakeEvolus())

    assert done.json()["step_ms"] == {"1": 3, "2": 18, "3": 2978, "4": 1, "5": 0}
    assert done.json()["credits"] == 0.0


async def test_confirm_refuses_verdicts_changed_after_the_arena():
    evolus = FakeEvolus()

    def deeper_cut(results):
        return [{**r, "chosen_plan": "฿300.00 off"} if r["sku"] == "SS-50" else r for r in results]

    started, _ = await confirm(evolus, deeper_cut)

    assert started.status_code == 403
    assert evolus.requests == []


async def test_the_recorded_workflow_run_is_there_when_evolus_is_not(monkeypatch):
    # The event workspace expires (31 Oct or 15 Nov) before judging may end. The run of the recorded Arena's 12
    # Verdicts on 15 Oct (evidence/evolus-verdict-workflow.md) stays viewable without calling Evolus.
    monkeypatch.delenv("EVOLUS_API_KEY")
    evolus = FakeEvolus()
    app = create_app(llm_settings=SETTINGS, evolus_transport=httpx.MockTransport(evolus.handle), sleep=no_sleep)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/confirm/recorded")).json()

    assert evolus.requests == []
    assert body["recorded"] is True
    assert body["execution_id"] == "4d903564-7cc8-f111-bf5b-000d3aae6dc8"
    assert (body["seconds"], body["credits"]) == (10.55, 0.0)
    assert len(body["result"]["upload"]) == 9
    assert [e["sku"] for e in body["result"]["escalations"]] == ["VC-30"]
    assert sorted(body["result"]["skipped"]) == ["RN-30", "SM-10"]


async def test_one_address_can_start_the_workflow_only_a_few_times_an_hour():
    # Each run leaves an execution in the event workspace and has the agent call the model.
    evolus = FakeEvolus()
    app = create_app(llm_settings=SETTINGS, evolus_transport=httpx.MockTransport(evolus.handle), sleep=no_sleep)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/api/arena", json={"recorded": True}) as response:
            events = [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]
        results = events[-1]["results"]
        codes = [
            (await client.post("/api/confirm", json={"results": results})).status_code
            for _ in range(api.CONFIRMS_PER_HOUR + 1)
        ]

    assert codes == [200] * api.CONFIRMS_PER_HOUR + [429]
    assert len(evolus.requests) == api.CONFIRMS_PER_HOUR


async def test_the_recorded_workflow_run_is_the_one_on_the_recorded_arenas_verdicts():
    # The Confirm step shows this run "on these same Verdicts" only after the recorded replay, so it must match them.
    evolus = FakeEvolus()
    app = create_app(llm_settings=SETTINGS, evolus_transport=httpx.MockTransport(evolus.handle), sleep=no_sleep)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/api/arena", json={"recorded": True}) as response:
            events = [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]
        recorded = (await client.get("/api/confirm/recorded")).json()["result"]

    results = events[-1]["results"]
    joining = [r for r in results if r["verdict"] != "escalate" and not r["skip"]]
    assert [(u["sku"], u["promo_plan"], u["campaign_price"], u["voucher"]) for u in recorded["upload"]] == [
        (r["sku"], r["chosen_plan"], r["waterfall"]["selling_price"], r["waterfall"]["voucher"]) for r in joining
    ]
    assert [(e["sku"], e["worst_case_as_invited"], e["worst_case_not_joining"]) for e in recorded["escalations"]] == [
        (r["sku"], r["invited_worst_total"], r["dont_join_total"]) for r in results if r["verdict"] == "escalate"
    ]
    assert recorded["skipped"] == [r["sku"] for r in results if r["skip"]]


async def test_a_product_confirmed_twice_is_refused():
    evolus = FakeEvolus()

    twice, _ = await confirm(evolus, lambda results: results[:1] * 2)

    assert twice.status_code == 422
    assert evolus.requests == []


async def test_a_finished_evolus_run_is_reported_without_asking_evolus_again():
    evolus = FakeEvolus()

    async def poll_twice() -> list[httpx.Response]:
        app = create_app(llm_settings=SETTINGS, evolus_transport=httpx.MockTransport(evolus.handle), sleep=no_sleep)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return [await client.get("/api/confirm/ex-1") for _ in range(2)]

    first, second = await poll_twice()

    assert first.json() == second.json()
    assert first.json()["result"] == WORKFLOW_RESULT
    assert len(evolus.requests) == 1


async def test_confirming_nothing_is_refused_without_starting_a_workflow():
    evolus = FakeEvolus()

    started, _ = await confirm(evolus, lambda results: [])

    assert started.status_code == 422
    assert evolus.requests == []
