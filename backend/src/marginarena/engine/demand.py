"""Campaign demand and profit for one Promo Plan."""

import math
from decimal import Decimal

from .fees import unit_economics
from .model import CampaignOutcome, CampaignTerms, MarketplaceProfile, PromoPlan, Sku


def campaign_outcome(sku: Sku, plan: PromoPlan, profile: MarketplaceProfile, terms: CampaignTerms) -> CampaignOutcome:
    if sku.elasticity is None:
        raise ValueError(f"SKU {sku.id} has no elasticity")
    unit = unit_economics(sku, plan, profile, terms)
    buyer_price = unit.seller_net - terms.platform_funded_discount
    # Elasticity is applied to price cuts only: the fitted model is unreliable when prices rise.
    ratio = min(1.0, float(buyer_price / sku.list_price))
    demand = sku.baseline_units * float(terms.traffic_lift) * ratio ** float(sku.elasticity)
    units = min(sku.stock, math.floor(demand))
    return CampaignOutcome(unit=unit, units=units, total_profit=unit.unit_profit * units)
