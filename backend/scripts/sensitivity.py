"""How the sample shop's Verdicts and Margin Protected move with the assumptions (engine only, no model calls).

Every SKU is re-selected with the recorded 12-product run's Plan Ideas and Counter-moves, as compare_policies.py
does. The script first checks that the recorded assumptions reproduce the recorded Verdicts and Margin Protected
exactly, then changes one thing at a time:

- the Campaign traffic lift for joining (×1.0 to ×3.0; ×2.5 is the default and has no source for 11.11);
- SS-50 without its labelled Seller override (the pooled elasticity and band, like every other product);
- Counter-moves: only the three generic hold, match and undercut moves, without the AI Rivals' moves;
- no AI at all: the generic moves and the engine's two default Plan Ideas (a plain cut, a voucher).

Each row's Margin Protected is measured against joining as invited under that row's own Scenarios. It also adds up,
from the recorded run itself, how far the Rivals' moves lowered the worst case the generic stress test reported
(red_team_cut) and how much the final plans beat the plans chosen before the Rivals (red_team_gain).

Run from the repo root:
    uv run --project backend python backend/scripts/sensitivity.py

Writes evidence/sensitivity.json and evidence/sensitivity.md.
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_policies import EVIDENCE, recorded_run, sat  # noqa: E402

from marginarena.engine import (  # noqa: E402
    CounterMove,
    GiftWithPurchase,
    PlanIdea,
    PriceCut,
    PromoPlan,
    SellerSettings,
    candidate_plans,
    evaluate_sku,
)
from marginarena.sample import load_shop  # noqa: E402

LIFTS = (Decimal("1.0"), Decimal("1.5"), Decimal("2.0"), Decimal("2.5"), Decimal("3.0"))


def decide(shop, item, moves, ideas, *, rivals=None, ai_moves=True, **kwargs) -> dict:
    """One SKU's Verdict and its share of Margin Protected under the given assumptions. `rivals` replaces the AI
    Rivals' moves with other moves per SKU."""
    sku, terms, seller, generic, plans, invited = setup(shop, item, ideas, **kwargs)
    extra = (rivals or moves)[sku.id] if ai_moves or rivals else []
    v = evaluate_sku(sku, invited, plans, [*generic, *extra], shop.profile, terms, seller)
    kept = v.chosen.worst_total if v.chosen else v.dont_join_total if v.skip else None
    return {
        "sku": sku.id,
        "verdict": "skip" if v.skip else v.verdict,
        "kept": None if kept is None else str(kept),
        "protected": None if kept is None else str(kept - v.as_invited.worst_total),
    }


def stress_cut(shop, item, ideas, extra: list[CounterMove]) -> Decimal:
    """How far `extra` moves lower the worst case of the plan chosen against the generic moves (red_team_cut)."""
    sku, terms, seller, generic, plans, invited = setup(shop, item, ideas)
    first = evaluate_sku(sku, invited, plans, generic, shop.profile, terms, seller)
    plan = first.chosen.plan if first.chosen else invited

    def worst(scenarios: list[CounterMove]) -> Decimal:
        return evaluate_sku(sku, plan, [], scenarios, shop.profile, terms, seller).as_invited.worst_total

    return worst(generic) - worst([*generic, *extra])


def box_corner(shop, item) -> list[CounterMove]:
    """The deepest move a Rival may propose (arena.py's bounds: 40% off, a 20% voucher, ฿60 shipping, a 25% gift)."""
    ref = reference(shop, item)
    return [
        CounterMove(
            rival="Box corner",
            rival_price_cut=Decimal("0.40"),
            voucher=sat(ref * Decimal("0.20")),
            free_shipping=Decimal("60"),
            gift_value=sat(ref * Decimal("0.25")),
        )
    ]


def random_rivals(shop, item, count: int = 4) -> list[CounterMove]:
    """Moves drawn uniformly inside the same bounds, as many as the AI Rivals made per product (fixed seed)."""
    rng = random.Random(f"{item.sku.id}-sensitivity")
    ref = reference(shop, item)
    return [
        CounterMove(
            rival="Random",
            rival_price_cut=Decimal(rng.randint(0, 40)) / 100,
            voucher=sat(ref * Decimal(rng.randint(0, 20)) / 100),
            free_shipping=Decimal(rng.randint(0, 60)),
            gift_value=sat(ref * Decimal(rng.randint(0, 25)) / 100),
        )
        for _ in range(count)
    ]


def reference(shop, item) -> Decimal:
    snapshot = shop.rival_snapshot.get(item.sku.id)
    return snapshot.reference_price if snapshot else item.sku.list_price


