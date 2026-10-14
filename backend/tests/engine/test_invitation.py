"""Evaluating a whole Campaign Invitation and its Margin Protected.

Margin Protected = worst-case profit of following the Verdicts (not joining for Escalate)
minus worst-case profit of joining every SKU exactly as invited. Hand-worked numbers, k = 1.
It can go down for an Escalate: a Margin Floor can cost profit, and the number says so.
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
    CounterMove(rival="Deep undercutter", rival_price_cut=Decimal("0.30")),
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
        # Revise: 25% off instead of 15% lifts worst-case profit from 7,842.52 to 9,616.02 (+1,773.50).
        InvitationItem(sku("ELASTIC", "30", "-2.8"), cut("15"), [cut("25")], required_discount=Decimal("0.15")),
        # Escalate: 20% off breaks the 10% floor. Not joining, worst case 1,477.70, vs joining 1,634.15 (-156.45).
        InvitationItem(sku("THIN", "50", "-1.52"), cut("20"), [cut("25")], required_discount=Decimal("0.20")),
    ]

    result = evaluate_invitation(
        items,
        RIVALS,
        get_profile("shopee-th-nonmall-prime-fmcg"),
        CampaignTerms(traffic_lift=Decimal("2"), cross_price_sensitivity=Decimal("1")),
        SellerSettings(margin_floor=Decimal("0.10")),
    )

    assert [v.verdict for v in result.verdicts] == ["revise", "escalate"]
    assert result.margin_protected == Decimal("1617.05")
