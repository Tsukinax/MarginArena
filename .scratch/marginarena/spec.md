# Spec: MarginArena MVP

Status: ready-for-agent
Map: [map.md](map.md) · Glossary: [CONTEXT.md](../../CONTEXT.md) · ADRs: [docs/adr](../../docs/adr/)
Deadline: complete submission by **Sat 17 Oct 2026 24:00 ICT**, frozen by **Sun 18 Oct 2026 17:00 ICT** (10:00 UTC), on lablab.ai.
Tracks: Reinvent Commerce (Vibe Generation) and Evolus Business Agents on AMD. Partner prize: Google, "best use of Gemma".

## Problem Statement

A Thai marketplace **Seller** gets a **Campaign Invitation** inside Seller Centre: "join 11.11 if you cut these SKUs by 15–25%". Joining is opt-in, and registration closes days before the **Campaign**. The Seller has to decide, product by product, whether joining makes money.

- **Fees are high.** Shopee charges a Non-Mall PRIME Seller 27.82% + ฿1.07 per order, and fees rose three times in 2026. Thai SMEs report fees take 22–40% of each order and that their average net profit is about 2.3%.
- **The discount compounds the problem.** A ฿100 item costing ฿50 earns ฿21.11 at full price but only ฿6.67 at 20% off.
- **Nobody knows the demand response in advance.** No one knows how many more units the discount will sell, or what competitors will do in reply.
- **Existing tools don't help at the decision point.** They report profit after the sale, or compute one unit's margin at a price the Seller types in. None checks a Campaign Invitation before the Seller commits.

So Sellers either join blindly and "sell well but lose money", or decline and lose traffic.

## Solution

MarginArena checks a Campaign Invitation before the Seller commits.

**Inputs:**
- the invitation, as a screenshot or PDF;
- a catalogue file with cost, stock, current price and 30-day lowest price;
- a **Margin Floor**;
- optionally a **Rival Snapshot**: screenshots of lookalike competitor listings;
- the Seller's **Brand Price Rules**, held in an Evolus knowledge library.

A "Use sample invitation" button loads the fictional shop Glow Lab BKK (12 skincare SKUs) so judges can try it immediately.

For every invited SKU, MarginArena runs an **Arena** on AMD hardware:
- **Strategists** propose **Promo Plans** made of **Promo Mechanics**.
- **Rivals**, constrained by the Rival Snapshot, answer with **Counter-moves**, over several rounds.
- A deterministic engine prices every pairing, using real marketplace fees and a demand model estimated from public e-commerce data.

The Promo Plan that stays above the Margin Floor against every Counter-move, and respects the Brand Price Rules, wins. Each SKU then gets a **Verdict**:
- **Approve:** join as invited.
- **Revise:** join with a better Promo Plan.
- **Escalate:** a person decides.

Every number in a Verdict carries an **Evidence Link**, and the explanation can be read in English or Thai.

After the Seller confirms, an Evolus workflow carries out the decisions:
- it prepares the bulk-upload file for Seller Centre;
- it sends revised Promo Plans to the Seller;
- it emails the shop owner an approval request for escalated SKUs.

Throughout, an AMD Evidence panel shows what ran on the AMD Instinct MI300X (Gemma-4-31B-IT on vLLM), how fast it ran, and what each Verdict cost.

## User Stories

1. As a Seller, I want to upload a screenshot or PDF of my Campaign Invitation, so that I don't retype the invited SKUs and required discounts.
2. As a Seller, I want to see the fields MarginArena read from my invitation and correct any of them, so that a misread doesn't drive a wrong Verdict.
3. As a Seller, I want to upload my catalogue as a CSV (cost, stock, current price, 30-day lowest price), so that the check uses my real costs, which Seller Centre doesn't hold.
4. As a Seller, I want to set a shop-wide Margin Floor and override it per SKU, so that the check reflects how much profit I actually need.
5. As a Seller, I want to choose my Marketplace Profile (Shopee Thailand Non-Mall PRIME by default), so that fees match my account.
6. As a Seller, I want to optionally upload screenshots of 2–3 competitor listings, so that the Rival moves tested against me are realistic.
7. As a Seller, I want my brand agreement's pricing clauses to be enforced, so that I never approve a plan that breaks a Brand Price Rule.
8. As a judge, I want a "Use sample invitation" button, so that I can try the whole flow without my own files.
9. As a Seller, I want to watch the Arena run live, so that I understand plans are being stress-tested rather than guessed.
10. As a Seller, I want each SKU to end in Approve, Revise or Escalate, so that I know exactly what to do with it.
11. As a Seller, I want SKUs grouped by Verdict, with the ones that need me shown first, so that I spend my attention where it matters.
12. As a Seller, I want a Revise Verdict to show the better Promo Plan and how much more it earns in the worst case, so that I can trust the change.
13. As a Seller, I want an Escalate Verdict to tell me why no plan passes, so that I can decide with the facts in front of me.
14. As a Seller, I want to see the Margin Protected for the whole invitation in baht with a USD equivalent, so that I know what checking was worth.
15. As a Seller, I want a "How we decided" view per SKU, so that I can follow the reasoning:
    - the margin waterfall: price, voucher, fees, cost, profit;
    - the Strategist × Rival grid;
    - the hardest Counter-move.
