#!/usr/bin/env bash
# MarginArena droplet bootstrap: Gemma-4-31B-IT on vLLM (ROCm) behind Caddy HTTPS.
#
# Run as root on a fresh AMD Developer Cloud MI300X droplet. It is safe to run again: every
# step checks what is already there and changes only what differs. infra/droplet/kit.py
# uploads it and runs it over SSH; the optional startup script from `kit.py prepare` runs it
# at first boot.
#
#   bash bootstrap.sh [--host NAME] [--with-qwen]
#     --host NAME   HTTPS hostname. Default: <public IP with dashes>.sslip.io, from the droplet metadata.
#     --with-qwen   Also serve Qwen3.6-27B under /qwen/v1 for the Evolus agent (the ticket 08 fallback).
#
# The API key comes from /opt/llm/vllm.env (VLLM_API_KEY=...). Every choice below is explained in
# .scratch/marginarena/research/model-serving-mi300x.md (§1.1 Gemma, §5 Qwen, §6 exposure).
set -euo pipefail

# Pinned versions. Change them here only.
VLLM_IMAGE='vllm/vllm-openai-rocm:v0.31.0@sha256:749f6f3f944f12af49966ac523c1f8573e4b229594b541954bd5f879b4496b1f'
CADDY_IMAGE='caddy:2.11.7@sha256:685ae3d7c34d9b5f8caeddc5d14051db7bbd88ff1f5a2fa0c16bd8ca328fb7af'
GEMMA_MODEL='google/gemma-4-31B-it'
GEMMA_REVISION='842da3794eaa0b77d5f08bae87a17459d91ff475'
QWEN_MODEL='Qwen/Qwen3.6-27B'
QWEN_REVISION='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
# The relative template path in the vLLM recipe breaks (vLLM issue #47600), so we mount our own copy.
TEMPLATE_URL='https://raw.githubusercontent.com/vllm-project/vllm/v0.31.0/examples/tool_chat_template_gemma4.jinja'
TEMPLATE_SHA256='afdbb2abe3667ccde95cc2f86919f05370339399bab5f750950a4390523b8927'

LLM_DIR=/opt/llm
ENV_FILE=$LLM_DIR/vllm.env
export DEBIAN_FRONTEND=noninteractive
export PATH=$PATH:/usr/sbin:/sbin:/opt/rocm/bin
export HOME=${HOME:-/root}  # the startup script runs without HOME; the docker CLI wants one

log() { printf '[bootstrap %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() {
  log "ERROR: $*" >&2
  exit 1
}

# 164.92.10.5 -> 164-92-10-5.sslip.io (kit.py derives the same name in Python).
sslip_host() { printf '%s.sslip.io\n' "${1//./-}"; }

# curl with the API key. The key goes in through stdin, so `ps` never shows it.
curl_with_key() {
  printf 'header = "Authorization: Bearer %s"\n' "$VLLM_API_KEY" | curl --config - "$@"
}

apt_install() {
  log "installing $*"
  apt-get -q -o DPkg::Lock::Timeout=600 update >/dev/null
  apt-get -q -y -o DPkg::Lock::Timeout=600 install "$@" >/dev/null
}

check_gpu() {
  [[ -e /dev/kfd && -d /dev/dri ]] || die "no AMD GPU driver (no /dev/kfd): create the droplet from a ROCm image"
  if command -v amd-smi >/dev/null; then
    log "GPU driver: $(amd-smi version 2>/dev/null | head -n 1 || true)"
  fi
}

ensure_docker() {
  command -v docker >/dev/null || apt_install docker.io
  systemctl enable --now docker >/dev/null 2>&1 || true
  local _
  for _ in $(seq 60); do
    docker info >/dev/null 2>&1 && return 0
    sleep 2
  done
  die "Docker is not running"
}

# Only SSH, HTTP (Let's Encrypt challenge and redirect) and HTTPS. vLLM listens on 127.0.0.1 and
# every container uses host networking, so Docker publishes no ports that could bypass ufw.
configure_firewall() {
  command -v ufw >/dev/null || apt_install ufw
  ufw --force reset >/dev/null
  ufw default deny incoming >/dev/null
  ufw default allow outgoing >/dev/null
  ufw allow 22/tcp >/dev/null
  ufw allow 80/tcp >/dev/null
  ufw allow 443 >/dev/null  # TCP, plus UDP for HTTP/3
  ufw --force enable >/dev/null
  log "firewall: only ports 22, 80 and 443 are open"
}

