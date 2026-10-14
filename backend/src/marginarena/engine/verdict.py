"""Robust selection of a Promo Plan and the Verdict for one invited SKU."""

from decimal import ROUND_HALF_UP, Decimal

from .demand import campaign_outcome
from .model import (
    CampaignTerms,
    CounterMove,
    MarketplaceProfile,
    PlanEvaluation,
    PriceCut,
    PromoPlan,
    SellerSettings,
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
    no_campaign = CampaignTerms(cross_price_sensitivity=terms.cross_price_sensitivity)
    dont_join_total = campaign_outcome(sku, PromoPlan(), profile, no_campaign).total_profit

    def evaluate(plan: PromoPlan) -> PlanEvaluation:
        outcomes = tuple(campaign_outcome(sku, plan, profile, terms, cm) for cm in counter_moves)
        worst_margin = min(o.unit.margin for o in outcomes)
        worst_total = min(o.total_profit for o in outcomes)
        expected_total = (sum(o.total_profit for o in outcomes) / len(outcomes)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        price_cut = sum((m.amount for m in plan.mechanics if isinstance(m, PriceCut)), Decimal("0"))
        meets_invitation = price_cut >= terms.required_discount * sku.list_price
        eligible = meets_invitation and worst_margin >= settings.margin_floor and worst_total >= dont_join_total
        return PlanEvaluation(plan, outcomes, meets_invitation, worst_margin, worst_total, expected_total, eligible)

    invited = evaluate(as_invited)
    others = tuple(evaluate(p) for p in candidates)
    eligible = [e for e in (invited, *others) if e.eligible]
    best = max(eligible, key=lambda e: e.expected_total, default=None)

    if best is None:
        verdict, chosen = "escalate", None
    elif invited.eligible and best.expected_total - invited.expected_total <= settings.approve_tolerance * abs(
        invited.expected_total
    ):
        verdict, chosen = "approve", invited
    else:
        verdict, chosen = "revise", best
    return SkuVerdict(sku, verdict, chosen, invited, others, dont_join_total)
