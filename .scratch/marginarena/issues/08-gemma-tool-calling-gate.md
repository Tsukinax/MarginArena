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
