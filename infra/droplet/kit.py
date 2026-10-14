#!/usr/bin/env python3
"""MarginArena GPU droplet kit: Gemma-4-31B-IT on an AMD Developer Cloud MI300X (stdlib only).

Run from the repo root:
  python3 infra/droplet/kit.py prepare        make the SSH key and API key, render the startup script
  python3 infra/droplet/kit.py copy WHAT      put ssh-key, user-data or api-key on the clipboard
  python3 infra/droplet/kit.py provision IP   set the droplet up over SSH, write VLLM_BASE_URL to .env
  python3 infra/droplet/kit.py check          HTTPS, auth, blocked paths, open ports, one streamed chat
  python3 infra/droplet/kit.py gate           ticket 08 tool-calling test; writes evidence/gate-*.md/.json
  python3 infra/droplet/kit.py ssh [-- CMD]   a shell (or one command) on the droplet
  python3 infra/droplet/kit.py forget         blank VLLM_BASE_URL once the droplet is destroyed

Guide for creating and destroying the droplet: infra/droplet/README.md.
Why each choice: .scratch/marginarena/research/model-serving-mi300x.md.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import ipaddress
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import gate

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BOOTSTRAP = HERE / "bootstrap.sh"
USER_DATA = HERE / ".generated" / "user-data.sh"
EVIDENCE = REPO / "evidence"
DEFAULT_ENV = REPO / ".env"
DEFAULT_KEY = Path.home() / ".ssh" / "marginarena_droplet_ed25519"
DEFAULT_DOMAIN = "sslip.io"
API_KEY_PATTERN = re.compile(r"[A-Za-z0-9_-]{32,}")  # bootstrap.sh checks the same rule
REMOTE_DIR = "/opt/llm"
USER_DATA_EOF = "MARGINARENA_BOOTSTRAP_EOF"
# vLLM paths that must not be reachable from outside, including the ones --api-key leaves open
# (vLLM security docs). Probed with GET: if one were forwarded, vLLM would answer 200 or 405, not 404.
PATHS_BLOCKED = (
    "/",
    "/health",
    "/ping",
    "/version",
    "/load",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/invocations",
    "/pause",
    "/is_paused",
    "/abort_requests",
    "/update_weights",
    "/tokenize",
    "/v1/completions",
    "/v1/responses",
    "/v1/embeddings",
    "/v1/messages",
    "/v1/chat/completions/batch",
    "/v1/models/../../pause",
    "/qwen/health",
)
PORTS_OPEN = (22, 80, 443)
PORTS_CLOSED = (2019, 8000, 8001, 8002, 8888)  # Caddy admin, vLLM, Jupyter


# ---------------------------------------------------------------- .env


def read_env(path: Path) -> dict[str, str]:
    """KEY=value pairs from a .env file; comments and blank lines are skipped."""
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("'\"")
    return values


def set_env_value(path: Path, key: str, value: str) -> None:
    """Replace the KEY= line (or append one). Every other line stays as it was; the file stays private."""
    lines = path.read_text().splitlines() if path.exists() else []
    out: list[str] = []
    written = False
    for line in lines:
        if not line.lstrip().startswith("#") and line.split("=", 1)[0].strip() == key:
            if not written:
                out.append(f"{key}={value}")
                written = True
            continue  # drop duplicate KEY= lines
        out.append(line)
    if not written:
        out.append(f"{key}={value}")
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, path)


def require_api_key(env_file: Path) -> str:
    key = read_env(env_file).get("VLLM_API_KEY", "")
    if not key:
        sys.exit(f"VLLM_API_KEY is empty in {env_file}. Run: python3 infra/droplet/kit.py prepare")
    if not API_KEY_PATTERN.fullmatch(key):
        sys.exit(f"VLLM_API_KEY in {env_file} must be 32+ letters, digits, - or _. Blank it and run prepare.")
    return key


# ---------------------------------------------------------------- hostnames


def public_ipv4(text: str) -> str:
    """The droplet's public IPv4 address, checked.

    >>> public_ipv4(" 164.92.10.5 ")
    '164.92.10.5'
    """
    try:
        ip = ipaddress.IPv4Address(text.strip())
    except ValueError:
        raise ValueError(f"{text!r} is not an IPv4 address like 164.92.10.5") from None
    if not ip.is_global:
        raise ValueError(f"{ip} is a private address; use the droplet's public IPv4 address")
    return str(ip)


def sslip_host(ip: str, domain: str = DEFAULT_DOMAIN) -> str:
    """The HTTPS hostname that sslip.io resolves back to the droplet's IP.

    >>> sslip_host("164.92.10.5")
    '164-92-10-5.sslip.io'
    """
    return f"{public_ipv4(ip).replace('.', '-')}.{domain}"


def ip_from_url(url: str) -> str:
    """The droplet IP inside an sslip.io (or nip.io) URL.

    >>> ip_from_url("https://164-92-10-5.sslip.io/v1")
    '164.92.10.5'
    """
    host = urllib.parse.urlparse(url).hostname or ""
    return public_ipv4(host.split(".")[0].replace("-", "."))


# ---------------------------------------------------------------- startup script


def render_user_data(api_key: str, bootstrap: str) -> str:
    """The optional startup script (DigitalOcean user data): writes the key and bootstrap.sh, then runs it."""
    if USER_DATA_EOF in bootstrap:
        raise ValueError(f"bootstrap.sh must not contain {USER_DATA_EOF}")
    if not API_KEY_PATTERN.fullmatch(api_key):
        raise ValueError("the API key must be 32+ letters, digits, - or _")
    body = bootstrap.rstrip("\n")
    return (
        "#!/bin/bash\n"
        "# MarginArena droplet startup script, made by `python3 infra/droplet/kit.py prepare`.\n"
        "# It holds the vLLM API key: paste it only into the droplet's startup-script box.\n"
        "# Log on the droplet: /var/log/cloud-init-output.log\n"
        "set -euo pipefail\n"
        "umask 077\n"
        f"mkdir -p {REMOTE_DIR}\n"
        f"printf 'VLLM_API_KEY=%s\\n' '{api_key}' > {REMOTE_DIR}/vllm.env\n"
        f"cat > {REMOTE_DIR}/bootstrap.sh <<'{USER_DATA_EOF}'\n"
        f"{body}\n"
        f"{USER_DATA_EOF}\n"
        f"bash {REMOTE_DIR}/bootstrap.sh\n"
    )


# ---------------------------------------------------------------- SSH


def ssh_command(ip: str, key: Path, user: str = "root") -> list[str]:
    """ssh with the kit's own key and known_hosts file, never prompting."""
    options = {
        "IdentitiesOnly": "yes",
        "BatchMode": "yes",  # fail instead of prompting
        "UserKnownHostsFile": key.with_name("marginarena_known_hosts"),
        "StrictHostKeyChecking": "accept-new",  # trust a new droplet on first contact, then pin it
        "ConnectTimeout": "10",
        "ServerAliveInterval": "30",
        "ServerAliveCountMax": "10",
    }
    return ["ssh", "-i", str(key), *[arg for k, v in options.items() for arg in ("-o", f"{k}={v}")], f"{user}@{ip}"]


