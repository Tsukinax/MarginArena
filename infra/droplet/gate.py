"""Ticket 08 gate: does tool calling hold up on our own vLLM endpoint?

The test and its pass rules are research §2.5 (.scratch/marginarena/research/model-serving-mi300x.md):

1. Fifty single-turn prompts with the Campaign Desk tools and tool_choice "auto", sent one at a
   time and then 16 at a time. Each run passes when at least 98% of replies carry tool calls whose
   arguments parse and fit the tool's schema, no reply ends with finish_reason "tool_calls" and an
   empty tool_calls list, and no <|channel>, <turn|> or <pad> leaks into the content.
2. Ten multi-turn loops (tool call, tool result, final answer). All must complete.
3. Not run: tool_choice "required" or a named tool. The gemma4 parser does not enforce them (§2.3),
   so MarginArena only sends "auto".
4. Arena: 100 concurrent response_format json_schema calls with max_tokens set. All must be valid
   JSON in the schema's shape.

kit.py passes in `request(method, url, key, body, timeout) -> (status, body_bytes)`, so this module
does no network I/O of its own and the tests can drive it with a fake server.
"""

from __future__ import annotations

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SAMPLE_SHOP = Path(__file__).resolve().parents[2] / "backend/src/marginarena/sample/glow_lab_bkk.json"
SAMPLING = {"temperature": 1.0, "top_p": 0.95}  # Google's recommended sampling for Gemma 4
TOOL_MAX_TOKENS = 512
ARENA_MAX_TOKENS = 400
VALID_CALL_RATE = 0.98
LEAK_TOKENS = ("<|channel>", "<channel|>", "<|turn>", "<turn|>", "<pad>")  # research §2.3
LEAK_TOKENS += ("<|tool_call>", "<tool_call|>", "<tool_call>", "</tool_call>", "<|im_end|>")  # unparsed tool calls

Request = Callable[..., "tuple[int, bytes]"]


def _tool(name: str, description: str, params: dict[str, tuple[str, str]], required: list[str]) -> dict:
    """A tool in the shape an Evolus Web API produces: flat, typed parameters with descriptions."""
    properties = {key: {"type": kind, "description": text} for key, (kind, text) in params.items()}
    parameters = {"type": "object", "properties": properties, "required": required}
    return {"type": "function", "function": {"name": name, "description": description, "parameters": parameters}}


TOOLS = [
    _tool(
        "evaluate_promo_plan",
        "Price one Promo Plan for one SKU in the 11.11 Campaign with MarginArena's engine. Returns the "
        "Verdict (Approve, Revise or Escalate), the worst-case profit and the worst-case margin.",
        {
            "sku_id": ("string", "Catalogue SKU id, for example NT-200"),
            "price_cut_pct": ("number", "Headline price cut in percent, for example 15"),
            "voucher_baht": ("number", "Shop voucher value in baht; 0 for none"),
            "min_spend_baht": ("number", "Minimum spend for the voucher in baht; 0 for none"),
            "gift_sku_id": ("string", "Catalogue SKU id given free with each order, if any"),
        },
        ["sku_id", "price_cut_pct"],
    ),
    _tool(
        "explain_verdict",
        "Get MarginArena's plain-language explanation of the Verdict for one SKU.",
        {"sku_id": ("string", "Catalogue SKU id"), "language": ("string", "en for English or th for Thai")},
        ["sku_id", "language"],
    ),
    _tool(
        "get_fee_rules",
        "Look up the marketplace fees (commission, payment fee, programme fees) for a seller type.",
        {"marketplace": ("string", "shopee-th or lazada-th"), "seller_type": ("string", "non-mall or mall")},
        ["marketplace"],
    ),
]
TOOL_SCHEMAS = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}

# Five Seller questions per SKU; each should make the agent call the tool named first.
TEMPLATES = (
    ("evaluate_promo_plan", "Should we join 11.11 with {name} at the invited {pct}% off? Check it still pays."),
    ("evaluate_promo_plan", "What if {sku} gets only {half}% off plus a ฿{voucher} voucher (min. spend ฿{min_spend})?"),
    ("explain_verdict", "Explain the verdict for {name} in Thai, please."),
    ("evaluate_promo_plan", "Try {sku} at {pct}% off with a free Gentle Amino Cleanser mini (AC-30) in every order."),
    ("get_fee_rules", "Which fees does Shopee Thailand take from us as a Non-Mall seller on orders of {name}?"),
)

