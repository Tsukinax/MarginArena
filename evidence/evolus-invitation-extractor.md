# Evidence: the Evolus extractor reads the Campaign Invitation PDF

`infra/evolus/evolus_kit.py apply` built the extractor agent "MarginArena Invitation Reader" (our own model
connection: Gemma-4-31B-IT on AMD Token Factory, with Qwen3.8-27B as its fallback) and its output structure
"Campaign Invitation" (marketplace, campaign, slot, registration closing date, and per product the SKU, name, list
price and minimum discount in percent).

The document is the fictional sample invitation `backend/src/marginarena/sample/glow-lab-bkk-invitation.pdf`, written
by `backend/scripts/make_sample_invitation.py` from the same JSON the Arena uses. It is the only document the app sends:
Token Factory, behind the extractor's model, may see sample data only.

## Runs on 15 Oct 2026

| Run | How | Execution | Time | Result |
|---|---|---|---|---|
| 1 | `ask-file` from a script | `5f4e9050-7fc8-f111-bf5b-000d3aae6dc8` (audit `3d64956b-7fc8-f111-bf5b-000d3aae6dc8`) | 35.7 s | all 5 header fields and all 12 product rows read correctly |
| 2 | "Read it with the Evolus extractor" in the web app (`POST /api/invitation/read`) | `d22f3ac1-7fc8-f111-bf5b-000d3aae6dc8` (audit `6187fbfc-7fc8-f111-bf5b-000d3aae6dc8`), read at 10:05:49Z | about 2 minutes | 12 of 12 minimum discounts match the invitation the Arena checks |
| 3 | `POST /api/invitation/read` on the live site (https://marginarena.vercel.app, functions in `hkg1`), called with curl | `e2424803-85c8-f111-bf5b-000d3aae6dc8` (audit `c825aa58-85c8-f111-bf5b-000d3aae6dc8`), read at 10:44:10Z | 147.85 s, as curl measured it | 12 of 12 minimum discounts match |

The app checks every discount it reads against the sample invitation and flags any difference
(`backend/tests/api/test_invitation_api.py`).

## What did not work

- With the platform OCR model `greenpt/documents`, the extraction failed with 502 ("Call to 'generic-ocr' failed").
  The other OCR model the application lists, `codedesign_documentintelligence`, was refused as an agent's OCR key.
- With OCR turned off on the agent and on the output structure, the model reads the PDF's own text. A scanned
  invitation would need OCR again.
- The time varies with Token Factory: 35.7 s in the first run, about 2 minutes in the second, 147.85 s in the third.
