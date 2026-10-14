"""Marketplace fees for one order of one unit.

Each fee is computed excluding VAT, rounded to the satang, then VAT is added and
rounded half up. This reproduces both marketplaces' published worked examples.
"""

from decimal import ROUND_HALF_UP, Decimal

from .model import CampaignTerms, FeeBreakdown, MarketplaceProfile, PriceCut, PromoPlan, ShopVoucher, Sku, UnitEconomics

SATANG = Decimal("0.01")


def _money(x: Decimal) -> Decimal:
    return x.quantize(SATANG, rounding=ROUND_HALF_UP)


def _with_vat(base: Decimal, rate: Decimal, vat_rate: Decimal) -> Decimal:
    fee = _money(base * rate)
    return fee + _money(fee * vat_rate)


def unit_economics(sku: Sku, plan: PromoPlan, profile: MarketplaceProfile, terms: CampaignTerms) -> UnitEconomics:
    price_cut = sum((m.amount for m in plan.mechanics if isinstance(m, PriceCut)), Decimal("0"))
    selling_price = sku.list_price - price_cut
    vouchers = sum((m.amount for m in plan.mechanics if isinstance(m, ShopVoucher)), Decimal("0"))
    seller_net = selling_price - vouchers
    # Fees are charged on the price after the Seller's own discounts and vouchers. Platform-funded
    # discounts are reimbursed to the Seller and never reduce a fee base.
    fee_base = seller_net
    vat = profile.vat_rate
    fees = FeeBreakdown(
        commission=_with_vat(fee_base, profile.commission_rate, vat),
        payment=_with_vat(fee_base + terms.buyer_paid_shipping, profile.payment_fee_rate, vat),
        programme=_with_vat(fee_base, profile.programme_fee_rate, vat),
        fixed=_with_vat(profile.fixed_fee_per_order, Decimal("1"), vat),
    )
    return UnitEconomics(selling_price=selling_price, seller_net=seller_net, fees=fees, payout=seller_net - fees.total, unit_cost=sku.cost)
