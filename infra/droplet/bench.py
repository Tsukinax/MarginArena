"""Benchmark Gemma-4-31B-IT on our MI300X droplet with vLLM's own `vllm bench serve`.

The benchmark runs inside the vLLM container on the droplet, against 127.0.0.1, so the laptop's network is not
measured. Each level sends short chat requests shaped like an Arena call (a 512-token prompt, a 128-token answer) at
a fixed number in flight. Standard library only, like kit.py. Run after `kit.py provision` and `kit.py check`:

    python3 infra/droplet/bench.py

Writes evidence/mi300x-benchmark.json (every number vLLM reported) and evidence/mi300x-benchmark.md (the report).
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import kit

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence"
LEVELS = (1, 8, 32, 64, 128)
INPUT_LEN, OUTPUT_LEN = 512, 128
FIELDS = (
    "completed",
    "duration",
    "request_throughput",
    "output_throughput",
    "total_token_throughput",
    "median_ttft_ms",
    "p99_ttft_ms",
    "median_tpot_ms",
    "p99_tpot_ms",
    "median_e2el_ms",
)


def on_droplet(ssh: list[str], script: str) -> str:
    """Runs a shell script inside the vLLM container and returns its standard output."""
    command = f"docker exec gemma sh -c {shlex.quote(script)}"
    result = subprocess.run([*ssh, command], capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        sys.exit(f"The droplet answered {result.returncode}: {result.stderr.strip()[-800:]}")
    return result.stdout


def level(ssh: list[str], model: str, concurrency: int) -> dict:
    prompts = max(16, concurrency * 4)
    out = f"/tmp/bench/c{concurrency}.json"
    script = (
        "mkdir -p /tmp/bench && OPENAI_API_KEY=\"$VLLM_API_KEY\" vllm bench serve --backend openai-chat "
        f"--base-url http://127.0.0.1:8000 --endpoint /v1/chat/completions --model {model} "
        f"--dataset-name random --random-input-len {INPUT_LEN} --random-output-len {OUTPUT_LEN} --ignore-eos "
        f"--num-prompts {prompts} --max-concurrency {concurrency} "
        f"--save-result --result-dir /tmp/bench --result-filename c{concurrency}.json "
        f"> /tmp/bench/c{concurrency}.log 2>&1; cat {out}"
    )
    result = json.loads(on_droplet(ssh, script))
    print(f"concurrency {concurrency}: {result.get('output_throughput', 0):.0f} output tokens/s", flush=True)
    return {"concurrency": concurrency, "prompts": prompts, **{k: result.get(k) for k in FIELDS}}


def report(record: dict) -> str:
    lines = [
        "# Evidence: Gemma-4-31B-IT on our own AMD Instinct MI300X (vLLM on ROCm)",
        "",
        "Reproduce: `python3 infra/droplet/kit.py provision <IP>`, `kit.py check`, then "
        "`python3 infra/droplet/bench.py`, which writes this file and `mi300x-benchmark.json`.",
        "",
        f"- **Measured:** {record['measured_at']} on one AMD Instinct MI300X droplet (AMD Developer Cloud), "
        f"image `{record['image']}`, model `{record['model']}` at revision `{record['revision'][:12]}`.",
        f"- **Load:** vLLM's `vllm bench serve` inside the container against 127.0.0.1, random prompts of "
        f"{INPUT_LEN} tokens and answers of exactly {OUTPUT_LEN} tokens (about one Arena call), at each number of "
        "requests in flight.",
        "",
        "| In flight | Requests | Requests/s | Output tokens/s | Total tokens/s | Median TTFT | p99 TTFT | "
        "Median time per output token | Median request time |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in record["levels"]:
        lines.append(
            f"| {r['concurrency']} | {r['completed']} | {r['request_throughput']:.2f} | "
            f"{r['output_throughput']:.0f} | {r['total_token_throughput']:.0f} | {r['median_ttft_ms']:.0f} ms | "
            f"{r['p99_ttft_ms']:.0f} ms | {r['median_tpot_ms']:.1f} ms | {r['median_e2el_ms'] / 1000:.2f} s |"
        )
    lines += ["", "## Environment, as the droplet reported it", "", "```", record["environment"].strip(), "```", ""]
    return "\n".join(lines)


def main() -> None:
    env = kit.read_env(ROOT / ".env")
    ip = kit.ip_from_url(env.get("VLLM_BASE_URL", ""))
    ssh = kit.ssh_command(ip, Path.home() / ".ssh" / "marginarena_droplet_ed25519")
    pins = kit.pinned_versions()
    environment = on_droplet(ssh, "vllm --version 2>/dev/null; amd-smi static --asic 2>/dev/null | head -25")
    levels = [level(ssh, pins["GEMMA_MODEL"], c) for c in LEVELS]
    record = {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "image": pins["VLLM_IMAGE"],
        "model": pins["GEMMA_MODEL"],
        "revision": pins["GEMMA_REVISION"],
        "environment": environment,
        "levels": levels,
    }
    (EVIDENCE / "mi300x-benchmark.json").write_text(json.dumps(record, indent=1) + "\n")
    (EVIDENCE / "mi300x-benchmark.md").write_text(report(record))
    print("wrote evidence/mi300x-benchmark.md and .json", flush=True)


if __name__ == "__main__":
    main()
