# Evidence: how the Verdicts move with the assumptions (sensitivity)

Reproduce: `uv run --project backend python backend/scripts/sensitivity.py`, which writes this file and `sensitivity.json`. Engine only: no model is called.

- **Measured:** 2026-10-17T10:36:44+00:00, on the Plan Ideas and Counter-moves of `evidence/runs/token-factory-sample-12sku.sse`. The first row reproduces that run's 12 Verdicts and its Margin Protected exactly (the script stops if it does not).
- **One change per row.** Each row's Margin Protected compares following its Verdicts with joining as invited under that row's own Scenarios; escalated products are left out, as always.
- These are model-based estimates for a fictional shop.

| Assumptions | Approve | Revise | Skip | Escalate | Margin Protected | SS-50 |
|---|---|---|---|---|---|---|
| Recorded assumptions (traffic ×2.5, SS-50 override, AI Rivals and Strategists) | 8 | 1 | 2 | 1 | ฿5,434.46 | revise |
| Traffic lift ×1.0 | 6 | 1 | 5 | 0 | ฿12,787.08 | revise |
| Traffic lift ×1.5 | 8 | 1 | 3 | 0 | ฿7,780.16 | revise |
| Traffic lift ×2.0 | 8 | 1 | 2 | 1 | ฿5,789.78 | revise |
| Traffic lift ×3.0 | 8 | 1 | 0 | 3 | ฿4,581.05 | revise |
| SS-50 at the pooled elasticity (no Seller override) | 9 | 0 | 2 | 1 | ฿1,648.50 | approve |
| Generic Counter-moves only (no AI Rivals) | 9 | 0 | 2 | 1 | ฿2,038.53 | approve |
| No AI at all (generic moves, default Plan Ideas) | 9 | 0 | 2 | 1 | ฿2,038.53 | approve |
| A box-corner Rival instead of the AI Rivals (deepest allowed move) | 8 | 1 | 2 | 1 | ฿4,005.56 | revise |
| Random Rivals instead of the AI Rivals (4 per product, fixed seed) | 8 | 1 | 2 | 1 | ฿4,113.36 | revise |

## What the AI Rivals found in the recorded run, against two controls without AI

- **Stress cases the generic moves missed:** on 12 of 12 products the Rivals' Counter-moves lowered the worst case of the plan chosen against the generic moves, by ฿76,929.86 in total (the sum of each product's `red_team_cut`).
- **Controls:** the same cut for a box-corner Rival (one move at the deepest the Rivals may propose: 40% off, a 20% voucher, ฿60 free shipping and a 25% gift) and for 4 random moves inside those bounds per product (a fixed seed).

| Product | AI Rivals | Box-corner Rival | Random Rivals |
|---|---|---|---|
| HB-30 | ฿2,546.70 | ฿21,940.80 | ฿21,940.80 |
| NT-200 | ฿4,486.08 | ฿24,112.68 | ฿24,112.68 |
| SS-50 | ฿22,203.20 | ฿40,382.07 | ฿37,745.44 |
| CN-50 | ฿2,121.98 | ฿6,734.98 | ฿6,734.98 |
| VC-30 | ฿1,426.32 | ฿4,120.48 | ฿4,120.48 |
| AC-150 | ฿6,080.72 | ฿29,984.24 | ฿29,984.24 |
| RN-30 | ฿568.62 | ฿1,358.37 | ฿1,358.37 |
| CG-80 | ฿15,695.30 | ฿20,584.00 | ฿20,584.00 |
| LM-15 | ฿17,740.32 | ฿17,740.32 | ฿17,740.32 |
| SM-10 | ฿673.04 | ฿1,389.04 | ฿1,389.04 |
| CM-100 | ฿3,003.28 | ฿13,622.02 | ฿13,085.72 |
| TK-4 | ฿384.30 | ฿3,971.10 | ฿3,971.10 |
| **Total** | **฿76,929.86** | **฿185,940.10** | **฿182,767.17** |

- **Decisions they changed:** SS-50, where the final plan keeps ฿3,785.96 more in the worst case than the plan chosen before the Rivals (the sum of `red_team_gain`). That change rests on SS-50's labelled Seller override (see the row without it above).

## Reading it

- The traffic lift has no source for 11.11 and moves every Verdict; it is a labelled value in the sample shop file.
- Rows without AI Rivals face fewer Scenarios, so joining as invited looks safer there: they show what the Seller would have believed without the red team, not a better outcome.
