# Research: when do the AI Rivals' Counter-moves change a decision? (input to Q56)

Run 14 Oct 2026 with the engine only, no LLM: `uv run --project backend python .scratch/marginarena/research/q56_red_team.py`.

## Why

Since maximin (Q52), no recorded run has seen the AI Rivals change a plan: every `leader` event says "holds", and
`red_team_gain` is zero or empty on every SKU. The Arena leads the pitch, so a judge can fairly ask what the
red team adds.

## Rules fixed before running

- Counter-moves: the three generic ones the Arena always uses (hold, match, undercut by 5 points), plus six moves
  Gemma actually proposed in `evidence/runs/*.sse` (cuts of 7–22%, ฿50–72 vouchers, ฿40 free shipping).
- Elasticity: the fitted pooled −1.49 with its band, or the literature mean −2.62 (Bijmolt et al. 2005, already cited
  in `elasticity-dataset.md`) as a labelled Seller override, with either the shop's band or its own band (the fitted
  band's relative width: −3.48 to −1.36).
- Cross-price sensitivity k: 1.0 (today's assumption) and 2.0. Neither value has a source.
- Every SKU and configuration is reported, including those where nothing changes.

## Results (12 sample SKUs, each against the same moves)

| Configuration | Decisions the AI moves change |
|---|---|
| A. Today: −1.49, shop band, k = 1 | **0 of 12** |
| B. −1.49, shop band, k = 2 | 8 of 12 |
| C. −2.62 override, shop band, k = 1 | 1 of 12 (RN-30, Skip → Escalate) |
| D. −2.62 override, own band, k = 1 | 8 of 12 (four Approves become Revises) |
| E. −2.62 override, own band, k = 2 | 7 of 12 |

- **The red team still finds real risk in A.** The recorded moves cut the worst case of the plan chosen against the
  generic moves by up to ฿27,468 (AC-150); NT-200 loses ฿16,262. The plan holds, but the Seller's worst case was too
  rosy. Commit 488948c now reports this as `red_team_cut`.
- **Decisions hinge on two unsourced assumptions:** k, and the weak edge of the elasticity band (−0.77), which
  penalises deeper cuts in the worst case.
- **A per-SKU elasticity override changes nothing on its own** (C): the band comes from the shop's `CampaignTerms`, so
  the weak edge −0.77 still decides the worst case. An override needs its own band.
- **SS-50 alone with an override (D for one SKU):** five of the six recorded moves each turn Approve into Revise. For
  example, the Undercutter at 15% + ฿50 voucher + ฿40 shipping makes ฿153 off keep ฿77,354 in the worst case against
  ฿72,993 for the invited ฿90 off.

## Caveats

- Each Counter-move is assumed to last the whole Campaign, so a midnight flash drop counts as a Campaign-long price.
  This overstates the threat.
- The override's band rule (same relative width as the fit) is our construction, not a published band.

## Options for Q56

1. Keep the assumptions; show the red team as risk discovery (done in 488948c). Honest, but the demo never shows the
   AI changing a plan.
2. Option 1, plus one labelled Seller override on a lookalike-heavy SKU (for example SS-50 sunscreen at the
   literature mean, with its own band), so the demo can show the AI turning an Approve into a Revise. Q51 already
   allows labelled per-SKU values. It needs a per-SKU band in the sample loader and the Arena (the engine is
   unchanged), and the UI must label it as a sample Seller override.
3. Change k or the default elasticity for every SKU. Not recommended: neither has a source, and the second reverses
   Q51.

## Decision

15 Oct: the user chose option 2 (recorded as Q56 in `issues/01-charting-grill.md`). Option 1 is built; the SS-50
override is next.
