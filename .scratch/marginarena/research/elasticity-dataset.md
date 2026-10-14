# Research: which public dataset should drive price elasticity?

Ticket: [02-elasticity-dataset](../issues/02-elasticity-dataset.md). Researched 14 Oct 2026 against primary sources. Every claim cites a numbered source (list at the end). **[A]** marks our own exploratory analysis of the downloaded files on 14 Oct 2026. Those scratch scripts are not in the repo; the build script should reproduce the numbers.

## Short answer

**Primary: FreshRetailNet-50K** (Dingdong Ltd.). It is CC BY 4.0, needs no login, and is **115 MB** to download (two parquet files) [1][2].

- The data is real online-order data from Dingdong's "frontier warehouse model for fresh e-commerce" (30-minute delivery) in 18 Chinese cities, March to June 2024 [4].
- It has 4.85M store × SKU × day rows across 50,000 series, 898 stores and 865 SKUs [1].
- Each row carries a daily **discount rate** (1.0 = full price, 0.9 = 10% off), an **activity (campaign) flag**, a holiday flag, weather, and **hourly stockout annotations** [1].
- Price variation is large: 51% of store-SKU-days are discounted, and 97% of series vary their discount over time [A].

It is the only candidate that is all of these: e-commerce, Asian, promotion-flagged, rich in price variation, and under a licence that allows use in an MIT repository.

**Method:** a log-log fixed-effects regression of units on the discount rate, using fully in-stock days only. The fixed effects are store×SKU and city×date. The activity flag is a control, standard errors are clustered by SKU, and the elasticity is estimated per category with empirical-Bayes shrinkage toward the pooled value.

- First pass [A]: pooled elasticity **−1.52** (SE 0.13) on in-stock days, and −1.39 (SE 0.11) on all days. Shrunk category elasticities range from about −0.6 to −2.9.
- Out-of-sample check on the held-out week [A]: on days where the discount deepened by more than 10%, scaling a naive 14-day baseline by the pooled elasticity cut the error (WAPE) from **0.403 to 0.326**.

**Fallback: The Complete Journey 2.0** (84.51°), through the `completejourney` R package. It is declared **CC0** on CRAN [7], downloads as about 38 MB of `.rds` files from GitHub without a login [9], and covers US grocery and general merchandise.

- Each transaction line includes the loyalty discount, the manufacturer-coupon discount (similar to a voucher) and units. A separate table gives display and mailer promotion flags by product × store × week [8][9].
- Caveat: the CC0 declaration comes from the package authors. The upstream 84.51° terms page (`www.8451.com/area51`) did not resolve on 14 Oct 2026, so it could not be checked.

**Rejected despite good fields, because of their licences:**

- dunnhumby "Breakfast at the Frat": research or non-commercial use only, no modification, and a gated form [11][12].
- M5/Walmart: non-commercial only, no redistribution [13].
- Dominick's: academic research only [19].
- JD.com MSOM: MSOM members only [20].

No usable Southeast-Asian dataset exists. Shopee and Tokopedia data are scraped snapshots with no sales time series and doubtful rights [22][23][24].

## Comparison table

Legend for the last three columns: (a) can a build script download it without a login or accepting terms; (b) may we commit derived elasticity parameters to a public MIT repo; (c) may we commit the raw data.

