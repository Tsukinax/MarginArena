"""Proof 3: four pricing policies over the sample invitation, under the same Scenarios (model-based estimates).

For each of the 12 invited SKUs:
- As invited: the cut the Campaign Invitation asks for (the platform's suggestion).
- Match the competitor: the Rival Snapshot's price, cut by the same Campaign discount (the competitor joins too and we
  match it), never less than the invitation asks. Without a snapshot the rival is assumed at our list price.
- LLM-direct: Gemma chooses the plan and computes its own Campaign units and profit from the same facts and formula
  the engine uses.
- MarginArena: the engine's choice, given the Plan Ideas and Counter-moves of the recorded Arena run.

Every policy faces the same Scenarios: the generic hold, match and undercut moves plus every Counter-move the AI
Rivals found in the recorded run, each at the point elasticity and both band edges. Every number is the engine's,
except LLM-direct's own estimates, which are compared with the engine's figures for the same plan.

Run from the repo root (Token Factory may only see sample data, which is all this sends):
    uv run --project backend --env-file .env python backend/scripts/compare_policies.py

Writes evidence/policy-comparison.json (everything) and evidence/policy-comparison.md (the report). With --report it
rebuilds the report from the saved JSON, calling no model.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import sys
from collections import defaultdict
from dataclasses import replace
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from pydantic import BaseModel, Field

from marginarena.engine import (
    CounterMove,
    GiftWithPurchase,
    PlanIdea,
    PriceCut,
    PromoPlan,
    SellerSettings,
    ShopVoucher,
    campaign_outcome,
    candidate_plans,
    evaluate_sku,
)
from marginarena.llm import LLMClient, LLMSettings, first_healthy
from marginarena.sample import load_shop

EVIDENCE = Path(__file__).resolve().parents[2] / "evidence"
RUN = EVIDENCE / "runs" / "token-factory-sample-12sku.sse"
POLICIES = ("As invited", "Match the competitor", "LLM-direct", "MarginArena")


class DirectPlan(BaseModel):
    price_cut_baht: float = Field(ge=0)
    voucher_baht: float = Field(default=0, ge=0)
    expected_units: float = Field(ge=0)
    expected_campaign_profit_baht: float
    why: str = ""


def sat(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def dec(x: float) -> Decimal:
    return Decimal(str(round(x, 2)))  # as arena._decimal reads a model's number


def recorded_run() -> tuple[dict, dict, dict]:
    """The recorded Arena's Counter-moves and Plan Ideas per SKU, and its results."""
    events = [json.loads(line[6:]) for line in RUN.read_text().splitlines() if line.startswith("data: ")]
    moves: dict[str, list[CounterMove]] = defaultdict(list)
    ideas: dict[str, list[tuple[bool, str | None]]] = defaultdict(list)
    for e in events:
        if e["type"] == "rival_move":
            moves[e["sku"]].append(
                CounterMove(
                    rival=e["rival"],
                    rival_price_cut=dec(e["headline_cut_pct"]) / 100,
                    voucher=dec(e["voucher_baht"]),
                    free_shipping=dec(e["free_shipping_baht"]),
                    gift_value=dec(e["gift_value_baht"]),
                )
            )
        elif e["type"] == "idea":
            ideas[e["sku"]].append((e["use_voucher"], e["gift"]))
    return moves, ideas, {r["sku"]: r for r in events[-1]["results"]}


def facts(shop, item, terms, rules) -> str:
    """What LLM-direct is told: the inputs and the formulas the engine uses, in words."""
    sku = item.sku
    p = shop.profile
    snapshot = shop.rival_snapshot.get(sku.id)
    lines = [
        f"Product: {sku.name}, list price ฿{sku.list_price}, unit cost ฿{sku.cost}, stock {sku.stock} units.",
        f"Campaign Invitation: {shop.invitation['campaign']}; the price cut must be at least "
        f"{(item.required_discount * 100).normalize():f}% of the list price.",
        f"Marketplace fees, charged on the price after the Seller's own cut and voucher: commission "
        f"{p.commission_rate * 100:f}%, payment {p.payment_fee_rate * 100:f}%, programme {p.programme_fee_rate * 100:f}%, "
        f"plus ฿{p.fixed_fee_per_order} per order. Each fee is rounded to the satang, then {p.vat_rate * 100:f}% VAT is "
        "added to it.",
        f"Demand: units = {sku.baseline_units} x {terms.traffic_lift} x (price the buyer pays / list price) ^ "
        f"({sku.elasticity}), rounded down, and never more than the stock. A voucher lowers the price the buyer pays.",
        f"The Seller needs at least {(shop.margin_floor * 100).normalize():f}% profit per unit, after fees and cost, as "
        "a share of the shelf price.",
    ]
    if snapshot:
        lines.append(f"A competitor sells a lookalike ({snapshot.rival}) at ฿{snapshot.reference_price}.")
    lines += [f"Brand agreement: {shop.brand_rule_texts[r.clause]}" for r in rules]
    return "\n".join(lines)


