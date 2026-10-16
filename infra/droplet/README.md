# The MI300X droplet: create it, use it, destroy it

> **Optional, never run, and not used for the submission.** MarginArena runs on AMD Token Factory only ([ADR 0005](../../docs/adr/0005-token-factory-is-the-only-inference-route.md), Q60). This folder is kept as a tested path for running the same model on our own GPU; no number in `evidence/` comes from it.

This kit would run MarginArena's own AI endpoint on one AMD Developer Cloud GPU droplet (one AMD Instinct MI300X), serving Gemma-4-31B-IT with vLLM behind HTTPS.

**It bills by the second from the moment it is created until it is destroyed, even while it is powered off** ($1.99 an hour for one MI300X in the console on 16 Oct 2026; earlier pages said $2.59). So we create it for a work session and destroy it afterwards. We have no $100 credit, so the card on file pays. A new account must first have its GPU limit raised ("Request Access" next to the greyed-out Create button). Nothing on the droplet needs saving: Claude rebuilds it from this folder in about 20 minutes.

## Once, before the first session

1. Claude runs `python3 infra/droplet/kit.py prepare`. This makes a dedicated SSH key on this Mac, an API key in `.env`, and a startup script. Nothing is created in the cloud.
2. In AMD Developer Cloud, open **Billing** and check that a payment card is on file. Without one, the **Create GPU Droplet** button stays grey.

## Create the droplet (you, about 5 minutes)

1. Sign in at [devcloud.amd.com](https://devcloud.amd.com).
2. In the left menu, open **GPU Droplets**, then click **Create GPU Droplet**.
3. **Region:** ATL1 (Atlanta).
4. **GPU plan:** MI300X, **1 GPU** (192 GB). Do not pick the 8-GPU plan: it costs 8 times as much.
5. **Image:** **ROCm Software**. If it is not in the list, pick **vLLM**; the setup script handles both.
6. **SSH key:** click **Add an SSH Key**. Claude puts the key on your clipboard (`kit.py copy ssh-key`). Paste it with Cmd+V, name it `marginarena-droplet`, add it, and make sure it is ticked. You only add it once; next time just tick it.
7. **Optional, saves a few minutes:** open **Show more options** and find **Startup scripts** (it may be called "user data" or "initialization scripts"). Claude puts the script on your clipboard (`kit.py copy user-data`); paste it into that box. If you can't find the box, skip this step. The script contains our API key, so don't paste it anywhere else.
8. Click **Create GPU Droplet**. Wait until the droplet shows **Active** (2–4 minutes).
9. Copy its **public IPv4 address** (for example `164.92.10.5`, not the private one that starts with `10.`) and send it to Claude.

## What Claude runs

```bash
python3 infra/droplet/kit.py provision <IP>   # sets the droplet up over SSH: 15-25 min; writes VLLM_BASE_URL to .env
python3 infra/droplet/kit.py check            # HTTPS, API key, blocked paths, closed ports, one test chat
python3 infra/droplet/kit.py gate             # ticket 08 tool-calling test; writes evidence/gate-gemma-tool-calling.md
python3 infra/droplet/bench.py                # vllm bench serve at 1-128 in flight; writes evidence/mi300x-benchmark.md
uv run --project backend --env-file .env python backend/scripts/record_arena.py --expect-route mi300x     # full Arena, 12 SKUs
uv run --project backend --env-file .env python backend/scripts/check_explainer.py --expect-route mi300x  # EN/TH explanations
python3 infra/droplet/kit.py ssh -- docker logs --tail 100 gemma   # when something needs debugging
```

If the gate fails, Claude adds a second model for the Evolus agent: `kit.py provision <IP> --with-qwen` serves Qwen3.6-27B at `https://<name>/qwen/v1`, then `kit.py gate --base-url https://<name>/qwen/v1` tests it.

## Connect Evolus (you, after each new droplet)

`provision` prints three values. In the Evolus workspace, open **Your models** and enter:

- **Base URL:** the `https://...sslip.io/v1` address. It contains the droplet's IP, so it changes with every new droplet.
- **Model:** `google/gemma-4-31B-it`
- **API key:** Claude puts it on your clipboard (`kit.py copy api-key`). It stays the same across droplets.

Then press **Test**.

## Destroy the droplet (you, every time you finish)

1. Open **GPU Droplets** and click the droplet.
2. Choose **Destroy** (in the droplet's left menu, or under **More**), then **Destroy this Droplet**, and confirm.
3. Check that the **GPU Droplets** list is empty. Also check that **Snapshots** and **Volumes** are empty: they would bill your card, not the credit.
4. Tell Claude. Claude runs `kit.py forget`, so the app goes back to AMD Token Factory.

Why destroy rather than power off? A powered-off GPU droplet still bills the full hourly rate (about $48–62 a day). Only destroying it stops the bill.

## If something goes wrong

- **"This address answered with a different SSH host key":** the kit pins each droplet's host key. If you just created a new droplet that happens to reuse an old IP, confirm that in the droplet list, then Claude runs `kit.py provision <IP> --reset-host-key`. If you did not create a new droplet, stop and tell Claude: something may be intercepting the connection.
- **"The droplet refused the MarginArena SSH key":** the droplet was created without the `marginarena-droplet` key ticked. Destroy it and create it again.
- **Certificate errors right after `provision`:** Let's Encrypt is still issuing the certificate; Claude runs `check` again a minute later. If Let's Encrypt refuses sslip.io, Claude runs `kit.py provision <IP> --domain nip.io`.
- **Ports 80/443 busy:** the image started Jupyter. The script stops it; if it can't, it prints what holds the port.
- **The startup script's log** is on the droplet: `kit.py ssh -- tail -50 /var/log/cloud-init-output.log`.

## How it works (for reviewers)

- `bootstrap.sh` runs on the droplet as root and is safe to rerun. It opens only ports 22, 80 and 443 (ufw); stops Jupyter if the image runs it; puts the model weights on the droplet's scratch disk; starts Caddy and vLLM in Docker; waits until both answer; and prints the URL.
- vLLM `v0.31.0` (ROCm image pinned by digest) serves `google/gemma-4-31B-it` at a pinned revision, with the `gemma4` tool-call and reasoning parsers, listening on `127.0.0.1` only and requiring the API key.
- Caddy gets a Let's Encrypt certificate for `<ip-with-dashes>.sslip.io`. It forwards only `/v1/chat/completions` and `/v1/models`, and only with the API key, because vLLM's own key check leaves paths such as `/invocations` and `/pause` open.
- `kit.py` (Python standard library only) runs on this Mac. Tests: `uv run --project backend pytest infra/droplet -q`.
- The reasons for every choice are in `.scratch/marginarena/research/model-serving-mi300x.md`.
