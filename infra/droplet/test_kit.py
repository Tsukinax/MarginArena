"""Local tests for the droplet kit. Nothing here touches a droplet or the internet.

Run from the repo root: uv run --project backend pytest infra/droplet -q
"""

import hashlib
import json
import re
import shutil
import stat
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import kit
import pytest
from test_gate import API_KEY, FakeVLLM

BOOTSTRAP = kit.BOOTSTRAP.read_text()
needs_bash = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def run_kit(tmp_path, *argv):
    paths = ["--env-file", str(tmp_path / ".env"), "--ssh-key", str(tmp_path / "ssh" / "key")]
    kit.main([*paths, "--user-data", str(tmp_path / "user-data.sh"), *argv])


# ---------------------------------------------------------------- hostname and .env


def test_the_https_name_is_the_public_ip_with_dashes():
    assert kit.sslip_host("164.92.10.5") == "164-92-10-5.sslip.io"
    assert kit.sslip_host("164.92.10.5", "nip.io") == "164-92-10-5.nip.io"
    assert kit.ip_from_url("https://164-92-10-5.sslip.io/v1") == "164.92.10.5"


@pytest.mark.parametrize("text", ["10.124.0.5", "192.168.1.20", "127.0.0.1", "164.92.10", "droplet"])
def test_private_or_malformed_addresses_are_refused(text):
    with pytest.raises(ValueError):
        kit.sslip_host(text)


@needs_bash
def test_the_bootstrap_derives_the_same_name():
    script = f'source "{kit.BOOTSTRAP}" && sslip_host 164.92.10.5'
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == kit.sslip_host("164.92.10.5")


def test_setting_one_env_value_leaves_every_other_line_alone(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# Token Factory\nTOKEN_FACTORY_API_KEY=rc-1\nVLLM_BASE_URL=\nVLLM_API_KEY=\nEVOLUS_API_KEY=e\n")
    kit.set_env_value(env, "VLLM_BASE_URL", "https://164-92-10-5.sslip.io/v1")
    assert env.read_text() == (
        "# Token Factory\nTOKEN_FACTORY_API_KEY=rc-1\nVLLM_BASE_URL=https://164-92-10-5.sslip.io/v1\n"
        "VLLM_API_KEY=\nEVOLUS_API_KEY=e\n"
    )
    assert stat.S_IMODE(env.stat().st_mode) == 0o600


def test_a_missing_env_value_or_file_is_created(tmp_path):
    env = tmp_path / ".env"
    kit.set_env_value(env, "VLLM_API_KEY", API_KEY)
    kit.set_env_value(env, "VLLM_BASE_URL", "https://164-92-10-5.sslip.io/v1")
    assert kit.read_env(env) == {"VLLM_API_KEY": API_KEY, "VLLM_BASE_URL": "https://164-92-10-5.sslip.io/v1"}


# ---------------------------------------------------------------- prepare and provision


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="needs ssh-keygen")
def test_prepare_makes_both_keys_once_and_never_prints_the_api_key(tmp_path, capsys):
    run_kit(tmp_path, "prepare")
    out = capsys.readouterr().out
    api_key = kit.read_env(tmp_path / ".env")["VLLM_API_KEY"]
    assert re.fullmatch(r"[0-9a-f]{64}", api_key)
    assert api_key not in out
    assert "ssh-ed25519 " in out  # the public key is meant to be pasted
    user_data = tmp_path / "user-data.sh"
    assert f"'{api_key}'" in user_data.read_text()
    assert stat.S_IMODE(user_data.stat().st_mode) == 0o600

    private_key = (tmp_path / "ssh" / "key").read_bytes()
    run_kit(tmp_path, "prepare")
    assert kit.read_env(tmp_path / ".env")["VLLM_API_KEY"] == api_key
    assert (tmp_path / "ssh" / "key").read_bytes() == private_key


def test_prepare_dry_run_changes_nothing(tmp_path, capsys):
    run_kit(tmp_path, "prepare", "--dry-run")
    assert "[dry run] would generate VLLM_API_KEY" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_provision_dry_run_shows_the_plan_and_connects_to_nothing(tmp_path, capsys):
    run_kit(tmp_path, "provision", "164.92.10.5", "--with-qwen", "--dry-run")
    out = capsys.readouterr().out
    assert "bash /opt/llm/bootstrap.sh --host 164-92-10-5.sslip.io --with-qwen" in out
    assert "VLLM_BASE_URL=https://164-92-10-5.sslip.io/v1" in out
    assert not (tmp_path / ".env").exists()


def test_provision_refuses_the_droplets_private_address(tmp_path):
    with pytest.raises(SystemExit, match="private address"):
        run_kit(tmp_path, "provision", "10.124.0.5", "--dry-run")


# ---------------------------------------------------------------- what runs on the droplet


