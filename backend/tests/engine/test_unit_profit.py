"""Unit profit and margin after fees and product cost.

Expected values come from the pitch worked example in
.scratch/marginarena/research/thai-seller-market.md (Shopee TH Non-Mall PRIME, 2026 fees).
"""

from decimal import Decimal

from marginarena.engine import CampaignTerms, PriceCut, PromoPlan, Sku, get_profile, unit_economics

SHOPEE = get_profile("shopee-th-nonmall-prime-fmcg")
ITEM = Sku(id="FMCG-100", name="฿100 item costing ฿50", list_price=Decimal("100"), cost=Decimal("50"))


def test_full_price_item_earns_21_11_per_unit():
    result = unit_economics(ITEM, PromoPlan(), SHOPEE, CampaignTerms())

    assert result.unit_profit == Decimal("21.11")
    assert result.margin == Decimal("0.2111")


def test_twenty_percent_off_leaves_6_67_per_unit():
    result = unit_economics(ITEM, PromoPlan(mechanics=(PriceCut(amount=Decimal("20")),)), SHOPEE, CampaignTerms())

    assert result.unit_profit == Decimal("6.67")
    assert result.margin == Decimal("0.0834")


def test_thirty_percent_off_loses_0_55_per_unit():
    # README's third figure: at ฿70 the fees come to ฿20.55, more than the ฿20 left after the ฿50 cost.
    result = unit_economics(ITEM, PromoPlan(mechanics=(PriceCut(amount=Decimal("30")),)), SHOPEE, CampaignTerms())

    assert result.unit_profit == Decimal("-0.55")
    assert result.margin == Decimal("-0.0079")
