# 01 Charting grill

Type: grilling
Status: resolved
Blocked by: none

## Question

What is MarginArena's destination, and what are the first decisions everything else depends on?

## Answer

Rounds 1–2 with the user, 14 Oct 2026:

- **Destination:** a build-ready spec for an MVP that can be submitted by 18 Oct 2026 17:00 ICT.
- **Tracker:** local markdown in `.scratch/`. `git init` is done, and a public GitHub repo comes later.
- **Primary user:** a B2C marketplace **Seller** (Shopee/Lazada style) during the 11.11 **Campaign**. B2B is out of scope.
- **Roles:** Claude writes all the code. The user submits on lablab.ai and records the video.
- **AMD access:**
  - The user can log in to Token Factory.
  - The $100 AMD Developer Cloud credits have been **granted**.
  - The Token Factory API is documented in `docs/api-guide/tokenfactory-guide.md`: 30 requests per minute and 8 concurrent requests per key, with Gemma-4-31B-IT available.
- **Decision unit:** one **Promo Plan** is one SKU in one Campaign. The outcome is a **Verdict**: Approve, Revise or Escalate.
- **What LLMs do:** parse the Seller's goal, propose plans as **Strategists**, stress-test them as **Rivals**, and explain the result. The engine computes every number ([ADR 0001](../../../docs/adr/0001-numbers-come-only-from-the-engine.md)).
- **Data:** real public data for price elasticity, real marketplace fee schedules, and a synthetic but realistic Seller catalogue.
- **Evolus track:** in scope, at the user's request. Its rules become mandatory for us.
- **Time:** the user says time is enough and wants the idea built out fully.

Round 3, where the user said "yes to all":

- **Q14** – Enter two tracks, Reinvent Commerce and Evolus. The user creates the Evolus workspace via `app.evolus.ai/join/AMDACT3`.
- **Q15** – Frame the product around Shopee Thailand. Show THB with USD alongside the key figures, and support multiple Marketplace Profiles. Say openly that elasticity comes from FreshRetailNet, which is Asian online-grocery data.
- **Q16** – The main storyline starts from a Campaign Invitation, given as a Seller Centre screenshot or PDF. It flows to the Arena, then the Verdict, then the Seller confirms (joining is opt-in by law), then an Evolus workflow carries the decision out. A Promo Plan the Seller types in is the secondary path.
- **Q17** – The Arena is a multi-round tournament of Strategists against Rivals. The winning plan is chosen robustly: it must stay above the Margin Floor against every Counter-move. Escalate when no plan passes, or when the elasticity uncertainty is too wide.
- **Q18** – The user has the `rc-` Token Factory key and will paste it into `.env`. They will check that a card is on file. No droplet will be created yet.
- **Q19** – Ask on Discord when judges actually test. The public app falls back to Token Factory, so it never goes down. Keep about 11 h of MI300X credit in reserve for judging windows ([ADR 0002](../../../docs/adr/0002-two-inference-routes.md)).
- **Q20** – Use DuckDNS for the droplet's HTTPS hostname. The user signs up.

Round 4, where the user said "yes to all":

- **Q21** – The Arena covers every SKU in a Campaign Invitation in parallel.
  - On the MI300X: about 12 SKUs × 6 Strategists × 6 Rivals × 3 rounds, roughly 430 LLM calls.
  - On Token Factory: about 3 × 2 × 2 × 2, roughly 24 calls.
  - Each Strategist proposes 3 Promo Plans. Tune these numbers after the speed benchmark.
- **Q22** – The Arena calls vLLM directly, bypassing Evolus ([ADR 0003](../../../docs/adr/0003-arena-bypasses-evolus.md)).
  - The Evolus main agent, "Campaign Desk", runs on our vLLM. It uses a document extractor for the Campaign Invitation and a knowledge library of fee and Campaign rules, explains the Verdict, and chats with the Seller.
  - After the Seller confirms, an Evolus workflow carries out the Verdict:
    - Approve produces a bulk-upload file for Seller Centre.
    - Revise sends the new Promo Plan to the Seller.
    - Escalate sends an approval email.
  - Adjust this after the checks in ticket 06.
