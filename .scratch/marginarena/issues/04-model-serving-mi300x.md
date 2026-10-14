# 04 Which model and serving setup should our own vLLM endpoint on MI300X use?

Type: research
Status: resolved
Blocked by: none

## Question

Which open model should our own vLLM endpoint on an AMD Developer Cloud MI300X serve? It has to do three jobs:

1. Be the Evolus main agent, which needs reliable tool and function calling.
2. Qualify for Google's "best use of Gemma" prize. Gemma-4-31B-IT is the first choice.
3. Handle high-concurrency batched Arena calls.

Specifically:

- Does vLLM on ROCm support Gemma 4 tool calling, and with which parser and flags?
- Which image or container should we use, how much memory does it take, and what throughput can we expect?
- How do we expose the endpoint securely: API key, firewall, HTTPS?
- How do we keep credit burn low (billing while powered off, snapshot then destroy then restore)?

Findings: `.scratch/marginarena/research/model-serving-mi300x.md`

## Answer

Full findings: [research/model-serving-mi300x.md](../research/model-serving-mi300x.md)

- **Model:**
  - `google/gemma-4-31B-it` (BF16, text-only) in one vLLM process on one MI300X. It is the Evolus agent, serves the Arena, and is our entry for the Gemma prize.
  - It must first pass a 30-minute tool-calling test on day 1. If it fails, add `Qwen/Qwen3.6-27B` (parser `qwen3_coder`) for the Evolus agent and keep Gemma for the Arena.
- **Image and flags:**
  - Image `vllm/vllm-openai-rocm:v0.31.0`, pinned by digest.
  - Flags: `--enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4`, the chat template given as an absolute path, `--language-model-only`, `--attention-backend TRITON_ATTN`, and `--host 127.0.0.1`.
- **Known Gemma tool-calling bugs:**
  - Grammar is not enforced.
  - `tool_choice=required` and named tool choice are ignored.
  - `tool_calls` can come back empty under concurrency.
- **Estimated capacity:**
  - About 100 concurrent 2k-token requests, or about 200 with fp8 KV.
  - 1,000–2,500 output tokens/s batched.
  - Roughly 25–45 s for each 100-call Arena round.
  - 10–20 minutes to boot a fresh droplet.
- **Security:**
  - vLLM's `--api-key` does not protect `/invocations` or `/pause`. So vLLM listens on localhost only, and Caddy serves HTTPS with only `/v1/chat/completions` and `/v1/models` allowed through.
  - The HTTPS name comes from DuckDNS or a domain we own. Only ports 22, 80 and 443 are open.
- **Cost:**
  - $2.59/hr gives 38.6 hours for $100. A droplet keeps billing until it is destroyed.
  - Rebuild from a script; don't rely on snapshots.
  - Proposed hours: Thu 3, Fri 5, Sat 4, Sun 07:00–22:00 ICT (15), plus 11.5 in reserve.
  - Develop against Token Factory's Gemma-4-31B-IT. It is the app's fallback only; the Evolus agent still needs our own endpoint.
- **Open, for the user:**
  - How to keep the demo up during the judging window (judges may test until 15 Nov; one always-on day costs about $62).
  - A DuckDNS account or domain.
