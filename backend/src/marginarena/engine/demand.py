"""Campaign demand and profit for one Promo Plan."""

import math
from decimal import Decimal

from .fees import unit_economics
from .model import CampaignOutcome, CampaignTerms, CounterMove, GiftWithPurchase, MarketplaceProfile, PromoPlan, Sku


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
    if buyer_price <= 0:
        raise ValueError(f"Promo Plan gives {sku.id} away: effective buyer price {buyer_price}")
    retained = 1.0
    if counter_move is not None:
        rival_price = rival_effective_price(sku, terms, counter_move)
        # ADR 0004: shoppers compare lookalikes, so we lose demand only to a Rival that ends up cheaper.
        if buyer_price > rival_price:
            retained = float(rival_price / buyer_price) ** float(terms.cross_price_sensitivity)
    demand = sku.baseline_units * float(terms.traffic_lift) * ratio ** float(sku.elasticity) * retained
    units = min(sku.stock, math.floor(demand))
    return CampaignOutcome(unit=unit, units=units, total_profit=unit.unit_profit * units)


MAX_RIVAL_CUT = Decimal("0.6")


def rival_effective_price(sku: Sku, terms: CampaignTerms, move: CounterMove) -> Decimal:
    """The Rival's price after its Counter-move, with vouchers, free shipping and gifts counted as a cut."""
    reference = terms.rival_reference_price or sku.list_price
    extras = move.voucher + move.free_shipping + move.gift_value
    cut = min(MAX_RIVAL_CUT, move.rival_price_cut + extras / reference)
    return reference * (1 - cut)
