"""Q56 experiment, engine only (no LLM): when do the Counter-moves AI Rivals really proposed change a decision?

Pre-registered rules (written before running):
- Counter-moves: the generic three the Arena always uses, plus the AI moves seen in evidence/runs/*.sse.
- Parameters varied only where a source or the spec allows it:
  * elasticity: pooled -1.49 (fit) or the literature mean -2.62 (Bijmolt et al. 2005, cited in research) as a
    labelled Seller override; band treatments: the shop band, or the override's own band (same relative width).
  * cross-price sensitivity k: 1.0 (current, an assumption) and 2.0 (sensitivity check only, no source).
- Report every SKU and every configuration, including the ones where nothing changes.
"""

from dataclasses import replace
from decimal import Decimal

from marginarena.engine import CounterMove, GiftWithPurchase, PlanIdea, PriceCut, PromoPlan, SellerSettings
from marginarena.engine import candidate_plans, evaluate_sku
from marginarena.sample import load_shop

AI_MOVES = [  # (rival, cut, voucher, free shipping, gift) as proposed by Gemma in recorded runs
    ("Price matcher", "0.07", "0", "40", "0"),
    ("Price matcher", "0.20", "0", "40", "0"),
    ("Undercutter", "0.05", "50", "40", "0"),
    ("Undercutter", "0.15", "50", "40", "0"),
    ("Undercutter", "0.22", "50", "40", "0"),
    ("Price matcher", "0.20", "72", "0", "0"),
]

shop = load_shop("glow-lab-bkk")
pooled = shop.catalogue["NT-200"].elasticity
low, high = shop.terms.elasticity_band[1], shop.terms.elasticity_band[0]  # band stored as (weak, strong)


def label(plan: PromoPlan) -> str:
    parts = []
    for m in plan.mechanics:
        parts.append(
            f"฿{m.amount} off" if isinstance(m, PriceCut) else f"gift {m.name}" if isinstance(m, GiftWithPurchase)
            else f"฿{m.amount} voucher"
        )
    return " + ".join(parts) or "none"


def decide(item, elasticity, band, k):
    sku = replace(item.sku, elasticity=elasticity)
    snapshot = shop.rival_snapshot.get(sku.id)
    terms = replace(
        shop.terms,
        required_discount=item.required_discount,
        rival_reference_price=snapshot.reference_price if snapshot else None,
        elasticity_band=band,
        cross_price_sensitivity=k,
    )
    rules = tuple(r for r in shop.brand_rules if r.binds(sku))
    settings = SellerSettings(margin_floor=shop.margin_floor, brand_rules=rules)
    invited = PromoPlan(mechanics=(PriceCut(amount=(sku.list_price * item.required_discount).quantize(Decimal("0.01"))),))
    gifts = [shop.catalogue[g] for g in shop.gift_candidates if g != sku.id]
    ideas = [PlanIdea(), PlanIdea(use_voucher=True)] + [
        PlanIdea(gift=GiftWithPurchase(cost=g.cost, perceived_value=g.list_price * shop.gift_value_ratio, name=g.id))
        for g in gifts
    ]
    plans = candidate_plans(sku, terms, ideas, rules)
    generic = [
        CounterMove(rival="Holder", rival_price_cut=Decimal("0")),
        CounterMove(rival="Matcher", rival_price_cut=item.required_discount),
        CounterMove(rival="Undercutter", rival_price_cut=item.required_discount + Decimal("0.05")),
    ]
    ai = [CounterMove(rival=r, rival_price_cut=Decimal(c), voucher=Decimal(v), free_shipping=Decimal(s), gift_value=Decimal(g))
          for r, c, v, s, g in AI_MOVES]
    before = evaluate_sku(sku, invited, plans, generic, shop.profile, terms, settings)
    after = evaluate_sku(sku, invited, plans, generic + ai, shop.profile, terms, settings)
    first = before.chosen or before.as_invited
    first_all = evaluate_sku(sku, first.plan, [], generic + ai, shop.profile, terms, settings).as_invited
    return before, after, first.worst_total - first_all.worst_total


def word(v):
    return "skip" if v.skip else v.verdict


configs = [
    ("A pooled -1.49, shop band, k=1 (today)", pooled, (high, low), Decimal("1")),
    ("B pooled -1.49, shop band, k=2", pooled, (high, low), Decimal("2")),
    ("C override -2.62, shop band, k=1", Decimal("-2.62"), (high, low), Decimal("1")),
    ("D override -2.62, own band, k=1", Decimal("-2.62"), (high / pooled * Decimal("-2.62"), low / pooled * Decimal("-2.62")), Decimal("1")),
    ("E override -2.62, own band, k=2", Decimal("-2.62"), (high / pooled * Decimal("-2.62"), low / pooled * Decimal("-2.62")), Decimal("2")),
]
for name, e, band, k in configs:
    print(f"\n=== {name}; band {band[0].quantize(Decimal('0.01'))} to {band[1].quantize(Decimal('0.01'))}")
    for item in shop.invited:
        before, after, cut = decide(item, e, band, k)
        b_plan = label(before.chosen.plan) if before.chosen else "-"
        a_plan = label(after.chosen.plan) if after.chosen else "-"
        changed = (word(before), b_plan) != (word(after), a_plan)
        print(
            f"{item.sku.id:7} before AI: {word(before):8} {b_plan:28} | after AI: {word(after):8} {a_plan:28} "
            f"| red-team cut ฿{cut:>9} {'CHANGED' if changed else ''}"
        )

print("\n=== SS-50 only: override -2.62 with its own band, k=1, one recorded AI move at a time")
ss50 = next(i for i in shop.invited if i.sku.id == "SS-50")
own_band = (high / pooled * Decimal("-2.62"), low / pooled * Decimal("-2.62"))
recorded = list(AI_MOVES)
for move in recorded:
    AI_MOVES[:] = [move]
    before, after, cut = decide(ss50, Decimal("-2.62"), own_band, Decimal("1"))
    kept = after.chosen.worst_total if after.chosen else after.as_invited.worst_total
    print(
        f"{move}: before {word(before)}, after {word(after)} "
        f"{label(after.chosen.plan) if after.chosen else '-'}; worst case as invited {after.as_invited.worst_total}, "
        f"with the Verdict {kept}"
    )
AI_MOVES[:] = recorded
