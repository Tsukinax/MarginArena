# MarginArena

MarginArena helps marketplace sellers decide whether a promotion makes money before they run it. It is built for the AMD Developer Hackathon ACT III, Reinvent Commerce and Evolus tracks.

## Language

### Commerce

**Seller**:
A business that sells to consumers through an online marketplace such as Shopee or Lazada, and decides its own prices and promotions.
_Avoid_: Merchant, shop, store, retailer, vendor

**Campaign**:
A marketplace sales event with fixed start and end times, such as 11.11, during which Sellers run promotions.
_Avoid_: Sale, event, mega sale

**Campaign Invitation**:
A marketplace's offer to a Seller to put specific SKUs into a Campaign. It states the price and discount bands and the programmes the Seller must accept. It reaches the Seller only inside the marketplace's Seller Centre.
_Avoid_: Campaign email, nomination, invite

**Marketplace Profile**:
The fee structure, currency and Campaign rules of one marketplace in one country, such as Shopee Thailand. Every Promo Plan is costed against one.
_Avoid_: Platform config, market settings

**Margin Floor**:
The lowest profit per unit, after marketplace fees and product cost and expressed as a percentage of the selling price, that a Seller will accept on a SKU during a Campaign. A Promo Plan that falls below it against any Counter-move cannot be approved.
_Avoid_: Minimum margin, threshold, red line

**Brand Price Rule**:
A clause in a Seller's agreement with a brand that limits how that brand's products may be priced or promoted, such as a maximum headline discount. It is set by the brand, not the Seller. A Promo Plan that breaks one cannot be approved.
_Avoid_: MAP policy, brand policy, price floor

**Promo Plan**:
A proposed promotion for one SKU during one Campaign. It combines one or more Promo Mechanics and includes the costs of joining the Campaign.
_Avoid_: Promotion, offer, deal, scenario, strategy

**Promo Mechanic**:
One way a Seller can make an offer more attractive: a price cut, a shop voucher with a minimum spend, a multi-buy discount on the same SKU, a gift with purchase, or a per-buyer quantity limit.
_Avoid_: Promo type, tactic, lever

**Margin Protected**:
How much more profit, in the worst case, a Seller keeps by following MarginArena's Verdicts than by joining every invited SKU exactly as invited.
_Avoid_: Savings, profit uplift, money saved

**Evidence Link**:
The connection from a number in a Verdict to the document it came from: a line of the Campaign Invitation, a fee rule, a Brand Price Rule clause, or a Rival Snapshot.
_Avoid_: Citation, reference, source

**Verdict**:
MarginArena's ruling on a Promo Plan. It is one of three outcomes: Approve; Revise, which comes with a better Promo Plan; or Escalate, which hands the decision to a person.
_Avoid_: Recommendation, result, decision, output

### Agents

**Strategist**:
An AI agent, acting for the Seller, that proposes Promo Plans.
_Avoid_: Planner, optimizer, advisor

**Rival**:
An AI agent that plays a competing seller and proposes counter-moves to stress-test Promo Plans. A Rival's moves are never treated as forecasts.
_Avoid_: Competitor agent, adversary, opponent

**Counter-move**:
A Rival's response to a Promo Plan, such as a price cut, a deeper voucher, or holding its price.
_Avoid_: Reaction, response, attack

**Rival Snapshot**:
What a Seller captures from lookalike competitor listings, such as price, vouchers and gifts. Rivals may only propose Counter-moves that are plausible given this snapshot.
_Avoid_: Competitor data, market scan

**Arena**:
The multi-round tournament in which Strategists' Promo Plans face Rivals' Counter-moves. The engine scores every pairing, and the Promo Plan that wins is the one that stays above the Margin Floor in every case.
_Avoid_: Simulation, war room, debate, battle