def forget_host_key(ip: str, key: Path) -> None:
    """Forget the pinned host key for an IP. Only on request (--reset-host-key), after the user confirms a
    NEW droplet reuses that IP: a changed key must otherwise stop the connection (security review)."""
    known_hosts = key.with_name("marginarena_known_hosts")
    if known_hosts.exists():
        subprocess.run(["ssh-keygen", "-R", ip, "-f", str(known_hosts)], capture_output=True)


def wait_for_ssh(ssh: list[str], minutes: int = 10) -> None:
    deadline = time.monotonic() + minutes * 60
    while True:
        result = subprocess.run([*ssh, "true"], capture_output=True, text=True)
        if result.returncode == 0:
            return
        error = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "no answer"
        if "REMOTE HOST IDENTIFICATION HAS CHANGED" in result.stderr or "Host key verification failed" in error:
            sys.exit(
                "This address answered with a different SSH host key than last time. If you just created a NEW "
                "droplet that reuses this IP (check the droplet list in AMD Developer Cloud), run provision again "
                "with --reset-host-key. Otherwise stop: something may be intercepting the connection."
            )
        if "Permission denied" in error:
            sys.exit(
                "The droplet refused the MarginArena SSH key: it was created without the `marginarena-droplet` "
                "key ticked. Destroy it and create it again (infra/droplet/README.md, 'Create the droplet', step 6)."
            )
        if time.monotonic() > deadline:
            sys.exit(f"SSH to the droplet did not work for {minutes} min: {error}")
        print(f"  waiting for SSH ({error})")
        time.sleep(10)


