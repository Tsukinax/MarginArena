# Shopee Thailand: Seller fees and mega Campaign rules (in force 14 Oct 2026)

This document is the fee and Campaign reference for the MarginArena Campaign Desk agent. MarginArena's pricing
engine computes every number in a Verdict; use this document to explain where a fee comes from, never to compute one.
Sources are listed at the end; the research behind them is in the MarginArena repository,
`.scratch/marginarena/research/marketplace-fees.md`.

## Marketplace Profile: Shopee Thailand, Non-Mall, PRIME Seller, FMCG (beauty, skincare)

| Fee | Rate excluding VAT | Rate including 7% VAT | Charged on |
|---|---|---|---|
| Sale Transaction Fee (commission) | 15% | 16.05% | item price after the Seller's own discounts and vouchers |
| Payment Transaction Fee | 3% | 3.21% | what the buyer pays, including buyer-paid shipping |
| PRIME Seller programme fee | 8% | 8.56% | assumed to be the commission base (Shopee does not publish it) |
| Platform Infrastructure Fee | ฿1 per completed order | ฿1.07 | waived when the shop completed 100 or fewer orders in the previous 30 days |

- Total for a PRIME Seller: **27.82% of the price after the Seller's own discounts, plus ฿1.07 per order.**
- Effective date: 4 Aug 2026, the third fee change of 2026 (after 7 Apr and 1 Jun).
- Platform-funded discounts (a Shopee rebate or Shopee voucher) do not reduce any fee base; Shopee repays them to the
  Seller.
- VAT: Thailand's rate is 7% until 30 Sep 2027. A Seller that is not VAT-registered counts fees including VAT.
- Worked example: an item listed at ฿399 sold at ฿299 with a ฿20 shop voucher has a fee base of ฿279. Fees are
  ฿44.78 commission, ฿23.88 PRIME, ฿8.96 payment and ฿1.07 per order: ฿78.69 in total, so the Seller is paid ฿200.31
  (with Shopee's ฿10 rebate) before product cost.

## Mega Campaigns such as 11.11

- Shopee charges no extra Campaign fee. A Campaign costs the Seller through the discount band it sets, the programmes
  it requires (PRIME for some Campaigns), and any co-funding.
- Campaign Invitations appear only inside Seller Centre (Campaigns menu, or Marketing Centre → Shopee Campaigns),
  never by email. Each lists shop conditions, product conditions, a price band, a discount band and minimum Campaign
  stock. The bands are visible only to the logged-in Seller, so MarginArena treats them as inputs.
- Reference prices shown with an invitation: the lowest price in the last 30 days and the average price in the last
  60 days.
- Joining is opt-in. In 2026 Thailand's Trade Competition Commission fined Shopee ฿3,472,488.50 for enrolling Sellers
  in promotions without consent, so the Seller confirms every Verdict before anything is registered.
- Products Shopee nominates itself cannot be opted out once approved; products the Seller nominates can be.
- Stock cannot be edited while a product is in a Campaign or Flash Sale.

## Lazada Thailand, for comparison

LazMall Beauty pays 17.5% commission, 3% payment fee and an 8% Premium Package fee, each plus 7% VAT (30.50% in
total), with no per-order fee. Lazada's own worked example pays the Seller ฿623.93 on a ฿1,000 item with a ฿100
Seller discount. Lazada locks prices during a mega Campaign, and Campaign stock can rise but not fall.

## Sources

- Shopee Thailand Help Center, Fee Policy, article 77254 (revised 3 Jul 2026, effective 4 Aug 2026).
- Shopee Thailand Non-Mall Sale Transaction Fee rate file, effective 4 Aug 2026.
- Shopee Thailand, PRIME Seller programme page (fee table effective 3 Mar 2026).
- Shopee Thailand, Platform Infrastructure Fee announcement (effective 15 Sep 2025).
- Shopee Seller Education Hub, "Shopee Campaigns" (30 Jan 2026) and "Preparing for Campaigns" (20 Jun 2022).
- Lazada Seller Center Help Center, Lazada Fee Policy (last update 3 Aug 2026).