# Quick Start images start JupyterLab on port 80 (in a container named "rocm", or as a host
# service). Caddy needs ports 80 and 443, and we don't need Jupyter.
free_web_ports() {
  if docker inspect --type container rocm >/dev/null 2>&1; then
    log "stopping the Quick Start container 'rocm' (its JupyterLab holds port 80)"
    docker update --restart=no rocm >/dev/null
    docker stop rocm >/dev/null
  fi
  local pid unit busy
  for pid in $(web_port_listeners | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u || true); do
    unit=$(ps -o unit= -p "$pid" | tr -d ' ' || true)
    if [[ $unit == *.service && $unit != docker.service && $unit != containerd.service ]]; then
      log "stopping $unit (it holds port 80 or 443)"
      systemctl disable --now "$unit" >/dev/null 2>&1 || true
    fi
  done
  sleep 1
  busy=$(web_port_listeners)
  [[ -z $busy ]] || die "ports 80/443 are still taken; stop this and run again: $busy"
}

web_port_listeners() {  # anything but our Caddy listening on 80 or 443
  ss -Hltnp '( sport = :80 or sport = :443 )' | grep -v '"caddy"' || true
}

# Model weights (~62 GB per model) go on the 5 TB scratch disk when there is one. It comes
# formatted (label DOSCRATCH) but unmounted, and it is wiped with the droplet like everything else.
prepare_dirs() {
  mkdir -p "$LLM_DIR"/{templates,vllm-cache,caddy/conf,caddy/data,caddy/config}
  HF_CACHE=$LLM_DIR/hf  # the 720 GB boot disk, if there is no scratch disk
  if blkid -L DOSCRATCH >/dev/null 2>&1; then
    mkdir -p /scratch
    if ! grep -q '^LABEL=DOSCRATCH' /etc/fstab; then
      printf 'LABEL=DOSCRATCH\t/scratch\text4\tdiscard,errors=remount-ro,nofail\t0 2\n' >>/etc/fstab
    fi
    if mountpoint -q /scratch || mount /scratch; then
      HF_CACHE=/scratch/hf
    else
      log "could not mount the scratch disk; using the boot disk"
    fi
  fi
  mkdir -p "$HF_CACHE"
  log "model cache: $HF_CACHE ($(df -h --output=avail "$HF_CACHE" | tail -n 1 | tr -d ' ') free)"
}

sha256_of() { sha256sum <"$1" | cut -c1-64; }

fetch_template() {
  local file=$LLM_DIR/templates/tool_chat_template_gemma4.jinja
  if [[ -f $file && $(sha256_of "$file") == "$TEMPLATE_SHA256" ]]; then
    return 0
  fi
  curl -fsSL --retry 3 -o "$file.tmp" "$TEMPLATE_URL"
  [[ $(sha256_of "$file.tmp") == "$TEMPLATE_SHA256" ]] || die "the chat template does not match its checksum"
  mv "$file.tmp" "$file"
}

# Only /v1/chat/completions and /v1/models reach vLLM, and only with the key. vLLM's own
# --api-key leaves /invocations, /pause and other paths open (vLLM security docs), so Caddy is
# the allowlist. Caddy fills {$SITE_HOST} and {$VLLM_API_KEY} from its environment when it
# loads the file, so the key is never written into it; admin and persist_config are off so the
# loaded config (with the key) is neither served on :2019 nor saved to disk.
write_caddyfile() {
  cat >"$1" <<'CADDYFILE'
{
	admin off
	persist_config off
}

{$SITE_HOST} {
	@gemma {
		path /v1/chat/completions /v1/models
		header Authorization "Bearer {$VLLM_API_KEY}"
	}
	handle @gemma {
		reverse_proxy 127.0.0.1:8001
	}

	# Second model (bootstrap.sh --with-qwen). Answers 502 while it is not running.
	@qwen {
		path /qwen/v1/chat/completions /qwen/v1/models
		header Authorization "Bearer {$VLLM_API_KEY}"
	}
	handle @qwen {
		uri strip_prefix /qwen
		reverse_proxy 127.0.0.1:8002
	}

	@api path /v1/chat/completions /v1/models /qwen/v1/chat/completions /qwen/v1/models
	handle @api {
		respond "Unauthorized" 401
	}

	handle {
		respond "Not found" 404
	}
}
CADDYFILE
}

# A short fingerprint of everything that defines a container. Its label tells a rerun whether
# the running container already matches.
config_label() { printf '%s\n' "$@" | sha256sum | cut -c1-16; }

