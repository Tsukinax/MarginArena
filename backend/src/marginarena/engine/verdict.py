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
    dont_join = [campaign_outcome(sku, PromoPlan(), profile, no_campaign, cm).total_profit for cm in moves]
    dont_join_total = min(dont_join)
    dont_join_expected = _mean(dont_join)
    band_skus = [replace(sku, elasticity=e) for e in (terms.elasticity_band or ())]

    def evaluate(plan: PromoPlan) -> PlanEvaluation:
        outcomes = tuple(campaign_outcome(sku, plan, profile, terms, cm) for cm in moves)
        edges = [tuple(campaign_outcome(b, plan, profile, terms, cm) for cm in moves) for b in band_skus]
        scenarios = outcomes + tuple(o for edge in edges for o in edge)
        worst_by_move = tuple(min(o.total_profit for o in move) for move in zip(outcomes, *edges, strict=True))
        worst_margin = min(o.unit.margin for o in scenarios)
        worst_total = min(o.total_profit for o in scenarios)
        expected_total = _mean([o.total_profit for o in outcomes])
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
        return PlanEvaluation(plan, outcomes, worst_margin, worst_total, expected_total, tuple(failed), worst_by_move)

    invited = evaluate(as_invited)
    others = tuple(evaluate(p) for p in candidates)
    eligible = [e for e in (invited, *others) if e.eligible]
    # Maximin (Q52): the plan whose worst case is best wins; expected profit only breaks ties.
    best = max(eligible, key=lambda e: (e.worst_total, e.expected_total), default=None)

    skip = False
    if best is None:
        # Feasible plans meet the invitation and every Brand Price Rule; only their economics failed. Skip only
        # when not joining wins in the worst case and in expectation; otherwise uncertainty decides, so escalate.
        feasible = [e for e in (invited, *others) if not any(_is_rule_failure(f) for f in e.failed_checks)]
        skip = bool(feasible) and all(
            e.worst_total < dont_join_total and e.expected_total < dont_join_expected for e in feasible
        )
        verdict, chosen = ("revise" if skip else "escalate"), None
    elif invited.eligible and best.worst_total - invited.worst_total <= settings.approve_tolerance * abs(
        invited.worst_total
    ):
        verdict, chosen = "approve", invited
    else:
        verdict, chosen = "revise", best
    return SkuVerdict(sku, verdict, chosen, invited, others, dont_join_total, skip)


def _is_rule_failure(check: str) -> bool:
    return check == "below the invited discount" or check.startswith("breaks ")


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
    protected = sum((_kept(v) - v.as_invited.worst_total for v in verdicts if v.chosen or v.skip), Decimal("0"))
    return InvitationResult(verdicts=verdicts, margin_protected=protected)


def _breaks(rule: BrandPriceRule, sku: Sku, price_cut: Decimal, mechanics: tuple[Mechanic, ...]) -> bool:
    if rule.max_price_cut is not None and price_cut > rule.max_price_cut * sku.list_price:
        return True
    if rule.min_shelf_price is not None and sku.list_price - price_cut < rule.min_shelf_price:
        return True
    if not rule.vouchers_allowed and any(isinstance(m, ShopVoucher) for m in mechanics):
        return True
    return not rule.gifts_allowed and any(isinstance(m, GiftWithPurchase) for m in mechanics)


def _kept(v: SkuVerdict) -> Decimal:
    """Worst-case profit of following a decided Verdict: the chosen plan, or not joining for a Skip."""
    return v.chosen.worst_total if v.chosen else v.dont_join_total


def _mean(values: list[Decimal]) -> Decimal:
    return (sum(values, Decimal("0")) / len(values)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
