"""MarginArena pricing engine: the only source of numbers (ADR 0001). Deterministic, no I/O."""

from .demand import campaign_outcome
from .fees import unit_economics
from .model import CampaignOutcome, CampaignTerms, CounterMove, FeeBreakdown, MarketplaceProfile, Mechanic, PriceCut, PromoPlan, ShopVoucher, Sku, UnitEconomics
from .profiles import get_profile

__all__ = [
    "CampaignOutcome",
    "CampaignTerms",
    "CounterMove",
    "FeeBreakdown",
    "MarketplaceProfile",
    "Mechanic",
    "PriceCut",
    "PromoPlan",
    "ShopVoucher",
    "Sku",
    "UnitEconomics",
    "campaign_outcome",
    "get_profile",
    "unit_economics",
]
