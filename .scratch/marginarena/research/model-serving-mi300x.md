# Research 04: Model and serving setup for our own vLLM endpoint on an AMD Developer Cloud MI300X

Ticket: [04-model-serving-mi300x](../issues/04-model-serving-mi300x.md). Research date: Wed 14 Oct 2026. I read only public pages and source code. I signed in to nothing and created no cloud resources.

How to read the labels:
- No label: the cited source states it directly.
- **[EST]**: my estimate. The working is shown. Measure it on day 1.
- **[INF]**: my inference from the cited facts.
- **[UNVERIFIED]**: a source I could not re-check today, or a page I could not load.

---

## 1. Recommendation

**Model.** Serve `google/gemma-4-31B-it` in BF16, text-only, from one vLLM process. That one process does all three jobs: the Evolus main agent (tool calling), the Arena batch calls (JSON output) and the Gemma story.
- Gate this on a 30-minute tool-calling acceptance test in the first GPU session (§2.5). The Gemma 4 tool parser has open reliability bugs, and unlike the Qwen and Hermes parsers it has no grammar enforcement (§2.3).
- If the test fails, add `Qwen/Qwen3.6-27B` as a second vLLM process on the same GPU and point the Evolus main agent at it. Gemma keeps the Arena (§5).

**Image.** Use `vllm/vllm-openai-rocm:v0.31.0`, pinned by digest `sha256:749f6f3f944f12af49966ac523c1f8573e4b229594b541954bd5f879b4496b1f`. It is 11.5 GB compressed, vLLM 0.31.0, with ROCm 7.2.3 user space. Don't rely on whatever vLLM the console's one-click image ships (§3).

