"""Domain types for the pricing engine. Terms follow CONTEXT.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(frozen=True)
class MarketplaceProfile:
    """Fee structure of one marketplace in one country (rates exclude VAT)."""

    id: str
    currency: str
    effective_from: str
    vat_rate: Decimal
    commission_rate: Decimal
    payment_fee_rate: Decimal
    programme_fee_rate: Decimal
    fixed_fee_per_order: Decimal = ZERO


@dataclass(frozen=True)
class Sku:
    id: str
    name: str
    list_price: Decimal
    cost: Decimal


@dataclass(frozen=True)
class PriceCut:
    """Promo Mechanic: a Seller-funded cut off the list price, in baht."""

    amount: Decimal


@dataclass(frozen=True)
class PromoPlan:
    mechanics: tuple[PriceCut, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CampaignTerms:
    """Per-order terms the Seller doesn't control."""

    platform_funded_discount: Decimal = ZERO
    buyer_paid_shipping: Decimal = ZERO


@dataclass(frozen=True)
class FeeBreakdown:
    commission: Decimal
    payment: Decimal
    programme: Decimal
    fixed: Decimal

    @property
    def total(self) -> Decimal:
        return self.commission + self.payment + self.programme + self.fixed


@dataclass(frozen=True)
class UnitEconomics:
    selling_price: Decimal
    fees: FeeBreakdown
    payout: Decimal