| Dataset | Source, channel | Price per unit per period | Units | Promo flags | Granularity, span | Download size | Licence | (a) | (b) | (c) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **FreshRetailNet-50K** [1][4] | Dingdong Ltd., 18 Chinese cities. Fresh-grocery **e-commerce** fulfilled from front warehouses [4] | Daily `discount` = ratio to list price. No absolute price [1] | `sale_amount`, normalised by one global coefficient [1] | `activity_flag`, `holiday_flag`, hourly stockout status [1] | Store × SKU × day, plus hourly. 2024-03-28 to 2024-07-02, 97 days [A] | 106.4 MB train + 8.4 MB eval parquet [2] | **CC BY 4.0**. The README says it is "ready for commercial/non-commercial use" [1] | Yes. Not gated [2b] | **Yes, with attribution** [5] | Licence allows it, but `train.parquet` is 101.5 MiB, over GitHub's 100 MiB limit [6] | **Primary** |
| **The Complete Journey 2.0** (`completejourney`) [7][8] | 84.51°. US grocery panel of 2,469 households over one year [7] | Derived from `sales_value`, `retail_disc`, `coupon_disc` and `coupon_match_disc` per line [9] | `quantity` [9] | `display_location` and `mailer_location` by product × store × week. Loyalty discount and coupons per line [8][9] | Transaction line, 1.47M rows [8]. Promotions: 20.9M rows [A] | about 38 MB (`transactions.rds` 12.8 MB, `promotions.rds` 25.0 MB) [9] | **CC0** as declared on CRAN [7]. Upstream terms not verifiable | Yes. Raw GitHub files [9] | Yes [7] | Yes [7] (caveat above) | **Fallback** |
| UCI Online Retail II [10] | UK non-store online gift-ware retailer. "Many customers … are wholesalers" [10] | `Price` per invoice line [10] | `Quantity` [10] | None [10] | Invoice line, 2009-12-01 to 2011-12-09, 1,067,371 rows [10] | 43.5 MB [10] (45.6 MB zip [A]) | **CC BY 4.0** [10] | Yes | Yes | Yes | Viable last resort. Unit price falls with order size (within-SKU correlation of log quantity and log price is −0.45 [A]), which biases elasticity |
| dunnhumby Breakfast at the Frat [11] | US grocery. Four categories, 156 weeks [11] | Base price and shelf price by product × store × week [11] | Units, visits, households, spend [11] | Sale tag (feature), in-store display [11] | Product × store × week | 30.7 MB zip [11] | Gated form with a required "I have read and agree to the dunnhumby Source Files terms of use" checkbox, and the link arrives by email [11]. Terms: "solely for research, personal or non-commercial purposes" and "not modified or altered in anyway" [12] | **No**. The user would have to accept terms | No | No | Rejected (licence) |
| dunnhumby The Complete Journey (original) [11] | US grocery. 2,500 households over two years [11] | From transactions | Yes | Campaigns, coupons [11] | Transaction | Large [11] | Same gate and terms as above [11][12] | No | No | No | Rejected (licence) |
| M5 Forecasting (Walmart) [13][15] | Walmart. 3,049 products, 10 stores in CA, TX and WI [15] | Weekly `sell_price` by store × item [15] | Daily units [15] | No promo column. Only SNAP days and events [15] | 2011-01-29 to 2016-06-19 [15] | Kaggle files | "Non-commercial purposes only"; "not … redistribute" [13]. Data licence: "Subject to Competition Rules" [14] | No (Kaggle login and rules acceptance) [14] | No | No | Rejected (licence) |
| Corporación Favorita [16] | Ecuador grocery | **No price field** [16] | `unit_sales` [16] | `onpromotion` [16] | Store × item × day | Kaggle files | "Subject to Competition Rules" [16] | No (login) [16] | No | No | Rejected (no price, licence) |
| Olist Brazilian E-Commerce [17] | Brazilian **marketplace**, multiple sellers [17] | `price` and `freight_value` per order item [A] | One row per item [A] | None | About 100k orders, 2016 to 2018 [17]. Median product sold **once**; only 174 products sold 50 or more units [A] | 44.7 MB zip [A] | **CC BY-NC-SA 4.0** [17]. Share-alike forces derived work onto a BY-NC-SA licence [18] | Anonymous Kaggle API download worked [A] | No (NC and SA conflict with MIT) [18] | No | Rejected (too sparse, licence) |
| Dominick's Finer Foods [19] | US grocery, store-level. Includes randomised pricing experiments [19] | Not checked (in the data manual) | Store-level sales [19] | Not checked | About 9 years, 3,500+ UPCs [19] | Several SAS zips [19] | "For academic research purposes only" [19] | n/a | No | No | Rejected (licence) |
| JD.com MSOM 2020 [20] | China e-commerce ("China's largest retailer"). 31,868 SKUs, March 2018 [20] | Not verified (login-only) | Transactions [20] | Not verified | 1 month [20] | Unknown | Offered "to MSOM members" [20]. The access page redirects to the INFORMS login [20b] | No | No | No | Rejected (access) |
| Instacart 2017 [21] | US online grocery | **No price** (orders and products only) [21] | Item sequences | None | 3M+ orders | Unknown | "For non-commercial use" [21] | Not tested | No | No | Rejected (no price) |
| Shopee / Tokopedia scrapes [22][23][24] | **SEA marketplaces** | Listing price and discount at scrape time [22][23] | Text buckets such as "1rb+ terjual", or none [23] | Discount % [23] | Snapshots, not SKU time series [22][23] | Small samples | CC BY-NC 4.0 [22]. Uploader-asserted Apache-2.0 [23]. "Other" [24]. The rights holder is not the uploader | Partly | No / doubtful | No | Rejected (no time-series price variation, doubtful rights) |
| REES46 multi-category store [25] | E-commerce events with price | Price on each event [25] | Purchase events | None | 7 months | 14.7 GB [25] | "Data files © Original Authors" [25] | Not tested | No | No | Rejected (no open licence; 14.7 GB) |
| Wish summer sales [26] | Wish marketplace scrape | Price and retail price [26] | Bucketed `units_sold`, cross-sectional [26] | Ad boosts | Snapshot | 1.4 MB | CC BY 4.0 (asserted by the uploader) [26] | Yes | Doubtful | Doubtful | Rejected (cross-sectional) |
| Kaggle "Retail Price Optimization" [27] | Unknown provenance | Monthly average unit price [27] | Monthly demand [27] | None | Product × month, 121 KB [27] | 0.1 MB | CC0 [27] | Yes | Yes | Yes | Rejected (credibility, size) |
| Amazon Reviews 2023 [28] | Amazon | Price "at time of crawling" only [28] | **None** [28] | None | One snapshot | Large | Not stated on the page [28] | n/a | n/a | n/a | Rejected (no units) |

