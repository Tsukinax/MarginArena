"""MarginArena pricing engine: the only source of numbers (ADR 0001). Deterministic, no I/O."""

from .fees import unit_economics
from .model import CampaignTerms, FeeBreakdown, MarketplaceProfile, Mechanic, PriceCut, PromoPlan, ShopVoucher, Sku, UnitEconomics
from .profiles import get_profile

__all__ = [
    "CampaignTerms",
    "FeeBreakdown",
    "MarketplaceProfile",
    "Mechanic",
    "PriceCut",
    "PromoPlan",
    "ShopVoucher",
    "Sku",
    "UnitEconomics",
    "get_profile",
    "unit_economics",
]