SYSTEM = (
    "You are a pricing assistant for a Thai online Seller on Shopee Thailand. Choose the Seller's Promo Plan for one "
    "product in the Campaign: a price cut in baht and an optional shop voucher in baht. Then compute, yourself, the "
    "expected units and the expected Campaign profit (units x (price after cut and voucher - fees - cost)), assuming "
    "the competitor does not react. Pick the plan that earns the most while keeping the Seller's minimum margin and "
    "every rule. Reply with JSON only: "
    '{"price_cut_baht": <number>, "voucher_baht": <number>, "expected_units": <number>, '
    '"expected_campaign_profit_baht": <number>, "why": "<one sentence>"}'
)


def outcome(evaluation, label: str) -> dict:
    return {
        "plan": label,
        "worst_total": str(evaluation.worst_total),
        "worst_margin": str(evaluation.worst_margin),
        "failed_checks": list(evaluation.failed_checks),
    }


def plan_label(plan: PromoPlan) -> str:
    parts = []
    for m in plan.mechanics:
        if isinstance(m, PriceCut):
            parts.append(f"฿{m.amount} off")
        elif isinstance(m, ShopVoucher):
            parts.append(f"฿{m.amount} voucher")
        elif isinstance(m, GiftWithPurchase):
            parts.append(f"gift: {m.name}")
    return " + ".join(parts) or "no promotion"


