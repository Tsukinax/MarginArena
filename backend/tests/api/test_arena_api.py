"""Seam 2: the backend HTTP API, with a scripted model server faked at the network boundary.

The real LLM client, Arena orchestrator and engine run unchanged; only the OpenAI-compatible
model server is replaced by an httpx MockTransport.
"""

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import httpx

from marginarena import api
from marginarena.api import create_app
from marginarena.llm import LLMSettings

SETTINGS = LLMSettings(route="token-factory", base_url="http://model.test/v1", api_key="test", model="Gemma-4-31B-IT")


class FakeModelServer:
    def __init__(self, moves=None, ideas=None, failures=(), bad_json=False):
        self.moves = moves if moves is not None else [{"headline_cut_pct": 5, "why": "nudge below the shop"}]
        self.ideas = (
            ideas if ideas is not None else [{"use_voucher": True, "gift_sku_id": "LM-15", "why": "pairs well"}]
        )
        self.failures = list(failures)  # HTTP statuses to return first, one per call
        self.bad_json = bad_json
        self.requests: list[dict] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        if self.failures:
            return httpx.Response(
                self.failures.pop(0), headers={"Retry-After": "0"}, json={"error": {"message": "busy"}}
            )
        system = body["messages"][0]["content"]
        if self.bad_json:
            content = "Sure! Here are some ideas: cut the price."
        elif "You are a Strategist" in system:
            content = json.dumps({"ideas": self.ideas})
        else:
            content = json.dumps({"moves": self.moves})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 300, "completion_tokens": 40},
            },
        )


async def no_sleep(_seconds: float) -> None:
    return None


async def run(server: FakeModelServer, **body) -> list[dict]:
    app = create_app(llm_settings=SETTINGS, llm_transport=httpx.MockTransport(server.handle), sleep=no_sleep)
    payload = {"shop": "glow-lab-bkk", "skus": ["NT-200"], "rounds": 1, "rivals": 1, "strategists": 1} | body
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/api/arena", json=payload) as response:
            assert response.status_code == 200
            return [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]


def result(events: list[dict]) -> dict:
    return events[-1]["results"][0]


async def test_sample_arena_streams_ideas_and_rival_moves_then_ends_with_a_verdict():
    events = await run(FakeModelServer())

    types = [e["type"] for e in events]
    assert types[0] == "run_started"
    assert types[-1] == "run_done"
    assert {"idea", "rival_move", "sku_decided"} <= set(types)
    assert result(events)["sku"] == "NT-200"
    assert result(events)["verdict"] in {"approve", "revise", "escalate"}
    assert events[-1]["telemetry"]["calls_ok"] == 2


async def test_a_deeper_rival_move_never_improves_the_worst_case():
    harmless = await run(FakeModelServer(moves=[{"headline_cut_pct": 0, "why": "hold"}]))
    deep = await run(FakeModelServer(moves=[{"headline_cut_pct": 35, "voucher_baht": 20, "why": "all in"}]))

    assert float(result(deep)["invited_worst_total"]) <= float(result(harmless)["invited_worst_total"])


async def test_a_counter_move_the_rivals_find_shows_how_far_it_cuts_the_worst_case():
    # Proof 6: the plan chosen against the three generic moves, re-checked against what the AI Rivals found.
    harmless = await run(FakeModelServer(moves=[{"headline_cut_pct": 0, "why": "hold"}]))
    deep = await run(FakeModelServer(moves=[{"headline_cut_pct": 35, "voucher_baht": 20, "why": "all in"}]))

    assert Decimal(result(harmless)["red_team_cut"]) == 0
    assert Decimal(result(deep)["red_team_cut"]) > 0


async def test_a_rival_move_turns_the_sunscreen_approve_into_a_revise():
    # Q56: SS-50 carries a labelled Seller override (elasticity -2.62, band -3.48 to -1.36). Against the generic
    # hold, match and undercut moves the invited cut holds; a Counter-move Gemma really proposed in a recorded run
    # (15% off, a ฿50 voucher and ฿40 free shipping) makes a deeper offer the better plan.
    undercut = {"headline_cut_pct": 15, "voucher_baht": 50, "free_shipping_baht": 40, "why": "undercut and stack"}

    events = await run(FakeModelServer(moves=[undercut]), skus=["SS-50"])

    first_leader = next(e for e in events if e["type"] == "round_started")["leader"]
    decided = result(events)
    assert first_leader == decided["generic_plan"] == decided["invited_plan"] == "฿90.00 off"
    assert next(e for e in events if e["type"] == "leader")["changed"] is True
    assert (decided["verdict"], decided["skip"]) == ("revise", False)
    assert Decimal(decided["chosen_worst_total"]) > Decimal(decided["invited_worst_total"])
    assert Decimal(decided["red_team_gain"]) > 0


