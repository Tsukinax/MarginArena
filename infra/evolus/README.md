# The Evolus kit: set up the event workspace from code

MarginArena drives Evolus through its REST API (Evolus Business Agents track). This folder holds what the workspace
needs and the script that sets it up, so the setup is reproducible rather than clicked together.

- `library/`: the documents for the Campaign Desk agent's knowledge library. They cover Shopee Thailand's fees and
  Campaign rules (with sources) and the fictional HydraLab reseller agreement behind the sample shop's Brand Price
  Rule. They are uploaded with `language=en`, because Evolus defaults to Italian.
- `evolus_kit.py plan`: **read-only.** It lists the agents, knowledge libraries, workflows and web services already in
  the workspace, the workflow step catalog, and the scopes of the User API Key. It saves the raw answers to
  `.plan/latest.json` (gitignored) and changes nothing.

- `evolus_kit.py apply [--model own/<alias> [--fallback own/<alias>]]`: **writes, so the user approves each run.** It
  finds each resource by name before creating it, so a rerun creates nothing new, and saves the IDs to `.env`
  (`EVOLUS_LIBRARY_ID`, `EVOLUS_AGENT_ID`, `EVOLUS_WORKFLOW_ID`, `EVOLUS_READER_ID`,
  `EVOLUS_INVITATION_STRUCTURE_ID`). It builds the knowledge library (every document in `library/`, in English), the
  Campaign Desk agent on the given own model with the library attached, the Verdict workflow (Split the Verdicts
  (Script), Bulk-upload file (CreateFile), Approval request (AgentCall), Assemble the result (Script), Result
  (Output)), and the Campaign Invitation extractor: the extractor agent "MarginArena Invitation Reader" and its output
  structure "Campaign Invitation", both with OCR off. Step types go to the API as the step catalog's numbers. Built on 15 Oct 2026 with
  `--model own/Gemma-4-31B-IT --fallback own/Qwen3.8-27B` ("tf-gemma on AMD" under "Your models").

```bash
uv run --project backend --env-file .env python infra/evolus/evolus_kit.py plan
uv run --project backend --env-file .env python infra/evolus/evolus_kit.py apply
uv run --project backend pytest infra/evolus -q   # plan only reads; apply creates once; neither prints a key
```

The app runs the workflow from the Confirm step (`POST /api/confirm`; it needs `EVOLUS_API_KEY`,
`EVOLUS_APPLICATION_ID` and `EVOLUS_WORKFLOW_ID`). In this workspace every AI block runs on "Your models" only, so the
approval request is drafted by the Campaign Desk agent rather than a platform AI Tool. One run is recorded in
`evidence/evolus-verdict-workflow.md`.

The Invitation step has the extractor read the sample invitation PDF (`POST /api/invitation/read`; it also needs
`EVOLUS_READER_ID` and `EVOLUS_INVITATION_STRUCTURE_ID`) and checks each minimum discount against the invitation the
Arena uses. Only that bundled sample is ever sent, because Token Factory may see sample data only. The platform OCR
failed with 502 on 15 Oct, so the extractor reads the PDF's own text; a scanned invitation would need OCR again. Two
runs are recorded in `evidence/evolus-invitation-extractor.md`.

API facts and quirks: the Evolus MCP endpoint `https://api.evolus.ai/mcp` (`tools/list`) documents every request body.
Why the Arena bypasses Evolus: `docs/adr/0003-arena-bypasses-evolus.md`.
