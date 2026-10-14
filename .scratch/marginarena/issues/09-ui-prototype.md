# 09 What should the MarginArena screens look like?

Type: prototype
Status: resolved
Blocked by: none
Who: Claude builds, user reviews (HITL)

## Question

What should the main flow look like, from uploading the Campaign Invitation, to watching the Arena live, to the Verdict and confirmation, alongside the AMD Evidence panel? Build three structurally different throwaway variants on one prototype route, using mock data and no LLM, switchable with `?variant=`. The user picks one, or picks parts from each.

## Answer

Chosen by the user on 14 Oct: **C as the backbone, with A's Arena and B's charts.**
- The flow is Variant C's guided Seller Inbox: Invitation, then Checking, then Verdicts, then Confirm. The human confirms, because joining a Campaign is opt-in.
- Step 2 (Checking) becomes Variant A's live Arena: the bracket, the GPU scoreboard and the commentary.
- The "How we decided" drawer gains Variant B's margin waterfall and the Strategist × Rival heat grid.
- The prototype code stays on a throwaway branch as a primary source, and only the decision moves into main.

## Comments

- 14 Oct: the prototype is built at `web/src/prototype/arena/` (`VariantA/B/C.tsx` and `mock.ts`). Run it with `npm --prefix web run prototype`, or use the "web" launch config, then open http://localhost:5173/prototype/arena?variant=A|B|C and switch variants with ←/→.
  - The mock engine uses the real Shopee fee rate (27.82% + ฿1.07) and per-SKU elasticities from −1.1 to −2.9.
  - The demo shop gets 7 Approve, 2 Revise and 3 Escalate verdicts; ฿23,156 of margin protected; 432 LLM calls.
  - Waiting on the user to choose a variant.
