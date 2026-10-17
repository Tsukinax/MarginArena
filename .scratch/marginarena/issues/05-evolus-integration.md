# 05 What can Evolus do for MarginArena, and how do we connect our model?

Type: research
Status: resolved
Blocked by: none

## Question

How do we connect our own OpenAI-compatible vLLM endpoint as the model in an Evolus event workspace? For each building block (workflows, document extractors, AI Tools, knowledge libraries, MCP connectors, sub-agents, chat widget), what does it do, and which REST or OpenAI-compatible API drives it? Can an Evolus agent or workflow call our own engine over HTTP, MCP or an AI Tool? What are the limits (credits, requests per minute), and what do Evolus staff check when they judge a workspace?

Findings: `.scratch/marginarena/research/evolus-integration.md` (kept locally, not in git: it names other teams' repos)

## Answer

Full findings: `research/evolus-integration.md` (kept locally, not in git)

- **Connecting our model:**
  - Start vLLM on our droplet with `--api-key --enable-auto-tool-choice --tool-call-parser <parser>`.
  - In the workspace, under **Your models**, enter the base URL, model name and key, then press Test and bind each agent to that model.
  - Calls to our own model use no Evolus credits. Port 8000 must be reachable from the internet and protected by the key.
- **APIs:**
  - REST at `https://api.evolus.ai/api/v1` (headers `X-ApiKey`, `X-Application-Id`)
  - OpenAI-compatible agent chat at `https://api.evolus.ai/v1` (`model=<appId>:<agentId>`)
  - MCP at `https://api.evolus.ai/mcp`
- **How Evolus calls us:** a workflow's "Call an endpoint (API)" block, or a webhook/`callbackUrl`, or chat-widget functions. Our own MCP connector may need the Business plan and is unconfirmed for event workspaces.
- **Limits:** 60 requests per minute per workspace; 50k credits, spent only on document reading, AI Tools and library indexing; at most 6 members. The workspace expires 31 Oct per lablab or 15 Nov per Evolus.
- **What Evolus staff check:** the connected model endpoint, the building blocks used, and the number of API calls. Judges score how deeply Evolus is used and how well the AMD model is integrated.
- **Recommended pattern:** our app runs the Arena and computes every number; an Evolus workflow carries out the Verdict; a knowledge library holds the fee and Campaign rules. Optional: an extractor for the Campaign invitation, the email AI Tool, and the widget.
- **Open:**
  - Run the day-1 checks in section 7 of the findings file. The user must do these inside the workspace.
  - The 60 rpm limit conflicts with running every Arena call through Evolus agent chat. Decide which calls go through Evolus and which go straight to vLLM.