# The Arena's Rival personas and output contract (backend/src/marginarena/arena.py).
RIVALS = (
    ("Undercutter", "cuts its headline price just below the shop"),
    ("Price matcher", "matches the shop's Campaign price exactly"),
    ("Voucher bomber", "keeps its price but stacks a large shop voucher"),
    ("Flash dropper", "runs a short, very deep flash price at midnight"),
    ("Free shipper", "absorbs shipping so buyers pay less in total"),
    ("Gift stacker", "adds a free gift instead of cutting its price"),
)
MOVE = {
    "type": "object",
    "properties": {
        "headline_cut_pct": {"type": "number", "minimum": 0, "maximum": 40},
        "voucher_baht": {"type": "number", "minimum": 0},
        "free_shipping_baht": {"type": "number", "minimum": 0, "maximum": 60},
        "gift_value_baht": {"type": "number", "minimum": 0},
        "why": {"type": "string"},
    },
    "required": ["headline_cut_pct", "voucher_baht", "free_shipping_baht", "gift_value_baht", "why"],
    "additionalProperties": False,
}
MOVES_SCHEMA = {
    "type": "object",
    "properties": {"moves": {"type": "array", "minItems": 1, "maxItems": 2, "items": MOVE}},
    "required": ["moves"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------- grading


def schema_errors(value, schema: dict, path: str = "$") -> list[str]:
    """Where `value` breaks `schema`, for the JSON Schema subset our tools and the Arena use.

    Bound violations start with "range:". Grammar backends may not enforce bounds, and the app
    rejects out-of-range proposals anyway, so they are reported but do not fail the gate.

    >>> schema_errors({"sku_id": "NT-200"}, TOOL_SCHEMAS["evaluate_promo_plan"])
    ['$.price_cut_pct is missing']
    """
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            return [f"{path} is not an object"]
        errors = [f"{path}.{key} is missing" for key in schema.get("required", []) if key not in value]
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                errors += schema_errors(item, properties[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{key} is not allowed")
        return errors
    if kind == "array":
        if not isinstance(value, list):
            return [f"{path} is not an array"]
        errors = []
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value)):
            errors.append(f"{path} has {len(value)} items")
        for i, item in enumerate(value):
            errors += schema_errors(item, schema.get("items", {}), f"{path}[{i}]")
        return errors
    if kind in ("number", "integer"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return [f"{path} is not a {kind}"]
        if kind == "integer" and not float(value).is_integer():
            return [f"{path} is not an integer"]
        low, high = schema.get("minimum"), schema.get("maximum")
        if (low is not None and value < low) or (high is not None and value > high):
            return [f"range: {path} = {value} is outside [{low}, {high}]"]
        return []
    if kind == "string":
        return [] if isinstance(value, str) else [f"{path} is not a string"]
    if kind == "boolean":
        return [] if isinstance(value, bool) else [f"{path} is not a boolean"]
    return []


def _arguments(function: dict):
    """A tool call's arguments as a dict. Raises ValueError when they are not a JSON object."""
    arguments = function.get("arguments")
    parsed = arguments if isinstance(arguments, dict) else json.loads(arguments or "")
    if not isinstance(parsed, dict):
        raise ValueError("not an object")
    return parsed


def inspect_reply(status: int, raw: bytes) -> tuple[dict, dict]:
    """Grade one chat reply (its tool calls, their arguments, leaked tokens); also return its message."""
    record: dict = {"status": status, "tools": [], "arg_errors": [], "leaks": [], "empty_tool_calls": False}
    if status != 200:
        record["error"] = f"HTTP {status}: {raw[:200].decode('utf-8', 'replace')}"
        return record, {}
    try:
        data = json.loads(raw)
        choice = data["choices"][0]
        message = choice["message"]
    except (ValueError, KeyError, IndexError, TypeError):
        record["error"] = "unreadable response"
        return record, {}
    calls = message.get("tool_calls") or []
    content = message.get("content") or ""
    record["finish_reason"] = choice.get("finish_reason")
    record["completion_tokens"] = int((data.get("usage") or {}).get("completion_tokens") or 0)
    record["empty_tool_calls"] = record["finish_reason"] == "tool_calls" and not calls
    record["leaks"] = [token for token in LEAK_TOKENS if token in content]
    if content:
        record["content"] = content[:300]
    for call in calls:
        function = call.get("function") or {}
        name = function.get("name")
        record["tools"].append(name)
        if name not in TOOL_SCHEMAS:
            record["arg_errors"].append(f"unknown tool {name!r}")
            continue
        try:
            arguments = _arguments(function)
        except (ValueError, TypeError):
            record["arg_errors"].append(f"{name}: arguments are not a JSON object: {function.get('arguments')!r:.120}")
            continue
        record["arg_errors"] += [f"{name}: {error}" for error in schema_errors(arguments, TOOL_SCHEMAS[name])]
        record.setdefault("arguments", []).append(arguments)
    record["valid_call"] = bool(calls) and not record["arg_errors"]
    return record, message


def _tool_failure(record: dict) -> str:
    """Why a single-turn reply fails the rules, or "" when it passes."""
    if record.get("error"):
        return record["error"]
    reasons = []
    if record["empty_tool_calls"]:
        reasons.append('finish_reason "tool_calls" with empty tool_calls')
    elif not record["tools"]:
        reasons.append(f"no tool call; content {record.get('content', '')[:120]!r}")
    if record["leaks"]:
        reasons.append(f"leaked {', '.join(record['leaks'])}")
    reasons += record["arg_errors"]
    return "; ".join(reasons)


# ---------------------------------------------------------------- the test


@dataclass(frozen=True)
class Endpoint:
    base_url: str
    key: str
    model: str
    request: Request

    def chat(self, body: dict) -> tuple[int, bytes]:
        return self.request("POST", f"{self.base_url}/chat/completions", self.key, {"model": self.model, **body}, 300)


@dataclass(frozen=True)
class Shop:
    system: str
    invited: list  # (catalogue row, invited discount in percent) for the first 10 invited SKUs


def load_shop(path: Path = SAMPLE_SHOP) -> Shop:
    data = json.loads(path.read_text())
    catalogue = {row["id"]: row for row in data["catalogue"]}
    invited = [(catalogue[i["sku"]], round(float(i["required_discount"]) * 100)) for i in data["invitation"]["items"]]
    lines = "\n".join(f"- {r['id']}: {r['name']} (list price ฿{r['list_price']})" for r in data["catalogue"])
    system = (
        f"You are the Campaign Desk agent for {data['shop']}, a Thai skincare shop on Shopee Thailand. "
        "The Seller is deciding which SKUs to put into the 11.11 Big Sale. Never work out prices, fees or "
        "profit yourself: call a tool for every number, then answer in one or two sentences from the tool "
        f"result.\nCatalogue:\n{lines}"
    )
    return Shop(system=system, invited=invited[:10])


def tool_prompts(shop: Shop) -> list[dict]:
    prompts = []
    for row, pct in shop.invited:
        price = float(row["list_price"])
        values = {
            "sku": row["id"],
            "name": row["name"],
            "pct": pct,
            "half": max(5, pct // 2),
            "voucher": max(10, round(price * 0.1 / 10) * 10),
            "min_spend": round(price / 100) * 100 + 100,
        }
        for n, (tool, text) in enumerate(TEMPLATES, 1):
            prompts.append({"id": f"{row['id']}-{n}", "tool": tool, "text": text.format(**values)})
    return prompts


def tool_result(call: dict) -> dict:
    """A canned engine answer, so the multi-turn loops can finish."""
    function = call.get("function") or {}
    try:
        args = _arguments(function)
    except (ValueError, TypeError):
        args = {}
    if function.get("name") == "evaluate_promo_plan":
        return {
            "sku_id": args.get("sku_id"),
            "verdict": "Revise",
            "worst_case_profit_baht": 18420.5,
            "worst_case_margin_pct": 11.8,
            "margin_floor_pct": 10.0,
            "better_plan": "15% off plus a ฿40 shop voucher with a ฿500 minimum spend",
        }
    if function.get("name") == "explain_verdict":
        return {
            "sku_id": args.get("sku_id"),
            "language": args.get("language"),
            "explanation": "ลด 15% แล้วกำไรต่ำกว่าเกณฑ์เมื่อคู่แข่งลดราคาตาม จึงแนะนำให้ใช้คูปองร้านค้าแทน",
        }
    return {"marketplace": "shopee-th", "seller_type": "non-mall", "fees_pct": 27.82, "fixed_fee_baht_per_order": 1.07}


def _ask_with_tools(endpoint: Endpoint, messages: list[dict]) -> tuple[dict, dict]:
    body = {"messages": messages, "tools": TOOLS, "tool_choice": "auto", "max_tokens": TOOL_MAX_TOKENS, **SAMPLING}
    try:
        return inspect_reply(*endpoint.chat(body))
    except Exception as error:  # a network or TLS failure counts as a failed request
        failed = {"error": f"{type(error).__name__}: {error}", "tools": [], "arg_errors": [], "leaks": []}
        return {**failed, "empty_tool_calls": False}, {}


def _single_turn(endpoint: Endpoint, shop: Shop, prompt: dict) -> dict:
    start = time.monotonic()
    record, _ = _ask_with_tools(
        endpoint, [{"role": "system", "content": shop.system}, {"role": "user", "content": prompt["text"]}]
    )
    record.update(id=prompt["id"], expected_tool=prompt["tool"], seconds=round(time.monotonic() - start, 3))
    return record


def _loop(endpoint: Endpoint, shop: Shop, prompt: dict) -> dict:
    """Tool call, tool result, final answer: up to 4 model calls, and at least one tool must be used."""
    messages = [{"role": "system", "content": shop.system}, {"role": "user", "content": prompt["text"]}]
    start, tool_rounds, tokens = time.monotonic(), 0, 0
    outcome = {"completed": False, "reason": "no final answer after 4 model calls"}
    for _ in range(4):
        record, message = _ask_with_tools(endpoint, messages)
        tokens += record.get("completion_tokens", 0)
        problem = record.get("error") or record["leaks"] or record["empty_tool_calls"] or record["arg_errors"]
        if problem:
            outcome = {"completed": False, "reason": f"turn {tool_rounds + 1}: {_tool_failure(record)}"}
            break
        calls = message.get("tool_calls") or []
        if not calls:
            answer = (message.get("content") or "").strip()
            if tool_rounds and answer:
                outcome = {"completed": True, "answer": answer[:300]}
            else:
                outcome = {"completed": False, "reason": "answered without a tool" if answer else "empty answer"}
            break
        tool_rounds += 1
        messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": calls})
        for call in calls:
            result = json.dumps(tool_result(call), ensure_ascii=False)
            messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": result})
    seconds = round(time.monotonic() - start, 3)
    return {"id": prompt["id"], "tool_rounds": tool_rounds, "completion_tokens": tokens, "seconds": seconds, **outcome}


def _arena_call(endpoint: Endpoint, shop: Shop, n: int) -> dict:
    row, pct = shop.invited[n % len(shop.invited)]
    rival, style = RIVALS[n % len(RIVALS)]
    offer = round(float(row["list_price"]) * (1 - pct / 100), 2)
    system = (
        "You are a Rival seller on Shopee Thailand with a lookalike product. "
        f"Persona: {rival}, who {style}. Reply with JSON only: "
        '{"moves": [{"headline_cut_pct": <0-40>, "voucher_baht": <number>, "free_shipping_baht": <0-60>, '
        '"gift_value_baht": <number>, "why": "<one sentence>"}]} with 1 or 2 moves. '
        "Vouchers may be at most 20% and gifts at most 25% of your usual price."
    )
    user = (
        f"Your product: a lookalike of {row['name']}, usual price ฿{row['list_price']}.\n"
        f"The shop's leading 11.11 offer for {row['name']}: shelf price ฿{offer}, buyers pay ฿{offer} "
        f"after shop vouchers ({pct}% off).\n"
        "Round 1: find the Counter-move that hurts this offer most while staying realistic for a seller."
    )
    body = {
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "counter_moves", "schema": MOVES_SCHEMA}},
        "max_tokens": ARENA_MAX_TOKENS,
        "temperature": 0.8,
    }
    record: dict = {"id": f"{row['id']} vs {rival} #{n}", "valid": False}
    start = time.monotonic()
    try:
        status, raw = endpoint.chat(body)
        record["status"] = status
        if status != 200:
            record["error"] = f"HTTP {status}: {raw[:200].decode('utf-8', 'replace')}"
        else:
            data = json.loads(raw)
            choice = data["choices"][0]
            content = choice["message"].get("content") or ""
            record["finish_reason"] = choice.get("finish_reason")
            record["completion_tokens"] = int((data.get("usage") or {}).get("completion_tokens") or 0)
            try:
                errors = schema_errors(json.loads(content), MOVES_SCHEMA)
            except ValueError:
                errors = ["not valid JSON"]
            record["shape_errors"] = [e for e in errors if not e.startswith("range:")]
            record["range_errors"] = [e for e in errors if e.startswith("range:")]
            record["valid"] = not record["shape_errors"]
            if not record["valid"]:
                record["content"] = content[:300]
    except Exception as error:  # a network or TLS failure counts as a failed request
        record["error"] = f"{type(error).__name__}: {error}"
    record["seconds"] = round(time.monotonic() - start, 3)
    return record


def _run_phase(task: Callable, items: list, workers: int) -> tuple[list[dict], dict]:
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(task, items))
    wall = time.monotonic() - start
    tokens = sum(r.get("completion_tokens", 0) for r in records)
    stats = {"concurrency": workers, "requests": len(records), "wall_s": round(wall, 1), "output_tokens": tokens}
    stats["output_tokens_per_s"] = round(tokens / wall, 1) if wall > 0 else 0.0
    return records, {**stats, **_latency(records)}


def _latency(records: list[dict]) -> dict:
    seconds = sorted(r["seconds"] for r in records if not r.get("error"))
    if not seconds:
        return {"p50_s": None, "p95_s": None}

    def rank(q: float) -> float:  # nearest-rank percentile
        return round(seconds[min(len(seconds) - 1, math.ceil(q * len(seconds)) - 1)], 2)

    return {"p50_s": rank(0.50), "p95_s": rank(0.95)}


def _grade_tool_phase(records: list[dict]) -> dict:
    n = len(records)
    valid = sum(1 for r in records if r.get("valid_call"))
    empty = sum(1 for r in records if r["empty_tool_calls"])
    leaks = sum(1 for r in records if r["leaks"])
    return {
        "valid_calls": valid,
        "valid_rate": round(valid / n, 4) if n else 0.0,
        "empty_tool_calls": empty,
        "no_tool_call": sum(1 for r in records if not (r["tools"] or r["empty_tool_calls"] or r.get("error"))),
        "leaks": leaks,
        "errors": sum(1 for r in records if r.get("error")),
        "other_tool_than_expected": sum(1 for r in records if r["tools"] and r["tools"][0] != r["expected_tool"]),
        "passed": n > 0 and valid / n >= VALID_CALL_RATE and empty == 0 and leaks == 0,
    }


def run(base_url: str, key: str, model: str, request: Request, progress: Callable[[str], None] = print) -> dict:
    """Run every part of the gate against one model and return all results (render_markdown reads them)."""
    endpoint = Endpoint(base_url.rstrip("/"), key, model, request)
    shop = load_shop()
    prompts = tool_prompts(shop)
    phases: dict[str, dict] = {}

    def verdict(passed: bool) -> str:
        return "PASS" if passed else "FAIL"

    for name, workers in (("single_turn_c1", 1), ("single_turn_c16", 16)):
        progress(f"  1. single-turn tool calls: {len(prompts)} prompts, {workers} at a time ...")
        records, stats = _run_phase(lambda p: _single_turn(endpoint, shop, p), prompts, workers)
        phase = phases[name] = {**stats, **_grade_tool_phase(records), "records": records}
        progress(
            f"     {phase['valid_calls']}/{phase['requests']} valid, {phase['empty_tool_calls']} empty tool_calls, "
            f"{phase['leaks']} leaks, p50 {phase['p50_s']} s -> {verdict(phase['passed'])}"
        )

    progress("  2. multi-turn loops: 10 conversations, 10 at a time ...")
    records, stats = _run_phase(lambda p: _loop(endpoint, shop, p), prompts[:10], 10)
    completed = sum(1 for r in records if r["completed"])
    phases["multi_turn"] = {**stats, "completed": completed, "passed": completed == len(records), "records": records}
    progress(f"     {completed}/{len(records)} completed -> {verdict(completed == len(records))}")

    progress("  4. Arena json_schema calls: 100 at a time ...")
    records, stats = _run_phase(lambda n: _arena_call(endpoint, shop, n), list(range(100)), 100)
    valid = sum(1 for r in records if r["valid"])
    phase = phases["arena_json"] = {
        **stats,
        "valid_json": valid,
        "out_of_range": sum(1 for r in records if r.get("range_errors")),
        "errors": sum(1 for r in records if r.get("error")),
        "passed": valid == len(records),
        "records": records,
    }
    progress(
        f"     {valid}/{len(records)} valid JSON, p50 {phase['p50_s']} s, p95 {phase['p95_s']} s, "
        f"{phase['output_tokens_per_s']} output tokens/s -> {verdict(phase['passed'])}"
    )

    return {
        "model": model,
        "passed": all(p["passed"] for p in phases.values()),
        "sampling": {**SAMPLING, "tool_max_tokens": TOOL_MAX_TOKENS, "arena_max_tokens": ARENA_MAX_TOKENS},
        "tools": TOOLS,
        "phases": phases,
    }


# ---------------------------------------------------------------- report


def failures(phases: dict) -> list[str]:
    found = []
    for name, phase in phases.items():
        for r in phase["records"]:
            if name.startswith("single_turn") and _tool_failure(r):
                found.append(f"`{name}` {r['id']}: {_tool_failure(r)}")
            elif name == "multi_turn" and not r["completed"]:
                found.append(f"`{name}` {r['id']}: {r['reason']}")
            elif name == "arena_json" and not r["valid"]:
                found.append(f"`{name}` {r['id']}: {r.get('error') or '; '.join(r.get('shape_errors', []))}")
    return found


def render_markdown(summary: dict, json_name: str) -> str:
    """The judge-facing evidence page for one gate run."""
    meta = summary.get("meta", {})
    pins = meta.get("pinned", {})
    seen = meta.get("observed_on_droplet", {})
    served = meta.get("served_model", {})
    phases = summary["phases"]
    c1, c16, loops, arena = (phases[k] for k in ("single_turn_c1", "single_turn_c16", "multi_turn", "arena_json"))
    is_qwen = "qwen" in summary["model"].lower()
    revision = pins.get("QWEN_REVISION" if is_qwen else "GEMMA_REVISION", "?")
    versions = ", ".join(
        f"{label} {seen[key]}" for label, key in (("vLLM", "vllm"), ("ROCm", "rocm_in_container")) if seen.get(key)
    )

    def verdict(phase: dict) -> str:
        return "PASS" if phase["passed"] else "**FAIL**"

    def tool_row(label: str, p: dict) -> str:
        return (
            f"| {label} | {p['requests']} | ≥ 98% valid tool calls; 0 empty `tool_calls`; 0 leaks | "
            f"{p['valid_calls']}/{p['requests']} valid ({p['valid_rate']:.0%}); {p['empty_tool_calls']} empty; "
            f"{p['leaks']} leaks; p50 {p['p50_s']} s, p95 {p['p95_s']} s | {verdict(p)} |"
        )

    if summary["passed"]:
        result = "**Result: PASS.** One model can serve both the Evolus agent and the Arena."
    elif is_qwen:
        result = "**Result: FAIL.** The failures are listed below."
    else:
        result = (
            "**Result: FAIL.** Next step (research §5): add Qwen3.6-27B for the Evolus agent with "
            "`python3 infra/droplet/kit.py provision <ip> --with-qwen`, then run this gate against it."
        )
    single = c1["requests"] + c16["requests"]
    lines = [
        f"# Evidence: tool calling on our own MI300X endpoint ({summary['model']})",
        "",
        "Ticket 08 gate. It decides whether one model can be both the Evolus main agent (tool calling) "
        "and the Arena's model (JSON output), or whether the Evolus agent also needs Qwen3.6-27B.",
        "",
        result,
        "",
        f"- **Model:** `{summary['model']}` at revision `{revision}`"
        + (f", max context {served['max_model_len']} tokens" if served.get("max_model_len") else ""),
        f"- **Serving:** `{seen.get('image') or pins.get('VLLM_IMAGE', '?')}`" + (f" ({versions})" if versions else ""),
        f"- **Hardware:** {seen.get('gpu') or 'AMD Instinct MI300X'}, one GPU, on an AMD Developer Cloud droplet"
        + (f"; host driver: {seen['host_driver']}" if seen.get("host_driver") else ""),
        *[f"- **vLLM at startup:** {seen[k]}" for k in ("kv_cache", "max_concurrency") if seen.get(k)],
        f"- **Endpoint:** `{meta.get('endpoint', '?')}`, Caddy HTTPS in front of vLLM on 127.0.0.1",
        f"- **Run:** {meta.get('date_utc', '?')} with `{meta.get('command', 'python3 infra/droplet/kit.py gate')}`. "
        f"Every request and reply: [{json_name}]({json_name})",
        f"- **Sampling:** temperature {SAMPLING['temperature']}, top_p {SAMPLING['top_p']}; max_tokens "
        f"{TOOL_MAX_TOKENS} for tool calls and {ARENA_MAX_TOKENS} for the Arena",
        "",
        "## Results",
        "",
        "| Test | Requests | Pass rule | Measured | Result |",
        "|---|---|---|---|---|",
        tool_row("1a. Single-turn tool calls, 1 at a time", c1),
        tool_row("1b. The same 50 prompts, 16 at a time", c16),
        f"| 2. Multi-turn loops (tool call, tool result, answer), 10 at a time | {loops['requests']} | "
        f"all complete | {loops['completed']}/{loops['requests']} completed | {verdict(loops)} |",
        f"| 4. Arena `json_schema` calls, 100 at a time | {arena['requests']} | "
        "100% valid JSON in the schema's shape | "
        f"{arena['valid_json']}/{arena['requests']} valid; p50 {arena['p50_s']} s, p95 {arena['p95_s']} s; "
        f"{arena['output_tokens']:,} output tokens in {arena['wall_s']} s ({arena['output_tokens_per_s']} tokens/s) "
        f"| {verdict(arena)} |",
        "",
        f"- Empty `tool_calls` (finish_reason `tool_calls` but no calls): "
        f"{c1['empty_tool_calls'] + c16['empty_tool_calls']} of {single} single-turn replies.",
        f"- No tool call at all: {c1['no_tool_call'] + c16['no_tool_call']} of {single}. A different tool than "
        f"expected: {c1['other_tool_than_expected'] + c16['other_tool_than_expected']} (reported only).",
        f"- Arena replies with a number outside the schema's bounds: {arena['out_of_range']} of {arena['requests']} "
        "(reported only; the app rejects and counts them).",
    ]
    if seen.get("args"):
        lines += ["", "## vLLM arguments, as running on the droplet", "", f"`{seen['args']}`"]
    found = failures(phases)
    lines += ["", "## Failures", ""]
    lines += [f"- {item}" for item in found[:15]] or ["None."]
    if len(found) > 15:
        lines.append(f"- ... and {len(found) - 15} more in the JSON file.")
    lines += [
        "",
        "## Not tested",
        "",
        '- `tool_choice: "required"` and named tools. The gemma4 parser does not enforce them (research §2.3), '
        'so MarginArena only sends `"auto"`.',
        "",
        "## Method",
        "",
        "- Pass rules: research §2.5 in `.scratch/marginarena/research/model-serving-mi300x.md`.",
        "- Prompts: 50 Seller questions about the Glow Lab BKK sample shop (10 invited SKUs, 5 kinds of question). "
        "Tools: `evaluate_promo_plan`, `explain_verdict` and `get_fee_rules`, with flat, typed parameters like an "
        "Evolus Web API tool. In the loops the tool results are canned.",
        "- Arena calls: the Rival prompt and output contract from `backend/src/marginarena/arena.py`, "
        "sent as `response_format: json_schema`.",
        "- Reproduce: create the droplet and run `python3 infra/droplet/kit.py provision <ip>` "
        "(see `infra/droplet/README.md`), then `python3 infra/droplet/kit.py gate`.",
        "",
    ]
    return "\n".join(lines)
