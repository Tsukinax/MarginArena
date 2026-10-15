"""Fit price elasticities from FreshRetailNet-50K and write the engine's parameters plus an evidence report.

Method (see .scratch/marginarena/research/elasticity-dataset.md):
    log q = a[store x SKU] + l[city x date] + beta * log(discount) + gamma * activity + e
estimated on fully in-stock days with positive sales, using two-way fixed effects by alternating
projections. Standard errors are clustered by product. Category slopes are fitted the same way
and shrunk toward the precision-weighted mean (empirical Bayes). The holdout compares a naive
14-day average with that average scaled by the elasticity, on the dataset's own eval week.

Usage:
    uv run --group fit python scripts/fit_elasticity.py [--data-dir DIR]

Data: FreshRetailNet-50K by Dingdong Ltd., CC BY 4.0, pinned revision below. Files are downloaded
into the data dir if missing and always checked against their SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REVISION = "c374e85975c82816c495acfa904cc55ab14a47d3"
URL = "https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K/resolve/{rev}/data/{name}.parquet"
SHA256 = {
    "train": "6706832db892bbae4969c19d87e07975d2543d2ba7d7d4756360654785de5a3d",
    "eval": "1b118840664280c6b88bffc84c80ee1f54c05d911e354b7599e5da10995e960e",
}
ROOT = Path(__file__).resolve().parents[2]
PARAMS_OUT = ROOT / "backend/src/marginarena/engine/data/elasticity.json"
REPORT_OUT = ROOT / "evidence/elasticity.md"
MIN_SERIES_PER_CATEGORY = 200


def fetch(data_dir: Path, name: str) -> Path:
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"downloading {name}.parquet ...")
        urllib.request.urlretrieve(URL.format(rev=REVISION, name=name), path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SHA256[name]:
        raise SystemExit(f"{path} has SHA-256 {digest}, expected {SHA256[name]}")
    return path


def demean(values: np.ndarray, groups: list[np.ndarray], tol: float = 1e-8, max_iter: int = 200) -> np.ndarray:
    """Remove several sets of fixed effects from each column by alternating projections."""
    out = values.astype(np.float64, copy=True)
    counts = [np.bincount(g) for g in groups]
    for _ in range(max_iter):
        before = out.copy()
        for g, n in zip(groups, counts, strict=True):
            for j in range(out.shape[1]):
                out[:, j] -= (np.bincount(g, weights=out[:, j]) / n)[g]
        if np.max(np.abs(out - before)) < tol:
            break
    return out


def clustered_ols(y: np.ndarray, x: np.ndarray, clusters: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    xtx_inv = np.linalg.inv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    resid = y - x @ beta
    k = x.shape[1]
    scores = np.zeros((clusters.max() + 1, k))
    for j in range(k):
        scores[:, j] = np.bincount(clusters, weights=x[:, j] * resid, minlength=clusters.max() + 1)
    meat = scores.T @ scores
    n_clusters = len(np.unique(clusters))
    adj = n_clusters / (n_clusters - 1)
    cov = adj * xtx_inv @ meat @ xtx_inv
    return beta, np.sqrt(np.diag(cov))


def codes(*cols: pd.Series) -> np.ndarray:
    return pd.MultiIndex.from_arrays(cols).factorize()[0] if len(cols) > 1 else cols[0].factorize()[0]


def fit(df: pd.DataFrame) -> tuple[float, float, float]:
    y = np.log(df["sale_amount"].to_numpy())
    x = np.column_stack([np.log(df["discount"].to_numpy()), df["activity_flag"].to_numpy(dtype=float)])
    groups = [codes(df["store_id"], df["product_id"]), codes(df["city_id"], df["dt"])]
    z = demean(np.column_stack([y, x]), groups)
    beta, se = clustered_ols(z[:, 0], z[:, 1:], codes(df["product_id"]))
    return float(beta[0]), float(se[0]), float(beta[1])


def shrink(betas: np.ndarray, ses: np.ndarray) -> tuple[np.ndarray, float, float]:
    w = 1 / ses**2
    mu = float(np.sum(w * betas) / np.sum(w))
    tau2 = max(0.0, float(np.var(betas, ddof=1) - np.mean(ses**2)))
    return mu + tau2 / (tau2 + ses**2) * (betas - mu), mu, tau2**0.5


def holdout(train: pd.DataFrame, test: pd.DataFrame, beta: float) -> dict:
    """WAPE of a naive 14-day mean vs the same mean scaled by (discount / mean discount)^beta."""
    last = train[train["dt"] > train["dt"].max() - pd.Timedelta(days=14)]
    base = last.groupby(["store_id", "product_id"]).agg(q=("sale_amount", "mean"), d=("discount", "mean"))
    t = test.join(base, on=["store_id", "product_id"], how="inner")
    t = t[(t["d"] > 0) & (t["discount"] > 0)]
    t["naive"] = t["q"]
    t["model"] = t["q"] * (t["discount"] / t["d"]) ** beta

    def wape(rows: pd.DataFrame, col: str) -> float:
        return float(np.abs(rows[col] - rows["sale_amount"]).sum() / rows["sale_amount"].sum())

    deeper = t[t["discount"] < 0.9 * t["d"]]
    shallower = t[t["discount"] > 1.1 * t["d"]]
    return {
        "rows_deeper_cut": int(len(deeper)),
        "wape_naive_deeper_cut": round(wape(deeper, "naive"), 3),
        "wape_model_deeper_cut": round(wape(deeper, "model"), 3),
        "rows_shallower": int(len(shallower)),
        "wape_naive_shallower": round(wape(shallower, "naive"), 3),
        "wape_model_shallower": round(wape(shallower, "model"), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "backend/.data/freshretailnet")
    args = parser.parse_args()

    cols = [
        "city_id",
        "store_id",
        "first_category_id",
        "product_id",
        "dt",
        "sale_amount",
        "stock_hour6_22_cnt",
        "discount",
        "activity_flag",
    ]
    train = pd.read_parquet(fetch(args.data_dir, "train"), columns=cols)
    test = pd.read_parquet(fetch(args.data_dir, "eval"), columns=cols)
    for frame in (train, test):
        frame["dt"] = pd.to_datetime(frame["dt"])

    in_stock = train[(train["stock_hour6_22_cnt"] == 0) & (train["sale_amount"] > 0) & (train["discount"] > 0)]
    print(f"fitting pooled model on {len(in_stock):,} in-stock rows ...")
    beta, se, gamma = fit(in_stock)

    rows = []
    for cat, sub in in_stock.groupby("first_category_id"):
        n_series = sub.groupby(["store_id", "product_id"]).ngroups
        if n_series < MIN_SERIES_PER_CATEGORY or sub["discount"].nunique() < 3:
            continue
        b, s, _ = fit(sub)
        rows.append((int(cat), n_series, b, s))
    cats = pd.DataFrame(rows, columns=["category", "series", "beta_raw", "se"])
    cats["beta_shrunk"], mu, tau = shrink(cats["beta_raw"].to_numpy(), cats["se"].to_numpy())
    band = (float(np.percentile(cats["beta_shrunk"], 10)), float(np.percentile(cats["beta_shrunk"], 90)))
    ho = holdout(train, test, beta)

    params = {
        "source": "FreshRetailNet-50K (Dingdong Ltd.), CC BY 4.0",
        "revision": REVISION,
        "fitted_on": date.today().isoformat(),
        "method": "two-way FE (store x SKU, city x date) OLS on log sales vs log discount, in-stock days",
        "pooled": {
            "elasticity": round(beta, 3),
            "se_cluster_product": round(se, 3),
            "activity_lift_log": round(gamma, 3),
        },
        "band_p10_p90": [round(band[0], 3), round(band[1], 3)],
        "categories": [
            {
                "category": r.category,
                "series": r.series,
                "elasticity": round(r.beta_shrunk, 3),
                "raw": round(r.beta_raw, 3),
                "se": round(r.se, 3),
            }
            for r in cats.sort_values("beta_shrunk").itertuples()
        ],
        "shrinkage": {"mu": round(mu, 3), "tau": round(tau, 3)},
        "holdout": ho,
        "applies_to": "price cuts only (overstates losses when a discount ends)",
    }
    PARAMS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PARAMS_OUT.write_text(json.dumps(params, indent=2) + "\n")

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(f"""# Evidence: price elasticity

