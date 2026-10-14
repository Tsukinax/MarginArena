"""The Arena (ADR 0004): AI explores what's open-ended; the engine solves what's closed.

For each invited SKU:
1. Strategists propose Plan Ideas, which are non-numeric.
2. The engine expands every idea into numeric Promo Plans.
3. The engine picks the plan that survives the generic Scenarios.
4. Each round, Rivals red-team the leading plan, and the engine re-selects against every Counter-move found so far.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field

from marginarena.engine import (
    CounterMove,
    GiftWithPurchase,
    PlanIdea,
    PriceCut,
    PromoPlan,
    SellerSettings,
    ShopVoucher,
    SkuVerdict,
    campaign_outcome,
    candidate_plans,
    evaluate_sku,
    rival_effective_price,
)
from marginarena.llm import LLMClient
from marginarena.sample import ElasticityOverride, InvitedSku, Shop

Emit = Callable[[dict], Awaitable[None]]
SKIP_LABEL = "Skip: don't join the Campaign with this product"

STRATEGISTS = (
    ("Margin keeper", "protects profit per unit and joins as lightly as the invitation allows"),
    ("Volume chaser", "wants the Shocking Sale slot to move as many units as possible"),
    ("Brand-safe merchandiser", "keeps brand agreements and prefers vouchers or gifts to deep headline cuts"),
)
RIVALS = (
    ("Undercutter", "cuts its headline price just below the shop"),
    ("Price matcher", "matches the shop's Campaign price exactly"),
    ("Voucher bomber", "keeps its price but stacks a large shop voucher"),
    ("Flash dropper", "runs a short, very deep flash price at midnight"),
    ("Free shipper", "absorbs shipping so buyers pay less in total"),
    ("Gift stacker", "adds a free gift instead of cutting its price"),
)


class IdeaOut(BaseModel):
    use_voucher: bool = False
    gift_sku_id: str | None = None
    why: str = ""


class IdeasOut(BaseModel):
    ideas: list[IdeaOut] = Field(min_length=1, max_length=3)


class MoveOut(BaseModel):
    headline_cut_pct: float = Field(ge=0, le=40)
    voucher_baht: float = Field(default=0, ge=0)
    free_shipping_baht: float = Field(default=0, ge=0, le=60)
    gift_value_baht: float = Field(default=0, ge=0)
    why: str = ""


class MovesOut(BaseModel):
    moves: list[MoveOut] = Field(min_length=1, max_length=2)


async def run_arena(
    shop: Shop, sku_ids: list[str] | None, rounds: int, rivals: int, strategists: int, llm: LLMClient, emit: Emit
) -> dict:
    invited = [i for i in shop.invited if sku_ids is None or i.sku.id in sku_ids]
    await emit(
        {
            "type": "run_started",
            "route": llm.settings.route,
            "model": llm.settings.model,
            "shop": shop.name,
            "label": shop.label,
            "invitation": shop.invitation,
            "skus": [i.sku.id for i in invited],
            "rounds": rounds,
            "rivals": rivals,
            "strategists": strategists,
            "elasticity": shop.elasticity_source,
        }
    )
    results = await asyncio.gather(*(_sku_arena(shop, i, rounds, rivals, strategists, llm, emit) for i in invited))
    done = {
        "type": "run_done",
        "results": results,
        "margin_protected": str(sum((Decimal(r["protected"]) for r in results), Decimal("0"))),
        "telemetry": llm.telemetry.snapshot(),
    }
    await emit(done)
    return done


async def _sku_arena(
    shop: Shop, item: InvitedSku, rounds: int, rivals: int, strategists: int, llm: LLMClient, emit: Emit
) -> dict:
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
    settings = SellerSettings(margin_floor=shop.margin_floor, brand_rules=rules)
    invited_plan = PromoPlan(mechanics=(PriceCut(amount=_satang(sku.list_price * item.required_discount)),))

    ideas = [PlanIdea(), PlanIdea(use_voucher=True)]
    for idea in await _ask_strategists(shop, item, rules, strategists, llm, emit):
        ideas.append(idea)
    plans = candidate_plans(sku, terms, ideas, rules)

    def judge(moves: list[CounterMove]) -> SkuVerdict:
        return evaluate_sku(sku, invited_plan, plans, moves, shop.profile, terms, settings)

    generic = [
        CounterMove(rival="Holder", rival_price_cut=Decimal("0")),
        CounterMove(rival="Matcher", rival_price_cut=item.required_discount),
        CounterMove(rival="Undercutter", rival_price_cut=item.required_discount + Decimal("0.05")),
    ]
    generic_verdict = verdict = judge(generic)
    scenarios = list(generic)
    rounds_played = 0
    for round_no in range(1, rounds + 1):
        leader = (verdict.chosen or verdict.as_invited).plan
        await emit({"type": "round_started", "sku": sku.id, "round": round_no, "leader": _label(leader)})
        found = await _ask_rivals(shop, item, terms, leader, round_no, rivals, llm, emit)
        rounds_played = round_no
        if not found:
            continue
        scenarios.extend(found)
        previous = verdict.chosen.plan if verdict.chosen else None
        verdict = judge(scenarios)
        current = verdict.chosen.plan if verdict.chosen else None
        await emit(
            {
                "type": "leader",
                "sku": sku.id,
                "round": round_no,
                "verdict": verdict.verdict,
                "skip": verdict.skip,
                "plan": _label(current) if current else None,
                "changed": current != previous,
                "telemetry": llm.telemetry.snapshot(),
            }
        )
        if current == previous and round_no > 1:
            break

    # Proof 6 (red-team value): how the engine-only plan fares against every Scenario found.
    generic_before = generic_verdict.chosen or generic_verdict.as_invited
    generic_plan = generic_before.plan
    generic_under_all = evaluate_sku(sku, generic_plan, [], scenarios, shop.profile, terms, settings).as_invited
    chosen = verdict.chosen
    shown = chosen or verdict.as_invited
    kept = chosen.worst_total if chosen else verdict.dont_join_total if verdict.skip else None
    result = {
        "sku": sku.id,
        "name": sku.name,
        "verdict": verdict.verdict,
        "skip": verdict.skip,
        "invited_plan": _label(invited_plan),
        "invited_failed_checks": list(verdict.as_invited.failed_checks),
        "invited_worst_total": str(verdict.as_invited.worst_total),
        "invited_expected_total": str(verdict.as_invited.expected_total),
        "chosen_plan": _label(chosen.plan) if chosen else SKIP_LABEL if verdict.skip else None,
        "chosen_worst_total": str(kept) if kept is not None else None,
        "chosen_expected_total": str(chosen.expected_total) if chosen else None,
        "chosen_worst_margin": str(chosen.worst_margin) if chosen else None,
        "dont_join_total": str(verdict.dont_join_total),
        "invited_worst_margin": str(verdict.as_invited.worst_margin),
        "margin_floor": str(settings.margin_floor),
        # Escalate hands the decision to a person: no Margin Protected and no red-team gain are claimed.
        "protected": str(kept - verdict.as_invited.worst_total) if kept is not None else "0",
        "generic_plan": _label(generic_plan),
        "generic_worst_total": str(generic_before.worst_total),
        "generic_worst_total_all_scenarios": str(generic_under_all.worst_total),
        # How much the Counter-moves the AI Rivals found lower that plan's worst case.
        "red_team_cut": str(generic_before.worst_total - generic_under_all.worst_total),
        "red_team_gain": str(chosen.worst_total - generic_under_all.worst_total) if chosen else None,
        "scenarios": len(scenarios),
        "waterfall": _waterfall(shown.plan, shown.outcomes[0].unit, sku),
        "scenario_grid": [
            {
                "rival": move.rival,
                "effective_rival_price": str(_satang(rival_effective_price(sku, terms, move))),
                "invited_total": str(inv.total_profit),
                "shown_total": str(chosen_outcome.total_profit),
                # The lowest profit for this move across the elasticity band: the worst case comes from these.
                "invited_worst": str(inv_worst),
                "shown_worst": str(shown_worst),
            }
            for move, inv, chosen_outcome, inv_worst, shown_worst in zip(
                scenarios,
                verdict.as_invited.outcomes,
                shown.outcomes,
                verdict.as_invited.worst_by_move,
                shown.worst_by_move,
                strict=True,
            )
        ],
        "evidence": _evidence(shop, item, rules, snapshot, override),
        "rounds_played": rounds_played,
        "plans_searched": len(plans) + 1,
    }
    await emit({"type": "sku_decided", **result})
    return result


async def _ask_strategists(shop, item, rules, count, llm, emit) -> list[PlanIdea]:
    sku = item.sku
    gifts = [shop.catalogue[g] for g in shop.gift_candidates if g != sku.id]
    rule_text = " ".join(shop.brand_rule_texts[r.clause] for r in rules) or "None."
    gift_list = "; ".join(f"{g.id}: {g.name}, ฿{g.list_price}" for g in gifts) or "none"
    user = (
        f"Product: {sku.name} ({sku.brand}), list price ฿{sku.list_price}.\n"
        f"Campaign Invitation: {shop.invitation['campaign']}, at least {_pct(item.required_discount)} off.\n"
        f"Brand agreement: {rule_text}\n"
        f"Catalogue items you may offer as a gift: {gift_list}."
    )
    allowed = {g.id for g in gifts}

    async def ask(name: str, style: str) -> list[PlanIdea]:
        system = (
            f"You are a Strategist for {shop.name}, a Thai online seller preparing for a marketplace Campaign. "
            f"Persona: {name}, who {style}. You propose Plan Ideas: non-numeric choices only. A pricing engine "
            "chooses every number and computes all profit, so never state prices or profit. Reply with JSON only: "
            '{"ideas": [{"use_voucher": true or false, "gift_sku_id": "<catalogue id or null>", '
            '"why": "<one sentence>"}]} with 1 to 3 ideas.'
        )
        out = await llm.json_chat(
            system, user, IdeasOut, accept=lambda o: all(i.gift_sku_id in allowed | {None} for i in o.ideas)
        )
        if out is None:
            return []
        ideas = []
        for idea in out.ideas:
            gift = None
            if idea.gift_sku_id:
                g = shop.catalogue[idea.gift_sku_id]
                gift = GiftWithPurchase(
                    cost=g.cost, perceived_value=_satang(g.list_price * shop.gift_value_ratio), name=g.name
                )
            ideas.append(PlanIdea(use_voucher=idea.use_voucher, gift=gift))
            await emit(
                {
                    "type": "idea",
                    "sku": sku.id,
                    "strategist": name,
                    "use_voucher": idea.use_voucher,
                    "gift": gift.name if gift else None,
                    "why": idea.why,
                }
            )
        return ideas

    batches = await asyncio.gather(*(ask(n, s) for n, s in STRATEGISTS[:count]))
    return [idea for batch in batches for idea in batch]


async def _ask_rivals(shop, item, terms, leader, round_no, count, llm, emit) -> list[CounterMove]:
    sku = item.sku
    reference = terms.rival_reference_price or sku.list_price
    snapshot = shop.rival_snapshot.get(sku.id)
    rival_product = snapshot.rival if snapshot else f"a lookalike of {sku.name}"
    offer = campaign_outcome(sku, leader, shop.profile, terms).unit
    user = (
        f"Your product: {rival_product}, usual price ฿{reference}.\n"
        f"The shop's leading 11.11 offer for {sku.name}: shelf price ฿{offer.selling_price}, "
        f"buyers pay ฿{offer.seller_net} after shop vouchers ({_label(leader)}).\n"
        f"Round {round_no}: find the Counter-move that hurts this offer most while staying realistic for a seller."
    )

    async def ask(name: str, style: str) -> list[CounterMove]:
        system = (
            "You are a Rival seller on Shopee Thailand with a lookalike product. "
            f"Persona: {name}, who {style}. Reply with JSON only: "
            '{"moves": [{"headline_cut_pct": <0-40>, "voucher_baht": <number>, "free_shipping_baht": <0-60>, '
            '"gift_value_baht": <number>, "why": "<one sentence>"}]} with 1 or 2 moves. '
            "Vouchers may be at most 20% and gifts at most 25% of your usual price."
        )
        out = await llm.json_chat(
            system,
            user,
            MovesOut,
            accept=lambda o: all(
                m.voucher_baht <= float(reference) * 0.20 and m.gift_value_baht <= float(reference) * 0.25
                for m in o.moves
            ),
        )
        if out is None:
            return []
        moves = []
        for m in out.moves:
            move = CounterMove(
                rival=name,
                rival_price_cut=_decimal(m.headline_cut_pct) / 100,
                voucher=_decimal(m.voucher_baht),
                free_shipping=_decimal(m.free_shipping_baht),
                gift_value=_decimal(m.gift_value_baht),
            )
            moves.append(move)
            await emit(
                {
                    "type": "rival_move",
                    "sku": sku.id,
                    "round": round_no,
                    "rival": name,
                    "headline_cut_pct": m.headline_cut_pct,
                    "voucher_baht": m.voucher_baht,
                    "free_shipping_baht": m.free_shipping_baht,
                    "gift_value_baht": m.gift_value_baht,
                    "effective_rival_price": str(_satang(rival_effective_price(sku, terms, move))),
                    "why": m.why,
                }
            )
        return moves

    batches = await asyncio.gather(*(ask(n, s) for n, s in RIVALS[:count]))
    return [move for batch in batches for move in batch]


def _waterfall(plan: PromoPlan, unit, sku) -> dict:
    return {
        "plan": _label(plan),
        "list_price": str(sku.list_price),
        "selling_price": str(unit.selling_price),
        "voucher": str(unit.selling_price - unit.seller_net),
        "seller_net": str(unit.seller_net),
        "fees": {
            "commission": str(unit.fees.commission),
            "payment": str(unit.fees.payment),
            "programme": str(unit.fees.programme),
            "fixed": str(unit.fees.fixed),
            "total": str(unit.fees.total),
        },
        "unit_cost": str(unit.unit_cost),
        "profit": str(unit.unit_profit),
        "margin": str(unit.margin),
    }


def _evidence(shop: Shop, item: InvitedSku, rules, snapshot, override: ElasticityOverride | None) -> list[dict]:
    """Evidence Links: where each input behind this SKU's numbers came from."""
    p = shop.profile
    links = [
        {
            "kind": "invitation",
            "text": f"{shop.invitation['campaign']} asks for at least {_pct(item.required_discount)} "
            f"off {item.sku.name}.",
            "source": f"Campaign Invitation, {shop.invitation['marketplace']} (sample)",
        },
        {
            "kind": "fees",
            "text": f"Commission {_pct(p.commission_rate)}, payment {_pct(p.payment_fee_rate)}, programme "
            f"{_pct(p.programme_fee_rate)} and ฿{p.fixed_fee_per_order} per order, plus {_pct(p.vat_rate)} VAT.",
            "source": f"Marketplace Profile {p.id}, effective {p.effective_from}",
        },
        {"kind": "elasticity", "text": override.text, "source": override.source}
        if override
        else {"kind": "elasticity", "text": shop.elasticity_source, "source": "evidence/elasticity.md"},
        {
            "kind": "rival_snapshot",
            "text": f"{snapshot.rival} at ฿{snapshot.reference_price}."
            if snapshot
            else "No Rival Snapshot for this product: the rival's price is assumed equal to your list price.",
            "source": "Rival Snapshot (sample)" if snapshot else "Assumption",
        },
        {
            "kind": "assumption",
            "text": f"Campaign traffic x{shop.terms.traffic_lift}; rival sensitivity "
            f"{shop.terms.cross_price_sensitivity}; a gift is valued at {_pct(shop.gift_value_ratio)} "
            "of its retail price.",
            "source": "Sample-shop assumptions (overridable)",
        },
    ]
    links += [{"kind": "brand_rule", "text": shop.brand_rule_texts[r.clause], "source": r.clause} for r in rules]
    return links


def _label(plan: PromoPlan) -> str:
    parts = []
    for m in plan.mechanics:
        if isinstance(m, PriceCut):
            parts.append(f"฿{m.amount} off")
        elif isinstance(m, ShopVoucher):
            parts.append(f"฿{m.amount} voucher")
        elif isinstance(m, GiftWithPurchase):
            parts.append(f"gift: {m.name or 'item'}")
    return " + ".join(parts) or "no promotion"


def _satang(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _decimal(x: float) -> Decimal:
    return Decimal(str(round(x, 2)))


def _pct(x: Decimal) -> str:
    return f"{(x * 100).normalize():f}%"  # ":f" keeps 20 from printing as 2E+1