async def test_the_recorded_run_replays_every_product_signed_and_labelled_without_the_model():
    # The default demo: a full 12-SKU run recorded on Token Factory, replayed in seconds and labelled as recorded.
    server = FakeModelServer()

    events = await run(server, recorded=True)

    assert events[0]["type"] == "run_started" and events[0]["recorded_at"]
    assert len(events[-1]["results"]) == 12
    assert all(r["signature"] for r in events[-1]["results"])
    assert server.requests == []


def test_the_replayed_run_is_the_recorded_evidence():
    # The app ships its own copy (a deploy may not see evidence/); it must stay the run evidence/ records.
    evidence = Path(__file__).resolve().parents[3] / "evidence" / "runs" / "token-factory-sample-12sku.sse"

    assert Path(str(api.RECORDED_RUN)).is_relative_to(Path(api.__file__).parent)
    assert api.RECORDED_RUN.read_bytes() == evidence.read_bytes()


async def test_model_output_that_is_not_json_is_rejected_and_counted():
    events = await run(FakeModelServer(bad_json=True))

    assert events[-1]["type"] == "run_done"
    assert "rival_move" not in [e["type"] for e in events]
    assert events[-1]["telemetry"]["calls_invalid"] == 2


async def test_out_of_range_rival_move_is_rejected():
    events = await run(FakeModelServer(moves=[{"headline_cut_pct": 90, "why": "give it away"}]))

    assert "rival_move" not in [e["type"] for e in events]
    assert events[-1]["telemetry"]["calls_invalid"] == 1


async def test_when_gemma_has_no_workers_the_run_falls_back_to_qwen_and_says_so():
    # 15 Oct: Token Factory answered every Gemma call with 500 "no_available_workers" while Qwen3.8-27B answered.
    seen: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":  # the catalogue still lists Gemma: it is only out of workers
            return httpx.Response(200, json={"data": [{"id": "Gemma-4-31B-IT"}, {"id": "Qwen3.8-27B"}]})
        body = json.loads(request.content)
        seen.append(body)
        if body["model"] == "Gemma-4-31B-IT":
            return httpx.Response(500, json={"error": {"message": '503 {"code":"no_available_workers"}'}})
        server = FakeModelServer()
        return server.handle(request)

    settings = LLMSettings(
        route="token-factory",
        base_url="http://model.test/v1",
        api_key="t",
        model="Gemma-4-31B-IT",
        fallback_model="Qwen3.8-27B",
    )
    app = create_app(llm_settings=settings, llm_transport=httpx.MockTransport(handle), sleep=no_sleep)
    payload = {"shop": "glow-lab-bkk", "skus": ["NT-200"], "rounds": 1, "rivals": 1, "strategists": 1}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/api/arena", json=payload) as response:
            events = [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]

    telemetry = events[-1]["telemetry"]
    assert (telemetry["calls_ok"], telemetry["model"]) == (2, "Qwen3.8-27B")
    assert [b["model"] for b in seen].count("Gemma-4-31B-IT") == 1  # no retries on a model with no workers
    assert all(b["reasoning_effort"] == "low" for b in seen if b["model"] == "Qwen3.8-27B")


GEMMA_THEN_DEEPSEEK = LLMSettings(
    route="token-factory",
    base_url="http://model.test/v1",
    api_key="t",
    model="Gemma-4-31B-IT",
    fallback_model="DeepSeek-V4-Flash",
)


def catalogue_without_gemma(seen: list[dict], listing_status: int = 200):
    """Token Factory as it answered on 15 Oct, 23:00 ICT: Gemma-4-31B-IT was gone from its catalogue."""
    server = FakeModelServer()

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(listing_status, json={"data": [{"id": "DeepSeek-V4-Flash"}, {"id": "Qwen3.8-27B"}]})
        body = json.loads(request.content)
        seen.append(body)
        if body["model"] == "Gemma-4-31B-IT":
            message = "Requested model Gemma-4-31B-IT not supported"
            return httpx.Response(400, json={"error": {"message": message, "type": "invalid_request_error"}})
        return server.handle(request)

    return handle


