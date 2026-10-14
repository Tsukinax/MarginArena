"""Seam 2: the backend HTTP API, with a scripted model server faked at the network boundary.

The real LLM client, Arena orchestrator and engine run unchanged; only the OpenAI-compatible
model server is replaced by an httpx MockTransport.
"""

import json
from decimal import Decimal

import httpx

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
