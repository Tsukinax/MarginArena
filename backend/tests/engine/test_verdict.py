"""Verdicts for one invited SKU: Approve, Revise or Escalate.

A Promo Plan is eligible only if it meets the invited discount, keeps the Margin Floor, and its
worst-case Campaign profit over every Scenario is at least the worst case of not joining under the
same Scenarios (ADR 0004). The eligible plan with the best worst-case profit wins (maximin, Q52); expected
profit (mean over Counter-moves at the point elasticity) only breaks ties. Expected numbers were worked
by hand (Shopee TH Non-Mall PRIME fees, k = 1).
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
HOLDER = CounterMove(rival="Holder", rival_price_cut=Decimal("0"))
DEEP_UNDERCUT = CounterMove(rival="Deep undercutter", rival_price_cut=Decimal("0.30"))
MATCHER = CounterMove(rival="Matcher", rival_price_cut=Decimal("0.20"))
RIVALS = (HOLDER, DEEP_UNDERCUT)


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


def terms(lift: str, required: str, band: tuple[Decimal, Decimal] | None = None) -> CampaignTerms:
    return CampaignTerms(
        traffic_lift=Decimal(lift),
        required_discount=Decimal(required),
        cross_price_sensitivity=Decimal("1"),
        elasticity_band=band,
    )


def floor(pct: str) -> SellerSettings:
    return SellerSettings(margin_floor=Decimal(pct))


def test_approve_when_joining_as_invited_is_safe_and_nothing_beats_it():
    result = evaluate_sku(sku("50", "-1.52"), cut("20"), [cut("25")], RIVALS, SHOPEE, terms("3", "0.20"), floor("0.05"))

    assert result.verdict == "approve"
    assert result.chosen.plan == cut("20")
    assert result.as_invited.worst_margin == Decimal("0.0834")
    assert result.as_invited.worst_total == Decimal("2454.56")
    assert result.as_invited.expected_total == Decimal("2631.32")
    assert result.dont_join_total == Decimal("1477.70")


def test_revise_when_a_deeper_cut_earns_clearly_more_on_an_elastic_sku():
    result = evaluate_sku(sku("30", "-2.8"), cut("15"), [cut("25")], RIVALS, SHOPEE, terms("2", "0.15"), floor("0.10"))

    assert result.verdict == "revise"
    assert result.chosen.plan == cut("25")
    assert result.chosen.worst_total == Decimal("9616.02")
    assert result.chosen.expected_total == Decimal("9961.92")
    assert result.as_invited.expected_total == Decimal("8690.36")


def test_escalate_when_no_plan_keeps_the_margin_floor():
    result = evaluate_sku(sku("50", "-1.52"), cut("20"), [cut("25")], RIVALS, SHOPEE, terms("3", "0.20"), floor("0.10"))

    assert result.verdict == "escalate"
    assert result.chosen is None


def test_plans_below_the_invited_discount_are_never_eligible():
    # A 10% cut would keep the floor, but the Campaign asks for 20%, so it can't win.
    result = evaluate_sku(sku("50", "-1.52"), cut("20"), [cut("10")], RIVALS, SHOPEE, terms("3", "0.20"), floor("0.10"))

    assert result.verdict == "escalate"


def test_a_rival_counter_move_can_flip_approve_into_revise():
    # Holding rivals: 15% off earns 9,538.20 and 20% off 9,947.91, within the 5% tolerance -> approve.
    # A rival matching 20% (฿80) undercuts our ฿85 but not ฿80: 15% falls to 9,250.54 expected -> revise to 20%.
    args = (sku("30", "-2.8"), cut("15"), [cut("20")])

    calm = evaluate_sku(*args, (HOLDER,), SHOPEE, terms("2", "0.15"), floor("0.10"))
    contested = evaluate_sku(*args, (HOLDER, MATCHER), SHOPEE, terms("2", "0.15"), floor("0.10"))

    assert calm.verdict == "approve"
    assert contested.verdict == "revise"
    assert contested.chosen.plan == cut("20")
    assert contested.as_invited.expected_total == Decimal("9250.54")


def test_plan_must_survive_the_weak_end_of_the_elasticity_band():
    # Point elasticity -1.52: 350 units, 2,334.50 >= not joining 2,111.00. At -0.77 only 296 units, 1,974.32.
    args = (sku("50", "-1.52"), cut("20"), [], (HOLDER,), SHOPEE)

    point_only = evaluate_sku(*args, terms("2.5", "0.20"), floor("0.05"))
    with_band = evaluate_sku(*args, terms("2.5", "0.20", band=(Decimal("-0.77"), Decimal("-1.98"))), floor("0.05"))

    assert point_only.verdict == "approve"
    assert with_band.verdict == "escalate"
    assert with_band.as_invited.worst_total == Decimal("1974.32")
    assert "earns less than not joining" in with_band.as_invited.failed_checks


def test_the_plan_with_the_best_worst_case_wins_even_if_another_expects_more():
    # Holder vs a rival at ฿72. 15% off expects 9,022.72 but falls to 8,257.40 if the rival undercuts;
    # 30% off (฿70, never undercut) earns 9,011.70 either way. Maximin picks 30%, a gain of 754.30 (> 5%).
    deep_72 = CounterMove(rival="Deep undercutter", rival_price_cut=Decimal("0.28"))

    result = evaluate_sku(
        sku("20", "-1.2"), cut("15"), [cut("30")], (HOLDER, deep_72), SHOPEE, terms("2", "0.15"), floor("0.10")
    )

    assert result.verdict == "revise"
    assert result.chosen.plan == cut("30")
    assert result.chosen.worst_total == Decimal("9011.70")
    assert result.as_invited.expected_total == Decimal("9022.72")
    assert result.as_invited.worst_total == Decimal("8257.40")


def test_skip_when_not_joining_beats_every_plan_in_the_worst_case():
    # Weak Campaign traffic (x1.5): 20% off is worst 1,227.28 and 25% off 660.96, while not joining keeps
    # 1,477.70 even if a rival cuts to ฿70. The answer is clear, so it is a Revise to skip (Q54).
    result = evaluate_sku(
        sku("50", "-1.52"), cut("20"), [cut("25")], RIVALS, SHOPEE, terms("1.5", "0.20"), floor("0.10")
    )

    assert result.verdict == "revise"
    assert result.skip is True
    assert result.chosen is None
    assert result.dont_join_total == Decimal("1477.70")
    assert result.as_invited.worst_total == Decimal("1227.28")


def test_escalate_not_skip_when_joining_still_earns_more_than_not_joining():
    # Lift x3: 20% off keeps 2,454.56 in the worst case against 1,477.70 for not joining, but breaks the 10% floor.
    result = evaluate_sku(sku("50", "-1.52"), cut("20"), [cut("25")], RIVALS, SHOPEE, terms("3", "0.20"), floor("0.10"))

    assert result.verdict == "escalate"
    assert result.skip is False
