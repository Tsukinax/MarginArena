"""Verdict explanations in English or Thai (spec: Explainer).

The model writes the prose; every number in it must already be in the engine's facts (ADR 0001).
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field

from marginarena.llm import LLMClient

Language = Literal["en", "th"]
MAX_DRAFTS = 2
NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
WRITE_IN = {"en": "plain English", "th": "natural, plain Thai (ภาษาไทย)"}
VERDICT_WORDS = {"approve": "Approve", "revise": "Revise", "escalate": "Escalate"}
MEANINGS = {
    "Approve": "Join the Campaign as invited.",
    "Revise": "Join the Campaign, but with MarginArena's Promo Plan instead of the invited one.",
    "Skip": "A kind of Revise: don't join the Campaign with this product.",
    "Escalate": "No plan passes every check, and the trade-off is the Seller's to make.",
}


class ExplanationOut(BaseModel):
    explanation: str = Field(min_length=1)


async def explain(result: dict, language: Language, llm: LLMClient) -> dict:
    """An explanation of one decided SKU (an Arena result) in `language`.

    A draft citing any number that is not in the facts is rejected and written again, at most twice.
    """
    facts = fact_sheet(result)
    user = f"FACTS:\n{facts}"
    rejected: list[dict] = []
    for _ in range(MAX_DRAFTS):
        out = await llm.json_chat(_system(language), user, ExplanationOut)
        if out is None:  # the model server failed or answered out of contract
            rejected.append({"text": None, "unsupported": []})
            continue
        unsupported = unsupported_numbers(out.explanation, facts)
        if not unsupported:
            return {"language": language, "text": out.explanation, "source": "model", "rejected": rejected}
        rejected.append({"text": out.explanation, "unsupported": unsupported})
        user = (
            f"FACTS:\n{facts}\n\nYour last draft was rejected: it used {', '.join(unsupported)}, which "
            "FACTS does not contain. Use only numbers from FACTS."
        )
    return {"language": language, "text": template(result, language), "source": "template", "rejected": rejected}


TEMPLATES = {
    "en": {
        "join": "{verdict}: join the Campaign with {plan}. Worst-case Campaign profit: {kept} with this plan, "
        "{invited} as invited ({invited_plan}), {not_joining} without joining.",
        "skip": "Skip: don't join the Campaign with this product. Worst-case Campaign profit: {not_joining} "
        "without joining, {invited} as invited ({invited_plan}).",
        "escalate": "Escalate: this one is your call. Joining as invited ({invited_plan}) fails these checks: "
        "{checks}. Worst-case Campaign profit: {invited} as invited, {not_joining} without joining.",
    },
    "th": {
        "join": "{verdict}: เข้าร่วมแคมเปญด้วย {plan} กำไรตลอดแคมเปญในกรณีแย่ที่สุดคือ {kept} ด้วยแผนนี้ "
        "{invited} ถ้าเข้าร่วมตามคำเชิญ ({invited_plan}) และ {not_joining} ถ้าไม่เข้าร่วม",
        "skip": "Skip: ไม่ควรนำสินค้านี้เข้าร่วมแคมเปญ กำไรตลอดแคมเปญในกรณีแย่ที่สุดคือ {not_joining} ถ้าไม่เข้าร่วม "
        "และ {invited} ถ้าเข้าร่วมตามคำเชิญ ({invited_plan})",
        "escalate": "Escalate: สินค้านี้คุณต้องตัดสินใจเอง การเข้าร่วมตามคำเชิญ ({invited_plan}) ไม่ผ่านเงื่อนไข: "
        "{checks} กำไรตลอดแคมเปญในกรณีแย่ที่สุดคือ {invited} ถ้าเข้าร่วมตามคำเชิญ และ {not_joining} ถ้าไม่เข้าร่วม",
    },
}
CHECKS_TH = {
    "below the Margin Floor": "กำไรต่อชิ้นต่ำกว่า Margin Floor",
    "earns less than not joining": "ได้กำไรน้อยกว่าการไม่เข้าร่วม",
    "below the invited discount": "ส่วนลดน้อยกว่าที่คำเชิญกำหนด",
}


def template(r: dict, language: Language) -> str:
    """The numbers-only explanation, used when the model's drafts fail the number check."""
    kind = "skip" if r["skip"] else "escalate" if r["verdict"] == "escalate" else "join"
    checks = r["invited_failed_checks"]
    if language == "th":
        checks = [CHECKS_TH.get(c, c.replace("breaks ", "ขัดกับ ")) for c in checks]
    return TEMPLATES[language][kind].format(
        verdict=_verdict_word(r),
        plan=r["chosen_plan"],
        kept=_money(r["chosen_worst_total"]) if kind == "join" else "",
        invited=_money(r["invited_worst_total"]),
        invited_plan=r["invited_plan"],
        not_joining=_money(r["dont_join_total"]),
        checks="; ".join(checks),
    )


