# Evidence: price elasticity

Reproduce: `cd backend && uv run --group fit python scripts/fit_elasticity.py`, which writes
`backend/src/marginarena/engine/data/elasticity.json` and this file.

- **Data:** FreshRetailNet-50K, Dingdong Ltd., CC BY 4.0, revision `c374e85975c8`, checked by SHA-256. It is real online fresh-grocery orders from 18 Chinese cities in 2024. We use it as an e-commerce starting point: Sellers can override any SKU.
- **Sample:** 2,457,513 store × SKU × day rows that were fully in stock and had positive sales.
- **Pooled elasticity: -1.49** (cluster-robust SE 0.12). A 10% price cut lifts unit sales by about 15%.
- **Category elasticities:** 22 categories with at least 200 series, after shrinkage. The p10–p90 band is -1.98 to -0.77 (μ -1.28, τ 0.67).

## Holdout (the dataset's own eval week)

Each model predicts daily sales for a store × SKU from its last 14 training days. The table shows WAPE (lower is better).

| Days | Rows | Naive 14-day mean | Mean × (discount ratio)^β |
|---|---|---|---|
| Discount deepened >10% | 22,575 | 0.426 | **0.350** |
| Discount became shallower >10% | 54,612 | 0.405 | 0.479 |

The engine applies elasticity to **price cuts only**, because the constant-elasticity model is not reliable when a discount ends.

## Limits

- Perishable groceries are not general marketplace goods.
- Category names are anonymised.
- The window contains no 11.11 Campaign.
- Discounts are set by the retailer, so the estimate may be biased toward zero. The literature mean is about −2.6.
