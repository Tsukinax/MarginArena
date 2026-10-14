"""Evaluating a whole Campaign Invitation and its Margin Protected.

Margin Protected = worst-case profit of following the Verdicts (not joining for Escalate)
minus worst-case profit of joining every SKU exactly as invited. Hand-worked numbers.
"""

from decimal import Decimal

from marginarena.engine import (
    CampaignTerms,
    CounterMove,
    InvitationItem,
    PriceCut,
    PromoPlan,
    SellerSettings,
    Sku,
    evaluate_invitation,
    get_profile,
)

RIVALS = (
    CounterMove(rival="Holder", rival_price_cut=Decimal("0")),
    CounterMove(rival="Undercutter", rival_price_cut=Decimal("0.10")),
)


def cut(baht: str) -> PromoPlan:
    return PromoPlan(mechanics=(PriceCut(amount=Decimal(baht)),))


def sku(sku_id: str, cost: str, elasticity: str) -> Sku:
    return Sku(
        id=sku_id,
        name=sku_id,
        list_price=Decimal("100"),
        cost=Decimal(cost),
        stock=1000,
        baseline_units=100,
        elasticity=Decimal(elasticity),
    )


def test_margin_protected_adds_the_gain_from_every_verdict():
    items = [
        # Revise: 25% off instead of 15% lifts worst-case profit from 8,932.60 to 9,685.20 (+752.60).
        InvitationItem(sku("ELASTIC", "30", "-2.8"), cut("15"), [cut("25")], required_discount=Decimal("0.15")),
        # Escalate: 20% off breaks the 10% floor; not joining keeps 2,111.00 instead of 1,754.21 (+356.79).
        InvitationItem(sku("THIN", "50", "-1.52"), cut("20"), [cut("25")], required_discount=Decimal("0.20")),
    ]

    result = evaluate_invitation(
        items,
        RIVALS,
        get_profile("shopee-th-nonmall-prime-fmcg"),
        CampaignTerms(traffic_lift=Decimal("2")),
        SellerSettings(margin_floor=Decimal("0.10")),
    )

    assert [v.verdict for v in result.verdicts] == ["revise", "escalate"]
    assert result.margin_protected == Decimal("1109.39")
