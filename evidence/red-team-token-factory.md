# Evidence: an AI Rival turns SS-50's Approve into a Revise (live, Token Factory)

The raw stream is [`runs/token-factory-sample-4sku-ss50-override.sse`](runs/token-factory-sample-4sku-ss50-override.sse).
Reproduce it with the `api` server running (it reads `.env`), then:

```bash
curl -sN -X POST http://localhost:8008/api/arena -H 'Content-Type: application/json' -d '{"shop":"glow-lab-bkk"}' -o evidence/runs/token-factory-sample-4sku-ss50-override.sse
```

Gemma proposes different Counter-moves on every run, so a rerun gives different numbers.

- **Measured:** finished 2026-10-14T17:56:23Z (15 Oct 00:56 ICT) on route `token-factory`, model `Gemma-4-31B-IT`,
  sample shop Glow Lab BKK.
- **Arena:** the fallback set of 4 SKUs, 1 Strategist, 2 Rivals, 2 rounds. 20 calls succeeded, 0 were invalid, 0 failed
  and 0 were retried; 1,646 completion tokens in 78.25 s.
- **Margin Protected:** ฿4,370.15 (SS-50 ฿3,728.85 and SM-10 ฿641.30; VC-30 is escalated and not counted).

| SKU | Verdict | Plan chosen first | Its worst case: generic moves / every Scenario | Red-team cut | Final plan | Its worst case |
|---|---|---|---|---|---|---|
| NT-200 | Approve | ฿58.50 off | ฿48,085.17 / ฿37,010.16 | ฿11,075.01 | ฿58.50 off | ฿37,010.16 |
| SS-50 | Revise | ฿90.00 off | ฿86,314.94 / ฿61,752.65 | ฿24,562.29 | ฿126.00 off + ฿34 voucher | ฿65,481.50 |
| VC-30 | Escalate | ฿118.00 off | ฿8,795.64 / ฿5,031.74 | ฿3,763.90 | none (a person decides) | – |
| SM-10 | Revise (Skip) | ฿79.80 off | ฿2,978.56 / ฿1,804.32 | ฿1,174.24 | don't join | ฿2,445.62 |

"Generic moves" are the hold, match and undercut moves the engine always tests. "Every Scenario" adds the Counter-moves
the AI Rivals found. The red-team cut is how far those moves lower the worst case of the plan chosen first. For
VC-30 and SM-10 no plan passed even against the generic moves, so the plan chosen first is joining as invited.

## SS-50, round by round

1. Before the Rivals, the invited ฿90.00 off is the leader. Against the generic moves the Verdict is Approve (an
   engine-only re-check with this run's Plan Ideas).
2. Round 1: the two Rivals propose a Counter-move each. The harder one is the Undercutter's 15% off, a ฿40 voucher and ฿40 free shipping (effective rival price ฿277.00).
   The engine re-selects over every Scenario, and the leader changes to ฿130.50 off + ฿23 voucher (Revise).
3. Round 2: the harder Counter-move is again the Undercutter's: 32% off, a ฿20 voucher and ฿40 free shipping (effective rival price ฿225.60).
   The leader changes again, to ฿126.00 off + ฿34 voucher.
4. Final: Revise. Against every Scenario, the plan keeps ฿65,481.50 in the worst case, against ฿61,752.65 for joining as
   invited (+฿3,728.85).

## What this rests on

- **SS-50 uses a labelled sample Seller override:** elasticity −2.62 (the published mean, Bijmolt, Van Heerde and
  Pieters 2005) with a band of −3.48 to −1.36, our construction at the fitted band's relative width. With the pooled
  fit (−1.49, band −1.977 to −0.771), an engine-only check found that the recorded Counter-moves change no decision
  (`.scratch/marginarena/research/q56-red-team.md`).
- **k = 1.0**, the share of buyers kept when a Rival ends up cheaper, has no source.
- **Each Counter-move is assumed to last the whole Campaign**, which overstates a short flash drop.
- **A Rival's move is a stress test, not a forecast** (ADR 0001). Every number above comes from the engine.
