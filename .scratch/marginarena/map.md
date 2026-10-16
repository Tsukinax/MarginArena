# Map: MarginArena

Label: wayfinder:map

## Destination

A build-ready `spec.md` for the MarginArena MVP, with every decision made, so that building it ends in a submission by **Sun 18 Oct 2026 17:00 ICT** (10:00 UTC) on lablab.ai. The MVP must satisfy all of these:

- the AMD requirement for prizes
- the Reinvent Commerce track rules
- the Evolus track rules

## Notes

- Domain: e-commerce promotion economics for marketplace Sellers. Terms live in `CONTEXT.md`; decisions live in `docs/adr/`.
- Skills for every session: `grilling` and `domain-modeling`. Research tickets follow the method in `research`.
- Tracker: local markdown (see `docs/agents/issue-tracker.md`). There is no git remote yet. Research findings go in `.scratch/marginarena/research/` instead of `research/*` branches.
- Team: the user plus Claude. Claude writes all the code. The user submits on lablab.ai, records the video, and handles anything that needs their account.
- Constraints:
  - AMD must run a meaningful, visible part of the product.
  - Commerce track: "Do not use a language model as the only forecasting method".
  - Evolus track: the event workspace (code AMDACT3); the main agent on our own vLLM endpoint on AMD Developer Cloud; at least 2 Evolus building blocks driven through the API; a containerized app; a public repo; a README that runs.
- Event context: `docs/reports/` and `docs/research_notes/` (kept locally, not in the public repo). Token Factory API: `docs/api-guide/tokenfactory-guide.md`.

## Destination reached

[spec.md](spec.md) was written on 14 Oct 2026 (Status: ready-for-agent). The remaining fog items below are build-time dependencies, not open design decisions.

## Decisions so far