16. As a Seller, I want every number in a Verdict linked to its source (an invitation line, a fee rule, a Brand Price Rule clause, a Rival Snapshot), so that I can verify it.
17. As a Seller, I want to read the Verdict explanation in Thai, so that I understand it in my own language.
18. As a Seller, I want to override a SKU's elasticity, so that my own sales experience can replace the dataset default.
19. As a Seller, I want to see the assumptions behind a Promo Mechanic (for example, how buyers value a gift), so that I know what the numbers depend on.
20. As a Seller, I want to confirm the Verdicts before anything happens, so that joining a Campaign stays my choice.
21. As a Seller, I want a bulk-upload file for the approved and revised SKUs, so that I can register them in Seller Centre in one step.
22. As a shop owner, I want an approval request by email for escalated SKUs, with the numbers, so that I can decide quickly.
23. As a Seller, I want to ask the Campaign Desk agent follow-up questions about a Verdict, so that I can explore "what if" without rerunning everything.
24. As a Seller, I want MarginArena to keep working when the AMD GPU endpoint is off, with a smaller Arena on AMD Token Factory and the route clearly labelled, so that I am never blocked.
25. As a judge, I want an AMD Evidence panel during the run (GPU, model, serving stack, tokens per second, requests in flight, time to first token), so that I can see what ran on AMD.
26. As a judge, I want an AMD Evidence page with the benchmark results and how to reproduce them, so that the claims are verifiable.
27. As a judge, I want to see the cost per Verdict on the MI300X compared with a closed API, so that the business case for open models on AMD is concrete.
28. As a judge, I want proof that the Arena is worth its LLM calls (Arena vs an exhaustive grid, and vs an LLM-direct policy), so that I can tell it isn't decoration.
29. As a judge, I want to see the elasticity holdout result against a naive baseline, so that I can trust the demand model.
30. As a judge, I want fee calculations checked against published marketplace examples, so that I can trust the fee model.
31. As an Evolus reviewer, I want to see what the workspace runs, so that I can score depth of use:
    - the connected model is our own vLLM endpoint;
    - the extractor, knowledge library, Web API tool and workflow are all in use;
    - each run leaves audit records.
32. As a developer, I want one script that provisions the Evolus workspace from scratch, so that the README runs.
33. As a developer, I want one script that brings up the MI300X droplet with the pinned vLLM image and HTTPS, so that GPU time isn't wasted on setup.
34. As a developer, I want the whole app to run with docker compose and a `.env`, so that anyone can reproduce it.
35. As a Seller, I want clear errors that say what failed and how to fix it, for example an unreadable invitation, a missing cost column, or a model route that is down.

## Implementation Decisions

**Architecture.** A Python FastAPI backend contains the engine, the Arena and the integrations. The frontend is React + TypeScript (Vite). Both ship in Docker, with a compose file. The public demo is hosted on Vercel. Inference uses two routes ([ADR 0002](../../docs/adr/0002-two-inference-routes.md)):
- **Primary:** our own vLLM endpoint on an AMD Developer Cloud MI300X, serving Gemma-4-31B-IT with the gemma4 tool and reasoning parsers. It listens on localhost behind Caddy HTTPS on a DuckDNS name.
- **Fallback:** AMD Token Factory's shared Gemma-4-31B-IT (30 requests/min, 8 concurrent).

The route is chosen per run by a health check and recorded on every result.

**Engine (deep module, deterministic, no I/O).** It is the only source of numbers ([ADR 0001](../../docs/adr/0001-numbers-come-only-from-the-engine.md)). It takes a SKU, a Marketplace Profile, a Promo Plan, a Counter-move, the Seller settings and the Brand Price Rules, and returns the unit economics, demand, Campaign profit, checks and Evidence Links. A wrapper evaluates a whole invitation and returns the Verdicts and Margin Protected.
- **Marketplace Profile:**
  - commission, payment fee and programme fee rates, plus the per-order fixed fee (and when it is waived);
  - the VAT treatment;
  - the fee base, which is the price after the Seller's own discounts and vouchers;
  - Shopee Thailand Non-Mall PRIME is the default; Lazada is a COULD.
