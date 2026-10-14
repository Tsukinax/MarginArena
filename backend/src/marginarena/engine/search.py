"""Every numeric Promo Plan worth testing for a set of Plan Ideas (ADR 0004)."""

from decimal import ROUND_HALF_UP, Decimal

from .model import BrandPriceRule, CampaignTerms, Mechanic, PlanIdea, PriceCut, PromoPlan, ShopVoucher, Sku

EXTRA_CUT_POINTS = range(26)  # 0 to 25 percentage points deeper than the invitation asks
VOUCHER_SHARES = tuple(Decimal(x) for x in ("0.025", "0.05", "0.075", "0.10", "0.15"))
MAX_CUT = Decimal("0.60")


def candidate_plans(
    sku: Sku, terms: CampaignTerms, ideas: list[PlanIdea], brand_rules: tuple[BrandPriceRule, ...] = ()
) -> list[PromoPlan]:
    max_cut = min((r.max_price_cut for r in brand_rules if r.max_price_cut is not None), default=MAX_CUT)
    min_shelf = max((r.min_shelf_price for r in brand_rules if r.min_shelf_price is not None), default=Decimal("0"))
    vouchers_ok = all(r.vouchers_allowed for r in brand_rules)
    gifts_ok = all(r.gifts_allowed for r in brand_rules)

    plans: dict[PromoPlan, None] = {}
    for idea in ideas:
        vouchers = [_whole_baht(sku.list_price * s) for s in VOUCHER_SHARES] if idea.use_voucher and vouchers_ok else []
        gift = idea.gift if gifts_ok else None
        for extra in EXTRA_CUT_POINTS:
            share = terms.required_discount + Decimal(extra) / 100
            cut = (sku.list_price * share).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if share > max_cut or sku.list_price - cut < min_shelf:
                break
            for voucher in [None, *vouchers]:
                mechanics: list[Mechanic] = [PriceCut(amount=cut)]
                if voucher:
                    mechanics.append(ShopVoucher(amount=voucher))
                if gift:
                    mechanics.append(gift)
                plans[PromoPlan(mechanics=tuple(mechanics))] = None
    return list(plans)


def _whole_baht(x: Decimal) -> Decimal:
    return x.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