async def main() -> None:
    shop = load_shop("glow-lab-bkk")
    moves, ideas, results = recorded_run()
    gifts = {g.name: g for g in shop.catalogue.values()}
    settings = await first_healthy(LLMSettings.routes_from_env())
    llm = LLMClient(settings)
    rows = []
    try:
        for item in shop.invited:
            sku = item.sku
            snapshot = shop.rival_snapshot.get(sku.id)
            override = shop.elasticity_overrides.get(sku.id)
            terms = replace(
                shop.terms,
                required_discount=item.required_discount,
                rival_reference_price=snapshot.reference_price if snapshot else None,
                elasticity_band=override.band if override else shop.terms.elasticity_band,
            )
            rules = tuple(r for r in shop.brand_rules if r.binds(sku))
            seller = SellerSettings(margin_floor=shop.margin_floor, brand_rules=rules)
            scenarios = [
                CounterMove(rival="Holder", rival_price_cut=Decimal("0")),
                CounterMove(rival="Matcher", rival_price_cut=item.required_discount),
                CounterMove(rival="Undercutter", rival_price_cut=item.required_discount + Decimal("0.05")),
                *moves[sku.id],
            ]

            def judge(plan: PromoPlan, sku=sku, terms=terms, seller=seller, scenarios=scenarios):
                return evaluate_sku(sku, plan, [], scenarios, shop.profile, terms, seller).as_invited

            invited = PromoPlan(mechanics=(PriceCut(amount=sat(sku.list_price * item.required_discount)),))
            rival_price = snapshot.reference_price if snapshot else sku.list_price
            match_price = sat(rival_price * (1 - item.required_discount))
            match = PromoPlan(
                mechanics=(PriceCut(amount=max(sku.list_price - match_price, invited.mechanics[0].amount)),)
            )

            # MarginArena: the engine's choice with the recorded run's Plan Ideas and Counter-moves.
            idea_objects = [PlanIdea(), PlanIdea(use_voucher=True)]
            for use_voucher, gift_name in ideas[sku.id]:
                g = gifts[gift_name] if gift_name else None
                gift = (
                    GiftWithPurchase(
                        cost=g.cost, perceived_value=sat(g.list_price * shop.gift_value_ratio), name=g.name
                    )
                    if g
                    else None
                )
                idea_objects.append(PlanIdea(use_voucher=use_voucher, gift=gift))
            plans = candidate_plans(sku, terms, idea_objects, rules)
            verdict = evaluate_sku(sku, invited, plans, scenarios, shop.profile, terms, seller)
            kept = verdict.chosen.worst_total if verdict.chosen else verdict.dont_join_total if verdict.skip else None
            recorded = results[sku.id]
            if verdict.verdict != recorded["verdict"] or str(kept) != str(recorded["chosen_worst_total"]):
                raise SystemExit(f"{sku.id}: re-selection {verdict.verdict} {kept} differs from the recorded run")
            if verdict.chosen:
                arena = outcome(verdict.chosen, plan_label(verdict.chosen.plan))
            elif verdict.skip:
                arena = {"plan": "don't join", "worst_total": str(verdict.dont_join_total), "failed_checks": []}
            else:
                arena = {"plan": "a person decides (Escalate)", "worst_total": None, "failed_checks": []}

            # LLM-direct: Gemma plans and computes on its own; the engine checks its plan and its arithmetic.
            out = await llm.json_chat(SYSTEM, facts(shop, item, terms, rules), DirectPlan)
            direct, error = None, None
            if out is not None:
                mechanics = [PriceCut(amount=sat(dec(out.price_cut_baht)))]
                if out.voucher_baht > 0:
                    mechanics.append(ShopVoucher(amount=sat(dec(out.voucher_baht))))
                plan = PromoPlan(mechanics=tuple(mechanics))
                direct = outcome(judge(plan), plan_label(plan))
                calm = campaign_outcome(sku, plan, shop.profile, terms)  # the competitor does not react
                claimed = dec(out.expected_campaign_profit_baht)
                error = {
                    "claimed_units": out.expected_units,
                    "engine_units": calm.units,
                    "claimed_profit": str(claimed),
                    "engine_profit": str(calm.total_profit),
                    "relative_error": str(sat(abs(claimed - calm.total_profit) / abs(calm.total_profit) * 100))
                    if calm.total_profit
                    else None,
                    "why": out.why,
                }
            rows.append(
                {
                    "sku": sku.id,
                    "name": sku.name,
                    "verdict": "skip" if verdict.skip else verdict.verdict,
                    "scenarios": len(scenarios),
                    "As invited": outcome(judge(invited), plan_label(invited)),
                    "Match the competitor": outcome(judge(match), plan_label(match)),
                    "LLM-direct": direct,
                    "MarginArena": arena,
                    "llm_direct_arithmetic": error,
                }
            )
            print(f"{sku.id}: done", flush=True)
    finally:
        telemetry = llm.telemetry.snapshot()
        await llm.aclose()
    measured = datetime.now(UTC).isoformat(timespec="seconds")
    write_report(rows, {"measured": measured, "route": settings.route, "model": settings.model, "telemetry": telemetry})


def total(rows: list[dict], policy: str) -> dict | None:
    """The policy's worst-case profit summed over `rows`, or None when it has no figure for one of them."""
    values = [r[policy] for r in rows]
    if any(v is None or v["worst_total"] is None for v in values):
        return None
    return {
        "worst_total": str(sum((Decimal(v["worst_total"]) for v in values), Decimal("0"))),
        "skus": len(values),
        "breaking_a_check": sum(1 for v in values if v["failed_checks"]),
    }