@needs_bash
def test_the_bootstrap_and_the_startup_script_are_valid_bash(tmp_path):
    subprocess.run(["bash", "-n", str(kit.BOOTSTRAP)], check=True)
    user_data = tmp_path / "user-data.sh"
    user_data.write_text(kit.render_user_data(API_KEY, BOOTSTRAP))
    subprocess.run(["bash", "-n", str(user_data)], check=True)


def test_the_startup_script_writes_the_key_then_runs_the_bootstrap():
    text = kit.render_user_data(API_KEY, BOOTSTRAP)
    assert text.startswith("#!/bin/bash\n")
    assert f"printf 'VLLM_API_KEY=%s\\n' '{API_KEY}' > /opt/llm/vllm.env" in text
    assert BOOTSTRAP.rstrip("\n") in text
    assert text.endswith("bash /opt/llm/bootstrap.sh\n")
    assert len(text.encode()) < 64 * 1024  # DigitalOcean's user data limit
    with pytest.raises(ValueError):
        kit.render_user_data("short", BOOTSTRAP)


@needs_bash
def test_a_rerun_replaces_a_container_only_when_its_configuration_changed(tmp_path):
    """Restarting vLLM costs paid minutes, so a rerun must leave a matching container alone."""
    calls, state = tmp_path / "calls", tmp_path / "state"
    docker = tmp_path / "bin" / "docker"  # a stub that logs its arguments; `inspect` prints the saved state
    docker.parent.mkdir()
    docker.write_text(f'#!/bin/bash\necho "$*" >> "{calls}"\n[[ $1 != inspect ]] || cat "{state}" 2>/dev/null\n')
    docker.chmod(0o755)

    def ensure(label: str) -> list[str]:
        calls.write_text("")
        script = f'source "{kit.BOOTSTRAP}" && ensure_container gemma {label} --network host IMAGE MODEL'
        path = f"{docker.parent}:/usr/bin:/bin:/usr/sbin:/sbin"
        subprocess.run(["bash", "-c", script], env={"PATH": path}, check=True, capture_output=True)
        return [line.split()[0] for line in calls.read_text().splitlines()]

    assert ensure("aaa") == ["inspect", "rm", "run"]  # nothing there yet: start it
    assert "run -d --name gemma --restart unless-stopped --label marginarena.config=aaa --network host IMAGE MODEL" in (
        calls.read_text()
    )
    state.write_text("aaa/true\n")
    assert ensure("aaa") == ["inspect"]  # same configuration, running: untouched
    assert ensure("bbb") == ["inspect", "rm", "run"]  # configuration changed: replaced
    state.write_text("aaa/false\n")
    assert ensure("aaa") == ["inspect", "rm", "run"]  # stopped: started again


def caddyfile() -> str:
    return BOOTSTRAP.split("<<'CADDYFILE'\n", 1)[1].split("\nCADDYFILE\n", 1)[0]


# Stand-ins for the droplet's system commands. Each logs its arguments to $CALLS.
STUBS = {
    # docker remembers each container's label in $STATE, as the daemon would.
    "docker": r"""
echo "docker $*" >> "$CALLS"
case $1 in
  inspect)
    name=${@: -1}
    [[ -f $STATE/$name ]] || exit 1
    case $* in
      *State.Status*) echo running ;;
      *marginarena.config*) echo "$(cat "$STATE/$name")/true" ;;
    esac ;;
  run)
    while (($#)); do
      case $1 in --name) name=$2; shift ;; --label) label=${2#marginarena.config=}; shift ;; esac
      shift
    done
    echo "$label" > "$STATE/$name" ;;
  rm) rm -f "$STATE/${@: -1}" ;;
  logs) echo "INFO 10-15 [kv_cache_utils.py:1] GPU KV cache size: 1,000,000 tokens" ;;
esac
exit 0
""",
    # curl: vLLM answers 401 without the key, everything else succeeds, downloads contain "template".
    "curl": r"""
echo "curl $*" >> "$CALLS"
[[ " $* " != *" --config - "* ]] || cat >/dev/null
[[ $* != *http_code* ]] || { printf 401; exit 0; }
while (($#)); do [[ $1 != -o || $2 == /dev/null ]] || printf template > "$2"; shift; done
""",
    "ufw": 'echo "ufw $*" >> "$CALLS"',
    "systemctl": "exit 0",
    "ss": "exit 0",  # nothing listens on 80 or 443
    "blkid": "exit 1",  # no scratch disk
    "amd-smi": "echo 'AMDSMI Tool: 26.0.0 | ROCm version: 7.2.3'",
}


