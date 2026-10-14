"""The engine turns Plan Ideas into every numeric Promo Plan worth testing (ADR 0004).

Rules from the spec: every plan meets the invited discount, never breaks a Brand Price Rule's cap,
offers a shop voucher only when the idea asks for one, and carries the idea's gift.
"""

from decimal import Decimal

from marginarena.engine import (
    BrandPriceRule,
    CampaignTerms,
    GiftWithPurchase,
    PlanIdea,
    PriceCut,
    ShopVoucher,
    Sku,
    candidate_plans,
)

ITEM = Sku(id="NT-200", name="Toner", list_price=Decimal("390"), cost=Decimal("98"))
TERMS = CampaignTerms(required_discount=Decimal("0.15"))
LIP_MASK_GIFT = GiftWithPurchase(cost=Decimal("58"), perceived_value=Decimal("125"))


def cuts(plan) -> Decimal:
    return sum((m.amount for m in plan.mechanics if isinstance(m, PriceCut)), Decimal("0"))


def test_every_plan_meets_the_invited_discount_and_the_invited_plan_is_included():
    plans = candidate_plans(ITEM, TERMS, [PlanIdea()])

    assert min(cuts(p) for p in plans) == Decimal("58.50")  # exactly the invited 15% of ฿390
    assert all(cuts(p) >= Decimal("58.50") for p in plans)


def test_plain_idea_offers_no_vouchers_or_gifts():
    plans = candidate_plans(ITEM, TERMS, [PlanIdea()])

    assert all(all(isinstance(m, PriceCut) for m in p.mechanics) for p in plans)


def test_voucher_idea_adds_vouchers_and_gift_idea_carries_the_gift():
    plans = candidate_plans(ITEM, TERMS, [PlanIdea(use_voucher=True, gift=LIP_MASK_GIFT)])

    assert any(any(isinstance(m, ShopVoucher) for m in p.mechanics) for p in plans)
    assert all(LIP_MASK_GIFT in p.mechanics for p in plans)


def test_no_plan_cuts_deeper_than_a_brand_cap():
    cap = BrandPriceRule(clause="Brand agreement 4.2", max_price_cut=Decimal("0.20"))

    plans = candidate_plans(ITEM, TERMS, [PlanIdea()], brand_rules=(cap,))

    assert max(cuts(p) for p in plans) == Decimal("78.00")  # 20% of ฿390
