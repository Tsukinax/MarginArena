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
uv run --project backend pytest infra -q                          # droplet and Evolus kit tests
uv run --project backend ruff check backend && uv run --project backend ruff format --check backend
web/node_modules/.bin/tsc -b web && npm --prefix web run lint      # web type check + oxlint
docker compose up --build                                         # one container on :8008; the recorded replay needs no key
```

Dev servers: `preview_start` with `api` (FastAPI on :8008, reads `.env`) and `web` (Vite on :5173, proxies `/api` to :8008), both defined in `.claude/launch.json`.

## Architecture

LLMs propose and explain; the engine computes every number (ADR 0001). AI explores what is open-ended, math solves what is closed (ADR 0004).

- `backend/src/marginarena/engine/`: pure functions over frozen dataclasses, money as `Decimal` rounded to the satang, no I/O. The pipeline is `fees.unit_economics` → `demand.campaign_outcome` → `verdict.evaluate_sku` → `verdict.evaluate_invitation`.
  - Fees: each fee is computed excluding VAT and rounded, then VAT is added. That order reproduces Lazada's published worked example and our hand-worked Shopee example (Shopee publishes none).
  - Demand: baseline × traffic lift × (buyer price / list price)^elasticity × share retained against a cheaper Rival, floored and capped at stock. The price ratio is capped at 1, so elasticity applies to price cuts only.
  - Verdict: Scenarios are every Counter-move × {point elasticity, both band edges}. Maximin picks among eligible plans; Skip is a Revise; Margin Protected leaves out Escalate. Full rules: spec.md, "Robust selection" and "Verdict".
  - `search.candidate_plans` expands non-numeric Plan Ideas into every numeric Promo Plan, clipped by Brand Price Rules.
- `arena.py`: per SKU, Strategists return Plan Ideas → the engine searches → three generic Counter-moves set the first leader → each round Rivals red-team the leader and the engine re-selects over every Scenario found; it stops once the leader holds. It streams SSE events and returns results as dicts of decimal strings, including proof 6: `red_team_cut` (how far the moves the Rivals found lower the first plan's worst case) and `red_team_gain` (how much the final plan beats it).
- `llm.py`: one OpenAI-compatible JSON client for both inference routes (ADR 0002). Output is schema-validated plus an `accept` check; invalid output is rejected and counted, never repaired. The route is the first healthy of `mi300x` (only when `VLLM_BASE_URL` is set) then `token-factory`; the submission runs on `token-factory` only (ADR 0005). When Token Factory says Gemma has no workers, the rest of the run uses `fallback_model` (Qwen3.8-27B, Q58) and the telemetry reports the answering `model`.
- `explainer.py` (`POST /api/explain`): turns one decided SKU into a fact sheet, asks the model for a short explanation in English or Thai, and rejects any draft citing a number that is not in the fact sheet (`unsupported_numbers`; rounding is allowed). One rewrite, then a numbers-only template. The check proves numbers, not which label they sit next to.
- `api.py`: `create_app` takes `llm_settings`, `routes`, `llm_transport`, `sleep` and `web_dist`, which is how tests inject a fake model server. It signs every decided SKU (HMAC, `RESULT_SIGNING_KEY`) and `/api/explain` refuses unsigned or changed results; `{"recorded": true}` replays `evidence/runs/token-factory-sample-12sku.sse` instead of calling the model; with `WEB_DIST` it also serves the built web app. `/api/invitation/read` has the Evolus extractor read the sample invitation PDF (only that file is ever sent) and `/api/confirm` runs the Evolus Verdict workflow; both need the `EVOLUS_*` IDs that `evolus_kit.py apply` writes to `.env`. Runs on Token Factory are capped and default to NT-200, SS-50, VC-30, SM-10 (Q55, Q56).
- `sample/`: the fictional Glow Lab BKK shop (12 skincare SKUs, HydraLab clause 4.2), with elasticity from `engine/data/elasticity.json`, except SS-50's labelled Seller override (Q56). It also ships the sample invitation PDF (`backend/scripts/make_sample_invitation.py`) and the replayed run in `recorded/` (a test keeps it identical to the copy in `evidence/runs/`).
- `web/src/`: React 19 + Vite, four steps (Invitation with the Evolus reading of the PDF, Arena with the recorded or live run, Verdicts, Confirm running the Evolus workflow) and the "How we decided" drawer. `api.ts` mirrors the backend's event and result shapes, so change both together. The UI formats money strings and leaves every calculation to the engine.
- `infra/droplet/`: a stdlib-only kit (`kit.py`, `gate.py`, `bootstrap.sh`) that sets up Gemma-4-31B-IT on vLLM behind Caddy on the MI300X. Optional since ADR 0005 and never run, so it is never cited as evidence. Runbook: `infra/droplet/README.md`.
- `infra/evolus/`: the Evolus kit (`evolus_kit.py`: `plan` only reads; `apply --model own/Gemma-4-31B-IT --fallback own/Qwen3.8-27B` builds the library, the Campaign Desk agent, the Verdict workflow and the invitation extractor, each found by name first) and the library documents in `library/`. Its README says what is built.
- `evidence/`: the only home of measured numbers: the elasticity holdout, the explainer's number check, the red-team run, the policy comparison (proof 3), the Evolus workflow and extractor runs, and the recorded Arena streams in `runs/`.

## Tests

New code is test-first, at three seams only (spec.md, "Testing Decisions"):

1. Engine public functions, with realistic inputs and the expected numbers worked by hand in a comment (`backend/tests/engine/test_verdict.py` is the reference style).
2. The HTTP API, running the real client, Arena and engine against a model server faked at the network edge (`FakeModelServer` with `httpx.MockTransport` and `sleep=no_sleep` in `backend/tests/api/test_arena_api.py`).
3. The explainer's number check, `unsupported_numbers` (`backend/tests/explainer/`).

Live checks against a real model or Evolus are scripts that write to `evidence/`, not unit tests: `backend/scripts/check_explainer.py`, `record_arena.py` (the replayed 12-SKU run) and `compare_policies.py` (proof 3; `--report` rebuilds the report without calling the model).

## Rules that protect the submission

- Every number a Seller, judge, README, slide or video sees comes from the engine or from a file in `evidence/`. Anything else is measured first or labelled as an assumption.
- Ask the user first before creating any cloud resource, running `infra/evolus/evolus_kit.py apply` or anything else that writes to their Evolus workspace, making the repo public, and before sending or publishing anything. Pushing commits to `main` is approved (15 Oct); it redeploys the live site.
- Token Factory receives sample data only; its terms forbid sensitive financial data.
- The MI300X droplet bills $2.59 an hour until it is destroyed, even powered off. The user creates and destroys it; afterwards run `python3 infra/droplet/kit.py forget`.
- Refer to `.env` entries by variable name only.
- Commit in small steps on `main`, subject line "Area: what changed" (`Engine:`, `Arena:`, `API:`, `Droplet:`). The remote is the private repo `Tsukinax/MarginArena`; every push to `main` redeploys https://marginarena.vercel.app (Vercel project `marginarena`, `vercel.json` services). Its secrets and IDs (`TOKEN_FACTORY_API_KEY`, `RESULT_SIGNING_KEY`, the `EVOLUS_*` names) are set by the user in the Vercel dashboard, and a change takes effect only after a new deployment. The repo goes public at submission.

## Gotchas

- Token Factory is paced at 15 requests/min (the account limit is 20) with 8 in flight, and it has been flaky; a labelled recorded run is the fallback. On 14 Oct its first calls hung for over 2 minutes: the client waits 120 s per try and makes up to 4 tries, so the Arena page looks frozen meanwhile. `/v1/usage` reports the limits; the daily quota resets at 16:00 UTC (midnight in Shanghai).
- `uvicorn` runs without reload: restart the `api` preview after any backend change. If ports 8008 or 5173 are taken by another session's stale servers, stop those first.
- Token Factory names the model `Gemma-4-31B-IT`; our own vLLM would serve it as `google/gemma-4-31B-it`. Evolus "Your models" takes the name the endpoint uses.
- Evolus: create workflows with `isActive: true` (otherwise execute returns 409), upload library documents with `language=en` (the default is Italian), and use `EVOLUS_USER_API_KEY` for web services, extractors, memories, skills and `/own-models/connections`. Step types go in as the step catalog's numbers, not names. In this workspace every AI block runs only on "Your models" (connection "tf-gemma on AMD"). The platform OCR failed with 502 on 15 Oct, so the extractor reads a PDF's own text with OCR off. The MCP endpoint `https://api.evolus.ai/mcp` (`tools/list`) documents every request body. The limit is 60 requests/min.
- Token Factory's Gemma-4-31B-IT is marked experimental and returned 500 "no_available_workers" for a while on 15 Oct; Qwen3.8-27B kept answering (it needs `reasoning_effort: low`).
- Vercel: functions run in `hkg1`, nearer Token Factory (a live 4-SKU run took 140.65 s from iad1, 112.10 s from hkg1). Deployment URLs ending in `-tsukinax-s-projects.vercel.app` sit behind Vercel Authentication; https://marginarena.vercel.app is public.
- Write Python files with the Write tool; a shell heredoc once left a literal `\n` in a file.
- `backend/pyproject.toml` holds the project's ruff rules; files outside `backend/` fall back to a stricter global config.

## Where to look

- Product scope, user stories, priorities, schedule: `.scratch/marginarena/spec.md`
- Why a design is the way it is: `docs/adr/`; every grilled decision, numbered Q1–Q58 (continue at Q59): `.scratch/marginarena/issues/01-charting-grill.md`
- Open tickets and tracker conventions: `.scratch/marginarena/issues/`, `docs/agents/issue-tracker.md`
- Token Factory and Evolus API facts and limits: `docs/api-guide/`
- Fees, elasticity, model serving, competitors, market numbers: `.scratch/marginarena/research/`
- Competition rules and judging: `docs/reports/` and `docs/research_notes/`
