# 03 What do Shopee and Lazada Thailand charge Sellers, and how do 11.11 Campaigns work?

Type: research
Status: resolved
Blocked by: none

## Question

What fees do Sellers pay on Shopee Thailand and Lazada Thailand in 2026? This covers commission by category, transaction/payment fees, service-programme fees (free shipping, coins/cashback) and VAT. How do Sellers get invited to and register for mega Campaigns such as 11.11: the required discount levels, co-funded vouchers, and how invitations are delivered? What does a real Campaign invitation contain?

Findings: `.scratch/marginarena/research/marketplace-fees.md`

## Answer

Full findings: [research/marketplace-fees.md](../research/marketplace-fees.md). The engine-parameter table is in section 4.

### Fees in force on 14 Oct 2026

Shopee last changed fees on 4 Aug 2026 and Lazada on 1 Aug 2026.

| Seller type | Commission | Payment | Free-shipping/voucher programme | Per order | Total |
|---|---|---|---|---|---|
| Shopee Non-Mall PRIME (FMCG, incl. 7% VAT) | 16.05% | 3.21% | 8.56% | ฿1.07 | **27.82% + ฿1.07** |
| LazMall | | | | | 30.50% |

- **Fee base:** the price after the Seller's own discounts and vouchers. Platform-funded discounts do not reduce it.
- **Lazada worked example:** the Seller receives ฿623.93. Use it as a golden test case for the engine.

### Campaigns

- Neither marketplace adds a Campaign fee. The Campaign's cost comes from three things:
  - the price and discount bands each Campaign sets;
  - the programmes it requires (Lazada Premium Package; Shopee PRIME);
  - co-funding (Shopee pays back part of the discount; the Thai Seller/Lazada split for Lazada Bonus is not published).
- **Invitations are only inside Seller Centre, never by email.** The bands are visible only after the Seller logs in, so they must be inputs, not constants.
- Lazada's 9.9 timeline is the template for 11.11: registration closes 4 days before the start, and prices are locked during the Campaign.
- Thailand's competition regulator fined Shopee for enrolling Sellers in promotions without their consent. Joining a Campaign is opt-in, so the Verdict must come before the Seller confirms.

### Demo Seller and gaps

- **Demo Seller:** a Shopee Non-Mall PRIME skincare shop, not VAT-registered, with a Lazada mirror. Worked example: a ฿279 net price pays ฿78.69 in fees (28.2%), so the Seller receives ฿200.31.
- **Gaps:**
  - Shopee doesn't publish the base for the PRIME programme fee; we assume the commission base.
  - The Shopee 11.11 2026 bands are behind login.
  - The Lazada Bonus split for Thailand is unknown (default 0%, with a sensitivity case at 60%).
