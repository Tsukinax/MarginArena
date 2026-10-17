# 06 Create the Evolus event workspace and run the day-1 checks

Type: task
Status: claimed
Blocked by: none
Who: user (HITL)

## Question

Create the workspace through https://app.evolus.ai/join/AMDACT3, put the API key and Application ID in `.env`, then answer the day-1 checks in section 7 of [research/evolus-integration.md](../research/evolus-integration.md):

- Can we add our own MCP connector, and can we use sub-agents?
- How many agents and workflows can we create?
- Does the "Call an endpoint (API)" block exist?
- Which model does the workflow's "Process with AI" step use?
- Can the app key manage knowledge libraries?
- Can Token Factory be added as a model?
- What status code does Evolus return when rate-limited?

## Comments

- 14 Oct: the user created the event workspace and signed in. Claude read the in-workspace API reference (read-only) and wrote [docs/api-guide/evolus-api.md](../../../docs/api-guide/evolus-api.md). What it answers:
  - **The agent can call our engine** through Web APIs (`/webservices` plus `POST /agents/{id}/webapi/{webapiId}`). We don't need our own MCP connector, although MCP servers can also be attached.
  - **Everything can be provisioned through the API.** Agents, libraries, extractors, web services and workflows (steps or the whole graph) can all be created from code. Web services, extractors, memories and skills need a **User API Key** (`X-User-ApiKey`), not the application key.
  - **A new workflow starts off.** It must be created with `isActive:true`, otherwise execute answers `409`.
  - **Library uploads default to Italian.** Pass `language=en`.
  - **Step types are integers 0–20.** Read their names from `GET /workflows/step-catalog` at runtime.
- **Still needed from the user:**
  1. The application API key and Application ID in `.env`.
  2. A **User API Key** with the scopes for agents, memories, webservices, json structures and workflows, also in `.env`.
  3. Confirmation that our vLLM model is added under "Your models" (needs the droplet; ticket 08).
- 15 Oct: the Evolus kit is in [infra/evolus/](../../../infra/evolus/README.md): the knowledge-library documents and `evolus_kit.py plan`, which only reads. The user approved running `plan`; it has not been run yet. Creating resources (`apply`) will be written against what `plan` returns, and the user approves each run that writes.
- 15 Oct: `plan` ran (read-only; it now also saves the docs of the workflow steps `apply` uses, the own model
  connections and the AI Tools catalog). The workspace had no agents, workflows, web services or own models. The user
  approved one run of `apply` for the knowledge library: "MarginArena Campaign Desk library" now holds both
  `library/` documents, uploaded with `language=en` (Evolus keeps the file name as the title); its ID is
  `EVOLUS_LIBRARY_ID` in `.env`. Decided with the user: until the droplet exists, the agent uses Token Factory's Gemma
  under "Your models" (alias `tf-gemma`, added by the user); after the GPU session the MI300X model becomes the main
  model and Token Factory its labelled fallback. The Verdict workflow drafts the approval request with the `email` AI
  Tool and sends nothing.
- 15 Oct, later: the user connected "tf-gemma on AMD" under "Your models" (Gemma-4-31B-IT and Qwen3.8-27B on Token
  Factory; Gemma had no workers at the time, so its test failed and Qwen's passed). `apply --model own/Gemma-4-31B-IT
  --fallback own/Qwen3.8-27B` built the Campaign Desk agent and the Verdict workflow (the API wants step types as the
  catalog's numbers). The Confirm step runs it; one run is in `evidence/evolus-verdict-workflow.md` (10.55 s, 0.0
  credits). The extractor is next.
- 15 Oct, evening: `apply` also built the Campaign Invitation extractor ("MarginArena Invitation Reader", output
  structure "Campaign Invitation"; IDs `EVOLUS_READER_ID` and `EVOLUS_INVITATION_STRUCTURE_ID`). The platform OCR
  failed (502 from `generic-ocr`), so OCR is off and the extractor reads the sample PDF's own text: 12 of 12 minimum
  discounts read correctly (`evidence/evolus-invitation-extractor.md`). The app's Invitation step runs it
  (`POST /api/invitation/read`). The live site answered 503 ("missing") until the deployment of `bceccf2`; then it
  read 12 of 12 in 147.85 s (run 3 in the evidence). Open from the day-1 list: the status code Evolus returns when
  rate-limited.
