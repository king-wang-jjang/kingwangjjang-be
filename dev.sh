#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs/dev"
PID_FILE="$ROOT_DIR/.dev-pids"

# Kept as a literal for testability and for grep-friendly operational checks.
DEV_ENV="SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE"

SERVICES=(
  "api-gateway:8000"
  "board-service:33333"
  "user-service:33334"
  "comment-service:33335"
)

ensure_dirs() {
  mkdir -p "$LOG_DIR"
}

ensure_env() {
  if [[ ! -f "$ROOT_DIR/.env" ]]; then
    echo "[WARN] .env not found under $ROOT_DIR. Services may fail to start." >&2
  fi
}

is_running() {
  local pid="$1"
  kill -0 "$pid" >/dev/null 2>&1
}

start_service() {
  local name="$1"
  local port="$2"
  local service_dir="$ROOT_DIR/$name"
  local log_file="$LOG_DIR/$name.log"

  if [[ ! -d "$service_dir" ]]; then
    echo "[ERROR] service directory not found: $service_dir" >&2
    exit 1
  fi

  (
    cd "$service_dir"
    env SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE poetry run uvicorn app.main:app --host 0.0.0.0 --port "$port" >"$log_file" 2>&1
  ) &

  local pid=$!
  echo "$name $pid $port $log_file" >> "$PID_FILE"
  echo "[INFO] started $name on :$port pid=$pid log=$log_file"
}

cmd_up() {
  ensure_dirs
  ensure_env
  cmd_down >/dev/null 2>&1 || true
  : > "$PID_FILE"

  for spec in "${SERVICES[@]}"; do
    IFS=":" read -r name port <<< "$spec"
    start_service "$name" "$port"
  done

  cmd_ps
}

cmd_down() {
  if [[ ! -f "$PID_FILE" ]]; then
    return 0
  fi

  while read -r name pid port log_file; do
    if [[ -n "${pid:-}" ]] && is_running "$pid"; then
      kill "$pid" >/dev/null 2>&1 || true
      echo "[INFO] stopped $name pid=$pid"
    fi
  done < "$PID_FILE"

  rm -f "$PID_FILE"
}

cmd_restart() {
  cmd_down
  cmd_up
}

cmd_logs() {
  ensure_dirs
  tail -f "$LOG_DIR"/*.log
}

cmd_ps() {
  if [[ ! -f "$PID_FILE" ]]; then
    echo "[INFO] no dev services tracked"
    return 0
  fi

  while read -r name pid port log_file; do
    if is_running "$pid"; then
      echo "$name pid=$pid port=$port status=running log=$log_file"
    else
      echo "$name pid=$pid port=$port status=stopped log=$log_file"
    fi
  done < "$PID_FILE"
}

usage() {
  cat <<'USAGE'
Usage: ./dev.sh <command>

Commands:
  up        Start local source services in the background
  down      Stop local source services
  restart   Restart local source services
  logs      Follow local service logs
  ps        Show local service process status

Examples:
  ./dev.sh up
  ./dev.sh logs
USAGE
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    up) cmd_up ;;
    down) cmd_down ;;
    restart) cmd_restart ;;
    logs) cmd_logs ;;
    ps) cmd_ps ;;
    -h|--help|help|"") usage ;;
    *) echo "Unknown command: $cmd" >&2; echo; usage; exit 1 ;;
  esac
}

main "$@"