def setup(shop, item, ideas, *, traffic_lift=None, override=True, ai_ideas=True):
    """The SKU, terms, settings, generic moves, candidate plans and invited plan, as the Arena sets them up."""
    sku = item.sku
    seller_override = shop.elasticity_overrides.get(sku.id) if override else None
    if sku.id in shop.elasticity_overrides and not override:
        pooled = next(i.sku.elasticity for i in shop.invited if i.sku.id not in shop.elasticity_overrides)
        sku = replace(sku, elasticity=pooled)
    snapshot = shop.rival_snapshot.get(sku.id)
    terms = replace(
        shop.terms,
        required_discount=item.required_discount,
        rival_reference_price=snapshot.reference_price if snapshot else None,
        elasticity_band=seller_override.band if seller_override else shop.terms.elasticity_band,
        traffic_lift=traffic_lift if traffic_lift is not None else shop.terms.traffic_lift,
    )
    rules = tuple(r for r in shop.brand_rules if r.binds(sku))
    seller = SellerSettings(margin_floor=shop.margin_floor, brand_rules=rules)
    generic = [
        CounterMove(rival="Holder", rival_price_cut=Decimal("0")),
        CounterMove(rival="Matcher", rival_price_cut=item.required_discount),
        CounterMove(rival="Undercutter", rival_price_cut=item.required_discount + Decimal("0.05")),
    ]
    gifts = {g.name: g for g in shop.catalogue.values()}
    idea_objects = [PlanIdea(), PlanIdea(use_voucher=True)]
    for use_voucher, gift_name in ideas[sku.id] if ai_ideas else []:
        g = gifts[gift_name] if gift_name else None
        gift = (
            GiftWithPurchase(cost=g.cost, perceived_value=sat(g.list_price * shop.gift_value_ratio), name=g.name)
            if g
            else None
        )
        idea_objects.append(PlanIdea(use_voucher=use_voucher, gift=gift))
    invited = PromoPlan(mechanics=(PriceCut(amount=sat(sku.list_price * item.required_discount)),))
    plans = candidate_plans(sku, terms, idea_objects, rules)
    return sku, terms, seller, generic, plans, invited


def variant(name: str, rows: list[dict]) -> dict:
    counts = {k: sum(r["verdict"] == k for r in rows) for k in ("approve", "revise", "skip", "escalate")}
    protected = sum((Decimal(r["protected"]) for r in rows if r["protected"] is not None), Decimal("0"))
    return {"name": name, "verdicts": counts, "margin_protected": str(protected), "skus": rows}


def main() -> None:
    shop = load_shop("glow-lab-bkk")
    moves, ideas, results = recorded_run()

    def run(name: str, **kwargs) -> dict:
        return variant(name, [decide(shop, item, moves, ideas, **kwargs) for item in shop.invited])

    base = run("Recorded assumptions (traffic ×2.5, SS-50 override, AI Rivals and Strategists)")
    for row in base["skus"]:
        recorded = results[row["sku"]]
        verdict = "skip" if recorded["skip"] else recorded["verdict"]
        kept = recorded["chosen_worst_total"] or (recorded["dont_join_total"] if recorded["skip"] else None)
        if row["verdict"] != verdict or row["kept"] != kept:
            raise SystemExit(f"{row['sku']}: {row['verdict']} {row['kept']} differs from the recorded run")
    events = [
        json.loads(line[6:])
        for line in (EVIDENCE / "runs" / "token-factory-sample-12sku.sse").read_text().splitlines()
        if line.startswith("data: ")
    ]
    recorded_total = events[-1]["margin_protected"]
    if base["margin_protected"] != recorded_total:
        raise SystemExit(f"Margin Protected {base['margin_protected']} differs from the recorded {recorded_total}")

    variants = [base]
    variants += [run(f"Traffic lift ×{lift}", traffic_lift=lift) for lift in LIFTS if lift != shop.terms.traffic_lift]
    variants.append(run("SS-50 at the pooled elasticity (no Seller override)", override=False))
    variants.append(run("Generic Counter-moves only (no AI Rivals)", ai_moves=False))
    variants.append(run("No AI at all (generic moves, default Plan Ideas)", ai_moves=False, ai_ideas=False))
    corner = {i.sku.id: box_corner(shop, i) for i in shop.invited}
    drawn = {i.sku.id: random_rivals(shop, i) for i in shop.invited}
    variants.append(run("A box-corner Rival instead of the AI Rivals (deepest allowed move)", rivals=corner))
    variants.append(run("Random Rivals instead of the AI Rivals (4 per product, fixed seed)", rivals=drawn))

    stress = []
    for item in shop.invited:
        sku = item.sku.id
        ai = stress_cut(shop, item, ideas, moves[sku])
        recorded_cut = results[sku]["red_team_cut"]
        if recorded_cut is not None and str(ai) != recorded_cut:
            raise SystemExit(f"{sku}: red_team_cut {ai} differs from the recorded {recorded_cut}")
        stress.append(
            {
                "sku": sku,
                "ai_rivals": str(ai),
                "box_corner": str(stress_cut(shop, item, ideas, corner[sku])),
                "random": str(stress_cut(shop, item, ideas, drawn[sku])),
            }
        )

    cut = sum((Decimal(r["red_team_cut"]) for r in results.values() if r["red_team_cut"] is not None), Decimal("0"))
    gain = sum((Decimal(r["red_team_gain"]) for r in results.values() if r["red_team_gain"]), Decimal("0"))
    meta = {
        "measured": datetime.now(UTC).isoformat(timespec="seconds"),
        "run": "evidence/runs/token-factory-sample-12sku.sse",
        "red_team_cut_total": str(cut),
        "red_team_cut_skus": sum(Decimal(r["red_team_cut"] or 0) > 0 for r in results.values()),
        "red_team_gain_total": str(gain),
        "red_team_gain_skus": [s for s, r in results.items() if r["red_team_gain"] and Decimal(r["red_team_gain"]) > 0],
    }
    data = {"meta": meta, "variants": variants, "stress": stress}
    (EVIDENCE / "sensitivity.json").write_text(json.dumps(data, indent=1) + "\n")
    write_report(variants, meta, stress)


