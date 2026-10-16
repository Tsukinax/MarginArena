# 08 Does Gemma-4-31B-IT tool calling hold up on our vLLM endpoint?

Type: task
Status: open
Blocked by: 07
Who: Claude (AFK, once the droplet is up)

## Question

Run the 30-minute tool-calling pass/fail test from [research/model-serving-mi300x.md](../research/model-serving-mi300x.md) against Gemma-4-31B-IT on the MI300X. Check it under concurrency, and check it through Evolus "Your models".

- **Pass:** serve Gemma alone.
- **Fail:** add Qwen3.6-27B for the Evolus agent.

Record the results; they are AMD evidence.

## Comments

- 14 Oct: the droplet kit is merged (`infra/droplet/`, commit a0e1400; 27 tests). `kit.py prepare` has run: the SSH key is `~/.ssh/marginarena_droplet_ed25519`, and VLLM_API_KEY is in `.env`. The gate is `python3 infra/droplet/kit.py gate`, which writes `evidence/gate-gemma-tool-calling.{md,json}`. It is still blocked on the user creating the droplet (`infra/droplet/README.md`).
- 15 Oct: deferred. Under ADR 0005 there is no droplet unless the user chooses a paid GPU session on Friday (Q57).
  Evolus "Your models" tested the Token Factory connection instead: Qwen3.8-27B passed answers, tool calling,
  streaming and reasoning; Gemma-4-31B-IT failed because Token Factory had no Gemma workers at the time (500
  "no_available_workers"). If a GPU session happens, run `kit.py gate` then.
- 16 Oct: the user approved a GPU session (one MI300X, about 3 h). AMD Developer Cloud keeps "Create GPU Droplet" greyed until a limit increase ("Request Access") or credits are approved; status unknown at 21:00 ICT. The console priced it at $1.99/hr with the "ROCm Software" 10.1 image; the SSH key `marginarena-droplet` is uploaded. `infra/droplet/bench.py` (targets vLLM's port 8001; not yet run on hardware) follows `gate`, then `record_arena.py` and `check_explainer.py` with `--expect-route mi300x`. Run order: `handoff.md` section 5.
- 17 Oct: cancelled (Q60). The organisers said standalone GPUs are not needed in ACT III; there will be no droplet, so this gate does not run.