- **Promo Mechanics:**
  - price cut;
  - shop voucher with a minimum spend;
  - multi-buy discount on the same SKU;
  - gift with purchase (its cost counted; the buyer's perceived value is an explicit, overridable assumption);
  - per-buyer quantity limit.

  Each mechanic has its own formula for effective price and unit cost. The MUST minimum is price cut, voucher with minimum spend, and gift.
- **Demand:**
  - Campaign units = baseline × Campaign traffic lift × (effective price ratio)^elasticity × Counter-move factor, capped at stock.
  - Elasticity applies to price cuts only.
  - Each category elasticity comes with a confidence band, and the Seller can override it per SKU.
- **Robust selection.** A Promo Plan is eligible only if all three hold:
  - for every Counter-move, its unit margin is at least the Margin Floor;
  - its worst-case Campaign profit is at least the "don't join" baseline;
  - it respects every Brand Price Rule.

  Among eligible plans, the one with the highest expected profit wins.
- **Verdict:**
  - **Approve** when joining as invited is eligible and within 5% of the best plan's expected profit.
  - **Revise** when a better eligible plan exists.
  - **Escalate** when no plan is eligible, when the elasticity band is too wide to separate plans, or when a Brand Price Rule is ambiguous.
- **Margin Protected** = the worst-case profit of following the Verdicts minus the worst-case profit of joining every SKU as invited.

**Elasticity fit (offline).**
- Download FreshRetailNet-50K (CC BY 4.0) at a pinned revision, checked by SHA-256.
- Fit a log-log fixed-effects model on in-stock days, with store×SKU and city×date effects and a control for the activity flag.
- Shrink category elasticities toward the pooled value.
- Commit only the parameters, a holdout report against the naive 14-day baseline, and an attribution notice.

**Arena orchestrator.**
- **Calls:** asynchronous, with a concurrency limit set per route.
- **Agents:** Strategists are 6 styles proposing 3 Promo Plans each; Rivals are 6 styles proposing Counter-moves inside the Rival Snapshot's plausible range.
- **Scale:** 3 rounds on the MI300X route. On the fallback route, 2 Strategists × 2 Rivals × 2 rounds on up to 3 SKUs, unless the Seller chooses otherwise.
- **Validation:** every LLM output is JSON against a schema. Invalid or out-of-range proposals are rejected and counted, never repaired silently.
- **Events:** the run streams events over Server-Sent Events (round started, plan proposed, Counter-move, pairing scored, SKU decided, telemetry).
- **Telemetry:** tokens/s, time to first token, requests in flight, calls done and failed, route, and cost per Verdict.

**Readers.**
- **Campaign Invitation:** the Evolus JSON extractor first, then Gemma vision on our route as a fallback.
- **Rival Snapshot:** Gemma vision extracts price, voucher and gift.
- **Catalogue:** a CSV parser that gives row-level errors.
- **Brand Price Rule:** the Campaign Desk agent turns the agreement in the knowledge library into structured constraints with clause references. Ambiguous clauses produce Escalate.

**Explainer.** It writes the Verdict explanation in English or Thai from engine outputs. Every number in the text must match an engine number; otherwise the explanation is rejected and regenerated. If that fails twice, the numbers-only template is used.

**Evolus integration** ([ADR 0003](../../docs/adr/0003-arena-bypasses-evolus.md), [API notes](../../docs/api-guide/evolus-api.md)). A provisioning script uses a User API Key for creation and the application key for runtime. It creates:
- a knowledge library (`language=en`) holding the fee rules and the fictional Glow Lab BKK brand agreement;
- a JSON extractor for Campaign Invitations;
- the Campaign Desk agent on `own/<alias>` (our vLLM) with the library attached;
- a Web API that exposes MarginArena's "evaluate" and "explain" endpoints, attached to the agent;
- a workflow created with `isActive: true`. It takes the confirmed Verdicts as parameters, routes Approve, Revise and Escalate, produces the bulk-upload file, drafts the approval email (AI Tool `email`), and calls our callback.

The Arena never goes through Evolus because of the 60 requests/min limit.

**API (backend).**
- sample data;
- upload and read an invitation;
- upload a catalogue;
- upload a Rival Snapshot;
- start an Arena run (returns a run id), then stream it, then get the results;
- explain a Verdict (EN/TH);
- confirm, which triggers the Evolus workflow;
- the Evolus callback;
- the evidence and benchmarks;
- the route health.

**UI.** The design from the prototype (branch `prototype/arena-ui`, ticket 09):
1. **Invitation:** inputs plus the sample button.
2. **Arena:** live bracket with the GPU scoreboard and commentary.
3. **Verdicts:** grouped list; the "How we decided" drawer holds the waterfall, the Strategist × Rival grid, the Evidence Links and the Thai toggle.
4. **Confirm:** the Evolus actions and their status.

An AMD Evidence panel stays visible, and a full Evidence page is linked. The UI is in English, prices are in THB with USD alongside, and the copy uses the glossary terms.

**Proof harness.** It produces committed, reproducible artifacts (data plus the command that made them), and the README, slides and video use only these numbers:
1. elasticity holdout against the naive baseline;
2. fee golden tests (Lazada's worked example ending at ฿623.93; Shopee ฿279 net → ฿200.31 payout);
3. a policy comparison over the demo catalogue: platform suggestion, match the competitor, LLM-direct, and MarginArena, labelled as model-based estimates; it includes the LLM-direct numeric error rate;
4. AMD performance: Arena wall time, tokens/s, time to first token, and a concurrency sweep from 1 to 128, on the MI300X against Token Factory;
5. agent quality: the share of valid proposals and the tool-call success rate;
6. Arena vs Grid: worst-case profit and the number of engine evaluations.

**Ops.**
- A droplet bootstrap script: pinned `vllm/vllm-openai-rocm` digest, Caddy, DuckDNS, and only ports 22, 80 and 443 open.
- The droplet is destroyed after each session, because a powered-off droplet still bills. GPU hours follow ticket 04's budget.
- Secrets live only in `.env`.

## Testing Decisions

- **What makes a good test:** it exercises behaviour through a public seam with realistic inputs and asserts on outputs a Seller or judge would see: Verdicts, numbers, Evidence Links, streamed events. It never checks internals.
- **Seam 1, the engine's public evaluation function.** This is test-first and carries most of the coverage:
  - golden fee cases from the marketplace examples;
  - one case per Promo Mechanic;
  - stock caps;
  - price-cuts-only elasticity;
  - robust selection;
  - every Verdict branch;
  - Brand Price Rule enforcement;
  - Margin Protected;
  - Evidence Link completeness.
- **Seam 2, the backend HTTP API with a scripted fake LLM client.** A full run goes from sample invitation to streamed events, then Verdicts, then confirm. It covers invalid JSON from the LLM, the fallback route and Evolus errors. The Evolus client is replaced by a recorded fake.
- **Seam 3, the explainer's numeric-consistency check.** Explanations with wrong numbers must be rejected.
- Live checks against the real vLLM endpoint and the real Evolus workspace are scripts that write evidence artifacts, not unit tests (ticket 08's tool-calling gate is one of them).
- This is greenfield, so the engine tests become the reference style for the others.

## Out of Scope

- B2B bulk-quote negotiation.
- Basket or multi-SKU Promo Plans (multi-buy of the same SKU is in).
- A full Thai UI; only the Verdict explanation toggles to Thai.
- Reading invitations directly from Seller Centre, or registering with the marketplace on the Seller's behalf.
- Enterprise features. Thousands of SKUs, on-prem deployment and multi-step approvals appear only as a roadmap slide and an Enterprise pricing tier, although the engine must not prevent them.
- Accounts, authentication and billing.
- Training or fine-tuning models.
- Audio input. ClausePulse Live was considered and rejected.

## Further Notes

- **Priorities ([ticket 01](issues/01-charting-grill.md), Q36):**
  - **MUST:** engine with golden tests; Arena on our vLLM; the Verdicts; the chosen UI; Evolus extractor, library and workflow; AMD Evidence with a real benchmark; Token Factory fallback; Vercel; README and Docker.
  - **SHOULD:** all five mechanics; Arena vs Grid; Rival Snapshot; Explain in Thai; Evidence Links; Brand Price Rule; LLM-direct baseline.
  - **COULD:** a Lazada profile; the Evolus chat widget.
- **Schedule:**
  - **Wed 14:** engine and elasticity; Arena on Token Factory.
  - **Thu 15:** 3 GPU hours (ticket 08 gate); UI; Evolus.
  - **Fri 16:** 5 GPU hours (full Arena and benchmarks); mechanics; Rival Snapshot; Vercel.
  - **Sat 17:** polish; README; slides; video script; the user records in the morning; submit before 24:00 ICT.
  - **Sun 18:** freeze before 17:00 ICT.
  - **Commits:** small and steady throughout.
- **Pitch:**
  - Lead with the Arena, a measured MI300X benchmark, and Evolus carrying out the Verdicts. Don't lead with "the LLM never invents numbers": at least five other entries already say it.
  - Business Value:
    - market: 1.2M Shopee TH Sellers, 170k in 9.9, fees 22–40%, net profit 2.3%, a regulator fee subcommittee formed 14 Oct 2026;
    - revenue model: Free, Pro ฿390, Agency ฿1,990 and Enterprise tiers, with assumptions labelled.
  - Only published Seller voices are quoted.
- **Open dependencies (map fog):**
  - the Seller Centre bulk-upload file format, which needs research;
  - the user's tickets 06 and 07: keys in `.env` including the Evolus User API Key, a card check, DuckDNS, and the GitHub account;
  - ticket 08's tool-calling gate;
  - a competitor re-snapshot on 17 Oct.