def baht(x: str) -> str:
    n = Decimal(x)
    return f"{'−' if n < 0 else ''}฿{abs(n):,.2f}"


def write_report(variants: list[dict], meta: dict, stress: list[dict]) -> None:
    lines = [
        "# Evidence: how the Verdicts move with the assumptions (sensitivity)",
        "",
        "Reproduce: `uv run --project backend python backend/scripts/sensitivity.py`, which writes this file and "
        "`sensitivity.json`. Engine only: no model is called.",
        "",
        f"- **Measured:** {meta['measured']}, on the Plan Ideas and Counter-moves of `{meta['run']}`. The first row "
        "reproduces that run's 12 Verdicts and its Margin Protected exactly (the script stops if it does not).",
        "- **One change per row.** Each row's Margin Protected compares following its Verdicts with joining as "
        "invited under that row's own Scenarios; escalated products are left out, as always.",
        "- These are model-based estimates for a fictional shop.",
        "",
        "| Assumptions | Approve | Revise | Skip | Escalate | Margin Protected | SS-50 |",
        "|---|---|---|---|---|---|---|",
    ]
    for v in variants:
        c = v["verdicts"]
        ss50 = next(r for r in v["skus"] if r["sku"] == "SS-50")
        lines.append(
            f"| {v['name']} | {c['approve']} | {c['revise']} | {c['skip']} | {c['escalate']} | "
            f"{baht(v['margin_protected'])} | {ss50['verdict']} |"
        )
    lines += [
        "",
        "## What the AI Rivals found in the recorded run, against two controls without AI",
        "",
        f"- **Stress cases the generic moves missed:** on {meta['red_team_cut_skus']} of 12 products the Rivals' "
        f"Counter-moves lowered the worst case of the plan chosen against the generic moves, by "
        f"{baht(meta['red_team_cut_total'])} in total (the sum of each product's `red_team_cut`).",
        "- **Controls:** the same cut for a box-corner Rival (one move at the deepest the Rivals may propose: 40% off, "
        "a 20% voucher, ฿60 free shipping and a 25% gift) and for 4 random moves inside those bounds per product "
        "(a fixed seed).",
        "",
        "| Product | AI Rivals | Box-corner Rival | Random Rivals |",
        "|---|---|---|---|",
        *[f"| {s['sku']} | {baht(s['ai_rivals'])} | {baht(s['box_corner'])} | {baht(s['random'])} |" for s in stress],
        f"| **Total** | **{baht(str(sum(Decimal(s['ai_rivals']) for s in stress)))}** | "
        f"**{baht(str(sum(Decimal(s['box_corner']) for s in stress)))}** | "
        f"**{baht(str(sum(Decimal(s['random']) for s in stress)))}** |",
        "",
        f"- **Decisions they changed:** {', '.join(meta['red_team_gain_skus']) or 'none'}, where the final plan keeps "
        f"{baht(meta['red_team_gain_total'])} more in the worst case than the plan chosen before the Rivals (the sum of "
        "`red_team_gain`). That change rests on SS-50's labelled Seller override (see the row without it above).",
        "",
        "## Reading it",
        "",
        "- The traffic lift has no source for 11.11 and moves every Verdict; the Seller can change it.",
        "- Rows without AI Rivals face fewer Scenarios, so joining as invited looks safer there: they show what the "
        "Seller would have believed without the red team, not a better outcome.",
        "",
    ]
    (EVIDENCE / "sensitivity.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
