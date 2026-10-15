# Evidence: the Evolus Verdict workflow carries out confirmed Verdicts

`infra/evolus/evolus_kit.py apply --model own/Gemma-4-31B-IT --fallback own/Qwen3.8-27B` built, in the Evolus event
workspace (15 Oct 2026):

- the knowledge library "MarginArena Campaign Desk library" (Shopee Thailand fees and Campaign rules; the sample
  HydraLab reseller agreement), uploaded in English;
- the agent "MarginArena Campaign Desk" on our own model connection "tf-gemma on AMD" (Gemma-4-31B-IT on AMD Token
  Factory, falling back to Qwen3.8-27B on the same route), with the library attached;
- the workflow "MarginArena Verdict", turned on, in five steps: Split the Verdicts (Script), Bulk-upload file
  (CreateFile, CSV), Approval request (AgentCall to the Campaign Desk agent), Assemble the result (Script), Result
  (Output).

## One run, as the Confirm step makes it

Reproduce: run the API with the Evolus keys and `EVOLUS_WORKFLOW_ID` in `.env`, choose "Watch all 12 products
(recorded run)", then "Confirm and run the Evolus workflow" (`POST /api/confirm`, then `GET /api/confirm/{id}`).

- **Input:** the 12 Verdicts of the recorded run (`runs/token-factory-sample-12sku.sse`), each checked against the
  server's signature first, with the engine's figures passed through unchanged.
- **Run:** execution `4d903564-7cc8-f111-bf5b-000d3aae6dc8`, requested 2026-10-15T09:40:01.79Z, completed
  09:40:12.35Z (10.55 s); 5 steps executed; **0.0 Evolus credits**, because every AI step ran on our own model.
- **Step times:** Split the Verdicts 0 ms, Bulk-upload file 77 ms, Approval request 10,205 ms, Assemble the result
  0 ms, Result 0 ms.
- **Output:** 9 SKUs to upload (each with its Promo Plan, Campaign price and shop voucher), 1 escalation (VC-30) and 2
  skips (RN-30, SM-10).

The Campaign Desk agent's draft, as returned (nothing was sent):

> Subject: Approval Required: 11.11 Big Sale Campaign Escalation
>
> Dear Shop Owner,
>
> We have one product that requires your decision for the 11.11 Big Sale. The Vitamin C Bright Serum 30 ml (VC-30) was
> escalated because it is below the Margin Floor. With the invited plan of ฿118.00 off, the worst case is 7369.32
> compared to 6239.50 if not joining. Please let us know if you approve this product for the campaign.

Every number in the draft is an engine figure from the input: ฿118.00 off as invited, 7,369.32 worst case as invited,
6,239.50 worst case without joining. The run does not report whether Gemma or its Qwen fallback answered; Gemma on
Token Factory had no workers earlier that hour.

## Limits

- The bulk-upload columns are MarginArena's; Seller Centre's template is not public.
- The workflow drafts the approval request and sends nothing.