- **Q23** – Stack: a Python FastAPI backend with the engine inside; elasticities fitted by an offline script, with only the parameters committed; a React + TypeScript (Vite) frontend; a Dockerfile and docker compose. The public demo is hosted on Vercel. The user needs a Vercel account.
- **Q24** – Proof, five items:
  1. The elasticity holdout (19% lower error).
  2. Fee golden tests: ฿623.93 for Lazada and ฿200.31 for Shopee.
  3. MarginArena against "accept the platform's suggested discount" and "match the competitor", labelled as model-based estimates.
  4. AMD performance: Arena wall time and tokens/s on the MI300X against Token Factory, with a concurrency sweep.
  5. Agent quality: the share of proposed Promo Plans that are valid, and the tool-call success rate.
- **Q25** – The demo Seller is a Shopee Non-Mall PRIME skincare shop with 12 SKUs.
  - Margin Floor is the per-unit profit after fees and cost, as a % of the selling price. The default is 10% for the shop, overridable per SKU.
  - Escalate when the total Campaign profit falls below the "don't join" baseline.
- **Q26** – Show a UI prototype before building for real. The user asked whether it would be in Figma; this is answered in round 5.

Round 5–6: the prototype is built in browser code, not Figma, and the chosen screens are C + A's Arena + B's charts (see ticket 09).

Round 7, where the user said "yes to all":
- **Q30** – Support five Promo Mechanics so the plan space cannot be brute-forced: a price cut, a shop voucher with a minimum spend, a multi-buy discount on the same SKU, a gift with purchase (its cost counted), and a per-buyer quantity limit. Strategists compose them, and the engine has a formula for each. Assumptions such as how much a gift is worth to buyers are shown and the Seller can override them.
- **Q31** – Add a sixth proof metric, **Arena vs Grid**. Over 12 SKUs, compare the Arena with an exhaustive price × voucher grid on worst-case profit and on the number of evaluations. Report it honestly even if the Arena loses, then iterate.
- **Q32** – Rivals are grounded in a **Rival Snapshot**: the Seller uploads 2–3 competitor listing screenshots, Gemma vision on MI300X extracts the prices, vouchers and gifts, and Counter-moves stay within plausible ranges.
- **Q33** – "Why AMD" rests on three measured reasons:
  1. Confidential cost and margin data stays on our own GPU with an open model.
  2. The Arena's burst concurrency (100+ requests) fits on one 192 GB MI300X.
  3. Cost per Verdict, compared with a closed API.
- **Q34** – The UI stays in English, with an "Explain in Thai" toggle on Verdicts. Gemma writes the text, and every number comes from the engine.
- **Positioning lesson from ticket 10:** lead with the Arena, the measured MI300X benchmark and Evolus carrying out the Verdict, not with "the LLM never invents numbers".
- The user approved local git commits (14 Oct). Do not push until ticket 07 names the GitHub account.

Round 8, where the user said "yes to all":
- **Q35** – The Seller provides four inputs:
  1. a Campaign Invitation screenshot or PDF, read by an Evolus extractor or Gemma vision;
  2. a catalogue CSV with cost, stock, current price and the 30-day lowest price;
  3. a Margin Floor;
  4. an optional Rival Snapshot.

  A "Use sample invitation" button loads the fictional Glow Lab BKK shop (12 skincare SKUs).
- **Q36** – Priorities:
  - **MUST:** engine with golden tests; Arena on our own vLLM; the three Verdicts; the chosen UI; Evolus extractor, library and workflow; an AMD Evidence page with a real benchmark; Token Factory fallback; Vercel deploy; README and Docker.
  - **SHOULD:** all five Promo Mechanics (three at minimum: price cut, shop voucher with minimum spend, gift); Arena vs Grid; Rival Snapshot; Explain in Thai.
  - **COULD:** a Lazada profile; the Evolus chat widget.
