"""The ticket 08 gate against a fake vLLM. Nothing here touches the network.

Run from the repo root: uv run --project backend pytest infra/droplet -q
"""

import json
import threading

import gate

API_KEY = "k" * 64


def reply(content, finish, calls=None) -> bytes:
    message = {"role": "assistant", "content": content}
    if calls is not None:
        message["tool_calls"] = calls
    choice = {"message": message, "finish_reason": finish}
    return json.dumps({"choices": [choice], "usage": {"completion_tokens": 20}}).encode()


class FakeVLLM:
    """Answers like a healthy vLLM; with empty_every=n, every n-th tool turn has empty tool_calls."""

    def __init__(self, empty_every=0):
        self.empty_every = empty_every
        self.turns = 0
        self.lock = threading.Lock()

    def __call__(self, method, url, key, body, timeout):
        assert (method, key) == ("POST", API_KEY) and url.endswith("/chat/completions")
        if "response_format" in body:
            move = {"headline_cut_pct": 18, "voucher_baht": 20, "free_shipping_baht": 0, "gift_value_baht": 0}
            return 200, reply(json.dumps({"moves": [{**move, "why": "undercut the shop"}]}), "stop")
        if body["messages"][-1]["role"] == "tool":
            return 200, reply("Revise it: 15% off plus a ฿40 voucher keeps an 11.8% worst-case margin.", "stop")
        with self.lock:
            self.turns += 1
            turn = self.turns
        if self.empty_every and turn % self.empty_every == 0:
            return 200, reply("", "tool_calls", calls=[])
        function = {"name": "evaluate_promo_plan", "arguments": json.dumps({"sku_id": "NT-200", "price_cut_pct": 15})}
        return 200, reply(None, "tool_calls", calls=[{"id": f"call-{turn}", "type": "function", "function": function}])


def quiet(_line):
    pass


def test_the_gate_passes_a_well_behaved_server():
    summary = gate.run("https://164-92-10-5.sslip.io/v1", API_KEY, "google/gemma-4-31B-it", FakeVLLM(), quiet)
    phases = summary["phases"]
    assert summary["passed"]
    assert [phases[p]["requests"] for p in phases] == [50, 50, 10, 100]
    assert phases["single_turn_c1"]["valid_calls"] == 50
    assert phases["multi_turn"]["completed"] == 10
    assert phases["arena_json"]["valid_json"] == 100
    assert "**Result: PASS.**" in gate.render_markdown(summary, json_name="gate.json")


def test_the_gate_fails_on_empty_tool_calls():
    summary = gate.run("https://x/v1", API_KEY, "google/gemma-4-31B-it", FakeVLLM(empty_every=10), quiet)
    first = summary["phases"]["single_turn_c1"]
    assert (first["empty_tool_calls"], first["no_tool_call"], first["passed"]) == (5, 0, False)
    assert not summary["passed"]
    page = gate.render_markdown(summary, json_name="gate.json")
    assert "**Result: FAIL.**" in page and "--with-qwen" in page  # the page says what to do next


def test_the_prompts_cover_ten_invited_skus_and_every_tool():
    prompts = gate.tool_prompts(gate.load_shop())
    assert len(prompts) == 50 and len({p["id"] for p in prompts}) == 50
    assert {p["tool"] for p in prompts} == set(gate.TOOL_SCHEMAS)


def test_a_reply_with_leaked_tokens_and_bad_arguments_is_not_a_valid_call():
    arguments = '{"sku_id": "NT-200", "price_cut_pct": "15"}'
    call = {"id": "1", "type": "function", "function": {"name": "evaluate_promo_plan", "arguments": arguments}}
    record, _ = gate.inspect_reply(200, reply("<|channel>thought", "tool_calls", calls=[call]))
    assert record["leaks"] == ["<|channel>"]
    assert record["arg_errors"] == ["evaluate_promo_plan: $.price_cut_pct is not a number"]
    assert not record["valid_call"]


def test_out_of_range_numbers_are_reported_but_keep_the_json_valid():
    move = {"headline_cut_pct": 55, "voucher_baht": 0, "free_shipping_baht": 0, "gift_value_baht": 0, "why": "deep"}
    errors = gate.schema_errors({"moves": [move]}, gate.MOVES_SCHEMA)
    assert errors == ["range: $.moves[0].headline_cut_pct = 55 is outside [0, 40]"]