is_current() {  # NAME LABEL
  local state='{{index .Config.Labels "marginarena.config"}}/{{.State.Running}}'
  [[ $(docker inspect --format "$state" "$1" 2>/dev/null || true) == "$2/true" ]]
}

ensure_container() {  # NAME LABEL DOCKER_RUN_ARGS...
  local name=$1 label=$2
  shift 2
  if is_current "$name" "$label"; then
    log "$name: already running with this configuration"
    return 0
  fi
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker run -d --name "$name" --restart unless-stopped --label "marginarena.config=$label" "$@" >/dev/null
  log "$name: started"
}

remove_container() {
  if docker inspect --type container "$1" >/dev/null 2>&1; then
    docker rm -f "$1" >/dev/null
    log "$1: removed"
  fi
}

start_caddy() {
  local host=$1 conf=$LLM_DIR/caddy/conf/Caddyfile
  write_caddyfile "$conf"
  # The Docker Hub image warns against mounting the Caddyfile itself, so we mount its folder.
  local args=(
    --network host
    --env-file "$ENV_FILE" -e "SITE_HOST=$host"
    -v "$LLM_DIR/caddy/conf:/etc/caddy:ro"
    -v "$LLM_DIR/caddy/data:/data"
    -v "$LLM_DIR/caddy/config:/config"
    "$CADDY_IMAGE"
  )
  ensure_container caddy "$(config_label "$(cat "$conf" "$ENV_FILE")" "${args[@]}")" "${args[@]}"
}

# Progress bars redraw one line with carriage returns; keep only their latest state.
last_log_line() {
  docker logs --tail 1 "$1" 2>&1 | tr '\r' '\n' | grep -v '^[[:space:]]*$' | tail -n 1 | cut -c1-150 || true
}

# Wait until a vLLM container answers /health. The first start downloads the weights.
wait_healthy() {  # NAME PORT
  local name=$1 port=$2 start=$SECONDS
  log "$name: waiting for vLLM on port $port (a first start downloads the weights: about 10-20 min)"
  until curl -fsS --max-time 5 "http://127.0.0.1:$port/health" >/dev/null 2>&1; do
    if [[ $(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || true) != running ]]; then
      docker logs --tail 60 "$name" >&2 || true
      die "$name stopped while starting; its last log lines are above"
    fi
    ((SECONDS - start < 3600)) || die "$name is still not healthy after 60 min"
    if (((SECONDS - start) % 60 < 10)); then  # about once a minute, the latest log line
      log "$name: $(((SECONDS - start) / 60)) min: $(last_log_line "$name")"
    fi
    sleep 10
  done
  log "$name: ready after $(((SECONDS - start) / 60)) min"
  docker logs "$name" 2>&1 | grep -i -E 'GPU KV cache size|Maximum concurrency' | sed 's/.*\] /  /' || true
}

start_models() {  # WITH_QWEN (true/false)
  local with_qwen=$1 gemma_memory=0.90
  if $with_qwen; then
    gemma_memory=0.50  # research §5: 0.50 for Gemma and 0.42 for Qwen on one 192 GB GPU
  fi
  # vLLM reads VLLM_API_KEY from vllm.env as its --api-key, which keeps the key out of `ps`.
  local common=(
    --network host --ipc host --shm-size 16G
    --device /dev/kfd --device /dev/dri --group-add video
    --cap-add SYS_PTRACE --security-opt seccomp=unconfined
    --env-file "$ENV_FILE" -e HF_XET_HIGH_PERFORMANCE=1
    -v "$HF_CACHE:/root/.cache/huggingface"
    -v "$LLM_DIR/vllm-cache:/root/.cache/vllm"
  )
  # The image's entrypoint is `vllm serve`, so the model comes first.
  local gemma=(
    "${common[@]}" -v "$LLM_DIR/templates:/templates:ro"
    "$VLLM_IMAGE" "$GEMMA_MODEL"
    --revision "$GEMMA_REVISION"
    --host 127.0.0.1 --port 8001
    --language-model-only
    --attention-backend TRITON_ATTN
    --max-model-len 32768
    --gpu-memory-utilization "$gemma_memory"
    --max-num-seqs 128
    --enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4
    --chat-template /templates/tool_chat_template_gemma4.jinja
    --structured-outputs-config '{"backend":"xgrammar","disable_any_whitespace":true}'
    --async-scheduling
  )
  local qwen=(
    "${common[@]}" -e VLLM_ROCM_USE_AITER=1
    "$VLLM_IMAGE" "$QWEN_MODEL"
    --revision "$QWEN_REVISION" --trust-remote-code
    --host 127.0.0.1 --port 8002
    --language-model-only
    --attention-backend ROCM_AITER_FA
    --max-model-len 32768
    --gpu-memory-utilization 0.42
    --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3
    --default-chat-template-kwargs '{"enable_thinking": false}'
  )
  local key_sum gemma_label
  key_sum=$(sha256sum <"$ENV_FILE")
  gemma_label=$(config_label "$key_sum" "${gemma[@]}")
  # vLLM sizes its cache from the GPU memory it finds free, so Gemma starts with the GPU to
  # itself and Qwen starts after it.
  if ! $with_qwen || ! is_current gemma "$gemma_label"; then
    remove_container qwen
  fi
  ensure_container gemma "$gemma_label" "${gemma[@]}"
  wait_healthy gemma 8001
  if $with_qwen; then
    ensure_container qwen "$(config_label "$key_sum" "${qwen[@]}")" "${qwen[@]}"
    wait_healthy qwen 8002
  fi
}

