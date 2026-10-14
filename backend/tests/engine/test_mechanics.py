"""Promo Mechanics beyond a plain price cut. Hand-worked numbers, Shopee TH Non-Mall PRIME fees."""

from decimal import Decimal

from marginarena.engine import (
    CampaignTerms,
    GiftWithPurchase,
    PriceCut,
    PromoPlan,
    ShopVoucher,
    Sku,
    campaign_outcome,
    get_profile,
)

SHOPEE = get_profile("shopee-th-nonmall-prime-fmcg")
ITEM = Sku(
    id="FMCG-100",
    name="฿100 item costing ฿50",
    list_price=Decimal("100"),
    cost=Decimal("50"),
    stock=1000,
    baseline_units=100,
    elasticity=Decimal("-1.52"),
)
DOUBLE_TRAFFIC = CampaignTerms(traffic_lift=Decimal("2"))


def test_gift_costs_the_seller_but_lifts_demand_by_its_perceived_value():
    # 20% off plus a ฿8 gift that buyers value at ฿15: profit 6.67 - 8 = -1.33 a unit;
    # demand responds to an effective ฿65 price: 100 x 2 x 0.65^-1.52 = 384.96 -> 384 units.
    plan = PromoPlan(
        mechanics=(PriceCut(amount=Decimal("20")), GiftWithPurchase(cost=Decimal("8"), perceived_value=Decimal("15")))
    )

    outcome = campaign_outcome(ITEM, plan, SHOPEE, DOUBLE_TRAFFIC)

    assert outcome.unit.fees.total == Decimal("23.33")
    assert outcome.unit.unit_profit == Decimal("-1.33")
    assert outcome.units == 384
    assert outcome.total_profit == Decimal("-510.72")


def test_voucher_below_its_minimum_spend_is_not_used():
    # A ฿10 voucher with a ฿100 minimum spend can't be used on an ฿80 single-unit order.
    plan = PromoPlan(mechanics=(PriceCut(amount=Decimal("20")), ShopVoucher(amount=Decimal("10"), min_spend=Decimal("100"))))

    outcome = campaign_outcome(ITEM, plan, SHOPEE, DOUBLE_TRAFFIC)

    assert outcome.unit.seller_net == Decimal("80")
    assert outcome.units == 280
