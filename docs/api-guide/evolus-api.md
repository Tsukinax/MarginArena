# Evolus Integration API: notes for MarginArena

Source: the in-workspace API reference at https://app.evolus.ai/company/api-docs (OpenAPI 3.0.4, "Evolus Integration API" v1). It has 179 operations in 22 tags. Read on 14 Oct 2026 while signed in to the event workspace. The full reference is visible only inside the workspace. Public overview: https://evolus.ai/en/developers.

No keys or workspace IDs are recorded here. They live in `.env`.

## Authentication

| Surface | Base URL | Headers |
|---|---|---|
| REST | `https://api.evolus.ai/api/v1` | `X-ApiKey` + `X-Application-Id` (application key), or `X-User-ApiKey` + `X-Application-Id` (personal User API Key) |
| OpenAI-compatible agent chat | `https://api.evolus.ai/v1` | `Authorization: Bearer <application API key>`, with `model = <applicationId>:<agentId>` |
| MCP | `https://api.evolus.ai/mcp` | same as REST |

**Important:** creating web services, JSON output structures, knowledge memories and skills requires a **personal User API Key** (`X-User-ApiKey`). The application key is refused. Our setup script therefore needs a User API Key with the right scopes (`GET /api/v1/user/api-keys/scopes` lists them).

## The whole setup can be provisioned in code

Every building block can be created through the API. A setup script can therefore build the workspace from scratch, which gives us a "README that runs":

1. **Agent:** `POST /api/v1/agents` with
   - `name`, `prompt`, `language`;
   - `modelKey`: the BYO model is `own/<alias>`, the alias set under "Your models";
   - `fallbackModelKeys`, `isExtractor`, `scriptToolEnabled`, `fileToolsEnabled`.
   
   Update it with `PUT /api/v1/agents/{agentId}` (partial update: an omitted field keeps its value, `null` clears it).
2. **Knowledge library:** `POST /api/v1/memories/simple` with `{name, type}`, where `type` 0 = Rag (semantic search) and 1 = Blob (markdown read whole). Then:
   - upload documents with `POST /api/v1/memories/{memoryId}/documents` (multipart `file`, query `language=en`; the default is Italian), or with `.../documents/import-url`;
   - attach the library to an agent with `POST /api/v1/agents/{agentId}/memories` and body `{memoryId}`.
3. **Extractor (JSON output structure):**
   - Create it with `POST /api/v1/agents/{agentId}/json`. Body fields: `title`, `userPrompt`, `structure` (the schema), `canUseOCR`, `pages`, `checkScript`, `maxCorrections`, `webhookId`.
   - Extract with `POST /api/v1/agents/{agentId}/json/{outputStructureId}/ask-file` (multipart `file`).
     - Query options: `ocrEngine`, `pageDefinitions`, `useWebhook`.
     - It is synchronous unless a webhook is configured.
     - It returns the headers `X-AskFile-Execution-Id` and `X-AskFile-Audit-Id`.
   - Batch version: `.../ask-files`.
4. **Our engine as a tool the agent can call (Web API):**
   - Create the service with `POST /api/v1/webservices` and body `{name}`.
   - Add an API definition with `POST /api/v1/webservices/{id}/apis`. Body: `{name, description, requestUrl, method:{method}, headers:[{key,value}], parameters:[{name, type, location, required, description, defaultValue}]}`.
   - Attach it to an agent with `POST /api/v1/agents/{agentId}/webapi/{webapiId}`. The agent can then call MarginArena's HTTP endpoints during a conversation.
   - Test it with `POST /api/v1/webservices/{id}/apis/{apiId}/invoke` and body `{parameters:[{name,value}]}`.
5. **MCP servers can also be attached to an agent:** `POST /api/v1/agents/{agentId}/mcpserver/{mcpServerId}`. The server must belong to an MCP collection of the application, and the plan may limit this.
6. **Workflow:**
   - Create it with `POST /api/v1/workflows`. Body: `name`, `description`, `tags`, `parameters:[{name,type,required,allowedValues,defaultValue,description}]`, `isActive`, `enableAuditKpi`.
     - **A new workflow is off by default.** Send `isActive:true`, or `execute` will answer `409`.
   - Add steps with `POST /api/v1/workflows/{id}/steps`. Fields:
     - `stepType`: an integer 0–20. Names and docs come from `GET /api/v1/workflows/step-catalog` and `.../step-catalog/{key}?part=n`.
     - `agentId`, `outputStructureId`, `webhookId`, `prompt`, `inputTemplate`, `inputStepIds`, `inputBranches`;
     - the `email*` fields;
     - `stepConfigJson` for things like `modelKey`.
   - Or save the whole graph atomically with `PUT /api/v1/workflows/{id}/graph`.
   - Run it with `POST /api/v1/workflows/{id}/execute` (multipart: `input`, `file`, `parameters`, `callbackUrl`, ...). It answers `202`; then `GET /api/v1/workflows/{id}/executions/{executionId}` returns `status`, `output`, `stepOutputs`, `stepStates` and `parameters`.
7. **Webhook:** `POST /api/v1/webhooks` with `{name, url, apiKeyName, apiKeyValue, contentType}`. Output structures and workflow steps can reference it.
8. **Workflow audits (quality KPIs):** `/api/v1/workflow-audits` and `.../statistics` record each run's result. Corrected data can be compared against it with `.../{auditId}/compare`. These give extra visible depth of Evolus use.

## Agent calls

- `POST /api/v1/agents/{agentId}/ask` with body `{content, conversationId?, fileId?, outputStructureId?, skipChatHistory?}`. It returns `{answer, citations[], conversationId, title}`. `totalTokenCount` is null for non-staff callers. Streaming version: `.../ask-stream`.
- `POST /v1/chat/completions` (OpenAI format). It accepts `temperature` and the other usual fields, but the public page says model settings come from the agent. `X-Conversation-Id` continues a conversation.

## Errors

Every error is `EvolusProblemDetails {title, status, detail, errorCode, traceId, params, errors}`. Codes used:

| Code | Meaning |
|---|---|
| 402 | Out of credits |
| 403 | Forbidden |
| 404 | Not found, including an ID that belongs to another application |
| 409 | Workflow is off |
| 413 | File too large |
| 422 | Validation failed |
| 429 | Rate limited; the OpenAI-compatible endpoint returns this |

## Limits (event workspace)

- 60 requests/min per workspace.
- 50,000 credits until 15 Nov 2026, 23:59 Italian time. Credits are spent on document reading, AI Tools and library indexing.
- Calls to our own model are free.

## What this means for MarginArena

- **Evolus can call our engine.** A Web API definition attached to the Campaign Desk agent does this, so we don't depend on custom MCP. This settles ticket 06's open question.
- **The setup is reproducible:** `scripts/evolus_setup.py` creates the library, extractor, agent, web API and workflow from code. It needs a **User API Key** in `.env`.
- **The workflow must be created with `isActive: true`**, or execute calls fail with `409`.
- **Upload library documents with `language=en`**, because the default is Italian.
- **Look up step types at runtime** from `step-catalog`; don't hard-code the integers.