def write_report(rows: list[dict], meta: dict) -> None:
    measured, telemetry = meta["measured"], meta["telemetry"]
    decided = [r for r in rows if r["verdict"] != "escalate"]
    # Every policy answered for these; LLM-direct may have given invalid answers for others.
    common = [r for r in decided if all(r[p] and r[p]["worst_total"] is not None for p in POLICIES)]
    totals = {p: total(decided, p) for p in POLICIES}
    totals_common = {p: total(common, p) for p in POLICIES}
    errors = [Decimal(r["llm_direct_arithmetic"]["relative_error"]) for r in rows if r["llm_direct_arithmetic"]]
    errors = [e for e in errors if e is not None]
    summary = {
        **meta,
        "recorded_run": RUN.name,
        "totals_over_decided_skus": totals,
        "totals_over_skus_every_policy_answered": {"skus": [r["sku"] for r in common], **totals_common},
        "llm_direct_relative_error_pct": {
            "median": str(statistics.median(errors)) if errors else None,
            "within_5pct": sum(1 for e in errors if e <= 5),
            "answers": len(errors),
        },
    }
    (EVIDENCE / "policy-comparison.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1) + "\n"
    )

    def cell(v: dict | None) -> str:
        if v is None:
            return "no valid answer"
        if v["worst_total"] is None:
            return v["plan"]
        flag = f" ✗ {'; '.join(v['failed_checks'])}" if v["failed_checks"] else ""
        return f"{v['plan']}: ฿{Decimal(v['worst_total']):,.2f}{flag}"

    lines = [
        "# Evidence: four pricing policies under the same Scenarios (proof 3)",
        "",
        "Reproduce: `uv run --project backend --env-file .env python backend/scripts/compare_policies.py`, which writes "
        "this file and `policy-comparison.json`. These are model-based estimates: every figure comes from the engine "
        "under the sample shop's assumptions, not from real sales.",
        "",
        f"- **Measured:** {measured} on route `{meta['route']}`, model `{meta['model']}`, sample shop Glow Lab BKK.",
        f"- **Scenarios:** per SKU, the generic hold, match and undercut moves plus every Counter-move the AI Rivals "
        f"found in `runs/{RUN.name}`, each at the point elasticity and both band edges.",
        "- **MarginArena** is the engine's choice given that run's Plan Ideas and Counter-moves; it reproduces the "
        "recorded Verdicts exactly (the script stops if it does not).",
        "- **LLM-direct** got the same facts and formulas as the engine, in words, and chose and computed on its own. "
        f"Calls: {telemetry['calls_ok']} answered, {telemetry['calls_invalid']} invalid, "
        f"{telemetry['calls_failed']} failed.",
        "",
        "## Worst-case Campaign profit per SKU",
        "",
        "✗ marks a plan that breaks a check: the invited discount, the Margin Floor, a Brand Price Rule, or earning less "
        "than not joining.",
        "",
        "| SKU | Verdict | " + " | ".join(POLICIES) + " |",
        "|---|---|" + "---|" * len(POLICIES),
    ]
    lines += [f"| {r['sku']} | {r['verdict']} | " + " | ".join(cell(r[p]) for p in POLICIES) + " |" for r in rows]
    lines += [
        "",
        "## Totals",
        "",
        f"Escalated SKUs are left out, as in Margin Protected: a person decides them. The second column keeps only the "
        f"{len(common)} SKUs every policy answered for, so every row adds up the same products.",
        "",
        f"| Policy | Worst case, {len(decided)} SKUs MarginArena decided | Worst case, the {len(common)} SKUs every "
        f"policy answered | Plans breaking a check, of {len(decided)} |",
        "|---|---|---|---|",
    ]

    def money(t: dict | None) -> str:
        return f"฿{Decimal(t['worst_total']):,.2f}" if t else "– (an invalid answer)"

    for p in POLICIES:
        breaking = sum(1 for r in decided if r[p] and r[p]["failed_checks"])
        lines.append(f"| {p} | {money(totals[p])} | {money(totals_common[p])} | {breaking} |")
    lines += [
        "",
        "## LLM-direct arithmetic, checked by the engine",
        "",
        "For LLM-direct's own plan, with the competitor not reacting, at the point elasticity.",
        "",
        "| SKU | Units: Gemma / engine | Campaign profit: Gemma / engine | Error |",
        "|---|---|---|---|",
    ]
    for r in rows:
        a = r["llm_direct_arithmetic"]
        if a is None:
            lines.append(f"| {r['sku']} | no valid answer | | |")
            continue
        err = f"{a['relative_error']}%" if a["relative_error"] is not None else "n/a"
        lines.append(
            f"| {r['sku']} | {a['claimed_units']:g} / {a['engine_units']} | "
            f"฿{Decimal(a['claimed_profit']):,.2f} / ฿{Decimal(a['engine_profit']):,.2f} | {err} |"
        )
    e = summary["llm_direct_relative_error_pct"]
    lines += [
        "",
        f"Median error {e['median']}%; {e['within_5pct']} of {e['answers']} answers within 5% of the engine.",
        "",
    ]
    (EVIDENCE / "policy-comparison.md").write_text("\n".join(lines))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        saved = json.loads((EVIDENCE / "policy-comparison.json").read_text())
        meta = {k: saved["summary"][k] for k in ("measured", "route", "model", "telemetry")}
        write_report(saved["rows"], meta)
    else:
        asyncio.run(main())
