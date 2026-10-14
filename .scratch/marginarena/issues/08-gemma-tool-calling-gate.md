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