**Droplet.** Use an AMD Developer Cloud `gpu-mi300x1-192gb` (1× MI300X) in ATL1, the only region offered ([DO: AMD availability](https://docs.digitalocean.com/products/amd/details/availability/); [DO: create AMD GPU Droplets](https://docs.digitalocean.com/products/amd/how-to/create/)).

**Exposure.** vLLM listens on `127.0.0.1` only. Caddy runs on the host, terminates HTTPS for a DNS name (DuckDNS or your own domain) and forwards only `/v1/chat/completions` and `/v1/models`. Use vLLM `--api-key` as a second layer. A DigitalOcean Cloud Firewall admits only 22, 80 and 443 (§6).

**Cost.** $100 buys **38.6 MI300X-hours** at the verified $2.59/hr. Destroy the droplet between sessions, because a powered-off droplet still bills. Rebuild from a script rather than from snapshots. Budget about 27 h through Sunday and keep about 11 h in reserve (§7).

### 1.1 Exact commands (single-model default)

Run these as root on the droplet. Secrets live only in `/opt/llm/*.env` and never go in git.

```bash
# 0) Sanity checks on a fresh droplet
amd-smi version                       # host driver; ROCm 7.2.x user space needs amdgpu 6.4.x or 30.10+ (see §3)
ufw status verbose                    # AMD's own guide uses ufw on these droplets
ss -ltnp | grep -E ':(80|443|8000|8001)\b' || true   # the Quick Start image may run Jupyter on :80, so stop it before starting Caddy

# 1) Folders and a pinned chat template (the relative path in the recipe breaks: vLLM issue #47600)
mkdir -p /opt/llm/{hf,vllm-cache,templates,caddy/conf,caddy/data,caddy/config}
curl -fsSL -o /opt/llm/templates/tool_chat_template_gemma4.jinja \
  https://raw.githubusercontent.com/vllm-project/vllm/v0.31.0/examples/tool_chat_template_gemma4.jinja

# 2) API key (give this value to Evolus as the model API key)
umask 077; printf 'VLLM_API_KEY=%s\n' "$(openssl rand -hex 32)" > /opt/llm/vllm.env

# 3) Pull the pinned image
IMG='vllm/vllm-openai-rocm:v0.31.0@sha256:749f6f3f944f12af49966ac523c1f8573e4b229594b541954bd5f879b4496b1f'
docker pull "$IMG"

# 4) Start Gemma 4 31B (the image ENTRYPOINT is `vllm serve`)
docker run -d --name gemma --restart unless-stopped \
  --network=host --ipc=host --shm-size 16G \
  --device=/dev/kfd --device=/dev/dri --group-add=video \
  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  --env-file /opt/llm/vllm.env -e HF_XET_HIGH_PERFORMANCE=1 \
  -v /opt/llm/hf:/root/.cache/huggingface \
  -v /opt/llm/vllm-cache:/root/.cache/vllm \
  -v /opt/llm/templates:/templates:ro \
  "$IMG" \
    --model google/gemma-4-31B-it \
    --revision 842da3794eaa0b77d5f08bae87a17459d91ff475 \
    --served-model-name gemma-4-31b-it \
    --host 127.0.0.1 --port 8001 \
    --language-model-only \
    --attention-backend TRITON_ATTN \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.90 \
    --max-num-seqs 128 \
    --enable-auto-tool-choice \
    --tool-call-parser gemma4 \
    --reasoning-parser gemma4 \
    --chat-template /templates/tool_chat_template_gemma4.jinja \
    --structured-outputs-config '{"backend":"xgrammar","disable_any_whitespace":true}' \
    --async-scheduling

docker logs -f gemma        # wait for "Application startup complete"; note the KV-cache size and max-concurrency lines
. /opt/llm/vllm.env; curl -s -H "Authorization: Bearer $VLLM_API_KEY" http://127.0.0.1:8001/v1/models
```

Caddy (`/opt/llm/caddy/conf/Caddyfile`). Replace the host name.

```caddy
marginarena.duckdns.org {
    @api path /v1/chat/completions /v1/models
    handle @api {
        reverse_proxy 127.0.0.1:8001
    }
    handle {
        respond 404
    }
}
```

```bash
docker run -d --name caddy --restart unless-stopped --network=host \
  -v /opt/llm/caddy/conf:/etc/caddy:ro \
  -v /opt/llm/caddy/data:/data -v /opt/llm/caddy/config:/config \
  caddy:2.11.7
```

Evolus model settings: base URL `https://marginarena.duckdns.org/v1`, model `gemma-4-31b-it`, API key = the `VLLM_API_KEY` value ([Evolus developers](https://evolus.ai/en/developers)).

Where each flag comes from:
- `gemma4` tool and reasoning parsers, the chat template, `--language-model-only` and `--async-scheduling`: the [vLLM Gemma 4 recipe](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md) and the [gemma-4-31B-it recipe YAML](https://github.com/vllm-project/recipes/blob/main/models/Google/gemma-4-31B-it.yaml).
- `TRITON_ATTN`: [AMD's Day 0 Gemma 4 article](https://www.amd.com/en/developer/resources/technical-articles/2026/day-0-support-for-gemma-4-on-amd-processors-and-gpus.html).
- Container device flags: [ROCm docs: vLLM](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/inference/vllm.html), via the repo notes.
- `disable_any_whitespace`: [vLLM v0.31.0 structured_outputs.py](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/config/structured_outputs.py) and [issue #42110](https://github.com/vllm-project/vllm/issues/42110).
- `VLLM_API_KEY`: [vLLM security docs](https://docs.vllm.ai/en/latest/usage/security.html).
- `HF_XET_HIGH_PERFORMANCE`: [HF env vars](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables).
- The model revision is the `main` commit on 14 Oct: [HF API](https://huggingface.co/api/models/google/gemma-4-31B-it/revision/main).
- Caddy mounts: [Docker Hub `caddy`](https://hub.docker.com/_/caddy), which warns not to mount the Caddyfile file directly. Caddy v2.11.7 was released 3 Oct 2026 ([release](https://github.com/caddyserver/caddy/releases/tag/v2.11.7)).

---

## 2. Gemma 4 tool calling on vLLM with ROCm

### 2.1 Support status
- vLLM has a `gemma4` tool-call parser and a `gemma4` reasoning parser. Both are registered in [`vllm/tool_parsers/__init__.py`](https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/__init__.py) and [`vllm/reasoning/__init__.py`](https://github.com/vllm-project/vllm/blob/main/vllm/reasoning/__init__.py).
- I checked the release tags:
  - v0.18.0 has no `gemma4` parser.
  - v0.19.0 (3 Apr 2026) and every later tag I checked (v0.20.0, v0.23.0, v0.27.0, v0.29.0, v0.31.0) have both parsers. Sources: the [v0.19.0 registry](https://github.com/vllm-project/vllm/blob/v0.19.0/vllm/tool_parsers/__init__.py) and [vLLM releases](https://github.com/vllm-project/vllm/releases).
  - The recipe sets `min_vllm_version: "0.19.1"` for gemma-4-31B-it ([recipe YAML](https://github.com/vllm-project/recipes/blob/main/models/Google/gemma-4-31B-it.yaml)).
- The parser is plain Python in the API-server layer, so it doesn't depend on ROCm ([gemma4_utils.py](https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/gemma4_utils.py)) **[INF]**.
- The recipe marks gemma-4-31B-it `mi300x: verified`. Its minimum AMD hardware for BF16 is "1× MI300X/MI325X/MI350X/MI355X" ([recipe YAML](https://github.com/vllm-project/recipes/blob/main/models/Google/gemma-4-31B-it.yaml); [Gemma 4 recipe](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md)).
- AMD announced Day 0 Gemma 4 support on Instinct GPUs through vLLM and SGLang. Its vLLM guidance is `--attention-backend TRITON_ATTN` "for all AMD GPUs". It says the model "fits on a single MI300X GPU (192 GB HBM) at TP=1 with full context length" ([AMD Day 0 Gemma 4](https://www.amd.com/en/developer/resources/technical-articles/2026/day-0-support-for-gemma-4-on-amd-processors-and-gpus.html), 2 Apr 2026).
- Gemma 4's tool-call format uses its own special tokens (`<|tool_call>call:name{...}<tool_call|>`). Thinking uses `<|channel>thought ... <channel|>`. Thinking is off unless you enable it ([Gemma 4 recipe](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md); [model card](https://huggingface.co/google/gemma-4-31B-it)).
- Model quality for agent work: the model card reports **Tau2 (average over 3) 76.9%** for Gemma 4 31B, against 16.2% for Gemma 3 27B ([model card](https://huggingface.co/google/gemma-4-31B-it)). The weak link is the serving parser (§2.3), not the model.

### 2.2 Flags and settings
| Flag | Why | Source |
|---|---|---|
| `--enable-auto-tool-choice` | Required for tool calling | [vLLM tool calling](https://docs.vllm.ai/en/latest/features/tool_calling.html) |
| `--tool-call-parser gemma4` | Gemma 4 tool format | [recipe](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md) |
| `--reasoning-parser gemma4` | Always set it. Open bug [#57231](https://github.com/vllm-project/vllm/issues/57231): without it, the tool parser leaks a synthetic `<|channel>` into content. | recipe; issue |
| `--chat-template <abs path>/tool_chat_template_gemma4.jinja` | The recipe's override "optimized for reasoning and tool calling". Use an **absolute** path. The relative `examples/...` path fails on pip installs ([#47600](https://github.com/vllm-project/vllm/issues/47600), open). In the ROCm image the file sits at `/app/vllm/examples/` while WORKDIR is `/app` ([Dockerfile.rocm v0.31.0](https://github.com/vllm-project/vllm/blob/v0.31.0/docker/Dockerfile.rocm)) **[INF]**. Mounting the [v0.31.0 copy](https://github.com/vllm-project/vllm/blob/v0.31.0/examples/tool_chat_template_gemma4.jinja) avoids both problems. | recipe; issue; Dockerfile |
| `--language-model-only` | Text-only. Skips the ~550M-parameter vision encoder and frees VRAM for KV cache. | [recipe YAML](https://github.com/vllm-project/recipes/blob/main/models/Google/gemma-4-31B-it.yaml); [model card](https://huggingface.co/google/gemma-4-31B-it) |
| `--attention-backend TRITON_ATTN` | AMD's Day 0 guidance. In vLLM source, the ROCm backends `ROCM_AITER_FA` and `ROCM_ATTN` support head sizes only up to 256. Gemma 4 31B's global layers use `global_head_dim: 512`. `TRITON_ATTN` accepts any head size ≥ 32. | [AMD Day 0](https://www.amd.com/en/developer/resources/technical-articles/2026/day-0-support-for-gemma-4-on-amd-processors-and-gpus.html); [rocm_aiter_fa.py](https://github.com/vllm-project/vllm/blob/main/vllm/v1/attention/backends/rocm_aiter_fa.py); [rocm_attn.py](https://github.com/vllm-project/vllm/blob/main/vllm/v1/attention/backends/rocm_attn.py); [triton_attn.py](https://github.com/vllm-project/vllm/blob/main/vllm/v1/attention/backends/triton_attn.py); [config.json](https://huggingface.co/google/gemma-4-31B-it/blob/main/config.json) |
| Thinking | Off by default. Enable per request with `extra_body={"chat_template_kwargs":{"enable_thinking":true}}`, or server-wide with `--default-chat-template-kwargs '{"enable_thinking": true}'`. Keep it off for Arena latency **[INF]**. | [recipe](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md) |
| Sampling | Google recommends `temperature=1.0, top_p=0.95, top_k=64`. Set sampling per request. Do **not** use `--override-generation-config`: open bug [#45591](https://github.com/vllm-project/vllm/issues/45591) says it drops `eos_token_id`, so Gemma 4 tool-calling generation "never stops". | [model card](https://huggingface.co/google/gemma-4-31B-it); issue |

### 2.3 Known reliability gaps
- **No enforcement for `tool_choice="required"` or named tools.** In v0.29.0, v0.31.0 and `main`, `Gemma4EngineToolParser` sets `supports_required_and_named = False`. Its `adjust_request` deliberately skips structured-output JSON for those cases ([source v0.31.0](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/tool_parsers/gemma4_engine_tool_parser.py)). Open bugs:
  - [#53363](https://github.com/vllm-project/vllm/issues/53363): `required` returns prose with `finish_reason:"tool_calls"` and `tool_calls: []`.
  - [#50477](https://github.com/vllm-project/vllm/issues/50477): named `tool_choice` is ignored, reported **inside the official ROCm container** on 0.26.0.
- **No structural-tag grammar for Gemma tool calls.** The `hermes` and `qwen3_coder` parsers set `structural_tag_model` (`"hermes"`, `"qwen_3_coder"`). Under the default `VLLM_ENFORCE_STRICT_TOOL_CALLING=true`, that constrains the tool-call output. The gemma4 parser sets none ([v0.31.0 qwen3](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/tool_parsers/qwen3_engine_tool_parser.py); [v0.31.0 hermes](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/tool_parsers/hermes_tool_parser.py); [structural_tag_registry.py](https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/structural_tag_registry.py)). The vLLM docs warn that in `auto` mode without structural tags, arguments "may occasionally be malformed or violate the function's parameter schema" ([vLLM tool calling](https://docs.vllm.ai/en/latest/features/tool_calling.html)).
- **Failures under concurrency (open, reported on NVIDIA hardware):**
  - [#50889](https://github.com/vllm-project/vllm/issues/50889): "intermittent… under concurrent agentic load", `finish_reason=tool_calls` with an empty `tool_calls` array (0.26.0).
  - [#39392](https://github.com/vllm-project/vllm/issues/39392): `<pad>`-only outputs for concurrent tool calls. A maintainer could not reproduce it and calls it GPU-specific. The reporter hit it on Ampere cards.
- **Format leaks:**
  - [#49955](https://github.com/vllm-project/vllm/issues/49955) (open): a trailing `<turn|>` appears since 0.26.0.
  - [#42110](https://github.com/vllm-project/vllm/issues/42110) (open): `json_schema` plus JSON instructions in the prompt can loop on whitespace. Mitigate with `disable_any_whitespace` (needs an explicit `xgrammar` or `guidance` backend, per [structured_outputs.py](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/config/structured_outputs.py)) and always set `max_tokens`.

### 2.4 Qwen and the Evolus "hermes" hint
- Evolus says "`--tool-call-parser hermes` fits Qwen models. Other model families need a different parser: check the vLLM documentation for your model." Its example model is `Qwen/Qwen2.5-7B-Instruct` ([Evolus developers](https://evolus.ai/en/developers)). So `gemma4` is acceptable to Evolus.
- `hermes` covers Qwen2.5 and QwQ ([vLLM tool calling](https://docs.vllm.ai/en/latest/features/tool_calling.html)). **Qwen3.6 uses `qwen3_coder`, not `hermes`** ([Qwen3.6-27B card](https://huggingface.co/Qwen/Qwen3.6-27B); [recipe](https://github.com/vllm-project/recipes/blob/main/models/Qwen/Qwen3.6-27B.yaml)).
- The `qwen3_coder` "silently ignores `required`/named" bug [#54808](https://github.com/vllm-project/vllm/issues/54808) was closed as completed on 29 Sep 2026.

### 2.5 Day-1 acceptance test (decides single model or two models)
Run this against our endpoint, not Token Factory, because the serving stack differs **[INF]**:
1. 50 single-turn prompts using the real Evolus/engine tool schemas, `tool_choice="auto"`, at concurrency 1 and 16. **Pass:**
   - ≥ 98% return non-empty `tool_calls` whose arguments parse and validate against the schema;
   - zero `finish_reason="tool_calls"` with empty `tool_calls`;
   - no `<|channel>`, `<turn|>` or `<pad>` in `content`.
2. 10 multi-turn loops (call, tool result, final answer). All must complete.
3. If issue 05 finds that Evolus sends `tool_choice="required"` or named tools, Gemma is expected to fail (§2.3). In that case choose the two-model setup.
4. Arena: 100 concurrent `response_format: json_schema` calls with `max_tokens` set. **Pass:** 100% valid JSON. Record p50/p95 latency.

The pass thresholds are my proposal **[INF]**.

---

## 3. Which image: what AMD Developer Cloud ships, and what we should run

What the console offers (I could not log in to see the live list) **[UNVERIFIED for today's console]**:
- DigitalOcean's AMD docs (last updated 13 Jul 2026) describe the default Quick Start image, slug `digitaloceanai-rocmjupyter`: Ubuntu 24.04, `amdgpu-dkms 6.12.12`, ROCm 6.4.0 on the host and in Docker, JupyterLab 4.4.2. No vLLM is listed ([DO: recommended AMD setup](https://docs.digitalocean.com/products/amd/getting-started/recommended-amd-droplet-setup/)).
- Search results list DigitalOcean Marketplace 1-Click images "vLLM 0.23.0 (ROCm 7.2.4)" and "vLLM 0.27.1 / 0.28.0 + vLLM-Omni (ROCm 7.14)". The snippets say "the vLLM container carries ROCm 7.2.3, because upstream vLLM does not publish a ROCm 7.14 container image". Those catalog pages now return HTTP 404 ([example URL](https://docs.digitalocean.com/products/marketplace/catalog/vllm-0-28-0-vllm-omni-rocm-7-14/)) **[UNVERIFIED]**.
  - Any vLLM ≥ 0.19.1 includes the `gemma4` parser (§2.1).
  - I found no evidence that any droplet image pre-loads Gemma 4 weights.
- AMD's Hugging Face collection "AMD Developer Cloud One Click Models" does include `google/gemma-4-31B-it`, `gemma-4-26B-A4B-it`, `gemma-4-12B-it`, `gemma-4-E4B-it`, `gemma-4-E2B-it`, `Qwen3.6-27B` and `Qwen3.6-35B-A3B` ([HF collection](https://huggingface.co/collections/amd/amd-developer-cloud-one-click-models-6a5827d748ecab89b16ea3e3)). That flow provisions an **AMD AI Notebooks** session, not a droplet ([AMD: HF one-click](https://www.amd.com/en/developer/resources/technical-articles/2026/run-hugging-face-models.html), via the repo notes). Participant evidence shows the notebook stack ran vLLM 0.23.1 on an MI300X VF (repo `docs/research_notes/.../amd_tech_and_compute.md`).
- AMD's own May 2026 Dev Cloud guide picks "the official ROCm Software image", runs `docker pull vllm/vllm-openai-rocm:latest` with `--network=host`, and opens a port with `sudo ufw allow 8001` ([AMD: Hermes Agent on AMD Developer Cloud](https://www.amd.com/en/developer/resources/technical-articles/2026/deploying-hermes-agent-for-free-on-amd-developer-cloud-with-open.html)).

What to run, and why `vllm/vllm-openai-rocm:v0.31.0`:
- **It is proven on MI300X.** The vLLM recipe measured Qwen3.6-27B on "one MI300X with `vllm/vllm-openai-rocm:v0.31.0`" on 12 Oct 2026 ([Qwen3.6-27B recipe](https://github.com/vllm-project/recipes/blob/main/models/Qwen/Qwen3.6-27B.yaml)).
- **Size.** It is 11.5 GB compressed. AMD's `rocm/vllm:rocm10.1.0_…_vllm-0.29.0` is 31.3 GB ([Docker Hub vllm-openai-rocm](https://hub.docker.com/r/vllm/vllm-openai-rocm/tags); [Docker Hub rocm/vllm](https://hub.docker.com/r/rocm/vllm/tags)). The pull is paid GPU time.
- **Driver window.**
  - v0.31.0's base is `rocm/dev-ubuntu-22.04:7.2.3-complete` ([Dockerfile.rocm_base v0.31.0](https://github.com/vllm-project/vllm/blob/v0.31.0/docker/Dockerfile.rocm_base)).
  - The ROCm matrix lists amdgpu 6.4.x and 30.10/30.20/30.30 drivers as supporting 7.2.x user space ("up to a year apart") ([ROCm user/kernel matrix](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/user-kernel-space-compat-matrix.html)).
  - I found no matrix row for ROCm 10.x user space on these drivers, so the ROCm 10.1 image is the riskier pick **[INF]**.
- **Pin by digest.** Open PR [#58761](https://github.com/vllm-project/vllm/pull/58761) would "Make ROCm 10.0 the default image", so `latest` may change under us.

---

## 4. Memory and throughput on one MI300X

Hardware: 192 GB HBM3, 5.3 TB/s, 1,307.4 TFLOPS peak BF16 dense ([AMD MI300X](https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html)). The droplet has 20 vCPU, 240 GiB RAM, a 720 GiB boot disk, a 5 TiB scratch disk and 10 Gbps public bandwidth ([DO: Droplet features](https://docs.digitalocean.com/products/droplets/details/features/)).

### 4.1 Weights
| Model | Safetensors | Gated | License | Notes |
|---|---|---|---|---|
| google/gemma-4-31B-it | 62.5 GB (includes ~550M vision params) | No | Apache-2.0 | dense, 60 layers, 256K context; recipe BF16 `vram_minimum_gb: 75` |
| Qwen/Qwen3.6-27B | 55.6 GB | No | Apache-2.0 | dense hybrid: 16 gated-attention + 48 DeltaNet layers |
| Qwen/Qwen3.6-35B-A3B | 71.9 GB | No | Apache-2.0 | MoE, 3B active; BF16 `vram_minimum_gb: 84` |
| google/gemma-4-26B-A4B-it | 51.6 GB | No | Apache-2.0 | MoE, 4B active |

Sources: [HF API gemma-4-31B-it](https://huggingface.co/api/models/google/gemma-4-31B-it), [Qwen3.6-27B](https://huggingface.co/api/models/Qwen/Qwen3.6-27B), [Qwen3.6-35B-A3B](https://huggingface.co/api/models/Qwen/Qwen3.6-35B-A3B), [gemma-4-26B-A4B-it](https://huggingface.co/api/models/google/gemma-4-26B-A4B-it); [Gemma 31B recipe YAML](https://github.com/vllm-project/recipes/blob/main/models/Google/gemma-4-31B-it.yaml); [Qwen3.6-35B-A3B recipe YAML](https://github.com/vllm-project/recipes/blob/main/models/Qwen/Qwen3.6-35B-A3B.yaml); [Qwen3.6-27B card](https://huggingface.co/Qwen/Qwen3.6-27B).

### 4.2 KV cache per request for Gemma 4 31B **[EST]**
Inputs from [config.json](https://huggingface.co/google/gemma-4-31B-it/blob/main/config.json):
- 50 sliding-window layers: 16 KV heads, head_dim 256, window 1,024.
- 10 full-attention layers: 4 KV heads, head_dim 512, `attention_k_eq_v: true`.

vLLM's hybrid KV manager keeps sliding layers' KV only for "the most recent `sliding_window_size` tokens" ([hybrid KV design](https://github.com/vllm-project/vllm/blob/v0.31.0/docs/design/hybrid_kv_cache_manager.md)).

Per-token bytes in BF16:
- Sliding layers: 50 × 2 × 16 × 256 × 2 B ≈ 0.82 MB per token, capped at 1,024 tokens.
- Full layers: 10 × 2 × 4 × 512 × 2 B ≈ 0.08 MB per token. This is an upper bound; K=V may halve it.

| Context per request | KV (BF16) | KV (fp8) |
|---|---|---|
| 2k tokens | ≈ 1.0 GB | ≈ 0.5 GB |
| 8k tokens | ≈ 1.5 GB | ≈ 0.75 GB |
| 32k tokens | ≈ 3.5 GB | ≈ 1.75 GB |

Capacity in the single-model setup, at `--gpu-memory-utilization 0.90` (default 0.92 per [cache.py](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/config/cache.py)):
- Budget: 0.90 × ~192 GB ≈ 172 GB.
- Subtract ~61 GB of text-only weights and ~6–10 GB of activations and graphs. About **100 GB is left for KV**.
- That fits **~100 concurrent 2k-token requests**, or ~200 with `--kv-cache-dtype fp8`.
- `fp8_e4m3` KV is documented as supported on ROCm ([quantized KV cache](https://github.com/vllm-project/vllm/blob/v0.31.0/docs/features/quantization/quantized_kvcache.md)). Test its quality before relying on it.
- Check vLLM's startup log lines for the real KV-cache size and "maximum concurrency".

### 4.3 Throughput **[EST]**
No published Gemma 4 MI300X benchmark exists: I found none on AMD, vLLM recipes or InferenceX. The anchors are:
- **Measured comparable model.** Qwen3.6-27B BF16 on one MI300X with `vllm-openai-rocm:v0.31.0` does single-stream decode of **66/56/27/13 tok/s** with image defaults and **67/67/65/62 tok/s** with `VLLM_ROCM_USE_AITER=1 --attention-backend ROCM_AITER_FA`, at ~200/2k/12k/32k prompt tokens ([Qwen3.6-27B recipe](https://github.com/vllm-project/recipes/blob/main/models/Qwen/Qwen3.6-27B.yaml)).
- **Bandwidth bound.** Reading ~61 GB of weights per token at 5.3 TB/s caps single-stream decode near 86 tok/s.

Estimates for Gemma 4 31B on `TRITON_ATTN`:
- **Single stream: ~40–65 tok/s.**
- **Aggregate decode at 64–128 concurrent short requests: ~1,000–2,500 output tok/s.** Working: each decode step reads the weights once plus ≈0.8 GB of sliding-window KV per sequence. At 4 TB/s effective that is ~29 ms per step at B=64 and ~42 ms at B=128, an upper bound of ~2,200–3,000 tok/s, discounted for Triton attention.
- **Prefill: ~8,000 tok/s.** That assumes ~40% of peak BF16 at 61 GFLOP per token.
- **One Arena round of 100 calls** (1,500 input and 250 output tokens each): **~25–45 s**. Prefill is ~18 s, or ~6 s if a shared 1,000-token prefix hits vLLM's prefix cache. Decode is ~15–25 s.

Tuning levers, all from the [Gemma 4 recipe](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md) unless noted:
- Put the shared Arena context at the **start** of every prompt so prefix caching reuses it **[INF]**.
- Raise `--max-num-seqs` (the recipe's "max throughput" row is 256–512).
- `--kv-cache-dtype fp8`.
- MTP speculative decoding with `google/gemma-4-31B-it-assistant`. The recipe tuned it on NVIDIA and says to experiment on other hardware. It also has an open crash bug, [#48503](https://github.com/vllm-project/vllm/issues/48503). Leave it off until the baseline works.
- Measure with the recipe's `vllm bench serve --dataset-name random --random-input-len 1500 --random-output-len 250 --num-prompts 100`.

Startup time per fresh droplet **[EST]**:
- Image pull: 11.5 GB, ~2–5 min.
- Weights: 62.5 GB. At least 50 s at the 10 Gbps cap; ~2–6 min realistically, with Xet high-performance mode.
- Load, compile and graph capture: ~3–8 min.
- **Total ~10–20 min of paid time per session.**

vLLM's compile cache lives in `~/.cache/vllm/torch_compile_cache`. The docs say you can "copy the whole … directory… to save a great amount of compilation time" ([torch.compile design](https://github.com/vllm-project/vllm/blob/v0.31.0/docs/design/torch_compile.md)). So `scp` `/opt/llm/vllm-cache` off the droplet before destroying it, and restore it next session **[INF]**.

---

## 5. Two models on one 192 GB GPU: should we, and how

**Answer.** It fits, but don't do it by default. Its cost: Gemma's KV room drops from ~100 GB to ~32 GB, so Arena concurrency falls from ~100 to ~30 two-thousand-token requests (~60 with fp8 KV) **[EST]**, and there are two processes to babysit. Do it only if the §2.5 acceptance test fails.

The mechanism exists:
- `--gpu-memory-utilization` is "a per-instance limit… if you have two vLLM instances running on the same GPU, you can set the GPU memory utilization to 0.5 for each instance" ([cache.py v0.31.0](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/config/cache.py)).
- AMD notes the Gemma 4 lineup suits "orchestration of several models running on Instinct GPUs" ([AMD Day 0](https://www.amd.com/en/developer/resources/technical-articles/2026/day-0-support-for-gemma-4-on-amd-processors-and-gpus.html)).

Pair Gemma with **Qwen3.6-27B**, not Qwen3.6-35B-A3B:
- 62.5 + 55.6 GB of weights leaves room. 62.5 + 71.9 GB leaves only ~40 GB for both KV caches **[EST]**.
- Qwen3.6-27B has only 16 full-attention layers with 4 KV heads, so its KV is ~64 KB per token **[EST from the card's architecture]**.
- The recipe gives exact MI300X flags for it.

| Process | `--gpu-memory-utilization` | Weights | KV left **[EST]** |
|---|---|---|---|
| gemma (port 8001) | 0.50 | ~61 GB | ~30 GB |
| qwen (port 8002) | 0.42 | ~56 GB | ~20 GB (≈300k tokens) |

```bash
# Start gemma first with --gpu-memory-utilization 0.50; wait for "Application startup complete", then:
docker run -d --name qwen --restart unless-stopped \
  --network=host --ipc=host --shm-size 16G \
  --device=/dev/kfd --device=/dev/dri --group-add=video \
  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  --env-file /opt/llm/vllm.env -e VLLM_ROCM_USE_AITER=1 -e HF_XET_HIGH_PERFORMANCE=1 \
  -v /opt/llm/hf:/root/.cache/huggingface -v /opt/llm/vllm-cache:/root/.cache/vllm \
  "$IMG" \
    --model Qwen/Qwen3.6-27B --revision 6a9e13bd6fc8f0983b9b99948120bc37f49c13e9 \
    --served-model-name qwen3.6-27b --trust-remote-code \
    --host 127.0.0.1 --port 8002 --language-model-only \
    --attention-backend ROCM_AITER_FA \
    --max-model-len 32768 --gpu-memory-utilization 0.42 \
    --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 \
    --default-chat-template-kwargs '{"enable_thinking": false}'
```

Flag sources:
- AITER env var, backend, parsers and `--trust-remote-code`: the [Qwen3.6-27B recipe](https://github.com/vllm-project/recipes/blob/main/models/Qwen/Qwen3.6-27B.yaml).
- `--language-model-only`: the [Qwen3.6-27B card](https://huggingface.co/Qwen/Qwen3.6-27B).
- Thinking toggle: Qwen3.6 "operate[s] in thinking mode by default" (card). Disabling it is a latency choice for the Evolus agent **[INF]**.
- Start the processes one after the other, so the second one profiles memory after the first has claimed its share **[INF]**.

Caddy routing for two models (Evolus base URL `https://<host>/qwen/v1`; Arena `https://<host>/gemma/v1`):

```caddy
marginarena.duckdns.org {
    @gemma path /gemma/v1/chat/completions /gemma/v1/models
    handle @gemma {
        uri strip_prefix /gemma
        reverse_proxy 127.0.0.1:8001
    }
    @qwen path /qwen/v1/chat/completions /qwen/v1/models
    handle @qwen {
        uri strip_prefix /qwen
        reverse_proxy 127.0.0.1:8002
    }
    handle {
        respond 404
    }
}
```

([Caddy `handle_path`/`uri strip_prefix`](https://caddyserver.com/docs/caddyfile/directives/handle_path))

---

## 6. Exposing the endpoint securely

Facts:
- **`--api-key` is not enough on its own.** It authenticates only `/v1`, `/v2`, `/inference` and `/cohere`. These stay **unauthenticated**:
  - `/invocations` ("the same inference capabilities as the protected `/v1` endpoints");
  - `/pause` and `/abort_requests` (denial of service);
  - `/update_weights`, `/tokenize`, `/health`, `/load` and more.

  vLLM recommends a reverse proxy that "explicitly allowlists only the endpoints you want to expose". It also warns that `torch.distributed`'s TCPStore "listens on all network interfaces" ([vLLM security](https://docs.vllm.ai/en/latest/usage/security.html); [v0.31.0 source](https://github.com/vllm-project/vllm/blob/v0.31.0/docs/usage/security.md)).
- `--api-key` accepts a list of keys. Set it with the `VLLM_API_KEY` environment variable ([cli_args.py v0.31.0](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/entrypoints/launchers/cli_args.py); [vLLM security](https://docs.vllm.ai/en/latest/usage/security.html)). Request-size abuse can be capped with `VLLM_MAX_N_SEQUENCES` (same docs).
- **Docker and UFW.** When you *publish* container ports (`-p`), "traffic… gets diverted before it goes through the ufw firewall settings" ([Docker docs](https://docs.docker.com/engine/network/packet-filtering-firewalls/)). Our setup uses `--network=host` and binds vLLM to `127.0.0.1`, so nothing is published **[INF]**.
- **What's open by default.** AMD's guide runs `sudo ufw allow 8001`, which implies UFW is active on the ROCm image ([AMD Hermes guide](https://www.amd.com/en/developer/resources/technical-articles/2026/deploying-hermes-agent-for-free-on-amd-developer-cloud-with-open.html)). A lablab tutorial says the droplet "blocks all ports except 22, 80, and 443" by default (via repo notes, **[UNVERIFIED]**). AMD's 2025 guide says Quick Start images launch Jupyter at `http://<public-IP>`, which is port 80 (via repo notes, **[UNVERIFIED]**).
- **DigitalOcean Cloud Firewalls** are free and "block all traffic that isn't expressly permitted by a rule". They filter "at the network layer before that traffic reaches your resources", so Docker can't bypass them ([DO Cloud Firewalls](https://docs.digitalocean.com/products/networking/firewalls/); [limits](https://docs.digitalocean.com/products/networking/firewalls/details/limits/)). Whether the AMD Developer Cloud console exposes them is **[UNVERIFIED]**; it runs on the same DO platform.
- **Evolus.** Evolus accepts `http://<droplet-ip>:8000/v1` and an API key, and warns: "Without `--api-key`, the vLLM endpoint is open to anyone who knows its address" ([Evolus developers](https://evolus.ai/en/developers)). It does not require HTTPS, but plain HTTP sends the key in cleartext **[INF]**.

Steps:
1. Run vLLM with `--host 127.0.0.1` and `VLLM_API_KEY` (§1.1). Never set `VLLM_SERVER_DEV_MODE=1` (vLLM security).
2. Put Caddy in front with a path allowlist: `/v1/chat/completions` and `/v1/models`. Add `/v1/responses` only if issue 05 shows Evolus needs it. Caddy flushes `text/event-stream` immediately, so streaming works ([Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)).
3. Firewall: allow inbound 22 (ideally only from your IP), 80 (ACME challenge and redirect) and 443. Allow nothing else: not 8000–8002, not Jupyter. Use a DO Cloud Firewall if the console has one, and `ufw` either way.
4. Get a DNS name for HTTPS:
   - **DuckDNS (free).** You sign in on duckdns.org yourself. `duckdns.org` is on the Public Suffix List, so each subdomain gets its own Let's Encrypt rate-limit bucket ([PSL](https://publicsuffix.org/list/public_suffix_list.dat); [LE rate limits](https://letsencrypt.org/docs/rate-limits/)). Update the record after each rebuild with `curl "https://www.duckdns.org/update?domains=<sub>&token=<token>&ip=<droplet-ip>"` ([DuckDNS spec](https://www.duckdns.org/spec.jsp)).
   - **A domain you already own**, with an A record.
   - **Avoid sslip.io and nip.io.** They are not on the PSL, so all their users share one rate-limit bucket.
   - **Avoid IP-address certificates.** Caddy serves IPs with self-signed certificates by default ([Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)). Public IP certificates exist only under LE's 6-day `shortlived` profile ([LE profiles](https://letsencrypt.org/docs/profiles/)).
5. Stable address across rebuilds (optional): a DO Reserved IP is free while assigned and $0.01/hr while unassigned ([DO Reserved IP pricing](https://docs.digitalocean.com/products/networking/reserved-ips/details/pricing/)). Whether it can attach to AMD GPU droplets is **[UNVERIFIED]**. DuckDNS updates are simpler.
6. After the event, rotate the key and destroy the droplet.

HTTPS options compared:
| Option | Verdict | Why |
|---|---|---|
| Caddy + DuckDNS or own domain | **Use** | Automatic Let's Encrypt; path allowlist; SSE flush |
| Named Cloudflare Tunnel | OK if you have a Cloudflare account and domain | Stable hostname; no inbound ports needed. It's a user-account action. |
| Cloudflare Quick Tunnel (`trycloudflare.com`) | **Don't** | "no uptime guarantee", "up to 200 in-flight requests", "do not support Server-Sent Events", and the "hostname changes each time" ([Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)) |
| Plain HTTP `:8000` | Last resort only | Evolus accepts it, but the key travels in cleartext and vLLM's unauthenticated paths are exposed |

---

## 7. Keeping credit burn low

Verified billing facts:
- **Price.** MI300X is **$2.59/hr**; 8× is $20.72/hr ([DO: AMD GPU pricing](https://docs.digitalocean.com/products/amd/details/pricing/); [DO Droplet pricing](https://docs.digitalocean.com/products/droplets/details/pricing/)). The older $1.99 lablab figure is stale. There is no MI300X spot tier; spot covers only MI350X/MI355X (DO Droplet pricing).
- **Billing.** Per second, with a 60 s or $0.01 minimum. "Powering off a GPU Droplet does not stop billing. To end billing, destroy the GPU Droplet" (DO Droplet pricing). AMD says the same: "If a GPU Instance is powered off, you are still billed" ([AMD Developer Cloud FAQ](https://www.amd.com/en/developer/resources/cloud-access/amd-developer-cloud.html)).
- **Credit rules.**
  - The credit "applies only to use on AMD Instinct MI300X GPUs". It does not cover volumes, object storage or backups.
  - It expires "thirty (30) days from the date of deposit".
  - When it runs out, a card on file is charged automatically. Without a card, "your AMD GPU VM will be destroyed" (AMD FAQ).
  - A valid payment method is required. Credits are for "testing or development" only ([DO: AMD credits](https://docs.digitalocean.com/products/amd/details/credits/)).
- **Snapshots.**
  - $0.06 per GB-month, a "full disk image" (not incremental) ([DO snapshot pricing](https://docs.digitalocean.com/products/snapshots/details/pricing/); [limits](https://docs.digitalocean.com/products/snapshots/details/limits/)).
  - GPU snapshots include the boot disk but **not the scratch disk**. Creation time grows with data size. Power-off is recommended first, and the droplet keeps billing while off ([DO: snapshot Droplets](https://docs.digitalocean.com/products/snapshots/how-to/snapshot-droplets/); [DO: scratch disk](https://docs.digitalocean.com/products/amd/how-to/use-scratch-disk/)).
  - DigitalOcean publishes no restore time **[UNVERIFIED]**. Whether snapshots count against the credit is not stated; AMD's exclusion list doesn't name them. Assume they bill to the card.
- **Limits.** GPU droplets cannot be resized ([DO: AMD limits](https://docs.digitalocean.com/products/amd/details/limits/)). Outbound transfer over the allowance is $0.01/GiB, and the allowance is 15,000 GiB per MI300X droplet (DO pricing; features).

**Snapshot or scripted rebuild?** Use a scripted rebuild **[INF]**.
- A snapshot holding ~100 GB (image plus weights) costs ~$6/month (~$0.20/day) on the card. Taking it costs GPU minutes while the droplet is powered off, and its restore time is unknown.
- What it saves is only the downloads, ~5–10 min per session (≈ $0.22–0.43).
- Rebuilding from §1.1 is reproducible, pinned and secret-free. Save only the small vLLM compile cache off-box (§4.3).
- If you snapshot anyway, delete `/opt/llm/*.env` first, and time one restore before relying on it.

**Hours budget (38.6 h = $100).** Develop prompts and tool schemas for free against Token Factory's `Gemma-4-31B-IT`, the same model (`docs/api-guide/tokenfactory-guide.md`). Use the GPU only for these sessions **[INF]**:

| Session (ICT) | Purpose | Hours | Cost |
|---|---|---|---|
| Thu 15 Oct | Bring-up, §2.5 acceptance test, `vllm bench serve`, choose one or two models | 3 | $7.77 |
| Fri 16 Oct | Evolus end-to-end, Arena tuning | 5 | $12.95 |
| Sat 17 Oct | Record video with the live endpoint and AMD metrics | 4 | $10.36 |
| Sun 18 Oct 07:00–22:00 | Up through the 17:00 ICT schedule deadline, the 19:00–21:00 ICT pitches and the 22:00 ICT platform deadline | 15 | $38.85 |
| Reserve | Overruns and any judging window organizers announce | 11.5 | $29.79 |
| **Total** | | **38.5** | **$99.72** |

Deadlines and pitch times are from the repo's `docs/research_notes/.../official_event_details.md`.

**Judging-window problem.** The repo notes quote Evolus at kickoff: "Your workspace is free until November 15th, so the judges can try your demo" ([kickoff, 10:34](https://www.youtube.com/watch?v=gqUj24Gtdr0&t=634s), via repo notes, **[UNVERIFIED]**). One always-on day costs $62.16, so the credit cannot keep the endpoint up for weeks. Options for the user to choose:
- (a) Ask organizers on Discord when Evolus and AMD judges actually test, and keep the endpoint up only then from the reserve.
- (b) Accept card charges for extra days.
- (c) Document in the README how to wake the endpoint, and show it working in the video.

Swapping the Evolus agent to a hosted API would break the track rule (§8).

---

## 8. Risks and fallbacks

| Risk | Mitigation | Fallback |
|---|---|---|
| Gemma 4 tool-call failures: unenforced `required`/named, empty `tool_calls`, leaks (§2.3) | Acceptance test (§2.5). Use `tool_choice:"auto"`. Always set `--reasoning-parser gemma4`. Retry client-side when `tool_calls` is empty. | Two-model setup (§5): Qwen3.6-27B with grammar-enforced `qwen3_coder` for the Evolus agent |
| JSON whitespace loop with `json_schema` ([#42110](https://github.com/vllm-project/vllm/issues/42110)) | `disable_any_whitespace` with the `xgrammar` backend; always set `max_tokens` | Use `json_object` mode and validate client-side |
| Trailing `<turn|>` ([#49955](https://github.com/vllm-project/vllm/issues/49955)) | Strip it client-side; check whether v0.31.0 still shows it | none |
| Chat-template path error ([#47600](https://github.com/vllm-project/vllm/issues/47600)) | Mount the v0.31.0 template and pass an absolute path | none |
| Host driver vs container ROCm mismatch | v0.31.0 image (ROCm 7.2.3); check `amd-smi version` first (§3) | Older `vllm/vllm-openai-rocm` tag, or the console's vLLM 1-click image (any vLLM ≥ 0.19.1 has `gemma4`) |
| `latest` tag drifts to ROCm 10 ([#58761](https://github.com/vllm-project/vllm/pull/58761)) | Pin by digest | none |
| No MI300X capacity in ATL1, the only region ([DO availability](https://docs.digitalocean.com/products/amd/details/availability/)) | Create Sunday's droplet early (06:00–07:00 ICT) **[INF]** | Token Factory for the app; see the Evolus caveat below |
| Credit exhausted or expired, so the droplet is destroyed (AMD FAQ) | Hours plan (§7); DO spend alert; destroy after every session | Card on file, at the user's discretion |
| Key leak or abuse of an open endpoint | Caddy allowlist; vLLM on loopback; firewall; rotate the key afterwards | none |
| Throughput below Arena needs | Prefix-cache layout, `--max-num-seqs`, fp8 KV, smaller Arena | Try `google/gemma-4-26B-A4B-it` (4B active, "runs almost as fast as a 4B-parameter model" per the [card](https://huggingface.co/google/gemma-4-31B-it)). Its tuned ROCm MoE configs are still an open PR ([#60504](https://github.com/vllm-project/vllm/pull/60504)), so benchmark it first. |

**Token Factory as a fallback** (from repo `docs/api-guide/tokenfactory-guide.md`):
- **What it offers.**
  - Base URL `https://developer.amd.com.cn/radeon/api/v1`, OpenAI-compatible.
  - It serves **`Gemma-4-31B-IT` (experimental)** with `tools`/`tool_choice` and `response_format: json_object`, on AMD GPUs.
  - It suits dev work and is an AMD-hosted fallback for the app and Arena.
- **Limits.**
  - 30 RPM per team key and 20 RPM per account.
  - **8 concurrent requests**, plus a daily spend cap.
  - "no SLA"; "Trial and development only".
  - Fields like `stop`, `seed` and `top_k` are silently dropped.
  - A 100-call Arena round would take ≥ 3.3 min there, so shrink the Arena in fallback mode **[INF]**.
- **What it does not satisfy.** It is **not** "your own vLLM endpoint on AMD Developer Cloud" ([lablab ACT III](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii); [Evolus developers](https://evolus.ai/en/developers)). Pointing the Evolus main agent at it would fail that track rule **[INF]**. Its terms also forbid proxying or re-badging the API (same guide).

---

## 9. Still open (needs a login, a measurement or issue 05)
1. Which images and vLLM versions the AMD Developer Cloud console offers today. Check on first create: the image list, then `docker images` and `amd-smi version` on the droplet.
2. Real numbers: startup time, KV capacity, tool-call pass rate and Arena latency. Measure in Thu's session and record them for the README and video.
3. Does Evolus use `tool_choice:"required"`/named, streaming or `/v1/responses` against our model? (issue 05) This decides the Gemma-only vs two-model setup and the Caddy allowlist.
4. Do snapshots and Reserved IPs work on AMD GPU droplets, and do they count against the credit?
5. When do Evolus and AMD judges test live endpoints? Ask organizers.
6. An unexplored zero-credit idea: run vLLM inside an AMD AI Notebooks session (the "One Click" route) and tunnel it out. Session limits, terms and inbound reachability are all unknown **[UNVERIFIED]**.