def upload(ssh: list[str], remote_path: str, content: str) -> None:
    """Write a file on the droplet, readable by root only. The content travels over stdin, never in argv."""
    command = f"umask 077 && mkdir -p {REMOTE_DIR} && cat > {remote_path}.tmp && mv {remote_path}.tmp {remote_path}"
    subprocess.run([*ssh, command], input=content.encode(), check=True)


def droplet_facts(ip: str, key: Path, container: str) -> dict[str, str]:
    """Versions as observed on the droplet, for the evidence report. Best effort: {} when SSH fails."""
    script = r"""
c=CONTAINER
echo "image=$(docker inspect --format '{{.Config.Image}}' $c 2>/dev/null)"
echo "args=$(docker inspect --format '{{json .Args}}' $c 2>/dev/null)"
echo "vllm=$(docker exec $c python3 -c 'import vllm; print(vllm.__version__)' 2>/dev/null)"
echo "rocm_in_container=$(docker exec $c cat /opt/rocm/.info/version 2>/dev/null)"
echo "gpu=$(amd-smi static 2>/dev/null | grep -m1 MARKET_NAME | cut -d: -f2- | xargs)"
echo "host_driver=$(amd-smi version 2>/dev/null | head -n 1)"
echo "kv_cache=$(docker logs $c 2>&1 | grep -i 'GPU KV cache size' | tail -n 1 | sed 's/.*\] //')"
echo "max_concurrency=$(docker logs $c 2>&1 | grep -i 'Maximum concurrency' | tail -n 1 | sed 's/.*\] //')"
""".replace("CONTAINER", container)
    if not key.exists():
        return {}
    try:
        result = subprocess.run(
            [*ssh_command(ip, key), "bash -s"], input=script, capture_output=True, text=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        return {}
    if result.returncode != 0:
        return {}
    facts = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    return {k: v.strip() for k, v in facts.items() if v.strip()}


# ---------------------------------------------------------------- HTTP


def http_request(
    method: str, url: str, key: str | None = None, body: dict | None = None, timeout: float = 60
) -> tuple[int, bytes]:
    """One request. HTTP error statuses are returned, not raised; network and TLS errors raise."""
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if key is not None:
        request.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def stream_chat(base_url: str, key: str, model: str, prompt: str, max_tokens: int = 256) -> dict:
    """One streamed chat completion, timed: time to first token, total time, output tokens/s."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    start = time.monotonic()
    first = None
    text: list[str] = []
    usage: dict = {}
    with urllib.request.urlopen(request, timeout=180) as response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            usage = chunk.get("usage") or usage
            for choice in chunk.get("choices", []):
                delta = choice.get("delta") or {}
                piece = delta.get("content") or delta.get("reasoning") or delta.get("reasoning_content")
                if piece and first is None:
                    first = time.monotonic()
                text.append(delta.get("content") or "")
    end = time.monotonic()
    tokens = int(usage.get("completion_tokens") or 0)
    decode = end - (first or end)
    return {
        "text": "".join(text),
        "ttft_s": (first or end) - start,
        "total_s": end - start,
        "completion_tokens": tokens,
        "tokens_per_s": tokens / decode if decode > 0 else 0.0,
    }


def port_open(ip: str, port: int, timeout: float = 3) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------- commands


def cmd_prepare(args: argparse.Namespace) -> None:
    key, dry = args.ssh_key, args.dry_run
    pub = key.with_name(key.name + ".pub")
    if key.exists():
        print(f"SSH key: {key} (already there, kept)")
        if not pub.exists() and not dry:
            derived = subprocess.run(["ssh-keygen", "-y", "-f", str(key)], capture_output=True, text=True, check=True)
            pub.write_text(derived.stdout)
    elif dry:
        print(f"[dry run] would create the SSH key {key}")
    else:
        key.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "marginarena-droplet", "-f", str(key)], check=True
        )
        print(f"SSH key: {key} (created)")
    if pub.exists():
        print("Public key, for the droplet's SSH key box (`kit.py copy ssh-key` puts it on the clipboard):")
        print(f"  {pub.read_text().strip()}")

    api_key = read_env(args.env_file).get("VLLM_API_KEY", "")
    if api_key:
        require_api_key(args.env_file)
        print(f"VLLM_API_KEY: already set in {args.env_file} (kept, not shown)")
    elif dry:
        print(f"[dry run] would generate VLLM_API_KEY into {args.env_file}")
    else:
        api_key = secrets.token_hex(32)  # 256 bits
        set_env_value(args.env_file, "VLLM_API_KEY", api_key)
        print(f"VLLM_API_KEY: generated into {args.env_file} (not shown)")

    if dry:
        print(f"[dry run] would write the startup script to {args.user_data}")
        return
    args.user_data.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.user_data, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(render_user_data(api_key, BOOTSTRAP.read_text()))
    print(f"Startup script: {args.user_data} (holds the API key; gitignored).")
    print("  Optional: paste it under 'Show more options' > 'Startup scripts' when creating the droplet")
    print("  (`kit.py copy user-data` puts it on the clipboard). Without it, provision does the same over SSH.")
    print("Next: create the droplet (infra/droplet/README.md), then: python3 infra/droplet/kit.py provision <IP>")


def cmd_copy(args: argparse.Namespace) -> None:
    if args.what == "ssh-key":
        pub = args.ssh_key.with_name(args.ssh_key.name + ".pub")
        if not pub.exists():
            sys.exit("No SSH key yet. Run: python3 infra/droplet/kit.py prepare")
        text = pub.read_text().strip() + "\n"
    elif args.what == "user-data":
        if not args.user_data.exists():
            sys.exit("No startup script yet. Run: python3 infra/droplet/kit.py prepare")
        text = args.user_data.read_text()
    else:
        text = require_api_key(args.env_file)
    try:
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
    except FileNotFoundError:
        sys.exit("pbcopy (macOS) is not available here; open the file instead.")
    print(f"Copied the {args.what} to the clipboard. Paste it with Cmd+V.")


def cmd_provision(args: argparse.Namespace) -> None:
    try:
        ip = public_ipv4(args.ip)
    except ValueError as error:
        sys.exit(str(error))
    host = sslip_host(ip, args.domain)
    base_url = f"https://{host}/v1"
    ssh = ssh_command(ip, args.ssh_key, args.user)
    remote = f"bash {REMOTE_DIR}/bootstrap.sh --host {host}" + (" --with-qwen" if args.with_qwen else "")
    if args.dry_run:
        print(f"[dry run] droplet {ip}, HTTPS name {host}")
        print(f"[dry run] would write {REMOTE_DIR}/vllm.env and {REMOTE_DIR}/bootstrap.sh over: {' '.join(ssh)}")
        print(f"[dry run] would run: {remote}")
        print(f"[dry run] would set VLLM_BASE_URL={base_url} in {args.env_file}")
        return
    api_key = require_api_key(args.env_file)
    if not args.ssh_key.exists():
        sys.exit("No SSH key yet. Run: python3 infra/droplet/kit.py prepare")

    print(f"Connecting to root@{ip} ...")
    if args.reset_host_key:
        forget_host_key(ip, args.ssh_key)
    wait_for_ssh(ssh)
    upload(ssh, f"{REMOTE_DIR}/vllm.env", f"VLLM_API_KEY={api_key}\n")
    upload(ssh, f"{REMOTE_DIR}/bootstrap.sh", BOOTSTRAP.read_text())
    print("Running bootstrap.sh on the droplet (a fresh droplet takes about 15-25 min) ...")
    if subprocess.run([*ssh, remote]).returncode != 0:
        sys.exit(
            "bootstrap.sh failed; the reason is above. Fix it and run provision again (it is safe to rerun).\n"
            "Logs: python3 infra/droplet/kit.py ssh -- docker logs --tail 100 gemma"
        )
    set_env_value(args.env_file, "VLLM_BASE_URL", base_url)
    pins = pinned_versions()
    print(f"\nVLLM_BASE_URL={base_url}  (written to {args.env_file})")
    print("Evolus > Your models:")
    print(f"  Base URL  {base_url}")
    print(f"  Model     {pins['GEMMA_MODEL']}")
    print("  API key   the VLLM_API_KEY in .env (`kit.py copy api-key` puts it on the clipboard)")
    if args.with_qwen:
        print(f"Evolus agent on Qwen instead: base URL https://{host}/qwen/v1, model {pins['QWEN_MODEL']}")
    print("Next: python3 infra/droplet/kit.py check")


def endpoint(args: argparse.Namespace) -> tuple[str, str]:
    env = read_env(args.env_file)
    base_url = (args.base_url or env.get("VLLM_BASE_URL", "")).rstrip("/")
    if not base_url:
        sys.exit(f"VLLM_BASE_URL is empty in {args.env_file}. Run provision first, or pass --base-url.")
    return base_url, require_api_key(args.env_file)


def cmd_check(args: argparse.Namespace) -> None:
    base_url, key = endpoint(args)
    parsed = urllib.parse.urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    failed: list[str] = []

    def report(ok: bool, text: str) -> None:
        print(f"{'ok  ' if ok else 'FAIL'}  {text}")
        if not ok:
            failed.append(text)

    print(f"Checking {base_url}")
    try:
        resolved = sorted({info[4][0] for info in socket.getaddrinfo(parsed.hostname, 443, socket.AF_INET)})
    except OSError as error:
        sys.exit(f"FAIL  DNS: {parsed.hostname} does not resolve ({error})")
    try:
        ip = ip_from_url(base_url)
    except ValueError:  # not an sslip.io name: check the address it resolves to
        ip = resolved[0]
    report(resolved == [ip], f"DNS: {parsed.hostname} -> {', '.join(resolved)}")

    probes = PORTS_OPEN + PORTS_CLOSED
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(probes)) as pool:
        is_open = dict(zip(probes, pool.map(lambda port: port_open(ip, port), probes)))
    unreachable = [p for p in PORTS_OPEN if not is_open[p]]
    exposed = [p for p in PORTS_CLOSED if is_open[p]]
    report(not unreachable, f"ports {PORTS_OPEN} reachable" + (f"; NOT: {unreachable}" if unreachable else ""))
    report(not exposed, f"ports {PORTS_CLOSED} closed from outside" + (f"; OPEN: {exposed}" if exposed else ""))

    try:
        status, _ = http_request("GET", f"{base_url}/models")
    except urllib.error.URLError as error:
        report(False, f"HTTPS: {error.reason} (Caddy may still be getting its certificate; retry in a minute)")
        sys.exit(1)
    report(status == 401, f"HTTPS certificate valid; GET /models without a key -> {status} (want 401)")
    status, _ = http_request("GET", f"{base_url}/models", key="wrong" + "0" * 32)
    report(status == 401, f"GET /models with a wrong key -> {status} (want 401)")
    status, raw = http_request("GET", f"{base_url}/models", key=key)
    models = [m.get("id") for m in json.loads(raw).get("data", [])] if status == 200 else []
    report(status == 200 and bool(models), f"GET /models with the key -> {status}; serves {models}")

    answers = {path: http_request("GET", origin + path, key=key, timeout=15)[0] for path in PATHS_BLOCKED}
    open_paths = {path: code for path, code in answers.items() if code not in (403, 404)}
    suffix = f"; NOT blocked: {open_paths}" if open_paths else ""
    report(not open_paths, f"{len(answers)} other paths blocked, even with the key (/invocations, /pause, ...){suffix}")

    if models:
        model = args.model or models[0]
        try:
            chat = stream_chat(base_url, key, model, "Count from 1 to 60, separated by commas. Only the numbers.")
            clean = not any(token in chat["text"] for token in gate.LEAK_TOKENS)
            report(
                chat["completion_tokens"] > 0 and clean,
                f"streamed chat with {model}: first token after {chat['ttft_s']:.2f} s, "
                f"{chat['completion_tokens']} tokens in {chat['total_s']:.2f} s ({chat['tokens_per_s']:.1f} tokens/s)",
            )
            print(f"      answer: {chat['text'][:80]!r}")
        except (OSError, ValueError) as error:  # URLError is an OSError
            report(False, f"streamed chat: {error}")
    print("All checks passed." if not failed else f"{len(failed)} check(s) failed.")
    sys.exit(1 if failed else 0)


def cmd_gate(args: argparse.Namespace) -> None:
    base_url, key = endpoint(args)
    status, raw = http_request("GET", f"{base_url}/models", key=key)
    if status != 200:
        sys.exit(f"GET {base_url}/models answered {status}; run check first.")
    served = json.loads(raw)["data"]
    entry = next((m for m in served if m["id"] == args.model), served[0])
    model = entry["id"]
    family = re.sub(r"[^a-z0-9]+", "-", model.split("/")[-1].lower()).split("-")[0]
    container = "qwen" if "qwen" in model.lower() else "gemma"

    print(f"Gate: {model} at {base_url} (takes about 5 min)")
    started = datetime.now(timezone.utc)
    summary = gate.run(base_url, key, model, request=http_request, progress=print)
    try:
        facts = droplet_facts(ip_from_url(base_url), args.ssh_key, container)
    except ValueError:
        facts = {}
    summary["meta"] = {
        "date_utc": started.strftime("%Y-%m-%d %H:%M UTC"),
        "command": " ".join(["python3 infra/droplet/kit.py", *args.argv]),
        "endpoint": base_url,
        "served_model": {k: entry.get(k) for k in ("id", "root", "max_model_len")},
        "pinned": pinned_versions(),
        "observed_on_droplet": facts,
    }
    stem = args.out or EVIDENCE / f"gate-{family}-tool-calling"
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    stem.with_suffix(".md").write_text(gate.render_markdown(summary, json_name=stem.with_suffix(".json").name))
    print(f"\n{'PASS' if summary['passed'] else 'FAIL'}: wrote {stem.with_suffix('.md')} and .json")
    sys.exit(0 if summary["passed"] else 1)


def pinned_versions() -> dict[str, str]:
    """The pins bootstrap.sh deploys (its variables are the single source of truth)."""
    text = BOOTSTRAP.read_text()
    names = ("VLLM_IMAGE", "CADDY_IMAGE", "GEMMA_MODEL", "GEMMA_REVISION", "QWEN_MODEL", "QWEN_REVISION")
    return {n: m.group(1) for n in names if (m := re.search(rf"^{n}='([^']+)'", text, re.M))}


def cmd_ssh(args: argparse.Namespace) -> None:
    try:
        ip = public_ipv4(args.ip) if args.ip else ip_from_url(read_env(args.env_file).get("VLLM_BASE_URL", ""))
    except ValueError:
        sys.exit("No droplet IP: pass --ip, or run provision first so VLLM_BASE_URL is set.")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    ssh = ssh_command(ip, args.ssh_key, args.user)
    if not command:
        ssh.insert(1, "-t")
    os.execvp("ssh", [*ssh, *command])


def cmd_forget(args: argparse.Namespace) -> None:
    set_env_value(args.env_file, "VLLM_BASE_URL", "")
    print(f"VLLM_BASE_URL blanked in {args.env_file}: the app uses Token Factory until the next provision.")


# ---------------------------------------------------------------- CLI


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="kit.py",
        description="Bring up Gemma-4-31B-IT on an AMD Developer Cloud MI300X droplet and prove it works. "
        "Guide: infra/droplet/README.md",
    )
    p.add_argument("--env-file", type=Path, default=DEFAULT_ENV, help="the .env to use (default: the repo root's)")
    p.add_argument("--ssh-key", type=Path, default=DEFAULT_KEY, help=f"the kit's SSH key (default: {DEFAULT_KEY})")
    p.add_argument("--user-data", type=Path, default=USER_DATA, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("prepare", help="make the SSH key and API key; render the optional startup script")
    s.add_argument("--dry-run", action="store_true", help="say what would be created, change nothing")
    s.set_defaults(func=cmd_prepare)

    s = sub.add_parser("copy", help="put the public SSH key, the startup script or the API key on the clipboard")
    s.add_argument("what", choices=("ssh-key", "user-data", "api-key"))
    s.set_defaults(func=cmd_copy)

    s = sub.add_parser("provision", help="set the droplet up over SSH, then write VLLM_BASE_URL to .env")
    s.add_argument("ip", help="the droplet's public IPv4 address")
    s.add_argument("--with-qwen", action="store_true", help="also serve Qwen3.6-27B under /qwen/v1 (ticket 08)")
    s.add_argument(
        "--reset-host-key",
        action="store_true",
        help="forget this IP's pinned SSH host key; only after confirming a NEW droplet reuses the IP",
    )
    s.add_argument("--domain", default=DEFAULT_DOMAIN, help="sslip.io, or nip.io if Let's Encrypt limits sslip.io")
    s.add_argument("--user", default="root")
    s.add_argument("--dry-run", action="store_true", help="print the steps, connect to nothing")
    s.set_defaults(func=cmd_provision)

    base_url_help = "default: VLLM_BASE_URL from .env (Qwen: https://<host>/qwen/v1)"
    s = sub.add_parser("check", help="from this laptop: HTTPS, auth, blocked paths, open ports, one streamed chat")
    s.add_argument("--base-url", help=base_url_help)
    s.add_argument("--model", help="default: the first model the endpoint lists")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("gate", help="ticket 08 tool-calling test; writes evidence/gate-<model>-tool-calling.md/.json")
    s.add_argument("--base-url", help=base_url_help)
    s.add_argument("--model", help="default: the first model the endpoint lists")
    s.add_argument("--out", type=Path, help="report path without extension (default: evidence/gate-<model>-...)")
    s.set_defaults(func=cmd_gate)

    s = sub.add_parser("ssh", help="open a shell on the droplet, or run one command: kit.py ssh -- docker ps")
    s.add_argument("--ip", help="default: the IP inside VLLM_BASE_URL")
    s.add_argument("--user", default="root")
    s.add_argument("command", nargs=argparse.REMAINDER)
    s.set_defaults(func=cmd_ssh)

    s = sub.add_parser("forget", help="blank VLLM_BASE_URL in .env after destroying the droplet")
    s.set_defaults(func=cmd_forget)
    return p


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    args = parser().parse_args(argv)
    args.argv = argv  # the gate report quotes the exact command
    args.func(args)


if __name__ == "__main__":
    main()
