#!/usr/bin/env bash
# Start, check, and stop one local Moody stack. Kills only processes this script started.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)
STATE_DIR=${MOODY_VERIFY_STATE_DIR:-/tmp/moody-verify}
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_URL=http://127.0.0.1:${BACKEND_PORT}
FRONTEND_URL=http://127.0.0.1:${FRONTEND_PORT}
READY_TIMEOUT_SECONDS=${MOODY_VERIFY_READY_TIMEOUT:-240}

usage() {
  echo "usage: moody-verify.sh launch|doctor|cleanup" >&2
  exit 2
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "moody-verify: required command not on PATH: $1" >&2
    exit 1
  fi
}

pid_alive() {
  local pid=$1
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

is_under() {
  local pid=$1 root=$2 hops=0
  while [[ -n "$pid" && "$pid" != "0" && "$pid" != "1" && "$hops" -lt 30 ]]; do
    if [[ "$pid" == "$root" ]]; then
      return 0
    fi
    pid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ' || true)
    hops=$((hops + 1))
  done
  return 1
}

listeners() {
  local port=$1
  lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true
}

port_owned_by() {
  local port=$1 root=$2 pid
  local found=0
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    found=1
    if ! is_under "$pid" "$root"; then
      return 1
    fi
  done < <(listeners "$port")
  [[ "$found" -eq 1 ]]
}

recorded_pid() {
  local name=$1
  local file="$STATE_DIR/$name.pid"
  if [[ -f "$file" ]]; then
    tr -d '[:space:]' < "$file"
  fi
}

our_stack_up() {
  local backend frontend
  backend=$(recorded_pid backend)
  frontend=$(recorded_pid frontend)
  pid_alive "$backend" && pid_alive "$frontend" \
    && port_owned_by "$BACKEND_PORT" "$backend" \
    && port_owned_by "$FRONTEND_PORT" "$frontend"
}

foreign_listener() {
  local port=$1 pid
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    echo "$pid"
    return 0
  done < <(listeners "$port")
  return 1
}

kill_tree() {
  local pid=$1 signal=$2 child
  if ! pid_alive "$pid"; then
    return 0
  fi
  while read -r child; do
    [[ -z "$child" ]] && continue
    kill_tree "$child" "$signal"
  done < <(pgrep -P "$pid" || true)
  kill "-$signal" "$pid" 2>/dev/null || true
}

api_url_ok() {
  local env_file="$REPO_ROOT/frontend/.env.local"
  local api_url=""
  if [[ -f "$env_file" ]]; then
    api_url=$(grep -E '^VITE_API_URL=' "$env_file" | tail -1 | cut -d= -f2- | tr -d '[:space:]' || true)
  fi
  if [[ -z "$api_url" ]]; then
    return 0
  fi
  case "$api_url" in
    http://localhost:8000|http://127.0.0.1:8000) return 0 ;;
    *)
      echo "moody-verify: VITE_API_URL must be http://localhost:8000 or http://127.0.0.1:8000" >&2
      return 1
      ;;
  esac
}

check_health() {
  local body
  body=$(curl -sf --max-time 5 "$BACKEND_URL/health") || return 1
  python3 -c 'import json,sys; assert json.loads(sys.argv[1]).get("status")=="ok"' "$body"
}

popular_count() {
  local body
  body=$(curl -sf --max-time 20 "$BACKEND_URL/popular") || return 1
  python3 -c 'import json,sys; data=json.loads(sys.argv[1]); results=data.get("results") or [];
assert isinstance(results, list) and len(results) >= 1
print(len(results))' "$body"
}

check_frontend() {
  curl -sf --max-time 5 "$FRONTEND_URL/" | grep -q '<title>Moody</title>'
}

cmd_doctor() {
  need_cmd curl
  need_cmd lsof
  need_cmd python3
  api_url_ok
  if ! our_stack_up; then
    echo "moody-verify doctor: instance is not the stack this script started" >&2
    exit 1
  fi
  check_health
  local count
  count=$(popular_count)
  check_frontend
  echo "moody-verify doctor: ok"
  echo "backend $BACKEND_URL pid=$(recorded_pid backend) health=ok popular=$count"
  echo "frontend $FRONTEND_URL pid=$(recorded_pid frontend) title=Moody"
}

wait_ready() {
  local deadline=$((SECONDS + READY_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    if check_health && popular_count >/dev/null && check_frontend; then
      return 0
    fi
    if ! pid_alive "$(recorded_pid backend)" || ! pid_alive "$(recorded_pid frontend)"; then
      echo "moody-verify: a started process exited before ready. See $STATE_DIR/*.log" >&2
      return 1
    fi
    sleep 1
  done
  echo "moody-verify: not ready after ${READY_TIMEOUT_SECONDS}s. See $STATE_DIR/*.log" >&2
  return 1
}

cmd_launch() {
  need_cmd curl
  need_cmd lsof
  need_cmd python3
  need_cmd uv
  need_cmd npm
  api_url_ok
  if [[ ! -f "$REPO_ROOT/backend/.env" ]]; then
    echo "moody-verify: backend/.env is missing (copy backend/.env.example and fill it in)" >&2
    exit 1
  fi
  if our_stack_up && check_health && popular_count >/dev/null && check_frontend; then
    echo "moody-verify launch: already ready"
    cmd_doctor
    return 0
  fi
  local pid
  if pid=$(foreign_listener "$BACKEND_PORT"); then
    echo "moody-verify: port $BACKEND_PORT is already in use by pid $pid. Refusing to start a second backend." >&2
    exit 1
  fi
  if pid=$(foreign_listener "$FRONTEND_PORT"); then
    echo "moody-verify: port $FRONTEND_PORT is already in use by pid $pid. Refusing to start a second frontend." >&2
    exit 1
  fi
  mkdir -p "$STATE_DIR"
  # setsid detaches from the launcher process group so a finished shell does not take the servers down.
  (
    cd "$REPO_ROOT/backend"
    export DB_POOL_MIN_SIZE=0
    export DB_APPLICATION_NAME=moody-verify
    exec python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
      uv run --python 3.13 --with-requirements requirements.txt \
      uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT"
  ) >"$STATE_DIR/backend.log" 2>&1 &
  echo $! >"$STATE_DIR/backend.pid"
  (
    cd "$REPO_ROOT/frontend"
    exec python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
      npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort
  ) >"$STATE_DIR/frontend.log" 2>&1 &
  echo $! >"$STATE_DIR/frontend.pid"
  if ! wait_ready; then
    cmd_cleanup || true
    exit 1
  fi
  cmd_doctor
}

cmd_cleanup() {
  local name pid
  if [[ ! -d "$STATE_DIR" ]]; then
    echo "moody-verify cleanup: no state at $STATE_DIR"
    return 0
  fi
  for name in backend frontend; do
    pid=$(recorded_pid "$name")
    if pid_alive "$pid"; then
      kill_tree "$pid" TERM
    fi
  done
  sleep 1
  for name in backend frontend; do
    pid=$(recorded_pid "$name")
    if pid_alive "$pid"; then
      kill_tree "$pid" KILL
    fi
  done
  rm -rf "$STATE_DIR"
  echo "moody-verify cleanup: stopped the processes this script started"
}

main() {
  local cmd=${1:-}
  case "$cmd" in
    launch) cmd_launch ;;
    doctor) cmd_doctor ;;
    cleanup) cmd_cleanup ;;
    *) usage ;;
  esac
}

main "$@"
