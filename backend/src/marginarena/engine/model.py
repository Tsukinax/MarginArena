"""Domain types for the pricing engine. Terms follow CONTEXT.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

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
    stock: int = 0
    baseline_units: int = 0
    """Units this SKU sells over a Campaign-length period at its list price, without a Campaign."""
    elasticity: Decimal | None = None
    """Price elasticity of demand (negative). Category default or the Seller's override."""


@dataclass(frozen=True)
class PriceCut:
    """Promo Mechanic: a Seller-funded cut off the list price, in baht."""

    amount: Decimal


@dataclass(frozen=True)
class ShopVoucher:
    """Promo Mechanic: a Seller-funded voucher in baht, usable above a minimum spend."""

    amount: Decimal
    min_spend: Decimal = ZERO


@dataclass(frozen=True)
class GiftWithPurchase:
    """Promo Mechanic: a free gift. The Seller pays its cost; buyers value it at an assumed, overridable amount."""

    cost: Decimal
    perceived_value: Decimal


Mechanic = PriceCut | ShopVoucher | GiftWithPurchase


@dataclass(frozen=True)
class PromoPlan:
    mechanics: tuple[Mechanic, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CampaignTerms:
    """Per-order terms the Seller doesn't control."""

    platform_funded_discount: Decimal = ZERO
    buyer_paid_shipping: Decimal = ZERO
    traffic_lift: Decimal = Decimal("1")
    """How much more traffic joining the Campaign brings, before any price effect."""
    required_discount: Decimal = ZERO
    """The Campaign Invitation's minimum price cut, as a fraction of list price."""
    cross_price_sensitivity: Decimal = Decimal("0.6")
    """Assumption, shown to the Seller and overridable: how strongly a Rival's effective price cut pulls demand away."""


@dataclass(frozen=True)
class CounterMove:
    """A Rival's response to a Promo Plan, expressed as its effective price cut (a fraction of its price)."""

    rival: str
    rival_price_cut: Decimal


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
    """Shelf price after Seller price cuts."""
    seller_net: Decimal
    """What the Seller is credited after its own vouchers; the base for marketplace fees."""
    fees: FeeBreakdown
    payout: Decimal
    unit_cost: Decimal

    @property
    def unit_profit(self) -> Decimal:
        return self.payout - self.unit_cost

    @property
    def margin(self) -> Decimal:
        """Unit profit as a share of the selling price: the measure the Margin Floor uses."""
        return (self.unit_profit / self.selling_price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CampaignOutcome:
    unit: UnitEconomics
    units: int
    total_profit: Decimal


@dataclass(frozen=True)
class BrandPriceRule:
    """A brand's pricing clause, already turned into a structured constraint, citing its clause."""

    clause: str
    max_price_cut: Decimal | None = None
    """Largest allowed headline cut, as a fraction of list price."""
    min_shelf_price: Decimal | None = None
    vouchers_allowed: bool = True
    gifts_allowed: bool = True


@dataclass(frozen=True)
class SellerSettings:
    margin_floor: Decimal
    brand_rules: tuple[BrandPriceRule, ...] = ()
    approve_tolerance: Decimal = Decimal("0.05")
    """Joining as invited is approved when the best plan earns at most this much more (relative)."""


@dataclass(frozen=True)
class PlanEvaluation:
    plan: PromoPlan
    outcomes: tuple[CampaignOutcome, ...]
    """One outcome per Counter-move, in the order given."""
    worst_margin: Decimal
    worst_total: Decimal
    expected_total: Decimal
    failed_checks: tuple[str, ...]
    """Why the plan can't be chosen; empty when eligible."""

    @property
    def eligible(self) -> bool:
        return not self.failed_checks


@dataclass(frozen=True)
class SkuVerdict:
    sku: Sku
    verdict: str
    """approve | revise | escalate"""
    chosen: PlanEvaluation | None
    as_invited: PlanEvaluation
    candidates: tuple[PlanEvaluation, ...]
    dont_join_total: Decimal


@dataclass(frozen=True)
class InvitationItem:
    """One SKU named in a Campaign Invitation, with the plan it was invited at and the alternatives to test."""

    sku: Sku
    as_invited: PromoPlan
    candidates: list[PromoPlan]
    required_discount: Decimal = ZERO
    counter_moves: tuple[CounterMove, ...] | None = None
    """Counter-moves for this SKU only, for example from its Rival Snapshot. None means the shared set."""


@dataclass(frozen=True)
class InvitationResult:
    verdicts: tuple[SkuVerdict, ...]
    margin_protected: Decimal
