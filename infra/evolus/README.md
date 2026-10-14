# The Evolus kit: set up the event workspace from code

MarginArena drives Evolus through its REST API (Evolus Business Agents track). This folder holds what the workspace
needs and the script that sets it up, so the setup is reproducible rather than clicked together.

- `library/`: the documents for the Campaign Desk agent's knowledge library. They cover Shopee Thailand's fees and
  Campaign rules (with sources) and the fictional HydraLab reseller agreement behind the sample shop's Brand Price
  Rule. They are uploaded with `language=en`, because Evolus defaults to Italian.
- `evolus_kit.py plan`: **read-only.** It lists the agents, knowledge libraries, workflows and web services already in
  the workspace, the workflow step catalog, and the scopes of the User API Key. It saves the raw answers to
  `.plan/latest.json` (gitignored) and changes nothing.

```bash
uv run --project backend --env-file .env python infra/evolus/evolus_kit.py plan
uv run --project backend pytest infra/evolus -q   # the kit's own tests: plan only reads and never prints a key
```

Creating the library, the Campaign Invitation extractor, the Campaign Desk agent (on our own vLLM model, `own/<alias>`
from "Your models") and the Verdict workflow (created with `isActive: true`) comes next. It will be written against
what `plan` returns, and the user approves each run that writes to the workspace.

API facts and quirks: `docs/api-guide/evolus-api.md`. Why the Arena bypasses Evolus: `docs/adr/0003`.
