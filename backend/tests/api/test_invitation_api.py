"""Seam 2 for reading the Campaign Invitation: POST /api/invitation/read has the Evolus extractor read the sample
invitation PDF, with Evolus faked at the network edge. Only the bundled sample is ever sent: Token Factory, behind
the extractor's model, may see sample data only.
"""

import copy
import json

import httpx
import pytest

from marginarena import api
from marginarena.api import create_app
from marginarena.llm import LLMSettings

SETTINGS = LLMSettings(route="token-factory", base_url="http://model.test/v1", api_key="test", model="Gemma-4-31B-IT")
DISCOUNTS = {
    "HB-30": 15, "NT-200": 15, "SS-50": 20, "CN-50": 15, "VC-30": 20, "AC-150": 15,
    "RN-30": 25, "CG-80": 15, "LM-15": 20, "SM-10": 20, "CM-100": 15, "TK-4": 25,
}  # fmt: skip
# What the real extractor returned for the sample PDF on 15 Oct (product names and list prices left out here).
READ = {
    "marketplace": "Shopee Thailand",
    "campaign": "11.11 Big Sale",
    "slot": "Shocking Sale, 11 Nov 00:00 to 23:59",
    "registration_closes": "7 Nov 2026",
    "items": [{"sku": sku, "minimum_discount_pct": pct} for sku, pct in DISCOUNTS.items()],
}


@pytest.fixture(autouse=True)
def evolus_env(monkeypatch):
    for name, value in {
        "EVOLUS_API_KEY": "app-key",
        "EVOLUS_APPLICATION_ID": "app-1",
        "EVOLUS_READER_ID": "reader-1",
        "EVOLUS_INVITATION_STRUCTURE_ID": "structure-1",
    }.items():
        monkeypatch.setenv(name, value)


class FakeExtractor:
    def __init__(self, read: dict):
        self.read = read
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/api/v1/agents/reader-1/json/structure-1/ask-file":
            headers = {"X-AskFile-Execution-Id": "ex-9", "X-AskFile-Audit-Id": "audit-9"}
            return httpx.Response(200, json=self.read, headers=headers)
        return httpx.Response(404, json={"title": "Not Found"})


async def call(extractor: FakeExtractor, method: str, path: str, **kwargs) -> httpx.Response:
    app = create_app(llm_settings=SETTINGS, evolus_transport=httpx.MockTransport(extractor.handle))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


async def test_evolus_reads_the_sample_invitation_and_every_discount_matches_the_one_the_arena_checks():
    extractor = FakeExtractor(READ)

    response = await call(extractor, "POST", "/api/invitation/read")

    body = response.json()
    sent = extractor.requests[0]
    assert sent.content.count(b"%PDF") == 1 and b'filename="glow-lab-bkk-invitation.pdf"' in sent.content
    assert sent.headers["X-ApiKey"] == "app-key"
    assert body["read"]["campaign"] == "11.11 Big Sale"
    assert (body["matches"], len(body["checks"])) == (True, 12)
    assert (body["execution_id"], body["audit_id"]) == ("ex-9", "audit-9")
    assert body["recorded"] is False


async def test_the_recorded_reading_answers_at_once_without_calling_evolus(monkeypatch):
    # A live read waits on Token Factory for up to minutes, and the event workspace expires before judging may end.
    # The reading the live site made on 15 Oct (run 3 in evidence/evolus-invitation-extractor.md) is replayed instead.
    monkeypatch.delenv("EVOLUS_API_KEY")
    extractor = FakeExtractor(READ)

    response = await call(extractor, "POST", "/api/invitation/read", json={"recorded": True})

    body = response.json()
    assert extractor.requests == []
    assert body["recorded"] is True
    assert body["read"]["campaign"] == "11.11 Big Sale"
    assert (body["matches"], len(body["checks"])) == (True, 12)
    assert body["execution_id"] == "e2424803-85c8-f111-bf5b-000d3aae6dc8"
    assert (body["read_at"], body["seconds"]) == ("2026-10-15T10:44:10Z", 146.06)


async def test_one_address_can_ask_for_only_a_few_live_readings_an_hour():
    # Each live read leaves an execution in the event workspace and calls the model behind the extractor.
    extractor = FakeExtractor({"items": []})  # a reading with no products is never kept, so every call reads again
    app = create_app(llm_settings=SETTINGS, evolus_transport=httpx.MockTransport(extractor.handle))

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        codes = [(await client.post("/api/invitation/read")).status_code for _ in range(api.LIVE_READS_PER_HOUR + 1)]
        recorded = await client.post("/api/invitation/read", json={"recorded": True})

    assert codes == [200] * api.LIVE_READS_PER_HOUR + [429]
    assert len(extractor.requests) == api.LIVE_READS_PER_HOUR
    assert recorded.status_code == 200


async def test_a_misread_discount_is_flagged():
    misread = copy.deepcopy(READ)
    next(i for i in misread["items"] if i["sku"] == "SS-50")["minimum_discount_pct"] = 15

    body = (await call(FakeExtractor(misread), "POST", "/api/invitation/read")).json()

    ss50 = next(c for c in body["checks"] if c["sku"] == "SS-50")
    assert body["matches"] is False
    assert (ss50["read_discount_pct"], ss50["expected_discount_pct"], ss50["matches"]) == ("15", "20", False)


async def test_the_sample_invitation_pdf_can_be_opened():
    response = await call(FakeExtractor(READ), "GET", "/api/invitation/sample.pdf")

    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_the_read_numbers_are_the_ones_the_sample_shop_holds():
    shop = json.loads(
        (
            __import__("pathlib").Path(__file__).resolve().parents[2] / "src/marginarena/sample/glow_lab_bkk.json"
        ).read_text()
    )
    held = {i["sku"]: round(float(i["required_discount"]) * 100) for i in shop["invitation"]["items"]}

    assert held == DISCOUNTS


async def test_a_matching_reading_is_kept_but_a_misreading_is_read_again():
    misread = copy.deepcopy(READ)
    next(i for i in misread["items"] if i["sku"] == "SS-50")["minimum_discount_pct"] = 15
    extractor = FakeExtractor(misread)
    app = create_app(llm_settings=SETTINGS, evolus_transport=httpx.MockTransport(extractor.handle))

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        wrong = (await client.post("/api/invitation/read")).json()
        extractor.read = READ
        right = (await client.post("/api/invitation/read")).json()
        kept = (await client.post("/api/invitation/read")).json()

    assert (wrong["matches"], right["matches"], right["cached"]) == (False, True, False)
    assert (kept["matches"], kept["cached"]) == (True, True)
    assert len(extractor.requests) == 2
