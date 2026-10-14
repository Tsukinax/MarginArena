"""Golden fee cases from the marketplaces' own published worked examples.

Sources: .scratch/marginarena/research/marketplace-fees.md, sections 2.1 and 4.
"""

from decimal import Decimal

from marginarena.engine import (
    CampaignTerms,
    PriceCut,
    PromoPlan,
    Sku,
    get_profile,
    unit_economics,
)


def test_lazada_official_lazmall_example_pays_out_623_93():
    # Lazada's worked example (LazMall, Beauty, rates from 1 Aug 2026): item ฿1,000,
    # seller discount ฿100, buyer pays ฿50 shipping, platform-funded voucher ฿180,
    # Seller in the Premium Package.
    sku = Sku(id="LZ-EX", name="Lazada example item", list_price=Decimal("1000"), cost=Decimal("0"))
    plan = PromoPlan(mechanics=(PriceCut(amount=Decimal("100")),))
    terms = CampaignTerms(platform_funded_discount=Decimal("180"), buyer_paid_shipping=Decimal("50"))

    result = unit_economics(sku, plan, get_profile("lazada-th-lazmall-beauty"), terms)

    assert result.fees.payment == Decimal("30.50")
    assert result.fees.commission == Decimal("168.53")
    assert result.fees.programme == Decimal("77.04")
    assert result.fees.total == Decimal("276.07")
    assert result.payout == Decimal("623.93")
