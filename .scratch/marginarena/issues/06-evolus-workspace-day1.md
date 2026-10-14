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