async def test_when_the_catalogue_no_longer_lists_gemma_the_run_starts_on_the_fallback_and_says_so():
    seen: list[dict] = []
    app = create_app(
        llm_settings=GEMMA_THEN_DEEPSEEK,
        llm_transport=httpx.MockTransport(catalogue_without_gemma(seen)),
        sleep=no_sleep,
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        health = (await client.get("/api/health")).json()
        async with client.stream("POST", "/api/arena", json=LIVE) as response:
            events = [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]

    assert health == {"route": "token-factory", "model": "DeepSeek-V4-Flash"}
    assert events[0]["model"] == "DeepSeek-V4-Flash"
    assert events[-1]["telemetry"]["calls_ok"] == 2
    assert {b["model"] for b in seen} == {"DeepSeek-V4-Flash"}


async def test_a_model_the_route_no_longer_serves_switches_the_run_to_the_fallback():
    # When the catalogue can't be read, the first "not supported" answer still moves the run to the fallback.
    seen: list[dict] = []
    handle = catalogue_without_gemma(seen, listing_status=503)
    app = create_app(llm_settings=GEMMA_THEN_DEEPSEEK, llm_transport=httpx.MockTransport(handle), sleep=no_sleep)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/api/arena", json=LIVE) as response:
            events = [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]

        health = (await client.get("/api/health")).json()
        async with client.stream("POST", "/api/arena", json=LIVE) as response:
            again = [json.loads(line[6:]) async for line in response.aiter_lines() if line.startswith("data: ")]

    telemetry = events[-1]["telemetry"]
    assert (telemetry["calls_ok"], telemetry["calls_failed"], telemetry["model"]) == (2, 0, "DeepSeek-V4-Flash")
    assert [b["model"] for b in seen].count("Gemma-4-31B-IT") == 1
    # The refusal is remembered for a while, so the sidebar and the next run name the model that will answer.
    assert health["model"] == "DeepSeek-V4-Flash"
    assert again[0]["model"] == "DeepSeek-V4-Flash"


async def test_busy_model_server_is_retried():
    server = FakeModelServer(failures=[429, 503])

    events = await run(server)

    assert events[-1]["telemetry"]["calls_ok"] == 2
    assert events[-1]["telemetry"]["retries"] == 2


async def get(path: str) -> httpx.Response:
    app = create_app(llm_settings=SETTINGS)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path)


async def test_shop_endpoint_describes_the_invitation_and_every_assumption():
    response = await get("/api/shops/glow-lab-bkk")

    shop = response.json()
    assert response.status_code == 200
    assert len(shop["invited"]) == 12
    assert shop["margin_floor"] == "0.10"
    assert shop["profile"]["effective_from"] == "2026-08-04"
    assert {"traffic_lift", "cross_price_sensitivity", "gift_value_ratio"} <= set(shop["assumptions"])
    assert shop["brand_rules"][0]["clause"] == "HydraLab reseller agreement, clause 4.2"


async def test_the_first_screen_states_the_sellers_problem_with_numbers_the_engine_computes():
    # README "The problem": a ฿100 product costing ฿50 at the shop's fees, at full price, 20% off and 30% off.
    shop = (await get("/api/shops/glow-lab-bkk")).json()

    assert [(e["discount_pct"], e["unit_profit"]) for e in shop["fee_example"]] == [
        ("0", "21.11"),
        ("20", "6.67"),
        ("30", "-0.55"),
    ]
    assert {(e["list_price"], e["cost"]) for e in shop["fee_example"]} == {("100", "50")}


async def test_the_first_screen_gets_the_recorded_runs_headline_from_the_recording_itself():
    # Shown before anyone presses play, so every figure must be the recorded run's own: its run_done, its leaders.
    summary = (await get("/api/arena/recorded")).json()

    assert summary["margin_protected"] == "5434.46"
    # The two Skips lead the first screen: they need no Seller override (evidence/sensitivity.md).
    # RN-30 protects 861.03 and SM-10 787.47 in the recorded run_done: 861.03 + 787.47 = 1648.50.
    assert summary["skipped"] == ["RN-30", "SM-10"]
    assert summary["margin_protected_by_skips"] == "1648.50"
    assert summary["verdicts"] == {"approve": 8, "revise": 1, "skip": 2, "escalate": 1}
    assert summary["rival_changed"] == ["SS-50"]
    assert (summary["route"], summary["model"], summary["products"]) == ("token-factory", "Gemma-4-31B-IT", 12)
    assert (summary["calls_ok"], summary["calls_failed"], summary["elapsed_seconds"]) == (60, 0, 248.55)
    assert summary["recorded_at"] == "2026-10-14T19:51:51+00:00"


