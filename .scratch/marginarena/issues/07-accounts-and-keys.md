# 07 Accounts and keys only the user can set up

Type: task
Status: open
Blocked by: none
Who: user (HITL)

## Question

The user's tasks:

- Paste the Token Factory `rc-` key into `.env`.
- Check that a card is on file with AMD Developer Cloud, so droplets can be created. Do not create a droplet yet.
- ~~Sign up for DuckDNS~~: replaced by sslip.io (Q49), so no signup is needed.
- Confirm which GitHub account will hold the public repo.
- Ask in the lablab Discord when judges test the demos, and record the answer here.

## Comments

- 15 Oct: the Token Factory key is in `.env` and in Vercel. No card or $100 credit is needed: the submission runs on
  Token Factory only (Q57, ADR 0005). GitHub: the private repo `Tsukinax/MarginArena` (created with `gh` on the user's
  approval; it goes public at submission). Vercel: project `marginarena` in team "Tsukinax's projects", linked to the
  repo, so every push to `main` redeploys https://marginarena.vercel.app. The user sets its secrets in the Vercel
  dashboard: `TOKEN_FACTORY_API_KEY`, `RESULT_SIGNING_KEY` and the `EVOLUS_*` names in `.env.example`. Still open: when
  judges test the demos.
- 16 Oct: the user confirmed judges review after the event ends and that the lablab form allows several tracks. AMD Developer Cloud: whether a card is on file is unconfirmed; the GPU limit is 0 until "Request Access" is approved. The user said they set "2" values on Vercel; which ones is not recorded yet.
