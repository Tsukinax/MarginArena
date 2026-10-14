# The Evolus kit: set up the event workspace from code

MarginArena drives Evolus through its REST API (Evolus Business Agents track). This folder holds what the workspace
needs and the script that sets it up, so the setup is reproducible rather than clicked together.

- `library/`: the documents for the Campaign Desk agent's knowledge library. They cover Shopee Thailand's fees and
  Campaign rules (with sources) and the fictional HydraLab reseller agreement behind the sample shop's Brand Price
  Rule. They are uploaded with `language=en`, because Evolus defaults to Italian.
- `evolus_kit.py plan`: **read-only.** It lists the agents, knowledge libraries, workflows and web services already in
  the workspace, the workflow step catalog, and the scopes of the User API Key. It saves the raw answers to
  `.plan/latest.json` (gitignored) and changes nothing.

- `evolus_kit.py apply`: **writes, so the user approves each run.** It finds each resource by name before creating
  it, so a rerun creates nothing new, and it saves the IDs to `.env`. So far it creates the knowledge library
  ("MarginArena Campaign Desk library", `EVOLUS_LIBRARY_ID`) and uploads every document in `library/` with the User
  API Key. First run: 15 Oct 2026.

```bash
uv run --project backend --env-file .env python infra/evolus/evolus_kit.py plan
uv run --project backend --env-file .env python infra/evolus/evolus_kit.py apply
uv run --project backend pytest infra/evolus -q   # plan only reads; apply creates once; neither prints a key
```

Next in `apply`: the Campaign Desk agent (on our own vLLM model, `own/<alias>` from "Your models", with Token
Factory as its labelled fallback), the Campaign Invitation extractor and the Verdict workflow (created with
`isActive: true`; it drafts the approval request for escalated SKUs with the `email` AI Tool and sends nothing).

API facts and quirks: `docs/api-guide/evolus-api.md`. Why the Arena bypasses Evolus: `docs/adr/0003`.
