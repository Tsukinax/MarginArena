# Evidence: what the Evolus workspace has run

Read on 17 Oct 2026, about 02:45 ICT, read-only through the Evolus MCP endpoint (`list_workflow_executions`,
`list_output_structure_executions`, `get_workflow_execution_detail`). No resource was created or changed by the reading.

## Two live runs from the live site, 17 Oct 2026

Both were started through https://marginarena.vercel.app, as a judge would start them, on the sample invitation and
the 12 recorded Verdicts.

| Run | Execution | Requested → completed (UTC, 16 Oct) | Result |
|---|---|---|---|
| Invitation extractor ("Read it again live with Evolus", `POST /api/invitation/read`) | `4bbe5168-99c9-f111-bf5b-6045bd9ce552` | 19:40:15 → 19:40:30 (14.9 s) | 12 of 12 minimum discounts match the invitation the Arena uses; 18 s as curl measured it |
| Verdict workflow ("Confirm and run the Evolus workflow", `POST /api/confirm`) | `ffdb5077-99c9-f111-bf5b-6045bd9ce552` | 19:40:40 → 19:40:43 (3.1 s) | 5 steps; 9 products to upload, VC-30's approval request drafted, nothing sent; **0.0 credits** |

Step times of the workflow run, in order (Split the Verdicts, Bulk-upload file, Approval request, Assemble the result,
Result): 3, 18, 2,978, 1 and 0 ms.

## Every execution in the workspace

**Verdict workflow:** 4 executions, all Completed, each with 5 steps.

| Execution | Requested (UTC) |
|---|---|
| `ffdb5077-99c9-f111-bf5b-6045bd9ce552` | 2026-10-16 19:40:40 |
| `28c484cf…` | 2026-10-15 09:57:28 |
| `11f866c6…` | 2026-10-15 09:57:05 |
| `4d903564-7cc8-f111-bf5b-000d3aae6dc8` (the recorded run the app shows) | 2026-10-15 09:40:01 |

**Invitation extractor:** 9 executions, 5 Completed and 4 Failed. The 4 failures are on 15 Oct (10:00:37, 10:00:51,
16:23:06 and 16:23:06 UTC), from the period when the platform OCR answered HTTP 502 (`evidence/evolus-invitation-extractor.md`);
every run since OCR was turned off has completed.

## Limits

- The Evolus records do not say whether Gemma-4-31B-IT or the agents' Qwen3.8-27B fallback answered.
- `get_model_usage` needs a platform permission this workspace's key does not have, so model-level usage is not shown.
