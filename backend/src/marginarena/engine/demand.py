"""Campaign demand and profit for one Promo Plan."""

import math
from decimal import Decimal

from .fees import unit_economics
from .model import GiftWithPurchase, CampaignOutcome, CampaignTerms, CounterMove, MarketplaceProfile, PromoPlan, Sku


def campaign_outcome(
    sku: Sku,
    plan: PromoPlan,
    profile: MarketplaceProfile,
    terms: CampaignTerms,
    counter_move: CounterMove | None = None,
) -> CampaignOutcome:
    if sku.elasticity is None:
        raise ValueError(f"SKU {sku.id} has no elasticity")
    unit = unit_economics(sku, plan, profile, terms)
    gift_value = sum((m.perceived_value for m in plan.mechanics if isinstance(m, GiftWithPurchase)), Decimal("0"))
    # Buyers respond to what they pay, less what they believe the gift is worth.
    buyer_price = unit.seller_net - terms.platform_funded_discount - gift_value
    # Elasticity is applied to price cuts only: the fitted model is unreliable when prices rise.
    ratio = min(1.0, float(buyer_price / sku.list_price))
    retained = 1.0
    if counter_move is not None:
        retained = (1.0 - float(counter_move.rival_price_cut)) ** float(terms.cross_price_sensitivity)
    demand = sku.baseline_units * float(terms.traffic_lift) * ratio ** float(sku.elasticity) * retained
    units = min(sku.stock, math.floor(demand))
    return CampaignOutcome(unit=unit, units=units, total_profit=unit.unit_profit * units)
