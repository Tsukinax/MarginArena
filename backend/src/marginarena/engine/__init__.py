"""MarginArena pricing engine: the only source of numbers (ADR 0001). Deterministic, no I/O."""

from .demand import campaign_outcome
from .fees import unit_economics
from .model import (
    CampaignOutcome,
    CampaignTerms,
    CounterMove,
    FeeBreakdown,
    MarketplaceProfile,
    Mechanic,
    PlanEvaluation,
    PriceCut,
    PromoPlan,
    SellerSettings,
    ShopVoucher,
    Sku,
    SkuVerdict,
    UnitEconomics,
)
from .profiles import get_profile
from .verdict import evaluate_sku

__all__ = [
    "CampaignOutcome",
    "CampaignTerms",
    "CounterMove",
    "FeeBreakdown",
    "MarketplaceProfile",
    "Mechanic",
    "PlanEvaluation",
    "PriceCut",
    "PromoPlan",
    "SellerSettings",
    "ShopVoucher",
    "Sku",
    "SkuVerdict",
    "UnitEconomics",
    "campaign_outcome",
    "evaluate_sku",
    "get_profile",
    "unit_economics",
]