## Primary dataset in detail: FreshRetailNet-50K

**What it is**

- The dataset was built by Dingdong Ltd. staff. It covers 898 "stores" (front warehouses) in 18 Chinese cities, March to June 2024. Hourly sales "are derived from online order transaction systems" [4].
- "Marketing campaigns are annotated with explicit discount rate ranges (e.g., 15%–30% price reductions)" [4].

**Fields** [1]

- Identifiers: `city_id`, `store_id`, and a category hierarchy `management_group_id` > `first_category_id` > `second_category_id` > `third_category_id` > `product_id`. All are **encoded integers, with no category names**.
- `dt`, then `sale_amount` and the 24-value `hours_sale`.
- `stock_hour6_22_cnt` and the 24-value `hours_stock_status`.
- `discount`, `holiday_flag` and `activity_flag`.
- Weather: `precpt`, `avg_temperature`, `avg_humidity`, `avg_wind_level`.

**Size and access**

- `data/train.parquet` is 106,436,287 bytes and `data/eval.parquet` is 8,440,124 bytes [2]. The dataset is not gated [2b].
- Both files downloaded anonymously, and the SHA-256 of `train.parquet` matched the LFS object ID `6706832d…a3d` [A].
- Since v1.0 (7 May 2025), the commit history shows only README edits [3].
- Pin revision `c374e85975c82816c495acfa904cc55ab14a47d3` and download from `https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K/resolve/<rev>/data/{train,eval}.parquet`. Verify these hashes [A]:
  - train: `6706832db892bbae4969c19d87e07975d2543d2ba7d7d4756360654785de5a3d`
  - eval: `1b118840664280c6b88bffc84c80ee1f54c05d911e354b7599e5da10995e960e`

**Splits** [A]

- Train: 4.5M rows, 2024-03-28 to 2024-06-25 (90 days).
- Eval: 350k rows, 2024-06-26 to 2024-07-02 (7 days), on the same 50,000 series.

**Price variation** [A]

- 51.5% of store-SKU-days have `discount < 1`.
- The median within-series SD of log(discount) is 0.067, and 96.8% of series vary.
- Across stores, the SD of log(discount) for the same product on the same day has a median of only 0.021. Discounts are therefore set centrally, per SKU and day, not store by store. This matters for endogeneity (see Pitfalls).

