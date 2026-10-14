# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

MarginArena checks a marketplace Campaign Invitation SKU by SKU before a Thai Shopee Seller commits: a deterministic engine prices every Promo Plan, AI Rivals red-team the leading plan, and each SKU ends in a Verdict. It is our entry to the AMD Developer Hackathon ACT III (tracks: Reinvent Commerce and Evolus Business Agents; binding deadline Sun 18 Oct 2026, 17:00 ICT). Claude writes all the code; the user submits on lablab.ai, records the video and does anything that needs their accounts. Talk to the user in Thai; keep code, file names and glossary terms in English.

The glossary below is binding: use its terms exactly in code, UI copy and docs.

@CONTEXT.md

## Commands

Run everything from the repo root. The shell keeps `cd` between tool calls, so these forms avoid it.

```bash
uv run --project backend pytest backend/tests -q                  # engine + API tests
uv run --project backend pytest backend/tests/engine/test_verdict.py::test_skip_when_not_joining_beats_every_plan_in_the_worst_case -q
uv run --project backend pytest infra/droplet -q                  # droplet kit tests
uv run --project backend ruff check backend && uv run --project backend ruff format --check backend
web/node_modules/.bin/tsc -b web && npm --prefix web run lint      # web type check + oxlint
```

Dev servers: `preview_start` with `api` (FastAPI on :8008, reads `.env`) and `web` (Vite on :5173, proxies `/api` to :8008), both defined in `.claude/launch.json`.

## Architecture

LLMs propose and explain; the engine computes every number (ADR 0001). AI explores what is open-ended, math solves what is closed (ADR 0004).

- `backend/src/marginarena/engine/`: pure functions over frozen dataclasses, money as `Decimal` rounded to the satang, no I/O. The pipeline is `fees.unit_economics` → `demand.campaign_outcome` → `verdict.evaluate_sku` → `verdict.evaluate_invitation`.
  - Fees: each fee is computed excluding VAT and rounded, then VAT is added. That order is what reproduces both marketplaces' published worked examples.
  - Demand: baseline × traffic lift × (buyer price / list price)^elasticity × share retained against a cheaper Rival, floored and capped at stock. The price ratio is capped at 1, so elasticity applies to price cuts only.
  - Verdict: Scenarios are every Counter-move × {point elasticity, both band edges}. Maximin picks among eligible plans; Skip is a Revise; Margin Protected leaves out Escalate. Full rules: spec.md, "Robust selection" and "Verdict".
  - `search.candidate_plans` expands non-numeric Plan Ideas into every numeric Promo Plan, clipped by Brand Price Rules.
- `arena.py`: per SKU, Strategists return Plan Ideas → the engine searches → three generic Counter-moves set the first leader → each round Rivals red-team the leader and the engine re-selects over every Scenario found; it stops once the leader holds. It streams SSE events and returns results as dicts of decimal strings, including the proof-6 `red_team_gain`.
- `llm.py`: one OpenAI-compatible JSON client for both inference routes (ADR 0002). Output is schema-validated plus an `accept` check; invalid output is rejected and counted, never repaired. The route is the first healthy of `mi300x` (only when `VLLM_BASE_URL` is set) then `token-factory`.
- `explainer.py` (`POST /api/explain`): turns one decided SKU into a fact sheet, asks the model for a short explanation in English or Thai, and rejects any draft citing a number that is not in the fact sheet (`unsupported_numbers`; rounding is allowed). One rewrite, then a numbers-only template. The check proves numbers, not which label they sit next to.
- `api.py`: `create_app` takes `llm_settings`, `routes`, `llm_transport` and `sleep`, which is how tests inject a fake model server. Runs on Token Factory are capped and default to the demo trio NT-200, VC-30, SM-10 (Q55).
- `sample/`: the fictional Glow Lab BKK shop (12 skincare SKUs, HydraLab clause 4.2), with elasticity from `engine/data/elasticity.json`.
- `web/src/`: React 19 + Vite, four steps (Invitation, Arena, Verdicts, Confirm) and the "How we decided" drawer. `api.ts` mirrors the backend's event and result shapes, so change both together. The UI formats money strings and leaves every calculation to the engine.
- `infra/droplet/`: a stdlib-only kit (`kit.py`, `gate.py`, `bootstrap.sh`) that sets up Gemma-4-31B-IT on vLLM behind Caddy on the MI300X. Runbook: `infra/droplet/README.md`.
- `evidence/`: the only home of measured numbers (elasticity holdout, recorded Arena runs, the tool-calling gate).

## Tests

New code is test-first, at three seams only (spec.md, "Testing Decisions"):

1. Engine public functions, with realistic inputs and the expected numbers worked by hand in a comment (`backend/tests/engine/test_verdict.py` is the reference style).
2. The HTTP API, running the real client, Arena and engine against a model server faked at the network edge (`FakeModelServer` with `httpx.MockTransport` and `sleep=no_sleep` in `backend/tests/api/test_arena_api.py`).
3. The explainer's number check, `unsupported_numbers` (`backend/tests/explainer/`).

Live checks against a real model or Evolus are scripts that write to `evidence/`, not unit tests (for example `backend/scripts/check_explainer.py`).

## Rules that protect the submission

- Every number a Seller, judge, README, slide or video sees comes from the engine or from a file in `evidence/`. Anything else is measured first or labelled as an assumption.
- Ask the user first before creating any cloud resource, running `scripts/evolus_setup.py` (it creates resources in their Evolus workspace), `git push` or creating the GitHub repo, and before sending or publishing anything.
- Token Factory receives sample data only; its terms forbid sensitive financial data.
- The MI300X droplet bills $2.59 an hour until it is destroyed, even powered off. The user creates and destroys it; afterwards run `python3 infra/droplet/kit.py forget`.
- Refer to `.env` entries by variable name only.
- Commit in small steps on `main`, subject line "Area: what changed" (`Engine:`, `Arena:`, `API:`, `Droplet:`). There is no remote yet.

## Gotchas

- Token Factory is paced at 15 requests/min (the account limit is 20) with 8 in flight, and it has been flaky; a labelled recorded run is the fallback.
- vLLM serves the model as `google/gemma-4-31B-it`, and Evolus "Your models" uses that same name.
- Evolus: create workflows with `isActive: true` (otherwise execute returns 409), upload library documents with `language=en` (the default is Italian), and use `EVOLUS_USER_API_KEY` for web services, extractors, memories and skills. The limit is 60 requests/min.
- Write Python files with the Write tool; a shell heredoc once left a literal `\n` in a file.
- `backend/pyproject.toml` holds the project's ruff rules; files outside `backend/` fall back to a stricter global config.

## Where to look

- Product scope, user stories, priorities, schedule: `.scratch/marginarena/spec.md`
- Why a design is the way it is: `docs/adr/`; every grilled decision, numbered Q1–Q55 (continue at Q56): `.scratch/marginarena/issues/01-charting-grill.md`
- Open tickets and tracker conventions: `.scratch/marginarena/issues/`, `docs/agents/issue-tracker.md`
- Token Factory and Evolus API facts and limits: `docs/api-guide/`
- Fees, elasticity, model serving, competitors, market numbers: `.scratch/marginarena/research/`
- Competition rules and judging: `docs/reports/` and `docs/research_notes/`
