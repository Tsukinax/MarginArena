# MarginArena

**Check a marketplace Campaign Invitation before you join it.** A deterministic pricing engine costs every Promo Plan
for every invited product, AI Rivals red-team the leading plan, and each product ends in a Verdict: Approve, Revise
(including Skip) or Escalate.

Built for the AMD Developer Hackathon ACT III (Reinvent Commerce; Evolus Business Agents). Every AI call runs on
Gemma-4-31B-IT through AMD Token Factory.

## The problem

A Thai Shopee Seller gets a Campaign Invitation inside Seller Centre: join 11.11 if you cut these products by 15–25%.
Joining is opt-in, and the Seller has to decide product by product whether it makes money.

- A Shopee Thailand Non-Mall PRIME Seller pays 27.82% of the price after its own discounts, plus ฿1.07 per order
  (fees effective 4 Aug 2026).
- At those fees, a ฿100 product that costs ฿50 earns ฿21.11 at full price, ฿6.67 at 20% off, and loses ฿0.55 at 30% off.
- Nobody knows in advance how many more units a discount sells, or what lookalike competitors will do in reply.

## Try it

- **Live demo:** coming with the submission.
- **On your machine:** `cp .env.example .env`, then `docker compose up --build` and open http://localhost:8008.
  - **Watch all 12 products (recorded run)** replays a real Arena recorded on AMD Token Factory. It needs no key.
  - **Run live** needs `TOKEN_FACTORY_API_KEY` in `.env`. It checks 4 of the 12 products, chosen to show every kind of
    Verdict, because Token Factory allows 20 requests a minute per account. The sample shop is the only data it sends.

## How it decides

1. **The engine computes every number** ([ADR 0001](docs/adr/0001-numbers-come-only-from-the-engine.md)):
   - marketplace fees, checked against the marketplaces' own worked examples (Lazada's pays out ฿623.93, Shopee's
     ฿200.31: `backend/tests/engine/test_fees.py`);
   - demand from a price elasticity fitted on public e-commerce data, with an uncertainty band;
   - each Promo Plan's Campaign profit in every Scenario: each Counter-move at the point elasticity and at both edges
     of the band.
2. **AI explores what is open-ended; math solves what is closed** ([ADR 0004](docs/adr/0004-ai-explores-open-ended-math-solves-closed.md)):
   - Strategists (Gemma) propose Plan Ideas, such as a voucher or a gift from the catalogue;
   - the engine searches every numeric Promo Plan those ideas allow, within the invitation and the Brand Price Rules;
   - each round, Rivals (Gemma) propose Counter-moves against the leading plan, and the engine re-selects over every
     Scenario found so far.
3. **The plan with the best worst case wins** (maximin), provided it keeps the Seller's Margin Floor, earns at least
   as much as not joining, and respects every Brand Price Rule.
4. **Every Verdict explains itself**: a waterfall, the Counter-moves it was tested against, Evidence Links, and a short
   explanation in English or Thai. An explanation citing any number the engine did not produce is rejected, and
   `/api/explain` only accepts results the server signed.

## Evidence

Every number in this README comes from the engine or from these files:

| What | File |
|---|---|
| Elasticity fit and its holdout against a naive baseline | [evidence/elasticity.md](evidence/elasticity.md) |
| An AI Rival turning SS-50's Approve into a Revise, live on Token Factory | [evidence/red-team-token-factory.md](evidence/red-team-token-factory.md) |
| Thai and English explanations checked number by number | [evidence/explainer-token-factory.md](evidence/explainer-token-factory.md) |
| Recorded Arena runs, as streamed | [evidence/runs/](evidence/runs/) |

## AMD

- Gemma-4-31B-IT on **AMD Token Factory** serves every Strategist, Rival and explanation call. The organisers confirmed
  that Token Factory counts as the AMD component for ACT III ([ADR 0005](docs/adr/0005-token-factory-is-the-only-inference-route.md)).
- The app shows the route and model on every run, with live telemetry: calls, invalid outputs, retries, tokens per
  second.
- `infra/droplet/` can serve the same model on an AMD Developer Cloud MI300X with vLLM. It is optional and was not used
  for the submission.

## Evolus

`infra/evolus/evolus_kit.py` sets up the Evolus workspace from code: `plan` only reads, and `apply` creates what is
missing, finding each resource by name first. So far it creates the Campaign Desk knowledge library (fees and the
sample brand agreement). See [infra/evolus/README.md](infra/evolus/README.md).

## Assumptions and limits

- **The sample shop is fictional.** Glow Lab BKK's costs, stock, baselines, brand agreement and Rival Snapshot are
  invented; the fees are Shopee Thailand's.
- **Elasticity comes from online grocery data** (FreshRetailNet-50K by Dingdong Ltd., CC BY 4.0, from Chinese cities;
  the repo holds only the fitted parameters), not marketplace skincare. SS-50 carries a
  labelled Seller override: the published mean elasticity, −2.62 (Bijmolt, Van Heerde and Pieters 2005), with a band of
  our own construction.
- **Two assumptions have no source:** when a Rival ends up cheaper, the Seller keeps (Rival price ÷ our price)^1.0 of
  its buyers, and each Counter-move lasts the whole Campaign, which overstates a short flash sale.
- **A gift is valued at 30% of its retail price** by buyers. This is an assumption the Seller can change.
- **The explanation check proves numbers, not labels.** Each shown explanation sits next to the engine's own figures.

## Develop

```bash
uv run --project backend pytest backend/tests -q        # engine and API tests (the model server is faked)
uv run --project backend --env-file .env uvicorn --factory marginarena.api:create_app --port 8008
npm --prefix web install && npm --prefix web run dev    # http://localhost:5173, proxies /api to :8008
```

Record a new demo run (sample data only): `uv run --project backend --env-file .env python backend/scripts/record_arena.py`.

## Repository

| Path | What |
|---|---|
| `backend/src/marginarena/engine/` | The pricing engine: pure functions, money in Decimal |
| `backend/src/marginarena/arena.py` | The Arena: Strategists, Rivals and re-selection, streamed as Server-Sent Events |
| `backend/src/marginarena/explainer.py` | Explanations in English or Thai, with the number check |
| `web/src/` | The web app: Invitation, Arena, Verdicts, Confirm |
| `docs/adr/` | Why the design is the way it is |
| `CONTEXT.md` | The glossary every name in the code follows |

## License

MIT. See [LICENSE](LICENSE).
