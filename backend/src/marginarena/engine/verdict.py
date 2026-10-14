"""Robust selection of a Promo Plan and the Verdict for one invited SKU."""

from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

from .demand import campaign_outcome
from .model import (
    BrandPriceRule,
    CampaignTerms,
    CounterMove,
    GiftWithPurchase,
    InvitationItem,
    InvitationResult,
    MarketplaceProfile,
    Mechanic,
    PlanEvaluation,
    PriceCut,
    PromoPlan,
    SellerSettings,
    ShopVoucher,
    Sku,
    SkuVerdict,
)


def evaluate_sku(
    sku: Sku,
    as_invited: PromoPlan,
    candidates: list[PromoPlan],
    counter_moves: tuple[CounterMove, ...] | list[CounterMove],
    profile: MarketplaceProfile,
    terms: CampaignTerms,
    settings: SellerSettings,
) -> SkuVerdict:
    moves = list(counter_moves) or [None]
    # Rivals act whether or not the Seller joins, so not joining faces the same Counter-moves (ADR 0004).
    no_campaign = replace(
        terms, traffic_lift=Decimal("1"), required_discount=Decimal("0"), platform_funded_discount=Decimal("0")
    )
    dont_join_total = min(campaign_outcome(sku, PromoPlan(), profile, no_campaign, cm).total_profit for cm in moves)
    band_skus = [replace(sku, elasticity=e) for e in (terms.elasticity_band or ())]

    def evaluate(plan: PromoPlan) -> PlanEvaluation:
        outcomes = tuple(campaign_outcome(sku, plan, profile, terms, cm) for cm in moves)
        scenarios = outcomes + tuple(campaign_outcome(b, plan, profile, terms, cm) for b in band_skus for cm in moves)
        worst_margin = min(o.unit.margin for o in scenarios)
        worst_total = min(o.total_profit for o in scenarios)
        expected_total = (sum(o.total_profit for o in outcomes) / len(outcomes)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        price_cut = sum((m.amount for m in plan.mechanics if isinstance(m, PriceCut)), Decimal("0"))
        failed: list[str] = []
        if price_cut < terms.required_discount * sku.list_price:
            failed.append("below the invited discount")
        if worst_margin < settings.margin_floor:
            failed.append("below the Margin Floor")
        if worst_total < dont_join_total:
            failed.append("earns less than not joining")
        failed += [
            f"breaks {r.clause}"
            for r in settings.brand_rules
            if r.binds(sku) and _breaks(r, sku, price_cut, plan.mechanics)
        ]
        return PlanEvaluation(plan, outcomes, worst_margin, worst_total, expected_total, tuple(failed))

    invited = evaluate(as_invited)
    others = tuple(evaluate(p) for p in candidates)
    eligible = [e for e in (invited, *others) if e.eligible]
    # Maximin (Q52): the plan whose worst case is best wins; expected profit only breaks ties.
    best = max(eligible, key=lambda e: (e.worst_total, e.expected_total), default=None)

    if best is None:
        verdict, chosen = "escalate", None
    elif invited.eligible and best.worst_total - invited.worst_total <= settings.approve_tolerance * abs(
        invited.worst_total
    ):
        verdict, chosen = "approve", invited
    else:
        verdict, chosen = "revise", best
    return SkuVerdict(sku, verdict, chosen, invited, others, dont_join_total)


def evaluate_invitation(
    items: list[InvitationItem],
    counter_moves: tuple[CounterMove, ...] | list[CounterMove],
    profile: MarketplaceProfile,
    terms: CampaignTerms,
    settings: SellerSettings,
) -> InvitationResult:
    verdicts = tuple(
        evaluate_sku(
            item.sku,
            item.as_invited,
            item.candidates,
            item.counter_moves or counter_moves,
            profile,
            replace(terms, required_discount=item.required_discount),
            settings,
        )
        for item in items
    )
    # Escalate hands the decision to a person, so it counts toward neither side.
    protected = sum((v.chosen.worst_total - v.as_invited.worst_total for v in verdicts if v.chosen), Decimal("0"))
    return InvitationResult(verdicts=verdicts, margin_protected=protected)


def _breaks(rule: BrandPriceRule, sku: Sku, price_cut: Decimal, mechanics: tuple[Mechanic, ...]) -> bool:
    if rule.max_price_cut is not None and price_cut > rule.max_price_cut * sku.list_price:
        return True
    if rule.min_shelf_price is not None and sku.list_price - price_cut < rule.min_shelf_price:
        return True
    if not rule.vouchers_allowed and any(isinstance(m, ShopVoucher) for m in mechanics):
        return True
    return not rule.gifts_allowed and any(isinstance(m, GiftWithPurchase) for m in mechanics)
