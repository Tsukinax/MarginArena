"""Loads a sample shop into engine objects. Elasticity comes from the committed FreshRetailNet fit."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from importlib import resources

from marginarena.engine import (
    BrandPriceRule,
    CampaignTerms,
    MarketplaceProfile,
    PriceCut,
    PromoPlan,
    Sku,
    get_profile,
    unit_economics,
)

SHOPS = {"glow-lab-bkk": "glow_lab_bkk.json"}


@dataclass(frozen=True)
class RivalSnapshotEntry:
    rival: str
    reference_price: Decimal


@dataclass(frozen=True)
class ElasticityOverride:
    """A Seller's own elasticity for one SKU, with its own band, in place of the pooled fit (Q56)."""

    elasticity: Decimal
    band: tuple[Decimal, Decimal]
    text: str
    """The label shown wherever this elasticity appears."""
    source: str


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
    elasticity_overrides: dict[str, ElasticityOverride]
    fallback_demo_skus: tuple[str, ...] = ()


def _elasticity() -> dict:
    return json.loads(resources.files("marginarena.engine").joinpath("data/elasticity.json").read_text())


def load_shop(shop_id: str) -> Shop:
    raw = json.loads(resources.files(__package__).joinpath(SHOPS[shop_id]).read_text())
    fit = _elasticity()
    pooled = Decimal(str(fit["pooled"]["elasticity"]))
    low, high = (Decimal(str(x)) for x in fit["band_p10_p90"])
    overrides = {sku_id: _override(o) for sku_id, o in raw.get("elasticity_overrides", {}).items()}
    catalogue = {
        row["id"]: Sku(
            id=row["id"],
            name=row["name"],
            brand=row["brand"],
            list_price=Decimal(row["list_price"]),
            cost=Decimal(row["cost"]),
            stock=row["stock"],
            baseline_units=row["baseline_units"],
            elasticity=overrides[row["id"]].elasticity if row["id"] in overrides else pooled,
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
        elasticity_overrides=overrides,
        fallback_demo_skus=tuple(raw.get("fallback_demo_skus", ())),
    )


def _override(raw: dict) -> ElasticityOverride:
    low, high = (Decimal(x) for x in raw["band"])
    return ElasticityOverride(
        elasticity=Decimal(raw["elasticity"]),
        band=(low, high),
        text=f"Sample Seller override: elasticity {raw['elasticity']}, band {low} to {high}. {raw['note']}",
        source=raw["source"],
    )


def describe_shop(shop: Shop) -> dict:
    """The shop as the UI shows it: invitation, catalogue, rules and every assumption, as plain JSON."""
    p = shop.profile
    return {
        "id": shop.id,
        "name": shop.name,
        "label": shop.label,
        "invitation": shop.invitation,
        "margin_floor": str(shop.margin_floor),
        "profile": {
            "id": p.id,
            "currency": p.currency,
            "effective_from": p.effective_from,
            "commission_rate": str(p.commission_rate),
            "payment_fee_rate": str(p.payment_fee_rate),
            "programme_fee_rate": str(p.programme_fee_rate),
            "fixed_fee_per_order": str(p.fixed_fee_per_order),
            "vat_rate": str(p.vat_rate),
        },
        "assumptions": {
            "traffic_lift": str(shop.terms.traffic_lift),
            "cross_price_sensitivity": str(shop.terms.cross_price_sensitivity),
            "gift_value_ratio": str(shop.gift_value_ratio),
            "elasticity": shop.elasticity_source,
        },
        "invited": [
            {
                "id": i.sku.id,
                "name": i.sku.name,
                "brand": i.sku.brand,
                "list_price": str(i.sku.list_price),
                "cost": str(i.sku.cost),
                "stock": i.sku.stock,
                "required_discount": str(i.required_discount),
            }
            for i in shop.invited
        ],
        "brand_rules": [
            {"clause": r.clause, "brand": r.brand, "text": shop.brand_rule_texts[r.clause]} for r in shop.brand_rules
        ],
        "rival_snapshot": {
            k: {"rival": v.rival, "reference_price": str(v.reference_price)} for k, v in shop.rival_snapshot.items()
        },
        "elasticity_overrides": {
            k: {"elasticity": str(o.elasticity), "band": [str(x) for x in o.band], "text": o.text, "source": o.source}
            for k, o in shop.elasticity_overrides.items()
        },
        "fee_example": fee_example(shop.profile),
    }


def fee_example(profile: MarketplaceProfile) -> list[dict]:
    """The Seller's problem in numbers (README "The problem"): a ฿100 product costing ฿50, at full price, 20% off and
    30% off, at this marketplace's fees."""
    item = Sku(id="EXAMPLE-100", name="฿100 product costing ฿50", list_price=Decimal("100"), cost=Decimal("50"))
    rows = []
    for pct in (Decimal("0"), Decimal("20"), Decimal("30")):
        cut = item.list_price * pct / 100
        plan = PromoPlan(mechanics=(PriceCut(amount=cut),) if cut else ())
        result = unit_economics(item, plan, profile, CampaignTerms())
        rows.append(
            {
                "list_price": str(item.list_price),
                "cost": str(item.cost),
                "discount_pct": str(pct),
                "unit_profit": str(result.unit_profit),
            }
        )
    return rows
