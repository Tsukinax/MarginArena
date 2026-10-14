"""Brand Price Rules: a plan that breaks a brand's pricing clause can never be approved."""

from decimal import Decimal

from marginarena.engine import (
    BrandPriceRule,
    CampaignTerms,
    CounterMove,
    PriceCut,
    PromoPlan,
    SellerSettings,
    ShopVoucher,
    Sku,
    evaluate_sku,
    get_profile,
)

SHOPEE = get_profile("shopee-th-nonmall-prime-fmcg")
RIVALS = (CounterMove(rival="Holder", rival_price_cut=Decimal("0")),)
ITEM = Sku(
    id="T-1",
    name="test item",
    list_price=Decimal("100"),
    cost=Decimal("30"),
    stock=1000,
    baseline_units=100,
    elasticity=Decimal("-2.8"),
)
MAX_15_OFF = BrandPriceRule(clause="Brand agreement 4.2", max_price_cut=Decimal("0.15"))


def test_plan_cutting_deeper_than_the_brand_allows_is_never_chosen():
    # 25% off would earn the most, but clause 4.2 caps the headline cut at 15%.
    terms = CampaignTerms(traffic_lift=Decimal("2"), required_discount=Decimal("0.15"))

    result = evaluate_sku(
        ITEM,
        PromoPlan(mechanics=(PriceCut(amount=Decimal("15")),)),
        [PromoPlan(mechanics=(PriceCut(amount=Decimal("25")),))],
        RIVALS,
        SHOPEE,
        terms,
        SellerSettings(margin_floor=Decimal("0.10"), brand_rules=(MAX_15_OFF,)),
    )

    assert result.verdict == "approve"
    deeper = result.candidates[0]
    assert deeper.eligible is False
    assert "breaks Brand agreement 4.2" in deeper.failed_checks


def test_invitation_that_demands_more_than_the_brand_allows_escalates():
    terms = CampaignTerms(traffic_lift=Decimal("2"), required_discount=Decimal("0.20"))

    result = evaluate_sku(
        ITEM,
        PromoPlan(mechanics=(PriceCut(amount=Decimal("20")),)),
        [PromoPlan(mechanics=(PriceCut(amount=Decimal("15")), ShopVoucher(amount=Decimal("10"))))],
        RIVALS,
        SHOPEE,
        terms,
        SellerSettings(margin_floor=Decimal("0.10"), brand_rules=(MAX_15_OFF,)),
    )

    assert result.verdict == "escalate"
    assert "breaks Brand agreement 4.2" in result.as_invited.failed_checks
    assert "below the invited discount" in result.candidates[0].failed_checks


def test_a_brand_rule_only_binds_that_brands_products():
    # The cap belongs to HydraLab; this item is the shop's own label, so the 25% plan stays eligible.
    own_label = Sku(
        id="T-2",
        name="own-label item",
        list_price=Decimal("100"),
        cost=Decimal("30"),
        stock=1000,
        baseline_units=100,
        elasticity=Decimal("-2.8"),
        brand="Glow Lab",
    )
    hydralab_cap = BrandPriceRule(clause="HydraLab agreement 4.2", max_price_cut=Decimal("0.15"), brand="HydraLab")
    terms = CampaignTerms(traffic_lift=Decimal("2"), required_discount=Decimal("0.15"))

    result = evaluate_sku(
        own_label,
        PromoPlan(mechanics=(PriceCut(amount=Decimal("15")),)),
        [PromoPlan(mechanics=(PriceCut(amount=Decimal("25")),))],
        RIVALS,
        SHOPEE,
        terms,
        SellerSettings(margin_floor=Decimal("0.10"), brand_rules=(hydralab_cap,)),
    )

    assert result.candidates[0].failed_checks == ()
