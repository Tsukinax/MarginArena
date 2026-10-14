# Evidence: four pricing policies under the same Scenarios (proof 3)

Reproduce: `uv run --project backend --env-file .env python backend/scripts/compare_policies.py`, which writes this file and `policy-comparison.json`. These are model-based estimates: every figure comes from the engine under the sample shop's assumptions, not from real sales.

- **Measured:** 2026-10-14T20:19:59+00:00 on route `token-factory`, model `Gemma-4-31B-IT`, sample shop Glow Lab BKK.
- **Scenarios:** per SKU, the generic hold, match and undercut moves plus every Counter-move the AI Rivals found in `runs/token-factory-sample-12sku.sse`, each at the point elasticity and both band edges.
- **MarginArena** is the engine's choice given that run's Plan Ideas and Counter-moves; it reproduces the recorded Verdicts exactly (the script stops if it does not).
- **LLM-direct** got the same facts and formulas as the engine, in words, and chose and computed on its own. Calls: 11 answered, 1 invalid, 0 failed.

## Worst-case Campaign profit per SKU

✗ marks a plan that breaks a check: the invited discount, the Margin Floor, a Brand Price Rule, or earning less than not joining.

| SKU | Verdict | As invited | Match the competitor | LLM-direct | MarginArena |
|---|---|---|---|---|---|
| HB-30 | approve | ฿88.50 off: ฿41,139.00 | ฿123.35 off: ฿40,811.64 ✗ breaks HydraLab reseller agreement, clause 4.2 | ฿118.0 off: ฿40,861.08 | ฿88.50 off: ฿41,139.00 |
| NT-200 | approve | ฿58.50 off: ฿43,599.09 | ฿84.85 off: ฿43,632.00 | ฿59.0 off: ฿43,630.08 | ฿58.50 off: ฿43,599.09 |
| SS-50 | revise | ฿90.00 off: ฿64,111.74 | ฿114.00 off: ฿65,947.35 | no valid answer | ฿157.50 off: ฿67,897.70 |
| CN-50 | approve | ฿103.50 off: ฿11,347.98 | ฿103.50 off: ฿11,347.98 | ฿138.0 off: ฿9,228.32 | ฿103.50 off: ฿11,347.98 |
| VC-30 | escalate | ฿118.00 off: ฿7,369.32 ✗ below the Margin Floor | ฿118.00 off: ฿7,369.32 ✗ below the Margin Floor | ฿118.0 off: ฿7,369.32 ✗ below the Margin Floor | a person decides (Escalate) |
| AC-150 | approve | ฿43.50 off: ฿53,782.92 | ฿69.85 off: ฿53,827.95 | ฿44.0 off: ฿53,812.35 | ฿43.50 off: ฿53,782.92 |
| RN-30 | skip | ฿197.50 off: ฿2,621.97 ✗ below the Margin Floor; earns less than not joining | ฿197.50 off: ฿2,621.97 ✗ below the Margin Floor; earns less than not joining | ฿198.0 off: ฿2,592.09 ✗ below the Margin Floor; earns less than not joining | don't join: ฿3,483.00 |
| CG-80 | approve | ฿52.50 off: ฿25,472.70 | ฿52.50 off: ฿25,472.70 | ฿53.0 off: ฿25,533.69 | ฿52.50 off: ฿25,472.70 |
| LM-15 | approve | ฿50.00 off: ฿20,213.73 | ฿50.00 off: ฿20,213.73 | ฿50.0 off: ฿20,213.73 | ฿50.00 off: ฿20,213.73 |
| SM-10 | skip | ฿79.80 off: ฿2,305.52 ✗ below the Margin Floor; earns less than not joining | ฿79.80 off: ฿2,305.52 ✗ below the Margin Floor; earns less than not joining | ฿80.0 off: ฿2,282.98 ✗ below the Margin Floor; earns less than not joining | don't join: ฿3,092.99 |
| CM-100 | approve | ฿48.00 off: ฿24,133.50 | ฿48.00 off: ฿24,133.50 | ฿48.0 off: ฿24,133.50 | ฿48.00 off: ฿24,133.50 |
| TK-4 | approve | ฿124.75 off: ฿8,902.95 | ฿124.75 off: ฿8,902.95 | ฿125.0 off: ฿8,879.32 | ฿124.75 off: ฿8,902.95 |

## Totals

Escalated SKUs are left out, as in Margin Protected: a person decides them. The second column keeps only the 10 SKUs every policy answered for, so every row adds up the same products.

| Policy | Worst case, 11 SKUs MarginArena decided | Worst case, the 10 SKUs every policy answered | Plans breaking a check, of 11 |
|---|---|---|---|
| As invited | ฿297,631.10 | ฿233,519.36 | 2 |
| Match the competitor | ฿299,217.29 | ฿233,269.94 | 3 |
| LLM-direct | – (an invalid answer) | ฿231,167.14 | 2 |
| MarginArena | ฿303,065.56 | ฿235,167.86 | 0 |

## LLM-direct arithmetic, checked by the engine

For LLM-direct's own plan, with the competitor not reacting, at the point elasticity.

| SKU | Units: Gemma / engine | Campaign profit: Gemma / engine | Error |
|---|---|---|---|
| HB-30 | 281 / 313 | ฿58,266.00 / ฿54,656.06 | 6.60% |
| NT-200 | 414 / 446 | ฿65,491.50 / ฿62,368.64 | 5.01% |
| SS-50 | no valid answer | | |
| CN-50 | 175 / 191 | ฿25,514.25 / ฿12,865.76 | 98.31% |
| VC-30 | 200 / 278 | ฿24,840.00 / ฿11,014.36 | 125.52% |
| AC-150 | 705 / 766 | ฿72,276.50 / ฿80,039.34 | 9.70% |
| RN-30 | 124 / 134 | ฿23,617.33 / ฿4,184.82 | 464.36% |
| CG-80 | 380 / 383 | ฿52,552.60 / ฿49,142.73 | 6.94% |
| LM-15 | 224 / 557 | ฿18,197.41 / ฿47,506.53 | 61.69% |
| SM-10 | 238 / 261 | ฿17,758.32 / ฿3,700.98 | 379.83% |
| CM-100 | 283 / 302 | ฿32,915.23 / ฿32,392.52 | 1.61% |
| TK-4 | 178 / 180 | ฿23,864.28 / ฿11,498.40 | 107.54% |

Median error 61.69%; 1 of 11 answers within 5% of the engine.