async def test_decided_sku_explains_its_numbers_with_a_waterfall_scenarios_and_evidence():
    events = await run(FakeModelServer())

    decided = next(e for e in events if e["type"] == "sku_decided")
    waterfall = {k: v for k, v in decided["waterfall"].items() if k not in ("plan", "fees")}
    fees = Decimal(decided["waterfall"]["fees"]["total"])
    # The waterfall must add up: what the Seller is credited, less fees and cost, is the profit shown.
    assert Decimal(waterfall["seller_net"]) - fees - Decimal(waterfall["unit_cost"]) == Decimal(waterfall["profit"])
    assert len(decided["scenario_grid"]) == decided["scenarios"]
    kinds = {link["kind"] for link in decided["evidence"]}
    assert {"invitation", "fees", "elasticity", "rival_snapshot"} <= kinds


async def test_the_sunscreen_elasticity_is_labelled_as_a_seller_override_with_its_source():
    # Q51: a per-SKU value is shown as the Seller's, with its source. Every other product keeps the pooled fit.
    shop = (await get("/api/shops/glow-lab-bkk")).json()
    sunscreen = await run(FakeModelServer(), skus=["SS-50"])
    toner = await run(FakeModelServer(), skus=["NT-200"])

    def elasticity_link(events: list[dict]) -> dict:
        return next(link for link in result(events)["evidence"] if link["kind"] == "elasticity")

    override = shop["elasticity_overrides"]["SS-50"]
    assert list(shop["elasticity_overrides"]) == ["SS-50"]
    assert (override["elasticity"], override["band"]) == ("-2.62", ["-3.48", "-1.36"])
    assert elasticity_link(sunscreen)["text"] == override["text"]
    assert override["text"].startswith("Sample Seller override: elasticity -2.62, band -3.48 to -1.36.")
    assert elasticity_link(sunscreen)["source"].startswith("Bijmolt, Van Heerde and Pieters (2005)")
    assert elasticity_link(toner)["text"].startswith("FreshRetailNet-50K")


async def test_evidence_links_write_percentages_as_plain_numbers():
    events = await run(FakeModelServer(), skus=["VC-30"])

    texts = " ".join(link["text"] for link in result(events)["evidence"])
    assert "at least 20% off" in texts
    assert "valued at 30% of its retail price" in texts


async def test_one_container_serves_the_web_app_and_the_api(tmp_path):
    (tmp_path / "index.html").write_text("<title>MarginArena</title>")
    app = create_app(llm_settings=SETTINGS, web_dist=tmp_path)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        page = await client.get("/")
        health = await client.get("/api/health")

    assert "<title>MarginArena</title>" in page.text
    assert health.json() == {"route": "token-factory", "model": "Gemma-4-31B-IT"}


GPU = LLMSettings(route="mi300x", base_url="http://gpu.test/v1", api_key="k", model="google/gemma-4-31B-it")


async def health_with_gpu_answering(status: int) -> dict:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"data": []})

    app = create_app(routes=(GPU, SETTINGS), llm_transport=httpx.MockTransport(handle))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return (await client.get("/api/health")).json()


async def test_our_mi300x_endpoint_is_used_when_it_answers():
    assert (await health_with_gpu_answering(200))["route"] == "mi300x"


async def test_token_factory_takes_over_when_the_mi300x_endpoint_is_down():
    assert (await health_with_gpu_answering(503))["route"] == "token-factory"


async def test_fallback_demo_shows_every_kind_of_verdict():
    # Q55: on Token Factory the sample run checks products chosen to show Approve, Escalate and Skip, plus SS-50,
    # where an AI Rival can turn an Approve into a Revise (Q56).
    events = await run(FakeModelServer(), skus=None)

    started = events[0]
    by_sku = {r["sku"]: r for r in events[-1]["results"]}
    assert started["skus"] == ["NT-200", "SS-50", "VC-30", "SM-10"]
    assert by_sku["SM-10"]["verdict"] == "revise"
    assert by_sku["SM-10"]["skip"] is True


LIVE = {"shop": "glow-lab-bkk", "skus": ["NT-200"], "rounds": 1, "rivals": 1, "strategists": 1}


