# Research: what do Shopee and Lazada Thailand charge Sellers, and how do mega Campaigns work?

Ticket: [03-marketplace-fees](../issues/03-marketplace-fees.md). Researched 14 Oct 2026. Every claim cites a numbered source (list at the end). Each source is marked **P** (primary: the marketplace's own help centre, fee files or announcements, or the Thai Revenue Department) or **S** (secondary: news, blogs and aggregators, used only to fill gaps). **[A]** marks our own counts and arithmetic on the official fee files, done on 14 Oct 2026.

No page needed a login, except where the text says so. Shopee and Lazada publish the category rate tables as PDFs linked from their help centres. We extracted the text of those PDFs for the category counts below. The extracted files are temporary scratch copies and are not in the repo.

## Short answer

**Fees in force on 14 Oct 2026.** Both marketplaces raised fees three times in 2026. The latest changes are **Shopee on 4 Aug 2026** [1] and **Lazada on 1 Aug 2026** [15][16]. We found no newer change announced up to 14 Oct 2026 [29]. Both marketplaces now charge a mid-size FMCG Seller almost the same take rate:

| Fee for an FMCG item (beauty, food, mom & baby, pets) | Shopee Non-Mall | Shopee Mall | Lazada Marketplace | LazMall |
|---|---|---|---|---|
| Commission ("Sale Transaction Fee" / "Marketplace Service Fee"), incl. 7% VAT | **16.05%** [2] | **19.26%** [3] | **16.05%** (15% + VAT) [15][17] | **18.73%** (17.5% + VAT) [16][18] |
| Payment / transaction fee, incl. VAT | 3.21% (3% + VAT) [1] | 3.21% [1] | 3.21% (3% + VAT) [14] | 3.21% [14] |
| Programme fee for free-shipping and voucher support, incl. VAT | PRIME Seller: **8.56%** (8% + VAT) [6] | 8.56% [6] | Premium Package: **8.56%** (8% + VAT) [14][15] | 8.56% [16] |
| Fixed fee per order | **฿1.07** (฿1 + VAT). Waived if the shop had ≤100 completed orders in the past 30 days [1][5] | ฿1.07 [1][5] | none [14] | none [14] |
| **Total, if the Seller is in the programme** | **27.82% + ฿1.07** | **31.03% + ฿1.07** | **27.82%** | **30.50%** |

- **Base.** Every percentage fee is charged on the item price **after Seller-funded discounts** (the Seller's own price cut and Seller vouchers). Platform-funded discounts do **not** lower the base. The payment fee also covers the shipping fee the buyer pays [1][14].
- **VAT.** Shopee quotes commission **including** VAT. It quotes the payment fee and the ฿1 fee **excluding** VAT [1]. Lazada quotes every fee excluding VAT and adds 7% on top [14]. Thailand's VAT stays at 7% until 30 Sep 2027 [27][28].
- **Category matters most for electronics.** Phones, laptops and cameras pay 7.49% on Shopee and 5.89% on Lazada. Fashion pays 17.12% (Shopee Non-Mall and Lazada Marketplace) [2][17].

**Campaigns.** Neither marketplace adds a fee during a Campaign. A Campaign costs the Seller money in three ways:

1. The discount. The Campaign price must sit inside a band set by the platform:
   - Shopee shows the lowest price in the last 30 days and the average price in the last 60 days as references [7].
   - Lazada auto-approves only prices at or below its "recommended price", which is the 90-day average selling price. Earlier Mega and A+ Campaign prices are left out of that average [23][24].
2. Effectively compulsory programmes.
   - Lazada mega Campaigns require Free Shipping Special and Campaign Voucher, now sold together as the Premium Package [21][22].
   - On Shopee, campaign and Flash Sale access is a PRIME Seller benefit [6], and some Campaigns are open to PRIME Sellers only [7].
3. Co-funding. This is optional on Shopee and sometimes mandatory on Lazada:
   - Shopee itself funds an extra item discount (a "rebate") and repays it to the Seller [7].
   - In Lazada's MEGA Campaigns, "Lazada Bonus" is a mandatory agreement [23]. Its Seller/Lazada split is not published for Thailand.

**Invitations.** Both marketplaces deliver invitations inside the Seller Centre. Neither uses email.

- **Shopee.** Each Campaign has a tier (Mega, A+, A, B, Global) and several sessions. Each Campaign lists shop conditions, product conditions, a price band and a discount band. The Seller nominates products, or confirms products that Shopee has pre-nominated [7]. "Easy Nomination" can auto-nominate products down to a floor price the Seller sets, called the **Best Mega Campaign Price** [8].
- **Lazada.** The Seller Centre lists only Campaigns the shop is eligible for. Each has a registration deadline, a Campaign window, mandatory agreements and sub-units (vouchers, main Campaign) [23]. A 9.9 (2026) guide gives a full timeline. Registration closed 4 days before the start, and prices were locked for the Campaign [21].

## 1. Shopee Thailand fee table (in force since 4 Aug 2026)

### 1.1 Fee schedule

Source for every row: the Shopee Fee Policy, help article 77254, revised 3 Jul 2026, effective 4 Aug 2026 00:00 [1], unless another source is cited.

| # | Fee | Rate | VAT | Base | Who pays | Effective / last change |
|---|---|---|---|---|---|---|
| 1 | Payment Transaction Fee | **3%** | excl. (+7% = 3.21%) | What the buyer pays + shipping + Shopee-funded item discount ("Shopee Item PRM") + Shopee Coins. **Excludes Seller-funded discounts.** Not charged on credit-card instalment or Special SPayLater orders, which use rows 6–7 | All Sellers | Unchanged on 4 Aug 2026 |
| 2 | Platform Infrastructure Fee | **฿1 per completed order** | excl. (= ฿1.07) | Per completed order, any payment channel | All Sellers, unless waived: shops with **≤100 completed orders in the previous 30 days** are exempt. Status is recomputed on the 1st of each month [5] | Introduced 15 Sep 2025 [5] |
| 3 | Account Maintenance Fee | ฿20 per month | incl. | Taken from Seller Balance | Inactive Sellers only | Unchanged |
| 4 | Sale Transaction Fee (commission), **Mall** | By category: **7.49–19.26%** [3] | **incl.** | **Original item price − Seller-funded item discounts.** Excludes shipping and other discounts | Mall Sellers | 4 Aug 2026: +1 or +2 points (excl. VAT) in some categories [1] |
| 5 | Sale Transaction Fee (commission), **Non-Mall** | By category: **7.49–17.12%** [2] | **incl.** | Same as row 4 | Non-Mall Sellers | Same as row 4 |
| 4–5a | Small-Seller discount | **−0.5 to −1.5 points** (excl. VAT) | — | Applies when total sales are **≤฿10,000 in the 30 days before the monthly cutoff** | Mall and Non-Mall | 7 Apr 2026 [29 S] |
| 6 | Credit-card instalment fee (replaces row 1) | 3 m **5%**, 6 m **6.5%**, 10 m+ **7%** | excl. | Like row 1 | All Sellers, on instalment orders | +1 point on 7 Apr 2026 [29 S]; unchanged on 4 Aug |
| 7 | Special SPayLater fee (replaces row 1) | 1 m 3%, 2 m 4%, 3 m 5%, 5 m 6.5%, 12 m 7% | excl. | Like row 1 | All Sellers, on these orders | Unchanged on 4 Aug |
| 8 | **PRIME Seller** service fee (optional programme) | **8%** for fashion, lifestyle, FMCG and others; **7–8%** for electronics; 7% for precious jewellery; 6% for investment gold/platinum [6] | **excl.** (+7% = 8.56%) [6] | "Charged per item by category". It applies to **every item sold by a member shop, even on orders that used no voucher** [6]. The base is not published; see note (c) | PRIME Sellers | Table effective 3 Mar 2026. The **per-item fee cap ended on 19 Nov 2025** [6] |

**Collection and refunds.**

- Rows 1, 2 and 4–7 are deducted from sales proceeds after the order completes. Row 3 is taken from Seller Balance [1].
- Shopee "may not charge" rows 1, 2 and 4–7 if the order is cancelled or refunded within the Shopee Guarantee period [1].
- The ฿1.07 fee is refunded only when the whole order is cancelled. A partial cancellation keeps it [5].

**Notes.**

- (a) **What counts as a Seller-funded discount.** Shopee's own tax guide defines Seller revenue as item sales − Seller discounts **and Seller vouchers** + buyer-paid shipping [12]. So Seller vouchers lower the commission base. Shopee vouchers and Shopee rebates do not [1].
- (b) **Shopee-funded item discount.** Shopee repays it to the Seller after the buyer pays. Example: normal price ฿100, Seller offer price ฿90, Shopee discount ฿5. The buyer pays ฿85, and the Seller receives ฿85 plus ฿5 from Shopee [7]. For the Seller, it is revenue-neutral.
- (c) **PRIME fee base: unknown.** The calculation-example page needs a Seller Centre login, so we did not open it [6]. We assume the same base as commission: item price after Seller discounts. Lazada's equivalent fee states that base explicitly [14].
- (d) **Withholding tax (WHT).** Sellers registered as companies must withhold tax on the fees they pay Shopee. Shopee refunds that amount once it receives the 50 Tawi certificate [13]. This affects cash flow only, not margin.

### 1.2 Commission by category, effective 4 Aug 2026

All rates **include VAT**; the figure in brackets excludes it. Taken from Shopee's official rate files [2][3][4]. Each file has 1,437 level-3 categories and four columns: Standard, PRIME, Small, and Small + PRIME [A].

| Category (examples) | Non-Mall standard | Non-Mall Small Seller | Mall standard | Mall Small Seller | Non-Mall before (1 Jun 2026) standard / PRIME |
|---|---|---|---|---|---|
| FMCG: skincare, makeup, food & beverages, mom & baby, pets, health | **16.05%** [15.0] | 14.45% | **19.26%** [18.0] | 17.66% | 13.91% / 12.84% |
| Fashion: women's and men's clothes, shoes, bags, Muslim fashion, watches, luggage | **17.12%** [16.0] | 15.52% | **19.26%** | 17.66% | 14.98% / 13.91% |
| Fashion accessories (rings etc.) | 13.38% | 11.77% | 16.59% | 14.98% | 11.24% / 11.24% |
| Home & living, sports, hobbies, stationery, tickets & vouchers | 16.05% | 14.45% | 19.26% | 17.66% | 13.91% / 12.84% |
| Books | 14.45% (PRIME 13.38%) | 12.84% | 17.66% | 16.05% | 12.31% / 10.17% |
| Small and kitchen appliances (air fryer etc.), earphones | 15.52% [14.5] | 13.91% | 16.59% | 14.98% | 13.38% / 12.31% |
| Large appliances (washing machine, fridge) | 11.24% | 10.70% | 11.77% | 11.24% | 11.24% / 10.17% |
| TVs | 8.56% | 8.03% | 8.56% | 8.03% | 7.49% / 7.49% |
| Mobile phones, tablets, laptops, desktops, cameras, game consoles | **7.49%** [7.0] | 6.96% | 7.49% | 6.96% | 7.49% / 7.49% |
| **Range over all categories** | **7.49–17.12%** | | **7.49–19.26%** | | 7.49–14.98% |

- **Distribution [A].** In the Non-Mall file, 862 of 1,437 categories pay 16.05% and 330 pay 17.12%. In the Mall file, 1,183 of 1,437 pay 19.26%.
- **The PRIME commission discount is mostly gone [A].** On 1 Jun 2026, PRIME Sellers paid about 1.07 points less (for example 12.84% vs 13.91% for FMCG). In the 4 Aug file, the PRIME column equals the standard column in **1,422 of 1,437** categories. The exceptions are books, motorcycles and precious metals. So in most categories a PRIME Seller's commission rose by **+3.21 points** between June and August. This matches the "up to about 3.21 points" increase reported in [30 S].
- **2026 timeline.**
  - 7 Apr: instalment fee +1 point; Small-Seller discount introduced [29 S].
  - 1 Jun: +1.5 points (excl. VAT) in many categories. The "Compare … 1 June 2026" file [4] and [29 S] both show this.
  - 4 Aug: +1 or +2 points (excl. VAT) [1]; PRIME discount removed [2][3].
- **Not in the official fee policy.** Two secondary sources claim things the fee policy [1] does not list:
  - A **5% "technical support fee"** from Feb 2026, for SG, MY, TH and VN [32 S].
  - **0% commission** for a new Seller's first 3 months, capped at 500 orders a month [33 S].

  Neither appears in Shopee Thailand's official fee policy (revised 3 Jul 2026) [1]. Treat both as unverified, and as possibly limited to cross-border or new-shop programmes. Do not put them in the default profile.

### 1.3 PRIME Seller programme (Shopee's free-shipping and voucher programme)

- **What it is.** PRIME Seller is the old **Free Shipping Xtra** (green label) and **Discount Xtra** (yellow label) under a new name [6]. The old "fss-ccb" programme link from the Seller Education article now redirects to the PRIME page [6].
- **Standard benefits** [6]. Buyers can use Shopee-sponsored free-shipping codes and discount or cashback codes on the shop's items. The shop also gets:
  - special tags and more visibility;
  - the chance to join Campaigns and Flash Sale slots;
  - a commission discount. This changed on 4 Aug 2026; see 1.2.
- **Fee.** See 1.1, row 8.
- **Joining and leaving** [6].
  - A form submitted by **Tuesday 23:59** joins the shop that **Friday**.
  - A shop may apply once a month. Membership renews automatically every month.
  - To leave, submit the exit form by the **25th, 23:59**. The shop is removed at the start of the next month.
- **Coins Cashback.** Shopee Thailand has no separate public Coins Cashback programme page any more; the old link redirects to PRIME [6]. A Seller can still create Coins Cashback-type vouchers that it funds itself [9].
  - A 2026 news piece [S] gives 5.35–7.49% for "Free Shipping Xtra or Coins Cashback". It predates the 3 Mar 2026 PRIME table, so we do not use it.

## 2. Lazada Thailand fee table (in force since 1 Aug 2026)

### 2.1 Fee schedule

Source: Lazada Fee Policy (last update 3 Aug 2026) [14], plus the 16 Jul 2026 announcements [15][16].

| Fee | Type | Rate | VAT | Base | Trigger | Effective |
|---|---|---|---|---|---|---|
| Marketplace Service Fee (MSF), **Marketplace** Sellers | Compulsory | By category: **5.5–16%** excl. VAT (5.89–17.12% incl.) [15][17] | +7% | **Item Price Credit − discount funded by Seller** | Successfully delivered orders | 1 Aug 2026 (+2 points excl. VAT in most categories) [15] |
| MSF, **LazMall** Sellers | Compulsory | By category: **5.5–17.5%** excl. VAT (5.89–18.73% incl.) [16][18] | +7% | Same | Same | 1 Aug 2026 [16] |
| Payment Fee | Compulsory | **3%** at item level | +7% (= 3.21%) | **Item Price Credit − Seller discount + shipping paid by buyer** | Same | Unchanged |
| PayLater Seller Interest Subsidy | Optional | 1.25% per month (15% a year) | — | Opted-in items paid with LazadaPayLater over 3, 6, 9 or 12 months | Same | — |
| **Premium Package** (Free Shipping Special + Campaign Voucher bundle) | Optional, but required for mega Campaigns (see 3.2) | **8%** flat [15][16] | +7% (= 8.56%) | **Item Price Credit − Seller discount**, on **every item sold** while in the programme | Same | 1 Aug 2026 (+1 point for most categories) [15] |
| Fixed per-order or platform fee | — | **None** in the fee policy [14] | — | — | — | — |

- **No per-order or per-item caps** appear anywhere in the fee policy [14].
- **Premium Package (PP) rate.** The PP rate follows "the category with the highest sales in the previous quarter", re-evaluated every quarter. At a flat 8%, this no longer matters [14].

**Premium Package history.**

| Effective | Premium Package (excl. VAT) | Free Shipping Special alone | Campaign Voucher alone | Source |
|---|---|---|---|---|
| 1 May 2026 (announced 15 Apr) | 6–8% by category | 6% (was 5%) | 7% (was 6%) | [19] |
| 1 Jul 2026 (announced 8 Jun) | 7–8% by category | sold only as part of PP | sold only as part of PP | [20] |
| 1 Aug 2026 (announced 16 Jul) | **8% flat** | — | — | [14][15][16] |

- The 1 May announcement says joining both programmes separately would cost 13% (6% + 7%), compared with 6–8% for the bundle [19].
- Sellers could opt out of PP during set windows, for example 16–30 Jun 2026 for the July rate. Otherwise membership renewed automatically [20].

**Official worked example** (LazMall, Beauty, rates from 1 Aug 2026) [14]. We recommend it as a **golden test vector** for the engine.

- **Order details.** Item Price Credit ฿1,000; Seller discount ฿100; buyer pays ฿50 shipping; the buyer uses a **platform Campaign voucher of ฿180**; the Seller is in PP.
- **Payment fee:** (1,000 − 100 + 50) × 3% = 28.50, plus VAT 2.00, gives **30.50**.
- **MSF:** (1,000 − 100) × 17.5% = 157.50, plus VAT 11.03, gives **168.53**.
- **PP:** (1,000 − 100) × 8% = 72.00, plus VAT 5.04, gives **77.04**.
- **Seller receives:** 1,000 − 100 − 30.50 − 168.53 − 77.04 = **฿623.93**.
- Note that the ฿180 platform voucher does **not** reduce any fee base. The buyer's shipping goes to the carrier and is not Seller revenue.

### 2.2 MSF by category, effective 1 Aug 2026

Taken from the official PDFs [17][18] and the announcement summaries [15][16]. Each PDF has roughly 2,600–2,700 rate rows, down to category level 5 [A]. Figures are excl. VAT, with incl. VAT in brackets.

| Cluster (examples) | Marketplace | LazMall |
|---|---|---|
| FMCG: beauty, food, pet food, mom & baby | **15%** (16.05%) | **17.5%** (18.73%) |
| Fashion: clothing (dresses etc.) | **16%** (17.12%). Cluster range 7.5–16% | 17.5% (18.73%). Cluster range 9–17.5% |
| General merchandise: home, sports, automotive | Mostly 15% (16.05%). Range 9.5–15% | Mostly 17.5%. Range 12–17.5% |
| Electronics accessories, small appliances, earphones | 14.5–15% (15.52–16.05%) | 15–17.5% |
| Laptops, cameras, desktops | **5.5%** (5.89%) | 5.5% (5.89%) |
| PC components, monitors | 7.5% (8.03%) | 7.5% |
| Storage, printers, TV cables | 10.5% (11.24%) | 10.5% |
| Digital vouchers | 12% (12.84%) | 14.5% (15.52%) |

**Distribution [A].** In the Marketplace file, 1,872 rows are at 15% and 236 at 16%. In the LazMall file, 2,153 rows are at 17.5%.

**Mobile phone handsets and tablets are missing** from the 1 Aug files; only their accessories appear [A]. KhumMai [29 S] notes the same and assumes the old rate of 6.96% incl. VAT.

**2026 MSF timeline.**

- 1 May: +1.2 to +1.6 points; the LazMall flat 13% rate was removed [29 S].
- 25 Jun: +1 point (excl. VAT). The announcement titles appear in Lazada's Seller Announcement list [14]; the figures come from [29 S].
- 1 Aug: +2 points (excl. VAT) in most categories [15][16].

## 3. Campaign mechanics (11.11 and other mega Campaigns)

### 3.1 Shopee Thailand

Sources: Seller Education Hub "Shopee Campaigns", 30 Jan 2026 [7]; Easy Nomination, 27 Apr 2026 [8]; Voucher Campaigns [9]; Campaign Packages, 20 Jul 2026 [10]; Shopee Price Guarantee T&C, 27 Jan 2026 [11].

- **Where invitations appear** [7].
  - The **Campaigns** menu in the left sidebar of Seller Centre, or **Marketing Centre → Shopee Campaigns → More**. The app has the same path.
  - Sub-accounts with "campaign access" can see them too.
  - The list shows "all upcoming Campaigns". Each row has one of four action buttons:
    - *Nominate products*;
    - *Add/edit products*;
    - *Go To Confirm*: products Shopee nominated for you, waiting for your confirmation;
    - *View*: the shop does not qualify.
- **Tiers and labels.** Campaigns are tiered **Mega, A+, A, B, Global**. Shopee sets the tier by how many products or shops the Campaign accepts. Labels such as "free shipping" or "Club exclusive" describe the selling point [7].
- **Structure.** A Campaign is split into **sessions**, which are time slots. A product can be nominated to several overlapping Campaigns, but it is **approved for only one session** [7].
- **Shop conditions shown with each Campaign** [7]:
  - penalty points;
  - not in vacation mode;
  - preparation time (DTS);
  - maximum number of products the shop may nominate;
  - shop rating and number of ratings;
  - "PRIME Seller only" for some Campaigns.
- **Product conditions shown with each Campaign** [7]:
  - **minimum stock**;
  - **original-price range**;
  - **promotion-price range** and **discount-% range**;
  - item condition (new or used);
  - minimum orders;
  - average daily sales over 30 days;
  - minimum daily orders;
  - likes;
  - purchase rate (unique buyers ÷ visitors over 30 days);
  - DTS;
  - product rating and number of ratings;
  - allowed categories;
  - Fulfilled-by-Shopee only;
  - PRIME only.
- **Price rules.** "Both the discount (%) and the promotion price must fall within the range the Campaign sets." A price outside the band triggers the error *"Campaign price must be ≥ {price} and ≤ {price}"* [7]. Two reference prices are shown [7]:
  - the **lowest price in the last 30 days**;
  - the **average price in the last 60 days**.

  A *Suggested price* column recommends a sharper price [7]. No fixed rule such as "X% below the 30-day low" is published. The band is set per Campaign and session, and the Seller sees it only inside the logged-in Seller Centre.
- **Fields the Seller fills per product** [7]:
  - promotion price (the *Seller Offer Price*, before any Shopee rebate);
  - **campaign stock**;
  - **purchase limit** per buyer.

  Bulk upload by Excel takes up to 1,000 variants per file.
- **Co-funding.** "Item discount issued by Shopee" (Shopee Item PRM, or "Rebate") lowers the buyer's price further. Shopee repays the amount to the Seller after payment [7]. It is not part of the commission base [1].
- **Shopee-nominated products.** Shopee can nominate a shop's products itself. The Seller then confirms, rejects, or sends *Feedback* changing the price, campaign stock or purchase limit [7].
  - Products nominated by Shopee cannot be opted out by the Seller once approved.
  - Seller-nominated approved products can be opted out ("Opt-out Products"). Shopee may review the opt-out [7].
- **Easy Nomination** (27 Apr 2026) [8].
  - The Seller sets a **Best Mega Campaign Price** (for 9.9, 10.10 and the like) and a **Best Non-Mega Campaign Price** once. Each is a floor before the Shopee discount.
  - Shopee then auto-nominates the products to eligible Campaigns and sends notifications. It never goes below the floor.
  - This maps exactly to a MarginArena output: **the lowest price at which the Promo Plan still meets the margin target**.
- **Voucher Campaigns** [9].
  - Seller vouchers (store or product codes; fixed amount, % or Coins Cashback) are nominated into voucher Campaign sessions.
  - Some sessions are open only to members of the free-shipping or discount programmes (now PRIME).
  - Shopee may "recommend" vouchers ("Pending confirmation") or nominate them for the Seller.
  - Once approved, a voucher's quantity can only be **increased**.
- **Paid add-ons** [10]. Campaign Packages are bought and managed in Seller Centre ("My Packages"). They include **Brand Max** homepage placements: Daily Discover banners, search prefill and a floating icon, some sold on a CPM basis.
- **Invitation-only programmes** [11].
  - "Shopee Price Guarantee" is open **only to Sellers who receive an invitation**.
  - Shopee pre-selects products. The Seller confirms them from the Main Account, or proposes its own with a price and daily campaign stock. Limited stock removes a product from consideration.
  - Changes take effect within 3 days. The Seller's KAM (key account manager) works Mon–Fri 09:00–17:30.
- **Consent.** In 2026 Thailand's Trade Competition Commission fined Shopee **฿3,472,488.50** under Section 57 [34 S]. The reason: Shopee had enrolled Sellers in sales promotions without notice or consent between June 2020 and August 2021. Today's flows are opt-in with explicit confirmation [7]. The Verdict should land **before** the Seller confirms.
- **11.11 in 2026.** No public page gives the dates or rules of Shopee Thailand's 11.11 2026. Campaign-specific bands live only in the logged-in Seller Centre. A secondary blog gives 6–15 Nov as Thailand's 11.11 window in 2025 [33 S, not verified].

### 3.2 Lazada Thailand

Sources:

- 9.9 2026 Campaign guide, updated 27 Aug 2026 [21];
- Seller campaign participation requirements, updated 20 Feb 2026 [22];
- "Why campaign registration fails", updated 10 Aug 2026 [23];
- "How to register for a Campaign", updated 27 Jan 2025 [24].

- **Where invitations appear** [22][23].
  - **Marketing Center → Campaigns**. The "Unregistered campaigns" tab shows **only Campaigns the shop is eligible for**. The "Ineligible" tab shows which metric fails.
  - The Seller Centre home page links each Campaign as `…/portal/campaign/unit-invitation/{id}` [21].
  - Programmes (Free Shipping Special, Premium Package) are joined on the separate **Lazada Programs** page [22].
- **Eligibility for MEGA Campaigns** (Birthday, 9.9, 11.11, 12.12), effective 3 Mar 2026 [22]. Each metric may also be "or no score yet", so new Sellers with no history can join [21]:
  - seller rating ≥ 85%;
  - fast delivery (non-FBL) ≥ 80%;
  - Seller cancellation rate ≤ 3%;
  - product quality ≥ 4.2 (with more than 5 reviews);
  - seller policy points in the last 90 days < 24.

  Metrics are measured on the **last day of registration** [22]. A+ Campaigns use lower thresholds (rating ≥ 80%, fast delivery ≥ 70%) [22].
- **Programmes required** [21][23]. For 9.9 2026 the eligibility list starts with "joined **Free Shipping Special and Campaign Voucher**". Since 1 Jul 2026 these are sold only as the Premium Package [20]. In practice, a mega Campaign costs a Seller outside Premium Package an extra **8.56% of item revenue**.
- **Price rule** [23][24].
  - A Campaign price is auto-approved only if it is **≤ the recommended price**. If it is higher, it is rejected automatically.
  - Recommended price for a selling SKU = **average selling price over the last 90 days, leaving out prices from Mega, A+ and special-mechanic Campaigns**.
  - Recommended price for a non-selling SKU = **lowest price in the last 90 days**, with the same exclusions.
  - "Do I have to cut the price further every time I join?" No: earlier Mega and A+ prices are excluded [24].
- **Flash Sale rule** [22]. The deal must be **≥ 3% below the lowest price in the last 30 days** and have **≥ 100 units** of deal stock. The SKU must have sold 60–70 or more units in the last 30 days, have a product rating above 4, and a cancellation rate ≤ 10%. The table's own header says "new criteria to be announced by 15 May 2025", so it may be out of date.
- **9.9 2026 timeline** [21]. This is a real recent mega-Campaign timeline, our best template for 11.11:
  - **4 Sep**: last day to register for the Campaign, the Campaign Voucher and Free Shipping Special;
  - **28 Aug – 9 Sep**: carrier and warehouse changes frozen;
  - **7–11 Sep**: **price lock**. Sellers cannot raise prices;
  - **8 Sep 20:00 – 11 Sep**: the Campaign.
- **After registering** [21][24].
  - Approval comes about **2 working days** before the Campaign starts.
  - During some Campaigns, editing price, images and video is blocked.
  - **Stock can be increased but not decreased.**
  - Withdrawing an approved item is approved 1–3 days before the Campaign. A resubmitted deal that is cheaper is approved at once; a pricier one is reviewed, which takes up to about 5 days.
- **Co-funded discounts.**
  - *Campaign vouchers*: Lazada funds them in return for the Premium Package fee [19]. They do not reduce the fee base [14].
  - *Lazada Bonus* (cross-store "spend X, save Y"): listed as a **mandatory agreement** on a real MEGA Campaign page [23]. The Thai Seller/Lazada split is not published. In Malaysia a co-funded voucher example uses **60% Seller / 40% Lazada**, and Lazada charges commission on its own 40% too [35 S].
  - *LazCoins discount*: Seller-funded and store-wide. It can be part-funded with Seller Virtual Credits at a stated ratio, for example 50:50, and cannot be cut for 3 days after starting [25].

### 3.3 What a real Campaign invitation contains

Lazada publishes a screenshot of a real **MEGA** Campaign page in Seller Centre ("Lazada Birthday: 25–27 Mar 24") [23]. It shows:

- A tier badge (**MEGA**), the Campaign name, and tags such as "annual festival" and "platform focus".
- **Registration deadline** (19 Mar 2024 23:59:59), **Campaign period** (24 Mar 20:00 – 27 Mar 23:59:59) and **warm-up start** (21 Mar).
- **Mandatory agreements**: *Lazada Bonus*, *FREE SHIPPING*, *Seller Agreement*. **Recommended**: *LazCoins*, *Sponsored Solutions*.
- Tabs: *Unregistered*, *Registered*, *Ineligible*.
- **Sub-units**, each with its own registration deadline and dates:
  - "Campaign Voucher" (voucher validity 23 Feb – 20 Mar);
  - "Main Campaign – submit all products", with a product counter ("1 / 2 products").
- A link to the **Campaign Agreement**, which holds the terms.
- After clicking Join, a product table. For each SKU it shows the **recommended price** (editable, must be ≤ recommended) and **stock**. Upload works one SKU at a time or by Excel [24].

A Shopee invitation, as described in [7] and [8], contains:

- The Campaign name and **tier** (Mega / A+ / A / B / Global) and its feature labels.
- **Sessions** with nomination deadlines.
- The **shop conditions** and **product conditions** lists in 3.1, including **price band**, **discount band** and **minimum stock**.
- Reference prices: the **30-day low** and the **60-day average**.
- A *Suggested price* per variant, and fields for **promotion price**, **campaign stock** and **purchase limit**.
- The Shopee-funded item discount, if any.
- Status: *Pending Shopee review / Approved / Rejected / Withdrawn*.

**What MarginArena should accept as an invitation.** These fields are the union of both marketplaces:

```yaml
campaign_invitation:
  marketplace: shopee_th | lazada_th
  campaign_name: "11.11 Big Sale"
  tier: MEGA | A+ | A | B
  registration_deadline: 2026-11-07T23:59:59+07:00
  campaign_start: 2026-11-11T00:00:00+07:00
  campaign_end: 2026-11-11T23:59:59+07:00
  price_lock: {start, end}                        # Lazada [21]
  required_programmes: [premium_package] | [prime_seller]   # [21][7]
  mandatory_agreements: [lazada_bonus, free_shipping, seller_agreement]   # [23]
  shop_eligibility: {seller_rating_min: 0.85, fast_delivery_min: 0.80, cancel_rate_max: 0.03, product_rating_min: 4.2, policy_points_max: 24}   # [22]
  sku_offer:
    reference_price_rule: avg_selling_price_90d_excl_mega | lowest_30d | avg_60d   # [24][7]
    reference_price: 349.00
    max_campaign_price: 299.00                    # Lazada: <= recommended; Shopee: band upper bound
    min_campaign_price: 199.00                    # Shopee band lower bound
    discount_pct_range: [0.15, 0.50]              # Shopee [7]
    min_campaign_stock: 50
    purchase_limit: 2
    platform_item_rebate: 10.00                   # Shopee-funded, repaid to Seller [7]
    platform_voucher_cofund_seller_share: 0.0     # Lazada Bonus share; unknown for TH [35]
```

## 4. Engine parameters: the Marketplace Profile

The engine should store every rate **excluding VAT**, apply VAT once, and record the effective date. Shopee publishes commission including VAT. Shopee's rates divide exactly by 1.07: 16.05 → 15.0, 17.12 → 16.0, 19.26 → 18.0, 7.49 → 7.0 [A].

### 4.1 Parameters

| Parameter | Meaning | Shopee TH default | Lazada TH default | Source |
|---|---|---|---|---|
| `profile_effective_from` | Date of the fee schedule | 2026-08-04 | 2026-08-01 | [1] / [14] |
| `vat_rate` | Thai VAT on platform fees | 0.07 (until 30 Sep 2027) | 0.07 | [27][28] |
| `seller_tier` | Selects the rate table | `non_mall` (or `mall`) | `marketplace` (or `lazmall`) | [1] / [14] |
| `commission_rate_ex_vat[category]` | Category commission | FMCG 0.150; fashion 0.160; small appliances 0.145; phones/laptops 0.070. Mall: FMCG/fashion 0.180 | FMCG 0.150; fashion 0.160; laptops 0.055. LazMall: FMCG/fashion 0.175 | [2][3] / [17][18] |
| `commission_base` | What the % applies to | item price − Seller item discount − Seller voucher (per item) | Item Price Credit − Seller-funded discount | [1][12] / [14] |
| `small_seller_discount_ex_vat` | Commission cut for small shops | 0.015 FMCG and fashion, 0.005 low-rate electronics, if sales in the last 30 days ≤ ฿10,000 | n/a | [1][2] |
| `payment_fee_rate_ex_vat` | Payment or transaction fee | 0.03 | 0.03 | [1] / [14] |
| `payment_fee_base` | | price after Seller discounts + buyer-paid shipping (+ Shopee-funded item discount and coins, which keeps the base equal to the price after Seller discounts) | Item Price Credit − Seller discount + buyer-paid shipping | [1] / [14] |
| `installment_mix` and `installment_rates_ex_vat` | Optional payment mix | default `{standard: 1.0}`; rates 3 m 0.05, 6 m 0.065, 10 m+ 0.07 | PayLater subsidy 1.25% per month (opt-in only) | [1] / [14] |
| `fixed_fee_per_order_ex_vat` | Flat fee per order | 1.00 (= ฿1.07) | 0 | [1][5] / [14] |
| `fixed_fee_waiver_orders_30d` | Fixed fee waived at or below this many completed orders | 100 | n/a | [5] |
| `programme` | Free-shipping and voucher programme | `prime_seller` | `premium_package` | [6] / [14] |
| `programme_fee_rate_ex_vat` | | 0.08 (0.07 for some electronics, 0.07 jewellery, 0.06 bullion) | 0.08 flat | [6] / [15][16] |
| `programme_fee_base` | | **assumed** = commission base (not published) | Item Price Credit − Seller discount | [6] / [14] |
| `programme_fee_cap_per_item` | | none (ended 19 Nov 2025) | none | [6] / [14] |
| `programme_required_for_campaign` | Must join to enter mega Campaigns | some Campaigns only (`PRIME Seller only`) | **yes** (FSS + Campaign Voucher) | [7] / [21][22] |
| `fees_charged_on` | When fees apply | completed orders; not charged on cancelled or refunded orders within the guarantee period | successfully delivered orders | [1] / [14] |
| `platform_item_rebate_treatment` | Shopee-funded item discount | revenue-neutral (repaid to Seller); not in commission base | n/a (campaign vouchers are platform-funded and not in the base) | [7][1] / [14] |
| `platform_voucher_cofund_seller_share` | Seller share of co-funded platform vouchers | 0 | 0 by default; sensitivity 0.6 (Malaysia example), with commission also charged on the platform-funded share | [35 S] |
| `campaign_price_rule` | Highest price that is auto-approved | within the Campaign's band; references are the 30-day low and 60-day average | ≤ recommended price (90-day average selling price, excluding Mega and A+ prices) | [7] / [23][24] |
| `campaign_min_discount_vs_30d_low` | Flash Sale rule | n/a (band per Campaign) | 0.03 for Flash Sale | [22] |
| `campaign_stock_rules` | | minimum campaign stock per Campaign; stock locked while the item is in a Campaign | stock can only increase; Flash Sale ≥ 100 units | [7][36] / [21][22] |
| `price_lock_window` | | none published | registration close → Campaign end (9.9: 7–11 Sep) | [21] |
| `seller_vat_registered` | Seller's own VAT status | **false** for the demo; must register above ฿1.8 M a year | same | [26] |
| `wht_on_fees` | Withholding tax on fees | 0 (cash-flow only; refunded) | 0 | [13] |

**When `seller_vat_registered = true`:**

- revenue in the margin calculation = price ÷ 1.07;
- platform fees count **excluding VAT**, because their VAT is reclaimable as input tax;
- Shopee issues tax invoices for fees on request [1].

**When it is false** (the demo default): revenue = price, and fees count **including VAT**.

### 4.2 Demo Seller

- **Who.** A Non-Mall shop on Shopee Thailand.
- **Category.** Beauty → Skincare (FMCG).
- **Status.**
  - Member of PRIME Seller, so it can reach Campaigns and Flash Sale slots [6].
  - Above ฿10,000 sales in 30 days, so not a Small Seller.
  - More than 100 orders in 30 days, so the ฿1.07 fee applies.
  - Not VAT-registered.
  - All payments are standard (no instalments).
  - The buyer pays no shipping, because a Shopee free-shipping code covers it.
- **Lazada mirror profile.** A Lazada Marketplace Seller in the same category with the Premium Package. It differs only by the ฿1.07 fixed fee.

```yaml
marketplace_profile:
  id: shopee-th-nonmall-prime-fmcg@2026-08-04
  currency: THB
  vat_rate: 0.07
  seller_vat_registered: false
  commission_rate_ex_vat: 0.150      # 16.05% incl. VAT [2]
  small_seller_discount_ex_vat: 0.0  # not eligible
  payment_fee_rate_ex_vat: 0.03      # 3.21% incl. [1]
  fixed_fee_per_order_ex_vat: 1.00   # ฿1.07 incl. [1][5]
  programme_fee_rate_ex_vat: 0.08    # PRIME 8.56% incl. [6]
  effective_take_rate_incl_vat: 0.2782   # + ฿1.07 per order
```

**Worked example** [A]. The SKU lists at ฿399. The Campaign price is ฿299, and a ฿20 Seller voucher is used. Shopee adds a ฿10 rebate.

- Commission and programme base: 399 − 100 − 20 = **฿279**. The rebate does not change it.
- Commission: 279 × 16.05% = **44.78**
- PRIME fee: 279 × 8.56% = **23.88**
- Transaction fee: 279 × 3.21% = **8.96**
- Platform fee: **1.07**
- **Total fees: ฿78.69**, which is **28.2%** of ฿279.
- **Payout: ฿200.31** (the buyer's ฿269 plus Shopee's ฿10 rebate, minus fees). Cost of goods, packaging and any Seller-paid shipping come out of this.
- The same order on Lazada Marketplace with the Premium Package costs ฿77.62 in fees (27.82%) and pays out ฿201.38.
- The official Lazada example in 2.1 is the second test vector. Its expected result is **฿623.93**.

## 5. Comparison (optional): Shopee Singapore

Source: Cube Asia take-rate tracker, updated 1 Aug 2026 [31 S]. It cites Shopee SG Help Center articles 2325 and 2450, which we could not render.

- **Rates.** Shopee Singapore Non-Mall commission is **7.43–11.79%** and Mall is **10.11–15.06%**, plus a **3.27%** transaction fee (Singapore GST is 9%).
- **Comparison with Thailand.** On the figures as published, Thailand's FMCG commission (16.05% Non-Mall, 19.26% Mall) is above Singapore's highest commission (15.06%), even before the PRIME fee. Cube does not say clearly whether its Singapore rates include GST.
- **Caution about this source.** Cube's Thailand figures (Non-Mall 9.77–14.18%) lag the official 4 Aug 2026 files [2]. Use aggregators as a cross-check only.

## 6. Gaps and risks

1. **Shopee PRIME fee base.** It is not public; the calculator needs a Seller Centre login [6]. We assume it equals the commission base.
2. **Shopee 11.11 2026 bands.** The price and discount bands per session are visible only to logged-in Sellers [7]. MarginArena should treat them as inputs from the invitation, not as constants.
3. **Lazada Bonus split in Thailand.** The share is unpublished. Use the Malaysian 60/40 figure only as a sensitivity case [35 S].
4. **Lazada phones and tablets.** These rows are missing from the 1 Aug 2026 MSF files [A].
5. **Unverified claims.** The Shopee 5% technical support fee and the 0% new-Seller commission appear only in secondary sources [32 S][33 S] and are absent from the official Thai fee policy [1].
6. **Fees change often.** There were three changes per marketplace in 2026. Store `profile_effective_from` with each profile, and show it in the UI next to every Verdict.

## Sources

All accessed 14 Oct 2026. P = primary, S = secondary.

1. **P** Shopee Thailand Help Center, "นโยบายค่าธรรมเนียม" (Fee Policy), article 77254. Revised 3 Jul 2026; effective 4 Aug 2026 00:00. https://help.shopee.co.th/portal/article/77254
2. **P** Shopee Thailand, "[EN] Non-Mall Sale Transaction Fee Rate – Effective 4 Aug 2026" (PDF linked from [1]). https://drive.google.com/file/d/1EiOQVESYZNQ6CMPBejrctqQNNl34ozMH/view (Thai version: https://drive.google.com/file/d/1Utdrir3pSl8psgVglAuaMP7bHnQoa4UQ/view)
3. **P** Shopee Thailand, "[EN] Mall Sale Transaction Fee Rate – Effective 4 Aug 2026" (PDF linked from [1]). https://drive.google.com/file/d/1GcaQ6jv-JcE-diGgZ7hJ-zV-BVBGCQTa/view
4. **P** Shopee Thailand, "Compare Sale Transaction Fee Rate – 1 June 2026", Non-Mall (EN) (PDF linked from [1] as the rates current before 4 Aug). https://drive.google.com/file/d/1iCx1EYirb0utQaYMtZWLgkib1O_bPQil/view
5. **P** Shopee Thailand, "ประกาศค่าธรรมเนียมโครงสร้างพื้นฐานแพลตฟอร์ม (Platform Infrastructure Fee)", effective 15 Sep 2025. https://shopee.co.th/m/PlatformInfrastructureFee
6. **P** Shopee Thailand, "โปรแกรม PRIME Seller" programme page. Service-fee table effective 3 Mar 2026; per-item cap ended 19 Nov 2025. https://shopee.co.th/m/PRIME-Seller-Program. It is reached from https://shopee.co.th/m/fss-ccb, which is linked from the Seller Education article "โปรแกรมส่งฟรี Xtra" https://seller.shopee.co.th/edu/article/1088. The fee calculator https://seller-rewards.shopee.co.th/shopeemarketingsolutions/prime-seller/fee needs a login and was not opened.
7. **P** Shopee Seller Education Hub, "แคมเปญของ Shopee", 30 Jan 2026. https://seller.shopee.co.th/edu/article/7490
8. **P** Shopee Seller Education Hub, "โปรแกรม จัดการราคาแคมเปญ (Easy Nomination)", 27 Apr 2026. https://seller.shopee.co.th/edu/article/27270
9. **P** Shopee Seller Education Hub, "แคมเปญ โค้ดส่วนลด", 12 Dec 2024. https://seller.shopee.co.th/edu/article/7484
10. **P** Shopee Seller Education Hub, "รูปแบบใหม่: จัดการแพ็กเกจแคมเปญออนไลน์บน Seller Centre", 20 Jul 2026. https://seller.shopee.co.th/edu/article/27957
11. **P** Shopee Thailand Help Center, "ข้อกำหนดและเงื่อนไข Shopee Price Guarantee", version 27 Jan 2026. https://help.shopee.co.th/portal/4/article/191989
12. **P** Shopee Seller Education Hub, "วิธีคิดรายได้และรายจ่ายจากการขายสินค้าบน Shopee ที่ต้องเสียภาษี", 1 Aug 2025. https://seller.shopee.co.th/edu/article/19445
13. **P** Shopee Seller Education Hub, "ภาษีหัก ณ ที่จ่ายสำหรับผู้ขายบนช้อปปี้", 25 Oct 2024. https://seller.shopee.co.th/edu/article/12017
14. **P** Lazada Seller Center Help Center, "Lazada Fee Policy", last update 3 Aug 2026. Includes the fee definitions, bases and the worked example. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?categoryId=1000028094&m_station=faq&questionId=1000159550
15. **P** Lazada Thailand, "ประกาศเปลี่ยนแปลงค่าธรรมเนียมบริการมาร์เก็ตเพลส และโปรแกรมลาซาด้า สำหรับร้านค้า Marketplace (มีผลบังคับใช้ตั้งแต่วันที่ 1 สิงหาคม 2569)". Announced 16 Jul 2026. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?categoryId=1000028132&m_station=faq&questionId=1000159545
16. **P** Lazada Thailand, the same announcement for LazMall Sellers, 16 Jul 2026. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?categoryId=1000028132&m_station=faq&questionId=1000159548
17. **P** Lazada Thailand, Marketplace Service Fee table for Marketplace Sellers, effective 1 Aug 2026 (PDF). https://lzd.co/TH-MPFee-MP010826 (resolves to https://files.alicdn.com/tpsservice/a4c71700b1ca4b774a273f7280985173.pdf)
18. **P** Lazada Thailand, Marketplace Service Fee table for LazMall Sellers, effective 1 Aug 2026 (PDF). https://lzd.co/TH-MPFee-LM010826 (resolves to https://files.alicdn.com/tpsservice/4e31a095c1df5bc0b4c3d37e1da31f1e.pdf)
19. **P** Lazada Thailand, "ประกาศ: ตารางอัตราค่าบริการ Premium Package, โปรแกรมส่งฟรีพิเศษกับลาซาด้า และ โปรแกรมคูปองแคมเปญ". Announced 15 Apr 2026; effective 1 May 2026. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?questionId=1000159414
20. **P** Lazada Thailand, "ตารางอัตราค่าบริการ Premium Package". Announced 8 Jun 2026; effective 1 Jul 2026. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?questionId=1000159479
21. **P** Lazada Thailand, "📔 คู่มือแคมเปญ เซลใหญ่ 9.9 ลดอลัง ปังทุกแบรนด์", updated 27 Aug 2026. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?categoryId=1000028076&m_station=faq&questionId=1000149241
22. **P** Lazada Thailand, "ข้อกำหนดการเข้าร่วมแคมแปญของผู้ขาย", updated 20 Feb 2026. The MEGA table is effective 3 Mar 2026. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?questionId=1000147523
23. **P** Lazada Thailand, "ทำไมถึงเข้าร่วมแคมเปญไม่สำเร็จ", updated 10 Aug 2026. Includes the screenshot of the "Lazada Birthday 25–27 Mar 24" MEGA Campaign page. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?categoryId=1000028076&m_station=faq&questionId=1000147582
24. **P** Lazada Thailand, "วิธีการสมัครเข้าร่วมแคมเปญ", updated 27 Jan 2025. Includes the recommended-price FAQ. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?categoryId=1000028076&m_station=faq&questionId=1000147382
25. **P** Lazada Thailand, "ส่วนลด Lazcoin ผู้ขายร่วมทุน SVC", updated 20 Nov 2025. https://sellercenter.lazada.co.th/helpcenter/s/faq/knowledge?categoryId=1000028073&m_station=faq&questionId=1000158917
26. **P** Thai Revenue Department, "ผู้ประกอบกิจการที่ไม่ต้องจดทะเบียนภาษีมูลค่าเพิ่ม" (VAT registration not required at ≤฿1.8 M a year). https://www.rd.go.th/7060.html
27. **S** Forvis Mazars, "Thailand maintains 7% VAT rate for another year". Royal Decree No. 807, gazetted 20 Aug 2026; 7% (6.3% VAT + 0.7% municipal) from 1 Oct 2026 to 30 Sep 2027. https://www.forvismazars.com/th/en/insights/doing-business-in-thailand/tax/thailand-maintains-7-vat-rate-for-another-year
28. **S** KPMG TaxNewsFlash, "Thailand: Reduced 7 percent VAT rate extended through September 2027", Sep 2026. https://kpmg.com/us/en/taxnewsflash/news/2026/09/thailand-reduced-7-percent-vat-rate-extended-through-september-2027.html
29. **S** KhumMai, "อัปเดตค่าธรรมเนียม 2569 ล่าสุด" (fee-change log, last updated 16 Jul 2026). Sources for the 7 Apr Shopee changes and the Lazada 1 May and 25 Jun rounds. https://khummai.com/fee-updates ; Lazada 1 Aug detail: https://khummai.com/fee-updates/2026-08-lazada-msf-pp-increase-aug01
30. **S** Ebrun (English), "Shopee Thailand Local Stores Face Third Commission Hike This Year…", 12 Jul 2026. https://english.ebrun.com/20260712/686590.shtml
31. **S** Cube Asia, "Shopee Take-Rate Tracker 2026", updated 1 Aug 2026. https://cube.asia/shopee-take-rate-tracker/
32. **S** Forest Shipping, "Shopee to Add a 5% Technical Support Fee Across Four Markets", 26 Dec 2025. https://www.forestshipping.com/shopee-5-technical-support-fee-four-markets
33. **S** Duoke, "2026 Shopee New Seller Onboarding Guide", 18 May 2026. Also its 2025 11.11 schedule: https://www.duoke.com/en/blog/article/182-2025-Sales-Guide-Conquer-Shopee-Lazada-TikTok-Shop-11-11-Mega-Sales-with-Winning-Strategies. Main article: https://www.duoke.com/en/blog/article/405-2026-Shopee-New-Seller-Onboarding-Guide-Registration-New-Seller-Policy
34. **S** Bangkok Biznews, commentary on the Trade Competition Commission's ฿3,472,488.50 fine on Shopee (Section 57; conduct June 2020 – Aug 2021). The page is undated, around Oct 2026. https://www.bangkokbiznews.com/tech/ai/1254988
35. **S** BigSeller, "A Complete Guide to Seller Virtual Credits (SVC) on Lazada Malaysia", 29 Sep 2025. Example 40% Lazada / 60% Seller; commission also charged on the Lazada-funded share. https://www.bigseller.pro/blog/articleDetails/3845/lazada-malaysia-seller-virtual-credits.htm
36. **P** Shopee Seller Education Hub, "เตรียมความพร้อมก่อนเข้าสู่แคมเปญ", 20 Jun 2022. Stock cannot be edited for items in Campaigns or Flash Sales. https://seller.shopee.co.th/edu/article/14584