- **Q37** – Schedule:
  - **Wed 14:** engine, elasticity fit, Arena on Token Factory.
  - **Thu 15:** MI300X for 3 h (ticket 08 gate), real UI, Evolus.
  - **Fri 16:** MI300X for 5 h (full Arena and benchmarks), mechanics, Rival Snapshot, Vercel.
  - **Sat 17:** polish, README, slides, video script; the user records; a complete submission before 00:00 ICT.
  - **Sun 18:** small fixes and a freeze before 17:00 ICT; the GPU stays up during judging windows.
- **Q38** – Claude writes a 4:30 video script with a shot list, plus a PDF deck. The user records and does the voice-over (language to be confirmed). Storyline: hook (฿100 item → ฿6.67), problem (1.2M Sellers, 2.3% net profit), live demo, six proofs, why AMD, market.
- The private Gemini chat and the local skills tooling are git-ignored.

Round 9, where the user said "yes to all":
- **Q39**
  - (a) The project is confirmed as **MarginArena** in the 11.11 Campaign theme. ClausePulse Live, Gemini's alternative idea, was rejected.
  - (b) Every number in a Verdict gets an **Evidence Link** (SHOULD).
- **Q40** – A **Brand Price Rule**: the demo shop has a fictional brand agreement, clearly labelled as fictional, stored in the Evolus knowledge library.
  - An agent extracts each clause into a structured constraint and keeps the clause reference.
  - The engine enforces the constraint deterministically.
  - An ambiguous clause leads to Escalate.
  - Priority: SHOULD.
- **Q41** – Proof metric 3 compares four policies: the platform's suggested discount, matching the competitor, an **LLM-direct** policy (Gemma plans and computes profit on its own), and MarginArena. Report how far the LLM-direct profit figures are from the engine's.
- **Gemini claims rejected as unverified or false:**
  - "90%+ win odds".
  - The backtest figures "28 loss cases / 0.0% leaks / +34.8% / 1.4 s".
  - "TokenRouter was the ACT II champion".

  Only numbers we measure ourselves may appear in the deck, the video or the README.

Round 10:
- **Q42** – The glossary is renamed to `CONTEXT.md`, and `docs/agents/domain.md` points the project skills at it.
- **Q43** – Option (a): the user records the voice-over in English from Claude's script, with a short Thai line plus English subtitles in the problem intro. **The video comes last**, after everything else is built.

Round 11:
- **Q44** – The user is relaxed about the "three screens" pattern. Keep the flow short (around four steps), never sprawling, and trim later if needed.
- **The lablab "How to Win" guide reviewed against the plan.** Gaps: no revenue model, no team/roadmap segment in the video, no first-hand seller pain, and an over-engineering perception risk that the Arena-vs-Grid and LLM-direct proofs must answer.
- **Q45** – Revenue model: tiered SaaS priced by SKUs checked per Campaign.
  - Tiers:
    - Free: 1 Campaign a month, up to 10 SKUs.
    - Pro: ฿390 a month, every Campaign, up to 200 SKUs, Rival Snapshot and the Thai explanation.
    - Agency: ฿1,990 a month, multiple shops, Evolus workflow.
  - Later distribution: the Shopee and Lazada app stores.
  - Slide TAM, conservative: 170k Sellers joined 9.9 (Shopee figure). 5% on Pro at ฿390 is about ฿40M a year (about $1.15M) in Thailand alone, plus five more SEA markets running the same Campaign mechanics.
  - Assumptions are labelled as assumptions in the slides.
