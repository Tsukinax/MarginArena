"""MarginArena pricing engine: the only source of numbers (ADR 0001). Deterministic, no I/O."""

from .demand import campaign_outcome
from .fees import unit_economics
from .model import (
    BrandPriceRule,
    CampaignOutcome,
    CampaignTerms,
    CounterMove,
    FeeBreakdown,
    GiftWithPurchase,
    InvitationItem,
    InvitationResult,
    MarketplaceProfile,
    Mechanic,
    PlanEvaluation,
    PlanIdea,
    PriceCut,
    PromoPlan,
    SellerSettings,
    ShopVoucher,
    Sku,
    SkuVerdict,
    UnitEconomics,
)
from .profiles import get_profile
from .search import candidate_plans
from .verdict import evaluate_invitation, evaluate_sku

__all__ = [
    "BrandPriceRule",
    "CampaignOutcome",
    "CampaignTerms",
    "CounterMove",
    "FeeBreakdown",
    "GiftWithPurchase",
    "InvitationItem",
    "InvitationResult",
    "MarketplaceProfile",
    "Mechanic",
    "PlanEvaluation",
    "PlanIdea",
    "PriceCut",
    "PromoPlan",
    "SellerSettings",
    "ShopVoucher",
    "Sku",
    "SkuVerdict",
    "UnitEconomics",
    "campaign_outcome",
    "candidate_plans",
    "evaluate_invitation",
    "evaluate_sku",
    "get_profile",
    "unit_economics",
]