verify() {  # HOST WITH_QWEN
  local host=$1 with_qwen=$2 code _
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/v1/models || true)
  [[ $code == 401 ]] || die "vLLM answered $code to a request without the key; expected 401"
  curl_with_key -fsS -o /dev/null http://127.0.0.1:8001/v1/models || die "vLLM refused the API key"
  log "waiting for the Let's Encrypt certificate for $host"
  for _ in $(seq 36); do
    if curl_with_key -fsS -o /dev/null --max-time 10 "https://$host/v1/models" 2>/dev/null; then
      log "HTTPS works: https://$host/v1"
      if $with_qwen; then
        curl_with_key -fsS -o /dev/null --max-time 10 "https://$host/qwen/v1/models" ||
          die "Qwen is not reachable through Caddy"
        log "HTTPS works: https://$host/qwen/v1"
      fi
      return 0
    fi
    sleep 5
  done
  docker logs --tail 40 caddy >&2 || true
  die "https://$host/v1/models did not answer within 3 min; Caddy's last log lines are above"
}

main() {
  local host='' with_qwen=false
  while (($#)); do
    case $1 in
      --host)
        host=${2:?--host needs a name}
        shift 2
        ;;
      --with-qwen)
        with_qwen=true
        shift
        ;;
      *) die "unknown argument: $1 (usage: bootstrap.sh [--host NAME] [--with-qwen])" ;;
    esac
  done
  [[ $EUID -eq 0 ]] || die "run this as root"

  # One run at a time: the startup script and `kit.py provision` may overlap.
  exec 9>/run/marginarena-bootstrap.lock
  if ! flock -n 9; then
    log "another bootstrap run is in progress (probably the startup script); waiting for it to finish"
    until flock -w 60 9; do
      log "still waiting; the startup script says: $(tail -n 1 /var/log/cloud-init-output.log 2>&1 | cut -c1-150)"
    done
  fi

  [[ -r $ENV_FILE ]] || die "$ENV_FILE is missing (kit.py provision writes it)"
  VLLM_API_KEY=$(sed -n 's/^VLLM_API_KEY=//p' "$ENV_FILE")
  [[ $VLLM_API_KEY =~ ^[A-Za-z0-9_-]{32,}$ ]] || die "VLLM_API_KEY in $ENV_FILE is missing or too short"
  if [[ -z $host ]]; then
    local ip
    ip=$(curl -fsS --max-time 5 http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address) ||
      die "no --host given and the droplet metadata service did not answer"
    host=$(sslip_host "$ip")
  fi
  log "hostname: $host"

  check_gpu
  ensure_docker
  configure_firewall
  free_web_ports
  prepare_dirs
  fetch_template
  start_caddy "$host"  # Caddy gets its certificate while vLLM loads
  log "pulling the vLLM image (11.5 GB; a few minutes on a fresh droplet)"
  docker pull -q "$VLLM_IMAGE" >/dev/null
  start_models "$with_qwen"
  verify "$host" "$with_qwen"
  log "Evolus > Your models: base URL https://$host/v1, model $GEMMA_MODEL, API key = VLLM_API_KEY in .env"
  if $with_qwen; then
    log "Evolus agent on Qwen: base URL https://$host/qwen/v1, model $QWEN_MODEL"
  fi
  printf 'VLLM_BASE_URL=https://%s/v1\n' "$host"
}

# Tests source this file for its functions; running it starts main.
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  main "$@"
fi