async def test_while_a_live_run_holds_token_factory_a_second_is_turned_away_but_the_replay_still_plays():
    # Token Factory allows 20 requests a minute per account, so two live runs at once would only stall each other.
    server = FakeModelServer()
    entered, release = asyncio.Event(), asyncio.Event()

    async def held(request: httpx.Request) -> httpx.Response:
        entered.set()
        await release.wait()
        return server.handle(request)

    app = create_app(llm_settings=SETTINGS, llm_transport=httpx.MockTransport(held), sleep=no_sleep)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        first = asyncio.create_task(client.post("/api/arena", json=LIVE))
        await asyncio.wait_for(entered.wait(), timeout=5)
        try:
            second = await asyncio.wait_for(
                client.post("/api/arena", json=LIVE, headers={"X-Forwarded-For": "203.0.113.9"}), timeout=5
            )
            replay = await asyncio.wait_for(client.post("/api/arena", json={"recorded": True}), timeout=5)
        finally:
            release.set()
        finished = await asyncio.wait_for(first, timeout=5)
        after = await client.post("/api/arena", json=LIVE, headers={"X-Forwarded-For": "203.0.113.9"})

    assert second.status_code == 429
    assert "recorded run" in second.json()["detail"]
    assert replay.status_code == 200 and '"run_done"' in replay.text
    assert finished.status_code == 200 and '"run_done"' in finished.text
    assert after.status_code == 200


async def test_one_address_gets_only_a_few_live_runs_an_hour():
    server = FakeModelServer()
    app = create_app(llm_settings=SETTINGS, llm_transport=httpx.MockTransport(server.handle), sleep=no_sleep)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        codes = [(await client.post("/api/arena", json=LIVE)).status_code for _ in range(api.LIVE_RUNS_PER_HOUR + 1)]
        elsewhere = await client.post("/api/arena", json=LIVE, headers={"X-Forwarded-For": "198.51.100.7"})
        replay = await client.post("/api/arena", json={"recorded": True})

    assert codes == [200] * api.LIVE_RUNS_PER_HOUR + [429]
    assert elsewhere.status_code == 200
    assert replay.status_code == 200


async def test_a_client_that_leaves_ends_its_live_run_and_frees_token_factory():
    # A judge who reloads or presses "Start over" while a live run looks frozen must be able to run live again at once.
    server = FakeModelServer()
    first_call, release = asyncio.Event(), asyncio.Event()

    async def first_run_hangs(request: httpx.Request) -> httpx.Response:
        if not first_call.is_set():
            first_call.set()
            await release.wait()  # never set: only cancelling the run ends this call
        return server.handle(request)

    app = create_app(llm_settings=SETTINGS, llm_transport=httpx.MockTransport(first_run_hangs), sleep=no_sleep)
    sent: list[dict] = []
    started = asyncio.Event()
    body = json.dumps(LIVE).encode()
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"}, "http_version": "1.1", "method": "POST",
        "scheme": "http", "path": "/api/arena", "raw_path": b"/api/arena", "query_string": b"", "root_path": "",
        "headers": [(b"content-type", b"application/json"), (b"host", b"test")], "client": ("192.0.2.1", 1),
        "server": ("test", 80),
    }  # fmt: skip
    messages = [{"type": "http.request", "body": body, "more_body": False}]

    async def receive() -> dict:
        if messages:
            return messages.pop(0)
        await started.wait()
        return {"type": "http.disconnect"}  # the judge leaves once the run has started

    async def send(message: dict) -> None:
        sent.append(message)
        if message["type"] == "http.response.body" and b"run_started" in message.get("body", b""):
            started.set()

    await asyncio.wait_for(app(scope, receive, send), timeout=5)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        again = await asyncio.wait_for(
            client.post("/api/arena", json=LIVE, headers={"X-Forwarded-For": "198.51.100.7"}), timeout=5
        )

    assert again.status_code == 200 and '"run_done"' in again.text


async def test_a_live_run_that_fails_frees_token_factory_for_the_next():
    server = FakeModelServer()
    calls: list[httpx.Request] = []

    def breaks_once(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            raise RuntimeError("the model server broke")
        return server.handle(request)

    app = create_app(llm_settings=SETTINGS, llm_transport=httpx.MockTransport(breaks_once), sleep=no_sleep)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        failed = await client.post("/api/arena", json=LIVE)
        again = await client.post("/api/arena", json=LIVE, headers={"X-Forwarded-For": "198.51.100.7"})

    assert '"type": "error"' in failed.text
    assert again.status_code == 200 and '"run_done"' in again.text