- [01 Charting grill](issues/01-charting-grill.md): the destination is a spec; the tracker is local; the Seller is a B2C marketplace Seller at 11.11; the user submits and Claude builds; the AMD credits and Token Factory login are ready; the decision unit is the Promo Plan and the outcome the Verdict; LLMs propose and the engine computes ([ADR 0001](../../docs/adr/0001-numbers-come-only-from-the-engine.md)); real public data drives elasticity; the Evolus track is in scope. Round 3: two tracks; Shopee TH framing with THB and USD; the Campaign Invitation storyline; robust Arena selection against the Margin Floor; [ADR 0002](../../docs/adr/0002-two-inference-routes.md) two inference routes; sslip.io hostname (Q49 replaced DuckDNS). Round 13: [ADR 0004](../../docs/adr/0004-ai-explores-open-ended-math-solves-closed.md): the engine searches the numbers, the AI red-teams and proposes Plan Ideas, Counter-moves act through relative price, the elasticity band is part of the Scenarios. Round 11: Enterprise is roadmap and pricing only (Q47); published Seller voices only, no invented testimonials; a short flow is fine without being strict; a tiered SaaS revenue model with a TAM (assumptions labelled). Round 10: the glossary is `CONTEXT.md`; the video is English voice-over, done last. Round 9: MarginArena confirmed over ClausePulse; Evidence Links; the Brand Price Rule in the Evolus library; an LLM-direct baseline; only measured numbers may be published. Round 8: the Seller's inputs and the sample shop; MUST/SHOULD/COULD priorities; the Wed–Sun schedule; the video and slide plan. Round 7: five Promo Mechanics; an Arena-vs-Grid proof; Rival Snapshot grounding; three measured "why AMD" reasons; an Explain-in-Thai toggle. Round 4: the Arena runs every Invitation SKU in parallel; [ADR 0003](../../docs/adr/0003-arena-bypasses-evolus.md) the Arena bypasses Evolus while the Campaign Desk agent and a workflow carry out the Verdict; FastAPI, React and Vercel; five proof metrics; a 12-SKU skincare demo Seller with a 10% Margin Floor.
- [05 Evolus integration](issues/05-evolus-integration.md): we connect our vLLM through Your models; our app drives Evolus over REST and agent chat; a workflow carries out the Verdict through a call-endpoint block or webhook; limits are 60 rpm and 50k credits; Evolus staff check the model endpoint, building blocks and call counts. Ticket 06 answered the day-1 checks, and on 15 Oct `evolus_kit.py apply` built the library, the Campaign Desk agent, the Verdict workflow and the invitation extractor (`evidence/evolus-*.md`).
- [02 Elasticity dataset](issues/02-elasticity-dataset.md): FreshRetailNet-50K (CC BY 4.0, Asian online grocery) as primary and Complete Journey as fallback; a log-log fixed-effects model on in-stock days with category elasticities shrunk to the pool; holdout error 19% lower on deeper discounts; elasticity applies to price cuts only; the grocery-vs-marketplace mismatch is stated openly with a Seller override.
- [04 Model serving on MI300X](issues/04-model-serving-mi300x.md): Gemma-4-31B-IT on vLLM 0.31 ROCm (gemma4 parsers), gated by a day-1 tool-calling test with Qwen3.6-27B as the fallback; vLLM is localhost-only behind HTTPS Caddy on an sslip.io name; $100 buys 38.6 h, so we rebuild from a script; Token Factory is the dev and app fallback; judging-window uptime is settled in ADR 0002.
- [03 Marketplace fees](issues/03-marketplace-fees.md): Shopee Non-Mall PRIME pays 27.82% + ฿1.07 and LazMall 30.50%, charged on the price after the Seller's own discounts; Campaigns cost the Seller through price/discount bands, required programmes and co-funding, not extra fees; invitations live only in Seller Centre and the bands are inputs; joining is opt-in, so the Verdict comes before the Seller confirms; the demo Seller is a skincare shop; Lazada's ฿623.93 example is a golden test.
- [09 UI prototype](issues/09-ui-prototype.md): Variant C's guided flow is the backbone, with Variant A's live Arena as the Checking step and Variant B's waterfall and heat grid inside the "How we decided" drawer.
- 10 ACT III field (ticket kept locally, not in the public repo, because it scores other teams): 12 entries so far, only 2 in Commerce; nobody does promotion pricing, SEA sellers, adversarial agents, Evolus for commerce, or self-served Gemma on MI300X; lead with the Arena, the MI300X benchmark and Evolus carrying out the Verdict, not with "the LLM never invents numbers"; commit in small steps; re-snapshot on 17 Oct.
- [11 Thai seller market](issues/11-thai-seller-market.md): ฿1.14T GMV; 1.2M Shopee TH Sellers, 170k of them in 9.9; over half of sales come from mega Campaigns; fees take 22–40% and average net profit is 2.3%; regulators are acting on platform fees; no existing tool costs a Campaign Invitation before the Seller commits.
- [Q57 / ADR 0005](../../docs/adr/0005-token-factory-is-the-only-inference-route.md): the submission runs on AMD Token Factory only, after the organisers confirmed in Discord that it counts as the AMD component and for the Google prize; no $100 credit, no droplet; the AMD mentor also confirmed it meets the Evolus track's own-endpoint rule.
- [Q58](issues/01-charting-grill.md): when Token Factory's Gemma has no workers, live runs and the Evolus agent fall back to Qwen3.8-27B on the same route, and the app names the model that answered.
- [Q59](issues/01-charting-grill.md) (15 Oct, night): Token Factory dropped Gemma-4-31B-IT from its catalogue for about 20 hours (back by 16 Oct 20:48 ICT) and Qwen3.8-27B spent its token budget thinking, so DeepSeek-V4-Flash is the fallback and the app reads the catalogue before a run.
- [Q60](issues/01-charting-grill.md) (17 Oct): no cloud GPU; the organisers said standalone GPUs are not needed in ACT III. Token Factory only; a live 4-SKU run on the live site answered 20 of 20 Gemma calls in 79.84 s.
- Field analysis (15 Oct, 22:50 ICT, kept locally, not in the public repo): 26 entries; best odds in the Evolus track, then Vibe Generation; lead the pitch with the Seller's money problem and disclose that 70% of Margin Protected is SS-50's override-driven Revise (README now does). The same night the demo was hardened (limits, recorded Evolus fallbacks) after a 56-agent review.
- 17 Oct, submission day: [Q61](issues/01-charting-grill.md) discloses that SS-50's Revise trades average profit (฿79,244.00 vs ฿108,260.42) for a safer worst case, in the README and deck. Engine-only controls ([evidence/sensitivity.md](../../evidence/sensitivity.md)) show the Verdicts hold with a deepest-move rule-based Rival or random Rivals, so the public text presents Gemma's part as the language work, not as risk only AI found. The API moved to Vercel `sin1` after Token Factory's chat calls hung from `hkg1`. The first screen states the problem and the recorded headline; Confirm shows the Evolus run's trail. The pitch (video script, deck, cover, lablab texts, Q&A card, an emergency MP4) is in `pitch/`, gitignored. Git history was rewritten to drop the research that scored other teams.
- [Q56 red-team research](research/q56-red-team.md): under today's assumptions the AI Rivals' Counter-moves cut worst cases but change no decision; every SKU now shows that cut, and SS-50 gets a labelled Seller override (elasticity −2.62 with its own band) so the demo can show a Rival turning an Approve into a Revise (Q56, option 2).

## Not yet specified

- The Seller Centre bulk-upload file format for Approve actions (research, needed before the workflow step that produces the file). The Evolus API facts are now in `docs/api-guide/evolus-api.md`, and the agent can call our engine through a Web API.
- A competitor re-snapshot on 17 Oct, using the same lablab endpoints as ticket 10.

## Out of scope

- B2B bulk-quote negotiation, because the MVP Seller is B2C.
- Basket or multi-SKU Promo Plans, because one Promo Plan covers one SKU in one Campaign.
- A full Thai-language UI, because the UI is in English for the judges. Only the Verdict explanation gets a Thai toggle (Q34).
- Reading Campaign Invitations straight from Seller Centre, because no public API exists and the Seller uploads a screenshot or PDF instead.
