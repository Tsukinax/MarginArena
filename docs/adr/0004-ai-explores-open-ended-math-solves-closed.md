# AI explores what's open-ended; math solves what's closed

The original Arena had LLM Strategists propose numeric Promo Plans for Rivals to stress-test. A scrutiny pass measured the alternative: the engine exhaustively evaluated 546 Promo Plans (26 price-cut levels × 7 voucher levels × 3 gift options) against 6 Counter-moves in 0.02 s. LLM proposals cannot beat exhaustive search on a closed numeric space, and the planned "Arena vs Grid" proof would have shown it.

We now split the work this way:

- **The engine searches every numeric Promo Plan.** This covers price cut, voucher, minimum spend and gift amounts, within the Campaign Invitation and the Brand Price Rules. It chooses the plan that survives every Scenario.
- **Rivals (AI) red-team the plan.** Each round they see the leading Promo Plan and the Rival Snapshot, then propose Counter-moves meant to break it. The engine adds those moves to the Scenarios and selects again. The Arena is this multi-round loop.
- **Strategists (AI) propose Plan Ideas.** These are non-numeric choices such as which catalogue item to give as a gift, or "use a voucher because the brand caps headline cuts". The engine fills in the numbers.
- **AI reads and explains:** the Campaign Invitation, Rival Snapshots, brand clauses, and Verdicts in English and Thai.

Two engine changes follow:

- **Counter-moves act through relative price.** A Seller loses demand only when a Rival's effective price ends up below the Seller's buyer price, in proportion to the gap: retained = (rival price / our price)^k. The sensitivity k is an overridable assumption. With a plain multiplier, Counter-moves could never change which plan wins, and red-teaming would be pointless.
- **Scenarios include the elasticity band (p10 to p90),** so the chosen plan is robust to demand uncertainty as well as to Rivals.

## Consequences

- **Proof metric 6 becomes "red-team value":**
  - how much the Counter-moves the AI discovered cut the worst-case profit of the best plan chosen under generic Scenarios;
  - on how many SKUs;
  - whether the Arena's plan holds up.
- **The "don't join" baseline is evaluated under the same Scenarios**, because Rivals act whether or not the Seller joins.
- **Token Factory is used only with sample data.** Its terms forbid sending sensitive financial data, so real Seller costs go only to our own MI300X endpoint.
- **The sample shop's live run is backed by a recorded MI300X run.** The UI labels it "recorded" and offers "Run live".
