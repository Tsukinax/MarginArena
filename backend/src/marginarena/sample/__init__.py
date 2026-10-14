"""Loads a sample shop into engine objects. Elasticity comes from the committed FreshRetailNet fit."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from importlib import resources

from marginarena.engine import BrandPriceRule, CampaignTerms, MarketplaceProfile, Sku, get_profile

SHOPS = {"glow-lab-bkk": "glow_lab_bkk.json"}


@dataclass(frozen=True)
class RivalSnapshotEntry:
    rival: str
    reference_price: Decimal


@dataclass(frozen=True)
class InvitedSku:
    sku: Sku
    required_discount: Decimal


@dataclass(frozen=True)
class Shop:
    id: str
    name: str
    label: str
    profile: MarketplaceProfile
    margin_floor: Decimal
    terms: CampaignTerms
    """Shop-wide terms; required discount and rival reference price are set per SKU."""
    gift_value_ratio: Decimal
    invitation: dict
    invited: tuple[InvitedSku, ...]
    catalogue: dict[str, Sku]
    gift_candidates: tuple[str, ...]
    brand_rules: tuple[BrandPriceRule, ...]
    brand_rule_texts: dict[str, str]
    rival_snapshot: dict[str, RivalSnapshotEntry]
    elasticity_source: str


def _elasticity() -> dict:
    return json.loads(resources.files("marginarena.engine").joinpath("data/elasticity.json").read_text())


def load_shop(shop_id: str) -> Shop:
    raw = json.loads(resources.files(__package__).joinpath(SHOPS[shop_id]).read_text())
    fit = _elasticity()
    pooled = Decimal(str(fit["pooled"]["elasticity"]))
    low, high = (Decimal(str(x)) for x in fit["band_p10_p90"])
    catalogue = {
        row["id"]: Sku(
            id=row["id"],
            name=row["name"],
            brand=row["brand"],
            list_price=Decimal(row["list_price"]),
            cost=Decimal(row["cost"]),
            stock=row["stock"],
            baseline_units=row["baseline_units"],
            elasticity=pooled,
        )
        for row in raw["catalogue"]
    }
    assumptions = raw["assumptions"]
    rules = raw["brand_rules"]
    return Shop(
        id=shop_id,
        name=raw["shop"],
        label=raw["label"],
        profile=get_profile(raw["profile"]),
        margin_floor=Decimal(raw["margin_floor"]),
        terms=CampaignTerms(
            traffic_lift=Decimal(assumptions["traffic_lift"]),
            cross_price_sensitivity=Decimal(assumptions["cross_price_sensitivity"]),
            elasticity_band=(high, low),
        ),
        gift_value_ratio=Decimal(assumptions["gift_value_ratio"]),
        invitation={k: v for k, v in raw["invitation"].items() if k != "items"},
        invited=tuple(
            InvitedSku(catalogue[item["sku"]], Decimal(item["required_discount"]))
            for item in raw["invitation"]["items"]
        ),
        catalogue=catalogue,
        gift_candidates=tuple(row["id"] for row in raw["catalogue"] if row.get("gift_candidate")),
        brand_rules=tuple(
            BrandPriceRule(
                clause=r["clause"],
                brand=r["brand"],
                max_price_cut=Decimal(r["max_price_cut"]),
                vouchers_allowed=r["vouchers_allowed"],
                gifts_allowed=r["gifts_allowed"],
            )
            for r in rules
        ),
        brand_rule_texts={r["clause"]: r["text"] for r in rules},
        rival_snapshot={
            sku_id: RivalSnapshotEntry(v["rival"], Decimal(v["reference_price"]))
            for sku_id, v in raw["rival_snapshot"].items()
        },
        elasticity_source=f"{fit['source']}, pooled {pooled} (band {low} to {high})",
    )
