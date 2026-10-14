"""Verdicts for one invited SKU: Approve, Revise or Escalate.

A Promo Plan is eligible only if it meets the invited discount, keeps the Margin Floor against
every Counter-move, and its worst-case Campaign profit is at least the "don't join" baseline.
The best eligible plan by expected profit (mean over Counter-moves) wins.
Expected numbers were worked by hand (Shopee TH Non-Mall PRIME fees).
"""

from decimal import Decimal

from marginarena.engine import (
    CampaignTerms,
    CounterMove,
    PriceCut,
    PromoPlan,
    SellerSettings,
    Sku,
    evaluate_sku,
    get_profile,
)

SHOPEE = get_profile("shopee-th-nonmall-prime-fmcg")
RIVALS = (
    CounterMove(rival="Holder", rival_price_cut=Decimal("0")),
    CounterMove(rival="Undercutter", rival_price_cut=Decimal("0.10")),
)


def cut(baht: str) -> PromoPlan:
    return PromoPlan(mechanics=(PriceCut(amount=Decimal(baht)),))


def sku(cost: str, elasticity: str) -> Sku:
    return Sku(
        id="T-1",
        name="test item",
        list_price=Decimal("100"),
        cost=Decimal(cost),
        stock=1000,
        baseline_units=100,
        elasticity=Decimal(elasticity),
    )


def test_approve_when_joining_as_invited_is_safe_and_nothing_beats_it():
    terms = CampaignTerms(traffic_lift=Decimal("3"), required_discount=Decimal("0.20"))

    result = evaluate_sku(
        sku("50", "-1.52"), cut("20"), [cut("25")], RIVALS, SHOPEE, terms, SellerSettings(margin_floor=Decimal("0.05"))
    )

    assert result.verdict == "approve"
    assert result.chosen.plan == cut("20")
    assert result.as_invited.worst_margin == Decimal("0.0834")
    assert result.as_invited.worst_total == Decimal("2634.65")
    assert result.as_invited.expected_total == Decimal("2721.36")


def test_revise_when_a_deeper_cut_earns_clearly_more_on_an_elastic_sku():
    terms = CampaignTerms(traffic_lift=Decimal("2"), required_discount=Decimal("0.15"))

    result = evaluate_sku(
        sku("30", "-2.8"), cut("15"), [cut("25")], RIVALS, SHOPEE, terms, SellerSettings(margin_floor=Decimal("0.10"))
    )

    assert result.verdict == "revise"
    assert result.chosen.plan == cut("25")
    assert result.chosen.worst_total == Decimal("9685.20")
    assert result.chosen.expected_total == Decimal("9996.51")
    assert result.as_invited.expected_total == Decimal("9235.40")


def test_escalate_when_no_plan_keeps_the_margin_floor():
    terms = CampaignTerms(traffic_lift=Decimal("3"), required_discount=Decimal("0.20"))

    result = evaluate_sku(
        sku("50", "-1.52"), cut("20"), [cut("25")], RIVALS, SHOPEE, terms, SellerSettings(margin_floor=Decimal("0.10"))
    )

    assert result.verdict == "escalate"
    assert result.chosen is None
    assert result.dont_join_total == Decimal("2111.00")


def test_plans_below_the_invited_discount_are_never_eligible():
    # A 10% cut would keep the floor, but the Campaign asks for 20%, so it can't win.
    terms = CampaignTerms(traffic_lift=Decimal("3"), required_discount=Decimal("0.20"))

    result = evaluate_sku(
        sku("50", "-1.52"), cut("20"), [cut("10")], RIVALS, SHOPEE, terms, SellerSettings(margin_floor=Decimal("0.10"))
    )

    assert result.verdict == "escalate"