- **Q46** – No Seller in the user's network, so the pitch uses only **published** Seller voices: the Thai e-Commerce Association survey (fees are the top complaint for 96%; average net profit 2.3%) and complaints reported in the press, as collected in ticket 11. Sources are cited, and no testimonial is invented.
- **Q47** – The hackathon focus stays on small Sellers, the underserved segment. Enterprise appears only as a roadmap and pricing tier, with no extra features built:
  - an **Enterprise** tier, "contact sales", for Mall stores and brands with thousands of SKUs, deployed on the customer's own AMD GPUs, with multi-step approval through Evolus;
  - a roadmap slide: small Sellers, then Shopee Mall/LazMall, then large brands on their own AMD hardware (the Trade Promotion Optimization / Revenue Growth Management space).
  - The engine must not get in the way of thousands of SKUs or per-SKU elasticity overrides.
- The `.gitignore` edit was accidental and has been reverted to the committed version.

Round 12:
- **Q49 (supersedes Q20)** – The droplet's HTTPS hostname comes from **sslip.io**, a name made from its IP, so no domain or account is needed. Options considered:
  - DuckDNS, which needs a signup;
  - a Cloudflare named tunnel, which needs a domain on Cloudflare;
  - the user's production domain: not worth the risk to production DNS or the public association;
  - plain http, rejected as insecure.
  
  Cost: after each rebuild the URL changes and the user pastes the new one into Evolus "Your models"; the bootstrap script prints it.
- **Q51 (supersedes parts of Q17, Q30 and Q31)** – After a `/scrutinize` pass ([ADR 0004](../../../docs/adr/0004-ai-explores-open-ended-math-solves-closed.md)), the work is split: the engine exhaustively searches the numeric plans; Rivals red-team the leading plan over several rounds; Strategists propose non-numeric Plan Ideas; the AI also reads inputs and explains Verdicts.
  - Counter-moves act through relative price.
  - Scenarios include the elasticity band.
  - Demo SKUs use the pooled elasticity of −1.49 with its band; any per-SKU value is labelled a Seller override.
  - Token Factory is used for sample data only.
  - A recorded MI300X run backs the sample shop.
  - Proof 6 becomes "red-team value".
- **Q52 (supersedes part of Q17)** – Selection is **maximin**: the eligible plan with the best worst-case profit wins, and expected profit only breaks ties. Approve compares worst cases.
  - Evidence: in the live Token Factory run, picking by expected profit chose a plan ฿88 worse in the worst case than the engine-only plan. That contradicts Margin Protected (a worst-case metric) and could make proof 6 negative.
- **Q53** – The default gift perceived value drops from 50% to **30%** of retail. It is shown and overridable, with its sensitivity in the UI.
  - Evidence: at 50%, the live run chose "add a mini gift" on every Revise.
- **Escalate is not "don't join"** (consistency fix found in the second live run). Margin Protected counts only Approve and Revise SKUs; an Escalate hands the decision to a person and shows its own worst-case line. Previously, assuming "don't join" made the run's total −฿1,130, because the Seller's own Margin Floor blocked a profitable join. Token Factory pacing is lowered to 15/min after 7 retries at 20/min.
- **Q54** – Skip is a kind of Revise: when no plan is eligible and not joining beats every feasible plan (one that meets the invitation and the Brand Price Rules) in both the worst case and expectation, the Verdict is Revise/Skip, and Margin Protected counts not joining minus joining as invited. Escalate is kept for genuine trade-offs: a floor that blocks a profitable join, an elasticity band that flips the outcome, or a brand conflict.
- **Q55** – The Token Factory fallback checks a trio chosen to show every Verdict (NT-200 Approve, VC-30 Escalate, SM-10 Skip) unless the Seller picks products. The numbers are still computed live.