@needs_bash
def test_the_bootstrap_steps_run_against_stub_commands(tmp_path):
    """Every step of a first run, a rerun, a switch to two models and back, without a droplet."""
    for name, body in STUBS.items():
        stub = tmp_path / "bin" / name
        stub.parent.mkdir(exist_ok=True)
        stub.write_text(f"#!/bin/bash\n{body.strip()}\n")
        stub.chmod(0o755)
    (tmp_path / "state").mkdir()
    calls, llm = tmp_path / "calls", tmp_path / "llm"
    script = f"""
source "{kit.BOOTSTRAP}"
LLM_DIR="{llm}" ENV_FILE="{llm}/vllm.env" TEMPLATE_SHA256={hashlib.sha256(b"template").hexdigest()}
mkdir -p "$LLM_DIR" && echo "VLLM_API_KEY={API_KEY}" > "$ENV_FILE" && VLLM_API_KEY={API_KEY}
host=164-92-10-5.sslip.io
step() {{ echo "== $1" >> "$CALLS"; }}
step setup; ensure_docker; configure_firewall; free_web_ports; prepare_dirs; fetch_template; start_caddy $host
step first; start_models false; verify $host false
step rerun; start_models false
step qwen; start_models true; verify $host true
step back; start_models false
"""
    path = f"{tmp_path / 'bin'}:/usr/bin:/bin:/usr/sbin:/sbin"
    env = {"PATH": path, "CALLS": str(calls), "STATE": str(tmp_path / "state")}
    result = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr

    log = calls.read_text()
    steps = {part.split("\n", 1)[0]: part for part in log.split("== ")[1:]}

    def runs(step: str) -> list[str]:
        return [line for line in steps[step].splitlines() if line.startswith("docker run")]

    firewall = ("--force reset", "default deny incoming", "allow 22/tcp", "allow 80/tcp", "allow 443", "--force enable")
    for rule in firewall:
        assert f"ufw {rule}" in steps["setup"]
    [caddy] = runs("setup")
    assert "--name caddy" in caddy and "SITE_HOST=164-92-10-5.sslip.io" in caddy
    assert kit.pinned_versions()["CADDY_IMAGE"] in caddy
    assert (llm / "caddy" / "conf" / "Caddyfile").read_text() == caddyfile() + "\n"

    [gemma] = runs("first")
    assert "--name gemma" in gemma and "--gpu-memory-utilization 0.90" in gemma
    assert f"{kit.pinned_versions()['VLLM_IMAGE']} google/gemma-4-31B-it --revision" in gemma
    assert runs("rerun") == []  # nothing changed, so nothing restarts
    gemma, qwen = runs("qwen")
    assert "--name gemma" in gemma and "--gpu-memory-utilization 0.50" in gemma  # Gemma first, with less memory
    assert "--name qwen" in qwen and "--gpu-memory-utilization 0.42" in qwen
    assert "docker rm -f qwen" in steps["back"] and "--gpu-memory-utilization 0.90" in runs("back")[0]

    assert "GPU KV cache size: 1,000,000 tokens" in result.stdout
    assert API_KEY not in log  # the key never appears in a command line


def test_caddy_forwards_only_the_two_openai_paths_and_only_with_the_key():
    conf = caddyfile()
    guarded = dict(re.findall(r"^\t@(\w+) \{\n(.*?)\n\t\}", conf, re.S | re.M))  # named matcher blocks
    assert set(guarded) == {"gemma", "qwen"}
    assert "path /v1/chat/completions /v1/models" in guarded["gemma"]
    assert "path /qwen/v1/chat/completions /qwen/v1/models" in guarded["qwen"]
    for matcher in guarded.values():
        assert 'header Authorization "Bearer {$VLLM_API_KEY}"' in matcher
    assert re.findall(r"handle @(\w+) \{[^}]*reverse_proxy", conf) == ["gemma", "qwen"]
    assert conf.count("reverse_proxy") == 2
    assert 'respond "Unauthorized" 401' in conf  # right path, missing or wrong key
    assert conf.endswith('\thandle {\n\t\trespond "Not found" 404\n\t}\n}')  # everything else
    assert "{$SITE_HOST} {" in conf and "admin off" in conf and "persist_config off" in conf


def test_images_models_and_flags_are_the_decided_ones():
    pins = kit.pinned_versions()
    assert re.fullmatch(r"vllm/vllm-openai-rocm:v0\.31\.0@sha256:[0-9a-f]{64}", pins["VLLM_IMAGE"])
    assert re.fullmatch(r"caddy:2\.11\.7@sha256:[0-9a-f]{64}", pins["CADDY_IMAGE"])
    assert pins["GEMMA_MODEL"] == "google/gemma-4-31B-it"  # the backend's default VLLM_MODEL
    assert re.fullmatch(r"[0-9a-f]{40}", pins["GEMMA_REVISION"])
    for flag in (
        "--host 127.0.0.1 --port 8001",
        "--language-model-only",
        "--attention-backend TRITON_ATTN",
        "--enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4",
        "--chat-template /templates/tool_chat_template_gemma4.jinja",
        "--tool-call-parser qwen3_coder",
        '--env-file "$ENV_FILE"',  # vLLM takes VLLM_API_KEY from it as its --api-key
    ):
        assert flag in BOOTSTRAP


