"""Seam 2: the backend HTTP API, with a scripted model server faked at the network boundary.

The real LLM client, Arena orchestrator and engine run unchanged; only the OpenAI-compatible
model server is replaced by an httpx MockTransport.
"""

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