Round 14 (15 Oct, with the user):
- **Q56** – No run since Q52 had the AI Rivals change a decision ([research/q56-red-team.md](../research/q56-red-team.md)). The user chose option 2, in two parts:
  - Every decided SKU shows what the Rivals found: the worst case of the plan chosen against the generic hold, match and undercut moves, and how far the Counter-moves the Rivals found cut it (`red_team_cut`, commit 352ffaf). This part is built.
  - SS-50 (sunscreen, a lookalike-heavy product) gets a labelled Seller override: the literature mean elasticity −2.62 with its own band at the fitted band's relative width (−3.48 to −1.36). Q51 already allows labelled per-SKU values. With it, five of six recorded Counter-moves each turn SS-50's Approve into a Revise. k stays 1.0, and the other SKUs keep the pooled fit and its band. Built in commit 1947f58.
  - The Token Factory fallback set grows to four SKUs (NT-200, SS-50, VC-30, SM-10) so it can show this. The user chose it on 15 Oct, accepting about a third more time per run.

Round 15 (15 Oct, with the user):
- **Q57** – Token Factory is the only inference route: no $100 credit and no droplet ([ADR 0005](../../../docs/adr/0005-token-factory-is-the-only-inference-route.md), superseding ADR 0002).
  - Evidence, from the user's Discord screenshots: lablab's announcement (13 Oct) that ACT III is hosted on Token Factory with no card and no need for the $100 credit, and an AMD mentor's answers (14 Oct) that the Token Factory API counts as a meaningful AMD component and Gemma through it counts for the Google prize.
  - The credit needs days of approval, so the user chose not to request it.
  - Consequences: no GPU session; AMD evidence comes from recorded Token Factory runs; the UI's claim about checking all 12 SKUs on our own MI300X goes.
  - Resolved the same day: another team asked in Discord whether Token Factory meets the Evolus track's "own vLLM endpoint" rule, and the AMD mentor answered (14 Oct, 07:13 ICT) that it "perfectly satisfies this requirement". The Evolus agent runs on Token Factory under "Your models" (alias `tf-gemma`).
- **Q58** – When Token Factory's Gemma has no workers (500 "no_available_workers", seen on 15 Oct), live runs and the Evolus agent fall back to Qwen3.8-27B on the same route, and the app says so. Gemma stays the model every run starts with. The user chose this on 15 Oct.
- **Q59** (15 Oct, about 23:00 ICT, decided by Claude under the approved plan; the user can overrule): Token Factory's `/models` no longer listed Gemma-4-31B-IT and answered 400 "not supported", while Qwen3.8-27B spent its whole 700-token budget thinking (1 to 2 valid answers of 20 per run). The fallback becomes DeepSeek-V4-Flash, which answered 20 of 20 calls in a live 4-SKU run (`evidence/runs/token-factory-sample-4sku-deepseek-fallback.sse`). The app reads the catalogue before a run, starts on the fallback when Gemma is missing, and also switches on "not supported". Gemma stays the first choice whenever Token Factory lists it; the recorded Gemma runs remain the evidence for the Gemma prize.
- **Q60** (17 Oct, the user's decision): no cloud GPU. The organisers said standalone GPUs "are not needed and not offered as a part of ACT III", so the GPU session approved on 16 Oct is cancelled (AMD Developer Cloud had also kept the account's GPU limit at 0, and the Radeon Cloud notebook the user opened was a 48 GB W7900D). MarginArena runs on AMD Token Factory only (ADR 0005); `infra/droplet/` stays optional and unrun. Gemma-4-31B-IT was back on Token Factory, and a live 4-SKU run on the live site answered 20 of 20 calls in 79.84 s (`evidence/runs/token-factory-live-site-4sku.sse`).
Round 16 (17 Oct, with the user):
- **Q61** – SS-50's Revise keeps ฿3,785.96 more in the worst case, but averaged over its Scenarios it earns ฿79,244.00 against ฿108,260.42 for joining as invited (maximin, Q52). The user chose to disclose it in the README and the deck, not in the video. The engine's rules stay as they are. The same night, engine-only controls (`evidence/sensitivity.md`) showed that a deepest-move Rival and random Rivals give the same Verdicts and lower worst cases further than Gemma's moves, so the public text no longer presents the Rivals' total cut as risk they found.
- The next question is Q62.
