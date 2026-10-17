# MarginArena: the details

The [README](../README.md) is the short version. This page keeps everything else: the full tour, how the engine
decides, every result with its caveats, the recorded runs, the Evolus build, every assumption, the failures we have
seen, the evidence files and the developer commands. Every product and profit number comes from the engine or from a
file in [`evidence/`](../evidence/); these are model-based estimates for a fictional shop, and no real Seller has used
MarginArena yet.

- [Try it, in full](#try-it-in-full)
- [The problem, in full](#the-problem-in-full)
- [How it decides, in full](#how-it-decides-in-full)
- [Rules the code enforces](#rules-the-code-enforces)
- [What it found, in full](#what-it-found-in-full)
- [Explanations](#explanations)
- [Business case, in full](#business-case-in-full)
- [AMD, in full](#amd-in-full)
- [Evolus, in full](#evolus-in-full)
- [Assumptions and limits, in full](#assumptions-and-limits-in-full)
- [Failures we have seen, and the safeguards](#failures-we-have-seen-and-the-safeguards)
- [Evidence, in full](#evidence-in-full)
- [Develop](#develop)
- [Repository](#repository)
- [Roadmap, in full](#roadmap-in-full)

## Try it, in full

**On the live site**, https://marginarena.vercel.app (no key, no sign-up):

1. Press **Watch the recorded Arena (about 20 s)**. It replays a real 12-product Arena recorded on AMD Token Factory
   and needs no key.
2. Watch the AI Rivals answer each product's plan. On **Daily Sunscreen** (SS-50) their moves changed the
   plan twice. That product carries a labelled Seller override (see [What it found](#what-it-found-in-full)), and a
   rule-based or random Rival changes it too ([sensitivity](../evidence/sensitivity.md)).
3. Press **See the Verdicts**: 8 join as invited (Approve), 1 joins with a better plan (Revise), 2 skip, 1 is left for
   the owner (Escalate). Open **How we decided** on any product, then press **ไทย** for the explanation in Thai; it
   appears at once, and **Ask Gemma again (live)** asks the model again.
4. Press **Review and confirm**, then **Confirm and run the Evolus workflow**: it writes the upload file and drafts the
   owner's approval request. Nothing is sent or registered.

If the sidebar says the backend is not reachable, wait a few seconds: a new server instance is starting.

**Run 4 live on AMD Token Factory** needs `TOKEN_FACTORY_API_KEY` in `.env` when you run it yourself. It checks 4 of
the 12 products, chosen to show every kind of Verdict, because Token Factory allows 20 requests a minute per account.
The sample shop is the only data it sends.

**On your machine:** `cp .env.example .env`, then `docker compose up --build`, and open http://localhost:8008. Checked
from a fresh clone of this repo on 17 Oct 2026 (macOS, Docker Desktop, Docker 29.8.2, no keys): the page,
`/api/health`, the recorded Arena (138 events, no errors), and the recorded Evolus reading and workflow run all answer.

**Sample shop only:** the demo runs on a fictional shop. A Seller's own catalogue, invitation and Rival Snapshot can't
be uploaded yet (on the roadmap).

The screenshot in the README (`images/arena.png`) shows the Arena after the recorded run: the Rivals' Counter-moves
change the leading plan of Daily Sunscreen, the product with the labelled override. Its Margin Protected figure,
฿5,434.46, includes that product's Revise; the two Skips alone keep ฿1,648.50.

## The problem, in full

A Thai Shopee Seller gets a Campaign Invitation inside Seller Centre: join 11.11 if you cut these products by 15–25%.
Joining is opt-in, and the Seller has to decide product by product whether it makes money.

- A Shopee Thailand Non-Mall PRIME Seller of beauty and other FMCG products pays 27.82% of the price after its own
  discounts, plus ฿1.07 per order (fees effective 4 Aug 2026;
  [marketplace-fees.md](../.scratch/marginarena/research/marketplace-fees.md)).
- At those fees, a ฿100 product that costs ฿50 earns ฿21.11 at full price, ฿6.67 at 20% off, and loses ฿0.55 at 30%
  off (`backend/tests/engine/test_unit_profit.py`). The waterfall in `images/margin-waterfall.png` shows the 20% case:
  after the discount, commission, PRIME programme, payment and per-order fees and the ฿50 cost, ฿6.67 profit per unit
  is left.
- Nobody knows in advance how many more units a discount sells, or what lookalike competitors will do in reply.

## How it decides, in full

`images/how-it-decides.png` shows the loop: AI on AMD Token Factory proposes Plan Ideas and Counter-moves and explains
each Verdict; the deterministic engine prices every Promo Plan and picks the best worst case; Evolus reads the
invitation and carries out confirmed Verdicts; a person confirms and decides escalated products. One clarification on
the diagram: the Arena reads the invitation from the sample shop file. The Evolus extractor's reading of the PDF is
checked against it, discount by discount; it is not fed into the Arena.

1. **The engine computes every number a Verdict uses** ([ADR 0001](adr/0001-numbers-come-only-from-the-engine.md)). A
   Rival's stated reason is its own words.
   - Marketplace fees, checked against Lazada's own worked example (it pays out ฿623.93) and a Shopee example we worked
     by hand from Shopee's published rates (it pays out ฿200.31): `backend/tests/engine/test_fees.py`. Each fee is
     computed excluding VAT and rounded, then VAT is added.
   - Demand from a price elasticity fitted on public online grocery sales (see
     [Assumptions](#assumptions-and-limits-in-full)), with an uncertainty band.
   - Each Promo Plan's Campaign profit in every Scenario: each Counter-move at the point elasticity and at both edges
     of the band.
2. **AI explores what is open-ended; math solves what is closed**
   ([ADR 0004](adr/0004-ai-explores-open-ended-math-solves-closed.md)).
   - Strategists (Gemma) propose Plan Ideas, such as a voucher or a gift from the catalogue.
   - The engine searches every numeric Promo Plan those ideas allow, within the invitation and the Brand Price Rules.
   - Each round, Rivals (Gemma) propose Counter-moves against the leading plan, and the engine re-selects over every
     Scenario found so far.
   - In the recorded run, each product had 1 Strategist proposing Plan Ideas and 2 Rivals red-teaming the leading plan
     over 2 rounds (48 Counter-moves across the 12 products). The engine searched 1,745 Promo Plans in all and tested
     each against every Scenario (`evidence/runs/token-factory-sample-12sku.sse`). The code defines 3 Strategist and 6
     Rival personas for a larger route that was not used.
3. **The plan with the best worst case wins** (maximin), provided it keeps the Seller's Margin Floor (10.0% on the
   sample shop), earns at least as much as not joining, and respects every Brand Price Rule. When no plan passes and
   not joining wins both in the worst case and on average, the Verdict is a Revise to Skip; otherwise the trade-off is
   the Seller's to make, and the Verdict is an Escalate.
4. **Every Verdict explains itself**: a waterfall, the Counter-moves it was tested against, Evidence Links, and a short
   explanation in English or Thai. An explanation citing any number the engine did not produce is rejected, and
   `/api/explain` only accepts Verdicts the server signed.

**Stack:** Python and FastAPI (money in `Decimal`, results streamed as Server-Sent Events), React and Vite, Gemma-4-31B-IT
on AMD Token Factory through an OpenAI-compatible client, Evolus (extractor, agent, knowledge library, workflow), Docker,
Vercel.

## Rules the code enforces

| Rule | Where | Test |
|---|---|---|
| The engine computes every number | `backend/src/marginarena/engine/` | `backend/tests/engine/test_unit_profit.py::test_thirty_percent_off_loses_0_55_per_unit` |
| The best worst case wins | `engine/verdict.py` | `backend/tests/engine/test_verdict.py::test_the_plan_with_the_best_worst_case_wins_even_if_another_expects_more` |
| Skip only when not joining beats every plan | `engine/verdict.py` | `backend/tests/engine/test_verdict.py::test_skip_when_not_joining_beats_every_plan_in_the_worst_case` |
| Invalid model output is rejected and counted, never repaired | `backend/src/marginarena/llm.py` | `backend/tests/api/test_arena_api.py::test_model_output_that_is_not_json_is_rejected_and_counted` |
| An explanation with an invented figure is rejected | `backend/src/marginarena/explainer.py` | `backend/tests/explainer/test_number_check.py::test_an_explanation_that_invents_a_figure_is_rejected` |
| A Verdict changed after the Arena is refused | `backend/src/marginarena/api.py` (signed results) | `backend/tests/api/test_explain_api.py::test_a_verdict_changed_after_the_arena_is_refused_before_the_model_sees_it`, `backend/tests/api/test_confirm_api.py::test_confirm_refuses_verdicts_changed_after_the_arena` |

## What it found, in full

These are model-based estimates for a fictional shop; every figure comes from the engine. *Worst case* means the
lowest profit across every Scenario tested. Margin Protected is how much more worst-case profit the Seller keeps by
following the Approve and Revise Verdicts (Skips included) than by joining those products exactly as invited; escalated
products are left out, because a person decides them.

- **Two Skips: ฿1,648.50.** Skipping RN-30 (Retinal Night Serum) and SM-10 (Hyaluronic Sheet Mask x10) keeps
  ฿1,648.50 more profit in the worst case than joining them as invited. This needs no override, but it rests on the
  assumed 2.5× Campaign traffic: at 3.0× both become Escalates ([evidence/sensitivity.md](../evidence/sensitivity.md)).
- **Margin Protected with the override: ฿5,434.46.** Following the 12 Verdicts of the recorded run keeps ฿5,434.46 more
  in the worst case than joining every product exactly as invited (the escalated product, VC-30, is left out:
  `evidence/runs/token-factory-sample-12sku.sse`). ฿3,785.96 of it (70%) comes from SS-50's Revise, which rests on a
  labelled sample Seller override (elasticity −2.62, the published mean, instead of our pooled −1.49). We added that
  override deliberately, so the sample shows a Counter-move changing a plan on a product with many lookalike listings:
  it is a demonstration, not a measured finding. At the pooled fit, SS-50 is an Approve
  ([q56-red-team.md](../.scratch/marginarena/research/q56-red-team.md), [evidence/sensitivity.md](../evidence/sensitivity.md)).
- **SS-50's Revise trades average profit for a safer worst case.** Maximin keeps ฿3,785.96 more in the worst case, but
  averaged over its 7 Counter-moves at the point elasticity the plan earns ฿79,244.00 against ฿108,260.42 for joining
  as invited. At the point elasticity, joining as invited earns more against all 7 Counter-moves; the Revise does
  better only at the edge of the elasticity band, against the 3 deepest undercuts (its "How we decided" table). A
  Seller who prefers the average can join as invited (`sku_decided` for SS-50 in
  `evidence/runs/token-factory-sample-12sku.sse`).
- **How much rests on the assumptions** ([evidence/sensitivity.md](../evidence/sensitivity.md)): if joining brings no
  extra traffic (×1.0), 5 products are Skips and Margin Protected is ฿12,787.08. At ×3.0 the two Skips become
  Escalates (8 Approve, 1 Revise, 0 Skip, 3 Escalate), and all ฿4,581.05 of Margin Protected comes from SS-50's
  override-based Revise.
- **The Verdicts do not depend on who plays the Rival.** With a rule-based Rival that always makes the deepest move
  allowed, or with random moves inside the same bounds (both on the same Plan Ideas), the Verdicts are the same 8
  Approve, 1 Revise, 2 Skip and 1 Escalate (Margin Protected ฿4,005.56 and ฿4,113.36). With only the three generic
  moves, SS-50 stays an Approve (฿2,038.53). Gemma's part is to propose Counter-moves with a stated reason, not deeper
  ones: those two controls lower the worst cases further than Gemma's moves do (the red-team cut summed over the 12
  products: ฿76,929.86 for Gemma's Rivals, ฿185,940.10 for the rule-based Rival, ฿182,767.17 for random Rivals). Never
  read the Rivals' cut as risk only AI found.
- **In percentages** (worst-case profit kept over joining as invited, from the engine's figures in
  [evidence/policy-comparison.md](../evidence/policy-comparison.md)): +32.8% on RN-30 and +34.2% on SM-10 by skipping
  them, +5.9% on SS-50 (with its override), and +1.8% across the 11 products MarginArena decided.
- **No plan breaks a check.** Under the same Scenarios, joining as invited breaks a check (the invited discount, the
  Margin Floor, a Brand Price Rule, or earning less than not joining) on 2 products and matching the competitor on 3.
  MarginArena's search rejects such plans, so its plans break none
  ([evidence/policy-comparison.md](../evidence/policy-comparison.md)).
- **Gemma's own arithmetic.** Given the same facts and formulas, Gemma's own Campaign profit estimates were off by a
  median 61.69% from the engine's, with 1 of 11 answers within 5% ([evidence/policy-comparison.md](../evidence/policy-comparison.md)).
  That is why the engine computes every number.
- **Red-teaming changed a Verdict.** In the recorded 12-product run, the Rivals' Counter-moves changed SS-50's leading
  plan in both rounds (the ฿3,785.96 above); a rule-based or random Rival changes it too. It happened again in a
  separate live 4-product run on Token Factory, where the Revise keeps ฿3,728.85 more in the worst case (Margin
  Protected ฿4,370.15; [evidence/red-team-token-factory.md](../evidence/red-team-token-factory.md)). Both rest on the
  SS-50 override.

## Explanations

- **Number check:** every number in a shown explanation must be a figure from the engine's fact sheet (rounding
  allowed); a draft that fails gets one rewrite, then a numbers-only template. For the recorded run's 12 Verdicts, 32
  explanations were asked (English and Thai) and 32 passed on the first draft
  ([evidence/explainer-replay-12sku.md](../evidence/explainer-replay-12sku.md)). An earlier run on 14 Oct passed 6 of 6
  ([evidence/explainer-token-factory.md](../evidence/explainer-token-factory.md)).
- **Labels:** the check proves numbers, not labels. A review of the first 24 recorded texts against the engine's
  figures found 5 that put a right number on the wrong label; the fact sheet and prompt were fixed, and the 24 texts
  now served were all read clean. In the 14 Oct run, one Thai text said the plan was tested against 183 Promo Plans,
  when the engine had searched 183 plans and tested the leader against the Counter-moves. A live re-ask ("Ask Gemma
  again (live)") is number-checked only.
- **Speed:** a recorded explanation is served for the exact Verdict it explains, in a median 0.17 s on the live site
  (0.16 to 0.19 s); asked live, the 32 answers took 6.1 to 77.3 s each (median 13.45 s).

## Business case, in full

All market figures are estimates or assumptions, with the arithmetic shown; sources are in
[thai-seller-market.md](../.scratch/marginarena/research/thai-seller-market.md).

- **Who it is for:** a Thai Shopee Seller who receives Campaign Invitations in Seller Centre and decides product by
  product whether to join. About 1.2 million Thai MSME shops are on Shopee, and about 170,000 Sellers reached new
  customers in the 9.9 (2026) Campaign (both are Shopee's own figures). A survey of more than 500 Thai SMEs, drawn from
  a complaint database, put average net profit after fees at 2.3%.
- **Why now:** Shopee and Lazada each raised their fees three times in 2026
  ([marketplace-fees.md](../.scratch/marginarena/research/marketplace-fees.md)), so every Campaign discount eats into a
  thinner margin. Thailand's new Platform Fee Subcommittee sorts fees into mandatory costs and optional ones, such as
  joining promotional Campaigns: the decision MarginArena checks (thai-seller-market.md, section 3.2).
- **Alternatives** (thai-seller-market.md, section 4): today's tools report profit after the sale (BigSeller, ZORT),
  work out one unit's margin at a price the Seller types in (KhumMai, GetOneCart), or help the marketplace fill its
  Campaign (Shopee Easy Nomination, Lazada recommended price). We found no tool, marketplace or third-party, that costs
  a Campaign Invitation's terms, tests the Promo Plan against competitor Counter-moves and a demand response, and
  returns a per-product Verdict against the Seller's Margin Floor before the Seller accepts.
- **Planned pricing (an assumption, not validated):** Free (1 Campaign a month, up to 10 products), Pro ฿390 a month,
  Agency ฿1,990 a month (several shops, the Evolus workflow), and Enterprise for Shopee Mall Sellers and brands.
- **Market in Thailand (estimates, at Pro ฿390 a month):** TAM: if every one of the 1.2M shops paid, ≈฿5.62B a year
  (a ceiling, since it counts shops); SAM: for the about 170,000 Thai Sellers that Shopee says reached new customers
  in 9.9 (our proxy for Campaign-active Sellers), ≈฿795.6M a year; SOM: at 5% of them (an assumption), ≈฿39.8M a
  year.
- **What it is worth to one Seller (estimate):** on the sample shop, the two Skips alone keep ฿1,648.50 more in the
  worst case ([evidence/sensitivity.md](../evidence/sensitivity.md)), about 4.2 months of Pro.
- **Go-to-market (planned, not started):** Thai Seller communities and e-commerce agencies (the Agency plan).
- **Why it needs AI, and why AI alone is not enough:** the AI does the language work (reading the Campaign Invitation,
  proposing Plan Ideas and Counter-moves with a reason, explaining each Verdict in Thai or English, drafting the
  owner's approval request). Gemma's own profit arithmetic was off by a median 61.69%
  ([evidence/policy-comparison.md](../evidence/policy-comparison.md)), so the engine computes every number, and the
  Verdicts come from the engine: with rule-based or random Rivals they are the same
  ([evidence/sensitivity.md](../evidence/sensitivity.md)).

## AMD, in full

- **What runs on AMD:** every Strategist, Rival and explanation call the app makes goes to Gemma-4-31B-IT through
  **AMD Token Factory**, AMD's hosted model API, and the Evolus agent and extractor use the same Token Factory
  connection (see [Evolus](#evolus-in-full) for its fallback). In the event Discord, lablab said ACT III is hosted on
  Token Factory, and an AMD mentor said (14 Oct 2026) that using its API counts as the AMD component
  ([ADR 0005](adr/0005-token-factory-is-the-only-inference-route.md)). Token Factory does not say which GPUs serve it,
  so we make no claim about the hardware.
- **Which model answered:** every Arena run and explanation recorded in [`evidence/`](../evidence/) was answered by
  Gemma-4-31B-IT, except the labelled fallback run `evidence/runs/token-factory-sample-4sku-deepseek-fallback.sse`.
- **Scale on Token Factory:** each product gets 1 Strategist and 2 Rivals over 2 rounds, because the account allows 20
  requests a minute.
- **When Gemma is unavailable:** the app reads Token Factory's model catalogue before a run and starts on
  DeepSeek-V4-Flash when Gemma is not listed; if a call answers that Gemma has no workers or is not served, the rest of
  the run switches. The sidebar, the Arena header and each explanation name the model that answered. On 15 Oct at
  about 23:00 ICT the catalogue no longer listed Gemma-4-31B-IT, and a live 4-SKU run on DeepSeek-V4-Flash answered 20
  of 20 calls in 95.9 s (`evidence/runs/token-factory-sample-4sku-deepseek-fallback.sse`).
- `infra/droplet/` holds a kit for serving the same model with vLLM on an AMD Developer Cloud MI300X. It was never
  run: this project used no GPU of its own, and nothing in the demo or the evidence comes from it.

### Recorded runs on Token Factory

Sample data only. The Model column comes from each stream's `run_started` event; the other figures come from its last
telemetry event, in [`evidence/runs/`](../evidence/runs/).

| Stream | Model | SKUs | Valid answers | Invalid | Failed | Retries | Tokens written | Wall time |
|---|---|---|---|---|---|---|---|---|
| `token-factory-sample-12sku.sse` (the replay) | Gemma-4-31B-IT | 12 | 60 | 0 | 0 | 2 | 5,153 | 248.55 s |
| `token-factory-sample-4sku-ss50-override.sse` | Gemma-4-31B-IT | 4 | 20 | 0 | 0 | 0 | 1,646 | 78.25 s |
| `token-factory-sample-3sku.sse` | Gemma-4-31B-IT | 3 | 15 | 0 | 0 | 1 | 1,258 | 86.41 s |
| `token-factory-sample-3sku-maximin.sse` | Gemma-4-31B-IT | 3 | 15 | 0 | 0 | 7 | 1,259 | 118.75 s |
| `token-factory-live-site-4sku.sse` (the live site, 17 Oct) | Gemma-4-31B-IT | 4 | 20 | 0 | 0 | 0 | 1,860 | 79.84 s |
| `token-factory-live-site-sin1-4sku.sse` (the live site from Singapore, 17 Oct) | Gemma-4-31B-IT | 4 | 20 | 0 | 0 | 0 | 1,748 | 102.5 s |
| `token-factory-sample-4sku-deepseek-fallback.sse` (fallback, 15 Oct) | DeepSeek-V4-Flash | 4 | 20 | 0 | 0 | 0 | 2,081 | 95.9 s |

The two 3-SKU streams were recorded on 14 Oct with earlier engine versions, so their Verdicts and Margin Protected
differ from the replay.

Wall time mostly reflects our own pacing (15 requests a minute, under Token Factory's limit of 20 per account), not the
model's speed. The replay plays the 12-SKU run back in about 20 seconds.

## Evolus, in full

**Model route.** The Evolus track asks for the main agent on an open model served "through your own vLLM endpoint on
AMD Developer Cloud". Our Campaign Desk agent and extractor use our AMD Token Factory connection through Evolus "Your
models" (Gemma-4-31B-IT, with a Qwen3.8-27B fallback; Evolus does not record which one answered). When another team
asked in the event Discord whether Token Factory meets the track's own-vLLM-endpoint rule, an AMD mentor answered (14
Oct 2026) that it "perfectly satisfies this requirement", and the organisers later said in Discord that standalone
GPUs "are not needed and not offered as a part of ACT III"
([ADR 0005](adr/0005-token-factory-is-the-only-inference-route.md)).

**How the app drives Evolus.** At run time, over the Evolus REST API
([api.py](../backend/src/marginarena/api.py)): reading the invitation calls the extractor
(`POST /agents/{id}/json/{structure}/ask-file`, from `POST /api/invitation/read`), and **Confirm** runs the workflow
(`POST /workflows/{id}/execute`, from `POST /api/confirm`). Building blocks used: a workflow, a document extractor
and a knowledge library, plus the Campaign Desk agent. The app runs in one container (`docker compose up --build`),
and no key is in the repo (locally, keys go in `.env`).

**In Evolus's own terms:** people stay in the loop when they are needed (Escalate goes to the shop owner, and nothing
happens until the Seller confirms); every run leaves a trail (the workflow's execution record shows each step's
output); and the exact sums come from code, not AI (the engine computes every number the workflow carries).

**Reading the invitation.** An Evolus document extractor reads the Campaign Invitation PDF (the sample's, the only
document the demo sends), and the app checks every discount it read against the invitation the Arena uses
([evidence/evolus-invitation-extractor.md](../evidence/evolus-invitation-extractor.md)). From the live site it read the
PDF in 14.9 s, and all 12 of 12 minimum discounts matched ([evidence/evolus-workspace-usage.md](../evidence/evolus-workspace-usage.md)).
The platform OCR failed with HTTP 502, so the extractor reads the PDF's own text; a scanned invitation would need OCR
again.

**Carrying out the Verdicts.** When the Seller confirms, MarginArena hands the Verdicts to the Evolus workflow
"MarginArena Verdict", which carries them out in 5 steps: Split the Verdicts (Script), Bulk-upload file (CreateFile),
Approval request (AgentCall), Assemble the result (Script), Result (Output). It sorts the Verdicts, writes the
bulk-upload file, and has the Campaign Desk agent draft the shop owner's approval request for escalated products,
using the engine's figures; the knowledge library with the fee rules and the brand agreement is attached to the agent.
The agent runs on our own model connection to AMD Token Factory, so the run uses no Evolus credits
([evidence/evolus-verdict-workflow.md](../evidence/evolus-verdict-workflow.md)): 0.0 credits in the recorded run (10.55
s) and in a live run from the live site (3.1 s). Nothing is sent or registered. The bulk-upload columns are our own
format, because Seller Centre's template is not public.

**Why the Arena bypasses Evolus.** The Arena's own calls go straight to Token Factory rather than through an Evolus
agent. Each one is a short JSON proposal that the engine scores at once, and an Evolus agent in between would add a hop
and count against the workspace's 60 requests a minute without changing any result
([ADR 0003](adr/0003-arena-bypasses-evolus.md)). Evolus runs the business process around the decision: it reads the
Campaign Invitation, holds the fee rules and the brand agreement, and carries out the Verdicts once the Seller
confirms.

**Built from code.** `infra/evolus/evolus_kit.py` builds all of it over the Evolus REST API: `plan` only reads, and
`apply` creates what is missing, finding each resource by name first. See
[infra/evolus/README.md](../infra/evolus/README.md).

**What an Evolus reviewer will find in our workspace:**

- the workflow "MarginArena Verdict" (5 steps);
- the agent "MarginArena Campaign Desk" with the knowledge library "MarginArena Campaign Desk library" (the 2
  documents in `infra/evolus/library/`);
- the extractor agent "MarginArena Invitation Reader" with the output structure "Campaign Invitation";
- the model connection "tf-gemma on AMD" under Your models.

**Every execution so far** ([evidence/evolus-workspace-usage.md](../evidence/evolus-workspace-usage.md)): the Verdict
workflow has 5 executions, 5 succeeded and 0 failed (seen in the workspace on 18 Oct, about 04:30 ICT). The invitation
extractor has 9 executions, 5 completed and 4 failed, all 4 failures on 15 Oct: 2 while the platform OCR answered HTTP
502, and 2 that the records do not explain. `get_model_usage` needs a platform permission this workspace's key does not
have, so model-level usage is not shown.

## Assumptions and limits, in full

- **The sample shop is fictional.** Glow Lab BKK's costs, stock, baselines, brand agreement and Rival Snapshot are
  invented; the fees are Shopee Thailand's. A Seller's own catalogue, invitation and Rival Snapshot can't be uploaded
  yet, and there are no input controls: every assumption is a labelled value in the sample shop file.
- **Elasticity comes from online grocery data**
  ([FreshRetailNet-50K](https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K) by Dingdong Ltd.,
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), from Chinese cities; we fitted (modified) parameters from
  it; the repo holds only the fitted parameters), not marketplace skincare. The pooled fit is −1.49, with a band of
  −1.98 to −0.77. On the dataset's own holdout it beats a naive baseline when discounts deepen (WAPE 0.350 vs 0.426)
  and does worse when they become shallower (0.479 vs 0.405), so the engine applies it to price cuts only. The window
  has no 11.11 Campaign, and the estimate may be biased toward zero ([evidence/elasticity.md](../evidence/elasticity.md)).
  SS-50 carries a labelled Seller override: the published mean elasticity, −2.62 (Bijmolt, Van Heerde and Pieters
  2005), with a band of our own construction.
- **Joining is assumed to bring 2.5× the Campaign traffic before any price effect**, against 1× for not joining. The
  starting point is Lazada reporting about 3.5× GMV in its March 2026 Birthday Campaign (a company claim about
  regional platform GMV, reported in the press).
  Our first derivation divided that only by the unit effect of an average 20% cut at elasticity −1.49 (×1.39). GMV is
  units times price, so taking out the 20% lower price as well (×0.8) gives about ×3.1 (our arithmetic). We kept ×2.5,
  which makes not joining look better: at ×3.0, Margin Protected is ฿4,581.05 and the two Skips become Escalates
  ([evidence/sensitivity.md](../evidence/sensitivity.md)). No source measures the lift for 11.11, it moves every
  Verdict, and it is a labelled value in the sample shop file.
- **Three assumptions have no source:** when a Rival ends up cheaper, the Seller keeps (Rival price ÷ our price)^1.0
  of its buyers; each Counter-move lasts the whole Campaign, which overstates a short flash sale; and buyers value a
  gift at 30% of its retail price. Each is a labelled value in the sample shop file.
- **Fees:** Shopee does not publish the base of its PRIME programme fee, so we assume the commission base. The rates
  are the FMCG category's, for a Seller that is not VAT-registered. Every buyer is assumed to claim the shop voucher.
- **The explanation check proves numbers, not labels.** Each shown explanation sits next to the engine's own figures
  (see [Explanations](#explanations)).
- **Token Factory may see sample data only,** so real Seller costs need a private model endpoint (on the roadmap).

## Failures we have seen, and the safeguards

- **Token Factory is a free shared service with no uptime promise.** On 15 Oct Gemma had no workers for a while (the
  run switched to a fallback model and said so); from that night until about 20:48 ICT on 16 Oct its catalogue did not
  list Gemma at all (the app now falls back to DeepSeek-V4-Flash); and on 14 Oct the first calls hung for over two
  minutes. The recorded run is therefore the default demo, labelled as recorded.
- **On 17 Oct, Token Factory's chat calls hung from Vercel's Hong Kong region** (the explanation fell back to its
  numbers-only template), while the same calls from Thailand answered in seconds. Moving the API to Singapore fixed
  it: a live 4-product run then answered 20 of 20 calls with Gemma
  (`evidence/runs/token-factory-live-site-sin1-4sku.sse`).
- **The Evolus platform OCR failed** (HTTP 502), so the extractor reads a PDF's own text. A scanned invitation would
  fail until OCR works again.
- **A right number with the wrong label:** one Thai explanation said the plan was tested against 183 Promo Plans; the
  engine had searched 183 plans and tested the leader against the Counter-moves
  ([evidence/explainer-token-factory.md](../evidence/explainer-token-factory.md)). The review of the replay's texts
  found 5 more, fixed before serving ([Explanations](#explanations)).
- **Safeguards:** the Seller confirms before anything happens, and nothing is registered with the marketplace or sent;
  Escalate hands a genuine trade-off to a person; every number in an explanation is checked against the engine;
  invalid model output is rejected and counted, never repaired; `/api/explain` and `/api/confirm` accept only Verdicts
  this server signed; Token Factory only ever sees the sample shop.

## Evidence, in full

Every product and profit number in the README and on this page comes from the engine or from these files; the fee and
market figures come from the last two, with their sources.

| What | File |
|---|---|
| Elasticity fit and its holdout against a naive baseline | [evidence/elasticity.md](../evidence/elasticity.md) |
| Red-teaming turning SS-50's Approve into a Revise, live on Token Factory (with the labelled override) | [evidence/red-team-token-factory.md](../evidence/red-team-token-factory.md) |
| Thai and English explanations checked number by number | [evidence/explainer-token-factory.md](../evidence/explainer-token-factory.md) |
| Gemma's explanations of the 12 replayed Verdicts, the review that caught 5 wrong labels, and their speed | [evidence/explainer-replay-12sku.md](../evidence/explainer-replay-12sku.md) |
| Four pricing policies under the same Scenarios, and Gemma's own arithmetic checked by the engine | [evidence/policy-comparison.md](../evidence/policy-comparison.md) |
| The Evolus Verdict workflow carrying out confirmed Verdicts | [evidence/evolus-verdict-workflow.md](../evidence/evolus-verdict-workflow.md) |
| The Evolus extractor reading the Campaign Invitation PDF | [evidence/evolus-invitation-extractor.md](../evidence/evolus-invitation-extractor.md) |
| Every Evolus execution in the workspace, and two live runs from the live site on 17 Oct | [evidence/evolus-workspace-usage.md](../evidence/evolus-workspace-usage.md) |
| How the Verdicts move with traffic lift, the SS-50 override and the AI Rivals, with the no-AI controls | [evidence/sensitivity.md](../evidence/sensitivity.md) |
| Recorded Arena runs, as streamed | [evidence/runs/](../evidence/runs/) |
| Shopee and Lazada fees (sourced research) | [.scratch/marginarena/research/marketplace-fees.md](../.scratch/marginarena/research/marketplace-fees.md) |
| Thai Seller market estimates and existing tools (sourced research) | [.scratch/marginarena/research/thai-seller-market.md](../.scratch/marginarena/research/thai-seller-market.md) |

## Develop

Run from the repo root.

```bash
uv run --project backend pytest backend/tests -q        # engine and API tests (the model server is faked)
uv run --project backend pytest infra -q                # infra and Evolus kit tests
web/node_modules/.bin/tsc -b web && npm --prefix web run lint   # web type check and lint
uv run --project backend --env-file .env uvicorn --factory marginarena.api:create_app --port 8008
npm --prefix web install && npm --prefix web run dev    # http://localhost:5173, proxies /api to :8008
```

Record a new demo run (sample data only): `uv run --project backend --env-file .env python backend/scripts/record_arena.py`.

Rebuild evidence without a model:

```bash
uv run --project backend python backend/scripts/sensitivity.py              # engine only -> evidence/sensitivity.md
uv run --project backend python backend/scripts/compare_policies.py --report  # rebuilds the report from the saved JSON
```

## Repository

| Path | What |
|---|---|
| `backend/src/marginarena/engine/` | The pricing engine: pure functions, money in Decimal |
| `backend/src/marginarena/arena.py` | The Arena: Strategists, Rivals and re-selection, streamed as Server-Sent Events |
| `backend/src/marginarena/llm.py` | One OpenAI-compatible JSON client; invalid output is rejected and counted |
| `backend/src/marginarena/explainer.py` | Explanations in English or Thai, with the number check |
| `backend/src/marginarena/api.py` | The HTTP API: signed results, the recorded replay, the Evolus calls |
| `backend/src/marginarena/sample/` | The fictional sample shop, its invitation PDF and the recorded runs the app replays |
| `backend/scripts/` | Scripts that write the evidence (recorded runs, explanations, policy comparison, sensitivity) |
| `web/src/` | The web app: Invitation, Arena, Verdicts, Confirm |
| `infra/evolus/` | The Evolus kit and the knowledge library documents |
| `infra/droplet/` | An optional MI300X + vLLM setup kit; it was never run, and nothing in the README or the evidence used it |
| `evidence/` | Every measured number, with how to reproduce it |
| `Dockerfile`, `compose.yaml` | One container on :8008; the recorded replay needs no key |
| `docs/adr/` | Why the design is the way it is |
| `CONTEXT.md` | The glossary every name in the code follows |

## Roadmap, in full

1. A pilot with Thai Sellers before 12.12 (we are looking for Sellers; none is running yet), so elasticity, traffic
   lift and rival behaviour are measured on real sales.
2. Uploads of a Seller's own catalogue and invitation, and Rival Snapshot capture: read lookalike competitor listings
   from screenshots.
3. A private model endpoint, so real Seller costs never go to a shared API.
4. More Marketplace Profiles: Lazada (the LazMall fees already match Lazada's worked example), then TikTok Shop.
5. Shopee Mall Sellers and brands, then other Southeast Asian markets with the same Campaign mechanics.

Built solo from Thailand for the AMD Developer Hackathon ACT III (Reinvent Commerce; Evolus Business Agents).
MIT license: see [LICENSE](../LICENSE).