Reproduce: `cd backend && uv run --group fit python scripts/fit_elasticity.py`, which writes
`backend/src/marginarena/engine/data/elasticity.json` and this file.

- **Data:** FreshRetailNet-50K, Dingdong Ltd., CC BY 4.0, revision `{REVISION[:12]}`, checked by SHA-256. It is real online fresh-grocery orders from 18 Chinese cities in 2024. We use it as an e-commerce starting point: Sellers can override any SKU.
- **Sample:** {len(in_stock):,} store × SKU × day rows that were fully in stock and had positive sales.
- **Pooled elasticity: {beta:.2f}** (cluster-robust SE {se:.2f}). A 10% price cut lifts unit sales by about {(0.9**beta - 1) * 100:.0f}% (0.9^β, as the engine's demand model computes it).
- **Category elasticities:** {len(cats)} categories with at least {MIN_SERIES_PER_CATEGORY} series, after shrinkage. The p10–p90 band is {band[0]:.2f} to {band[1]:.2f} (μ {mu:.2f}, τ {tau:.2f}).

## Holdout (the dataset's own eval week)

Each model predicts daily sales for a store × SKU from its last 14 training days. The table shows WAPE (lower is better).

| Days | Rows | Naive 14-day mean | Mean × (discount ratio)^β |
|---|---|---|---|
| Discount deepened >10% | {ho["rows_deeper_cut"]:,} | {ho["wape_naive_deeper_cut"]:.3f} | **{ho["wape_model_deeper_cut"]:.3f}** |
| Discount became shallower >10% | {ho["rows_shallower"]:,} | {ho["wape_naive_shallower"]:.3f} | {ho["wape_model_shallower"]:.3f} |

The engine applies elasticity to **price cuts only**, because the constant-elasticity model is not reliable when a discount ends.

## Limits

- Perishable groceries are not general marketplace goods.
- Category names are anonymised.
- The window contains no 11.11 Campaign.
- Discounts are set by the retailer, so the estimate may be biased toward zero. The literature mean is about −2.6.
""")
    print(json.dumps(params["pooled"]), "band", params["band_p10_p90"], "holdout", ho)


if __name__ == "__main__":
    main()