def fact_sheet(r: dict) -> str:
    """The engine's figures for one Verdict: everything the model may cite, and nothing else."""
    verdict = _verdict_word(r)
    lines = [
        f"Product: {r['name']} ({r['sku']})",
        f"Verdict: {verdict}. {MEANINGS[verdict]}",
        f"Joining as invited ({r['invited_plan']}): worst-case Campaign profit {_money(r['invited_worst_total'])}, "
        f"expected {_money(r['invited_expected_total'])}, "
        f"worst-case margin per unit {_pct(r['invited_worst_margin'])}.",
    ]
    if r["invited_failed_checks"]:
        lines.append(f"Joining as invited fails these checks: {'; '.join(r['invited_failed_checks'])}.")
    if r["chosen_plan"] and not r["skip"]:
        lines.append(
            f"MarginArena's Promo Plan ({r['chosen_plan']}): worst-case Campaign profit "
            f"{_money(r['chosen_worst_total'])}, expected {_money(r['chosen_expected_total'])}, "
            f"worst-case margin per unit {_pct(r['chosen_worst_margin'])}."
        )
    lines.append(f"Not joining: worst-case Campaign profit {_money(r['dont_join_total'])}.")
    if r["verdict"] != "escalate":
        lines.append(f"Margin Protected by following this Verdict: {_money(r['protected'])}.")
    w = r["waterfall"]
    lines.append(
        f"Per unit with {w['plan']}: shelf price {_money(w['selling_price'])}, shop voucher {_money(w['voucher'])}, "
        f"marketplace fees {_money(w['fees']['total'])}, product cost {_money(w['unit_cost'])}, profit "
        f"{_money(w['profit'])} ({_pct(w['margin'])} of the shelf price)."
    )
    hardest = min(r["scenario_grid"], key=lambda g: Decimal(g["shown_total"]))
    lines.append(
        f"Hardest Counter-move: {hardest['rival']}, rival price {_money(hardest['effective_rival_price'])}. "
        f"Tested against {r['scenarios']} Counter-moves over {r['rounds_played']} rounds; "
        f"{r['plans_searched']} Promo Plans searched."
    )
    if r.get("red_team_gain") is not None:
        lines.append(
            "Before the AI Rivals joined, the engine's plan would keep "
            f"{_money(r['generic_worst_total_all_scenarios'])} in the worst case against these Counter-moves; "
            f"this plan keeps {_money(r['chosen_worst_total'])}."
        )
    lines += [f"Source ({e['source']}): {e['text']}" for e in r["evidence"]]
    return "\n".join(lines)


def _system(language: Language) -> str:
    return (
        "You explain one MarginArena Verdict to a small online Seller in Thailand. "
        f"Write in {WRITE_IN[language]}: 3 to 5 short sentences on what to do, why, and the hardest Counter-move "
        "the plan was tested against. Use only numbers that appear in FACTS, written with digits. You may round a "
        "number, but never add, subtract, multiply or estimate a new one. Keep these words in English: Approve, "
        "Revise, Skip, Escalate, Promo Plan, Margin Floor, Counter-move, Campaign. "
        'Reply with JSON only: {"explanation": "<your text>"}'
    )


def _verdict_word(r: dict) -> str:
    return "Skip" if r["skip"] else VERDICT_WORDS[r["verdict"]]


def _money(value: str) -> str:
    amount = Decimal(value)
    return f"{'−' if amount < 0 else ''}฿{abs(amount):,.2f}"


def _pct(value: str) -> str:
    return f"{(Decimal(value) * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"


def unsupported_numbers(text: str, facts: str) -> list[str]:
    """The numbers in `text`, as written, that are not a figure in `facts`.

    A figure may be rounded to fewer decimal places (฿1,227.28 as ฿1,227), never to a different value.
    """
    allowed = [_value(m.group()) for m in NUMBER.finditer(facts)]
    return [m.group() for m in NUMBER.finditer(text) if not _traceable(_value(m.group()), allowed)]


def _traceable(number: Decimal, allowed: list[Decimal]) -> bool:
    places = Decimal(1).scaleb(number.as_tuple().exponent)
    try:
        return any(fact.quantize(places, rounding=ROUND_HALF_UP) == number for fact in allowed)
    except InvalidOperation:  # more digits than any engine figure carries
        return False


def _value(token: str) -> Decimal:
    return Decimal(token.replace(",", ""))