# ---------------------------------------------------------------- HTTP helpers, against a local server


class LocalVLLM(BaseHTTPRequestHandler):
    def do_GET(self):
        status = 200 if self.headers.get("Authorization") == f"Bearer {API_KEY}" else 401
        self.send_response(status)
        self.end_headers()
        self.wfile.write(b'{"data": [{"id": "google/gemma-4-31B-it"}]}' if status == 200 else b"Unauthorized")

    def do_POST(self):
        json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for piece in ("1", ", 2", ", 3"):
            self.wfile.write(f"data: {json.dumps({'choices': [{'delta': {'content': piece}}]})}\n\n".encode())
        self.wfile.write(b'data: {"choices": [], "usage": {"completion_tokens": 3}}\n\ndata: [DONE]\n\n')

    def log_message(self, *args):
        pass


@pytest.fixture
def local_vllm():
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalVLLM)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_http_errors_come_back_as_statuses(local_vllm):
    assert kit.http_request("GET", f"{local_vllm}/models")[0] == 401
    assert kit.http_request("GET", f"{local_vllm}/models", key=API_KEY)[0] == 200


def test_a_streamed_chat_is_read_and_timed(local_vllm):
    chat = kit.stream_chat(local_vllm, API_KEY, "google/gemma-4-31B-it", "Count to 3.")
    assert chat["text"] == "1, 2, 3"
    assert chat["completion_tokens"] == 3
    assert chat["total_s"] >= chat["ttft_s"] >= 0


# ---------------------------------------------------------------- the gate command


def test_the_gate_command_writes_judge_facing_evidence(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(f"VLLM_BASE_URL=https://164-92-10-5.sslip.io/v1\nVLLM_API_KEY={API_KEY}\n")
    fake = FakeVLLM()

    def request(method, url, key=None, body=None, timeout=60):
        if url.endswith("/models"):
            served = {"id": "google/gemma-4-31B-it", "root": "google/gemma-4-31B-it", "max_model_len": 32768}
            return 200, json.dumps({"data": [served]}).encode()
        return fake(method, url, key, body, timeout)

    monkeypatch.setattr(kit, "http_request", request)
    facts = {"vllm": "0.31.0", "max_concurrency": "Maximum concurrency for 32,768 tokens per request: 37.65x"}
    monkeypatch.setattr(kit, "droplet_facts", lambda *args: facts)
    with pytest.raises(SystemExit) as exit:
        kit.main(["--env-file", str(env), "gate", "--out", str(tmp_path / "gate-gemma-tool-calling")])
    assert exit.value.code == 0

    raw = (tmp_path / "gate-gemma-tool-calling.json").read_text()
    page = (tmp_path / "gate-gemma-tool-calling.md").read_text()
    assert API_KEY not in raw and API_KEY not in page
    assert json.loads(raw)["passed"]
    assert "**Result: PASS.**" in page
    assert kit.pinned_versions()["VLLM_IMAGE"] in page and "vLLM 0.31.0" in page and facts["max_concurrency"] in page
    assert kit.pinned_versions()["GEMMA_REVISION"] in page and "max context 32768 tokens" in page
    assert f"python3 infra/droplet/kit.py --env-file {env} gate --out" in page


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="needs ssh-keygen")
def test_provision_keeps_a_pinned_host_key_unless_told_to_reset(tmp_path, monkeypatch):
    # A changed host key must stop the connection, not be silently re-trusted (security review).
    run_kit(tmp_path, "prepare")
    forgotten: list[str] = []
    monkeypatch.setattr(kit, "forget_host_key", lambda ip, key: forgotten.append(ip))

    def stop(*args, **kwargs):
        raise SystemExit("stop before connecting")

    monkeypatch.setattr(kit, "wait_for_ssh", stop)

    with pytest.raises(SystemExit):
        run_kit(tmp_path, "provision", "164.92.10.5")
    assert forgotten == []

    with pytest.raises(SystemExit):
        run_kit(tmp_path, "provision", "164.92.10.5", "--reset-host-key")
    assert forgotten == ["164.92.10.5"]


def test_a_changed_host_key_stops_with_advice(monkeypatch):
    changed = subprocess.CompletedProcess(
        [], 255, "", "@@@ WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED! @@@\nHost key verification failed.\n"
    )
    monkeypatch.setattr(kit.subprocess, "run", lambda *a, **k: changed)

    with pytest.raises(SystemExit, match="--reset-host-key"):
        kit.wait_for_ssh(["ssh", "root@164.92.10.5"], minutes=1)