**Promo flag** [A]

- `activity_flag = 1` on 37.8% of rows. 97.7% of activity days are discounted, against 23.3% of non-activity days.
- The flag therefore marks a campaign (like a marketplace Campaign) and adds a non-price lift on top of the price cut.

**Censoring** [A][4]

- 44% of training store-SKU-days have at least one stockout hour between 06:00 and 22:00 [A].
- The authors report that "deeper price reductions … increase stockouts" [4], so including stockout days biases elasticity toward zero.

**Domain gap**

- These are perishable groceries ("vegetables, meat & poultry & eggs, fruits, seafood, frozen goods") [4], not the general merchandise a Shopee Seller lists at 11.11.
- Because categories are encoded, they cannot be mapped to Seller categories by name [1].

## Licence findings

**FreshRetailNet-50K: CC BY 4.0 [1]**

- The licence lets anyone "reproduce and Share" the material and "produce, reproduce, and Share Adapted Material" [5].
- Conditions: keep the attribution and licence notices, and "indicate if You modified the Licensed Material" [5].
- An adapter's own licence "must not prevent recipients of the Adapted Material from complying with this Public License" [5]. An MIT-licensed repo that carries a CC BY notice for the derived parameters meets this.
- The README has said CC BY 4.0 since v1.0 [3]. The line "ready for commercial/non-commercial use" was added in a later README edit [1][3].
- What we may do:
  - (a) download it in a build script;
  - (b) commit derived elasticity tables, with an attribution and changes notice in the README and in a NOTICE file or a header in the parameters file;
  - (c) commit the raw files only if they were split or put on Git LFS, because `train.parquet` exceeds GitHub's 100 MiB block [6]. Downloading at build time is simpler.

**completejourney: CC0 [7]**

- CC0 means no conditions. The raw `.rds` files sit in the package's GitHub `data/` folder [9].
- Risk: the CC0 grant is the package authors' (Boehmke, Mortimer) [7]. The data "originated from 84.51°" [9], and that site could not be reached to confirm its terms.
- Mitigation: credit 84.51° and the package anyway, and prefer the primary dataset.

**UCI Online Retail II: CC BY 4.0 [10]**

- Cite Chen (2012), DOI 10.24432/C5CG6D [10].

**Rejected licences**

- dunnhumby: the site licence limits material to "research, personal or non-commercial purposes", forbids modification, and forbids storing or adapting it "for any other purpose" without written permission [12]. Downloads also need an email and a ticked terms box [11]. We must not do that for the user. A derived-parameter commit under MIT would conflict with these terms.
- M5: "non-commercial purposes only" and "not to transmit, duplicate, publish, redistribute" [13].
- Olist: NonCommercial plus ShareAlike. The adapter's licence "must be a Creative Commons license with the same License Elements" [18], which is incompatible with MIT for derived files.
- Dominick's: "academic research purposes only" [19].
- Instacart: "non-commercial use" [21].
- JD.com: limited to MSOM members [20].

## Estimation method (for the build script)

**Data preparation**

1. Load both parquet files at the pinned revision.
2. Keep rows with `stock_hour6_22_cnt == 0`, which are fully in stock, and `sale_amount > 0`. Zeros are 4.5% of rows [A]. This leaves about 2.46M training rows [A].

**Model**

$$\log q_{s,i,t} = \alpha_{s,i} + \lambda_{city,t} + \beta_{c(i)}\,\log d_{s,i,t} + \gamma\,\text{activity}_{s,i,t} + \varepsilon_{s,i,t}$$

- **q** is `sale_amount`. The global normalising coefficient [1] is absorbed by $\alpha$.
- **d** is the discount rate, so $\beta$ is the own-price elasticity relative to list price.
- **Fixed effects:**
  - store×SKU absorbs level, assortment and the normaliser;
  - city×date absorbs holidays, weather and city-wide demand shocks. Collinear covariates such as `holiday_flag` drop out [A].
