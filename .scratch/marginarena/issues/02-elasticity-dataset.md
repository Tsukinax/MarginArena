# 02 Which public dataset should drive price elasticity?

Type: research
Status: resolved
Blocked by: none

## Question

Which public dataset gives a credible SKU-level price-elasticity estimate for marketplace promotions? It needs real price variation and units sold, ideally with promotion flags, and preferably from e-commerce or Southeast Asia. It also needs a licence that allows use in a public MIT repository. Which estimation method fits it, and how large is the dataset to download?

Findings: `.scratch/marginarena/research/elasticity-dataset.md`

## Answer

Full findings: [research/elasticity-dataset.md](../research/elasticity-dataset.md)

### Dataset

- **Primary: FreshRetailNet-50K** (Dingdong, Hugging Face).
  - Real online fresh-grocery orders: 865 SKUs × 898 stores × 97 days in 2024, in 18 Chinese cities.
  - Fields: a daily discount rate, a campaign flag, and hourly stockout records.
  - Licence: CC BY 4.0. It downloads at build time (115 MB, pinned revision and SHA-256). We commit the derived elasticities with attribution, not the raw data, because `train.parquet` is over 100 MB.
- **Fallback:** The Complete Journey 2.0 (CC0 as declared on CRAN, not confirmed with 84.51°). It is US grocery data with coupon and loyalty-discount fields.
- **Rejected for licence or access:** M5/Walmart, dunnhumby, Dominick's, JD, Olist. Favorita and Instacart have no prices, and no usable Southeast-Asian dataset exists.

### Method

- A log-log fixed-effects regression on in-stock days only, with fixed effects for store×SKU and city×date and a control for the campaign flag.
- One elasticity per category, shrunk toward the pooled value.

### First-pass results

- Pooled elasticity −1.52 (SE 0.13). Category values range from about −0.55 to −2.9.
- **Holdout:** on days where the discount deepened by more than 10%, error fell from 0.403 to 0.326 (about −19%) against a naive 14-day average.
- The model does badly when a discount ends, so apply the elasticity to price cuts only and say so openly.

### Risks

- The data is perishable groceries, not general marketplace goods.
- Category names are anonymised.
- There is no 11.11 period in the data.
- `sale_amount` may be revenue rather than quantity: the README changed its wording on 9 Oct 2026.
- The engine should present elasticity with an uncertainty band that the Seller can override.
