"""Marketplace Profiles. Rates exclude VAT. Sources: .scratch/marginarena/research/marketplace-fees.md."""

from decimal import Decimal

from .model import MarketplaceProfile

_PROFILES = {
    p.id: p
    for p in (
        MarketplaceProfile(
            id="shopee-th-nonmall-prime-fmcg",
            currency="THB",
            effective_from="2026-08-04",
            vat_rate=Decimal("0.07"),
            commission_rate=Decimal("0.15"),
            payment_fee_rate=Decimal("0.03"),
            programme_fee_rate=Decimal("0.08"),
            fixed_fee_per_order=Decimal("1.00"),
        ),
        MarketplaceProfile(
            id="lazada-th-lazmall-beauty",
            currency="THB",
            effective_from="2026-08-01",
            vat_rate=Decimal("0.07"),
            commission_rate=Decimal("0.175"),
            payment_fee_rate=Decimal("0.03"),
            programme_fee_rate=Decimal("0.08"),
        ),
    )
}


def get_profile(profile_id: str) -> MarketplaceProfile:
    return _PROFILES[profile_id]
