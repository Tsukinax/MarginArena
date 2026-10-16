"""Golden fee cases: Lazada's published worked example, and a Shopee example worked by hand from Shopee's
published rates (Shopee publishes no worked example).

Sources: .scratch/marginarena/research/marketplace-fees.md, sections 2.1 and 4.
"""

from decimal import Decimal

from marginarena.engine import (
    CampaignTerms,
    PriceCut,
    PromoPlan,
    ShopVoucher,
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


def test_shopee_nonmall_prime_example_with_seller_voucher_pays_out_200_31():
    # Shopee TH Non-Mall PRIME (FMCG, 4 Aug 2026 rates): lists at ฿399, Campaign price ฿299,
    # a ฿20 shop voucher is used, and Shopee co-funds a ฿10 discount.
    sku = Sku(id="SP-EX", name="Shopee example item", list_price=Decimal("399"), cost=Decimal("0"))
    plan = PromoPlan(mechanics=(PriceCut(amount=Decimal("100")), ShopVoucher(amount=Decimal("20"))))
    terms = CampaignTerms(platform_funded_discount=Decimal("10"))

    result = unit_economics(sku, plan, get_profile("shopee-th-nonmall-prime-fmcg"), terms)

    assert result.fees.commission == Decimal("44.78")
    assert result.fees.programme == Decimal("23.88")
    assert result.fees.payment == Decimal("8.96")
    assert result.fees.fixed == Decimal("1.07")
    assert result.fees.total == Decimal("78.69")
    assert result.payout == Decimal("200.31")
