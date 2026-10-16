# Evidence: how the Verdicts move with the assumptions (sensitivity)

Reproduce: `uv run --project backend python backend/scripts/sensitivity.py`, which writes this file and `sensitivity.json`. Engine only: no model is called.

- **Measured:** 2026-10-16T18:20:57+00:00, on the Plan Ideas and Counter-moves of `evidence/runs/token-factory-sample-12sku.sse`. The first row reproduces that run's 12 Verdicts and its Margin Protected exactly (the script stops if it does not).
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

## What the AI Rivals found in the recorded run

- **Risk the generic stress test missed:** on 12 of 12 products the Rivals' Counter-moves lowered the worst case of the plan chosen against the generic moves, by ฿76,929.86 in total (the sum of each product's `red_team_cut`).
- **Decisions they changed:** SS-50, where the final plan keeps ฿3,785.96 more in the worst case than the plan chosen before the Rivals (the sum of `red_team_gain`). That change rests on SS-50's labelled Seller override (see the row without it above).

## Reading it

- The traffic lift has no source for 11.11 and moves every Verdict; the Seller can change it.
- Rows without AI Rivals face fewer Scenarios, so joining as invited looks safer there: they show what the Seller would have believed without the red team, not a better outcome.