- **Category slopes:** estimate $\beta_c$ at `first_category_id` level (32 categories) [A]. Then apply empirical-Bayes shrinkage: $\hat\beta_c^{EB} = \mu + \frac{\tau^2}{\tau^2+se_c^2}(\hat\beta_c-\mu)$, with $\mu$ the precision-weighted mean and $\tau^2$ by method of moments.
  - Do **not** ship raw per-SKU slopes. Of 224 SKUs with at least 2,000 in-stock observations, per-SKU elasticities have a median of −0.62 and **23% are positive** [A]. That is noise.
- **Standard errors:** cluster by `product_id`.
- **Tooling:** `pyfixest` (MIT) does OLS and Poisson with high-dimensional fixed effects [30]. Plain numpy alternating projections also work and ran in about 10 s on a laptop [A].
- **Robustness:** a Poisson pseudo-ML (PPML) model with the same fixed effects (`pf.fepois`) keeps the zero-sales days [30].

**First-pass results** [A]

| Specification | β (log discount) | SE (cluster SKU) | Activity lift γ |
|---|---|---|---|
| All days, sales > 0 (4.30M rows) | −1.39 | 0.11 | +0.05 |
| In-stock days only (2.46M rows) | **−1.52** | 0.13 | +0.07 |
| In-stock, non-activity days only | −2.07 | n/a | n/a |
| In-stock, activity days only | −1.58 | n/a | n/a |
| 22 first-level categories with at least 200 series, raw → shrunk | −0.46…−3.05 → −0.55…−2.91. Precision-weighted μ = −1.29, τ = 0.73 | n/a | n/a |

As a sanity anchor, a meta-analysis of 1,851 published estimates puts the average price elasticity at **−2.62**. It also finds that correcting for endogeneity makes elasticities larger in magnitude [29]. Our −1.4 to −1.5 is within range and, if anything, conservative.

**How the engine should use it (proposal for the spec)**

- Units multiplier = $(p_{promo}/p_{ref})^{\beta}\cdot e^{\gamma\cdot \text{campaign}}$.
- Apply it to **price cuts only**. See the asymmetry pitfall.
- Show an uncertainty band from the spread of category elasticities, for example the shrunk p10 to p90.
- How a Seller voucher maps to an effective price cut (for example, through a claim rate) is a spec decision, not settled here.

## Known pitfalls

- **Endogeneity.** Dingdong chooses its discounts:
  - markdowns on slow or ageing stock push β toward zero;
  - campaigns timed for high-demand days push it away from zero.
  - Mitigations: the fixed effects, plus the observation that discounts barely vary across stores on a given product-day (median SD 0.021 [A]). Discounts are therefore set centrally and are unlikely to react to *local* demand shocks.
  - The meta-analysis evidence [29] suggests any remaining bias makes our elasticity too small in magnitude, not too large.
  - Optional upgrade: a Hausman-style instrument (the same SKU's discount in other cities that day).
- **Censoring.** Deeper discounts cause more stockouts [4]. Using in-stock days only moved β from −1.39 to −1.52 [A]. A further option is the authors' two-stage latent-demand recovery using `hours_stock_status` [4].
- **Asymmetry and post-promotion behaviour.** In the held-out week [A]:
  - on days where the discount *deepened* by more than 10%, actual sales were 1.46× the naive baseline and the elasticity predicted 1.50×;
  - on days where it became *shallower*, actual sales were 0.93× and the elasticity predicted 0.68×.
  - Constant elasticity fits cuts well and badly overstates losses when a discount ends. MarginArena prices cuts, so apply β only to cuts. The window cannot measure post-promo dips or stockpiling.
- **Normalised units.** On 2026-10-09 the README changed the `sale_amount` description from "daily sales amount" to "daily sales quantity" [3].
  - If the old wording was right, the values are revenue and the quantity elasticity is β − 1.
  - Pin the current revision, cite its definition, and state this assumption in the README.
- **Domain transfer.**
  - The data is perishable grocery in China, 2024. The window does not include 11.11 (it ends 2 July [A]), and categories are unlabeled [1].
  - Present the result as an e-commerce prior with a band, let the Seller override it, and say so in the video and README.
  - completejourney gives a non-food cross-check, for example DRUG GM [A].
- **Short window.** 97 days [A]. No long-run or reference-price dynamics can be estimated.

## Out-of-sample validation the team can report

The design uses the dataset's own split. Fit on the 90-day `train` split and score the 7-day `eval` split (2024-06-26 to 07-02) on in-stock days. The metric is WAPE = Σ|actual − predicted| / Σactual.

- **Baseline:** a naive, price-blind forecast, equal to the series' mean in-stock sales over the last 14 training days.
- **Model:** the same baseline × (d / d̄₁₄)^β, where d̄₁₄ is the series' mean discount over those 14 days.

Results [A]:

| Holdout subset | n | WAPE naive | WAPE naive × category β | WAPE naive × pooled β = −1.4 |
|---|---|---|---|---|
| All eval in-stock days | 205,301 | 0.324 | 0.397 (cuts-only variant: **0.319**) | 0.403 |
| **Promo-start days**: discount at least 10% deeper than d̄₁₄ | 14,224 | 0.403 | 0.353 | **0.326** |
| Discount at least 10% shallower than d̄₁₄ | 32,102 | 0.356 | 0.395 | 0.434 |

**Headline for the README and video:** on held-out promo-start days, the elasticity-adjusted forecast reduced error from 0.403 to 0.326 WAPE, about 19% lower than the naive baseline. With category β, the predicted lift was 1.50× against an actual 1.46×.

Also report the failure case honestly: the model overstates losses when a discount ends, which is why the engine applies β to cuts only.

The pooled β beat the unshrunk category β, which supports shrinkage. Also report a category-level lift calibration: across 13 categories, the correlation between actual and predicted lift was 0.44 [A].

## Fallback in detail: completejourney

**Fields** [9]

- Transactions: `household_id`, `store_id`, `basket_id`, `product_id`, `quantity`, `sales_value`, `retail_disc` (loyalty card), `coupon_disc` (manufacturer coupon), `coupon_match_disc`, `week`, `transaction_timestamp`.
- Promotions: `display_location` and `mailer_location` by product × store × week [8].

**First pass** [A]

- Sample: 3,402 products with at least 40 active weeks, with product and week fixed effects plus display and mailer shares.
- Pooled elasticity −1.02, display +0.12, mailer +0.49.
- By department: GROCERY −1.36, DRUG GM −1.23, MEAT-PCKGD −1.74, PRODUCE −0.41.

**Weaknesses**

- It is a household panel, so volumes are thin: the median is 4 units per product-week [A].
- It is brick-and-mortar US grocery.
- Its CC0 rests on the package [7].

## Sources

1. FreshRetailNet-50K dataset card, Hugging Face, revision c374e85: https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K/blob/c374e85975c82816c495acfa904cc55ab14a47d3/README.md
2. FreshRetailNet-50K file tree with byte sizes (HF API): https://huggingface.co/api/datasets/Dingdong-Inc/FreshRetailNet-50K/tree/main?recursive=true
   2b. Dataset metadata (`"gated": false`, licence, revision SHA): https://huggingface.co/api/datasets/Dingdong-Inc/FreshRetailNet-50K
3. FreshRetailNet-50K commit history (v1.0 on 2025-05-07; README-only edits since, including the 2026-10-09 "amount" → "quantity" wording): https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K/commits/main. Old card at v1.0: https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K/blob/01a4be637d72261d180f14a96c3c1aec8c0c1e1e/README.md
4. Wang et al., "FreshRetailNet-50K: A Stockout-Annotated Censored Demand Dataset…", arXiv:2505.16319 (Dingdong Ltd.; fresh e-commerce; data integration; stockout and discount analysis): https://arxiv.org/abs/2505.16319
5. Creative Commons Attribution 4.0 legal code: https://creativecommons.org/licenses/by/4.0/legalcode.en
6. GitHub Docs, "About large files on GitHub" (100 MiB block): https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
7. CRAN, `completejourney` (License: CC0; 2,469 households, one year; from 84.51° Complete Journey 2.0): https://cran.r-project.org/web/packages/completejourney/index.html
8. `completejourney` README (tables, 1,469,307 transactions, promotions): https://github.com/bradleyboehmke/completejourney
9. `completejourney` data folder and field docs: https://github.com/bradleyboehmke/completejourney/tree/master/data, https://github.com/bradleyboehmke/completejourney/blob/master/R/transactions.R, https://github.com/bradleyboehmke/completejourney/blob/master/R/get_data.R
10. UCI ML Repository, Online Retail II (CC BY 4.0; 1,067,371 instances; 43.5 MB; DOI 10.24432/C5CG6D): https://archive.ics.uci.edu/dataset/502/online+retail+ii
11. dunnhumby Source Files (dataset descriptions; gated download form; BATF zip asset 30,714,553 bytes in page metadata): https://www.dunnhumby.com/source-files/
12. dunnhumby Terms & Conditions: https://www.dunnhumby.com/terms-and-conditions/
13. Kaggle, M5 Forecasting – Accuracy, Rules §7 Competition Data: https://www.kaggle.com/competitions/m5-forecasting-accuracy/rules
14. Kaggle, M5 data page ("License: Subject to Competition Rules"; sign-in needed): https://www.kaggle.com/competitions/m5-forecasting-accuracy/data
15. M5 Competitors' Guide (files, fields, dates, 3,049 products, 10 stores): https://github.com/Mcompetitions/M5-methods/blob/master/M5-Competitors-Guide.pdf
16. Kaggle, Corporación Favorita data page (fields; "Subject to Competition Rules"): https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting/data
17. Kaggle, Brazilian E-Commerce Public Dataset by Olist (CC BY-NC-SA 4.0): https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
18. Creative Commons BY-NC-SA 4.0 legal code: https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en
19. Kilts Center, Dominick's dataset: https://www.chicagobooth.edu/research/kilts/research-data/dominicks
20. Shen et al. (2020), "JD.com: Transaction-Level Data for the 2020 MSOM Data Driven Research Challenge", M&SOM 26(1): https://doi.org/10.1287/msom.2020.0900
    20b. Access page (redirects to the INFORMS login): https://connect.informs.org/msom/events/datadriven2020
21. Instacart, "3 Million Instacart Orders, Open Sourced": https://tech.instacart.com/3-million-instacart-orders-open-sourced-d40d29ead6f2
22. rebrowser/shopee-dataset (CC BY-NC 4.0 preview; premium-locked price fields): https://huggingface.co/datasets/rebrowser/shopee-dataset
23. Kaggle, Tokopedia listings (snapshot; `Terjual` text buckets): https://www.kaggle.com/datasets/pandaa12/indonesia-e-commerce-dataset-tokopedia-listings
24. Kaggle, Shopee Sales Data Apr–May 2023 (interview sample; licence "Other"): https://www.kaggle.com/datasets/yoongsin/shopee-sample-data
25. Kaggle, eCommerce behavior data from multi category store (REES46): https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store
26. Kaggle, Sales of summer clothes in e-commerce Wish: https://www.kaggle.com/datasets/jmmvutu/summer-products-and-sales-in-ecommerce-wish
27. Kaggle, Retail Price Optimization: https://www.kaggle.com/datasets/suddharshan/retail-price-optimization
28. Amazon Reviews 2023 (McAuley Lab): https://amazon-reviews-2023.github.io/
29. Bijmolt, Van Heerde and Pieters (2005), "New Empirical Generalizations on the Determinants of Price Elasticity", JMR 42(2) (abstract: mean −2.62; endogeneity raises magnitude): https://doi.org/10.1509/jmkr.42.2.141.62296
30. pyfixest (MIT; OLS, IV and Poisson with high-dimensional fixed effects): https://github.com/py-econometrics/pyfixest

Licence and size metadata for Kaggle datasets [17][23][24][25][26][27] was read from Kaggle's public dataset API, `https://www.kaggle.com/api/v1/datasets/view/<owner>/<slug>`.

[A] Own analysis, 14 Oct 2026, on files downloaded to the session scratchpad (FreshRetailNet-50K at the pinned revision, Online Retail II, Olist, completejourney). These figures are exploratory and should be reproduced by the build script before they go into the README.
