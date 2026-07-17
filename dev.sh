#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs/dev"
PID_FILE="$LOG_DIR/.dev-pids"

# Kept as a literal for testability and for grep-friendly operational checks.
DEV_ENV="SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE DATABASE_URL=<from .env>"

SERVICES=(
  "gpt-service:33336"
  "api-gateway:33330"
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

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

resolve_python_executable() {
  local project_dir="$1"
  local venv_python="$project_dir/.venv/bin/python"

  if [[ -x "$venv_python" ]]; then
    echo "$venv_python"
    return 0
  fi

  if has_cmd poetry && [[ -f "$project_dir/pyproject.toml" ]]; then
    local poetry_python
    poetry_python="$(cd "$project_dir" && poetry env info --executable 2>/dev/null || true)"
    if [[ -x "$poetry_python" ]]; then
      echo "$poetry_python"
      return 0
    fi
  fi

  if has_cmd python3; then
    echo "python3"
    return 0
  fi

  echo "python"
}

load_dev_env_file() {
  local env_file="$ROOT_DIR/.env"
  [[ -f "$env_file" ]] || return 0

  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    local line="${raw_line#"${raw_line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "${line:0:1}" == "#" || "$line" != *=* ]] && continue

    local key="${line%%=*}"
    local value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi

    if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ && -z "${!key+x}" ]]; then
      export "$key=$value"
    fi
  done < "$env_file"
}

urlencode_component() {
  local value="$1"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 is required to encode DB credentials for DATABASE_URL." >&2
    exit 1
  fi

  VALUE="$value" python3 -c 'import os, urllib.parse; print(urllib.parse.quote(os.environ["VALUE"], safe=""))'
}

server_database_reachable() {
  local host="${DB_HOST:-}"
  local port="${DB_PORT:-5432}"
  [[ -n "$host" ]] || return 1

  if command -v nc >/dev/null 2>&1; then
    nc -z -w 2 "$host" "$port" >/dev/null 2>&1
    return $?
  fi

  if command -v timeout >/dev/null 2>&1; then
    timeout 2 bash -c "</dev/tcp/$host/$port" >/dev/null 2>&1
    return $?
  fi

  return 1
}

should_use_server_database() {
  local target="${DEV_DATABASE_TARGET:-local}"

  if [[ "${USE_SERVER_DB:-}" == "1" || "$target" == "server" ]]; then
    return 0
  fi

  if [[ "$target" == "auto" && -n "${DB_HOST:-}" && -n "${DB_NAME:-}" && -n "${DB_USER:-}" && -n "${DB_PASSWORD:-}" ]]; then
    server_database_reachable
    return $?
  fi

  return 1
}

configure_server_database_env() {
  : "${DB_HOST:?DB_HOST is required when DEV_DATABASE_TARGET=server.}"
  : "${DB_NAME:?DB_NAME is required when DEV_DATABASE_TARGET=server.}"
  : "${DB_USER:?DB_USER is required when DEV_DATABASE_TARGET=server.}"
  : "${DB_PASSWORD:?DB_PASSWORD is required when DEV_DATABASE_TARGET=server.}"

  local port="${DB_PORT:-5432}"
  local encoded_user encoded_password
  encoded_user="$(urlencode_component "$DB_USER")"
  encoded_password="$(urlencode_component "$DB_PASSWORD")"

  export DATABASE_URL="postgresql+psycopg://${encoded_user}:${encoded_password}@${DB_HOST}:${port}/${DB_NAME}"
  echo "[INFO] using external server database ${DB_HOST}:${port}/${DB_NAME}"
}

configure_local_database_url() {
  [[ -z "${DATABASE_URL:-}" ]] || return 0
  [[ -n "${POSTGRES_USER:-}" && -n "${POSTGRES_PASSWORD:-}" && -n "${POSTGRES_DB:-}" ]] || return 0

  local host="${POSTGRES_HOST:-localhost}"
  local port="${POSTGRES_PORT:-5432}"
  local encoded_user encoded_password
  encoded_user="$(urlencode_component "$POSTGRES_USER")"
  encoded_password="$(urlencode_component "$POSTGRES_PASSWORD")"

  export DATABASE_URL="postgresql+psycopg://${encoded_user}:${encoded_password}@${host}:${port}/${POSTGRES_DB}"
}

configure_database_env() {
  if should_use_server_database; then
    configure_server_database_env
    return
  fi

  if [[ "${DEV_DATABASE_TARGET:-}" == "auto" && -n "${DB_HOST:-}" ]]; then
    echo "[WARN] external server database ${DB_HOST}:${DB_PORT:-5432} is not reachable; using local dev database"
  fi

  configure_local_database_url
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

  : "${DATABASE_URL:?DATABASE_URL is required. Set it in .env or the current shell.}"
  local python_runner
  python_runner="$(resolve_python_executable "$service_dir")"
  (
    cd "$service_dir"
    if has_cmd setsid; then
      setsid env SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE DATABASE_URL="$DATABASE_URL" "$python_runner" -m uvicorn app.main:app --host 0.0.0.0 --port "$port" >"$log_file" 2>&1 < /dev/null &
    else
      nohup env SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE DATABASE_URL="$DATABASE_URL" "$python_runner" -m uvicorn app.main:app --host 0.0.0.0 --port "$port" >"$log_file" 2>&1 < /dev/null &
    fi
    echo "$!" > "$LOG_DIR/$name.pid"
  )

  local pid
  pid="$(cat "$LOG_DIR/$name.pid")"
  rm -f "$LOG_DIR/$name.pid"
  echo "$name $pid $port $log_file" >> "$PID_FILE"
  echo "[INFO] started $name on :$port pid=$pid log=$log_file"
}

stop_port() {
  local port="$1"
  local pids=""

  if has_cmd lsof; then
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  fi

  if [[ -z "$pids" ]] && has_cmd fuser; then
    pids="$(fuser "$port"/tcp 2>/dev/null || true)"
  fi

  for pid in $pids; do
    if [[ -n "$pid" ]] && is_running "$pid"; then
      kill "$pid" >/dev/null 2>&1 || true
      echo "[INFO] stopped process on :$port pid=$pid"
    fi
  done

  [[ -z "$pids" ]] || sleep 1
}

seed_service() {
  local name="$1"
  local service_dir="$ROOT_DIR/$name"

  if [[ ! -d "$service_dir" ]]; then
    echo "[ERROR] service directory not found: $service_dir" >&2
    exit 1
  fi

  (
    cd "$service_dir"
    : "${DATABASE_URL:?DATABASE_URL is required. Set it in .env or the current shell.}"
    local python_runner
    python_runner="$(resolve_python_executable "$service_dir")"
    env SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE DATABASE_URL="$DATABASE_URL" "$python_runner" -m app.db.seed
  )
}

cmd_up() {
  ensure_dirs
  ensure_env
  load_dev_env_file
  export AI_SERVICE_URL="${AI_SERVICE_URL:-http://localhost:33336}"
  configure_database_env
  cmd_down >/dev/null 2>&1 || true
  : > "$PID_FILE"

  for spec in "${SERVICES[@]}"; do
    IFS=":" read -r name port <<< "$spec"
    start_service "$name" "$port"
  done

  cmd_ps
}

cmd_seed() {
  ensure_dirs
  ensure_env
  load_dev_env_file
  configure_database_env

  seed_service "user-service"
  seed_service "board-service"
  seed_service "comment-service"
}

cmd_down() {
  if [[ -f "$PID_FILE" ]]; then
    while read -r name pid port log_file; do
      if [[ -n "${pid:-}" ]] && is_running "$pid"; then
        kill "$pid" >/dev/null 2>&1 || true
        echo "[INFO] stopped $name pid=$pid"
      fi
    done < "$PID_FILE"

    rm -f "$PID_FILE"
  fi

  for spec in "${SERVICES[@]}"; do
    IFS=":" read -r _name port <<< "$spec"
    stop_port "$port"
  done
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
  seed      Create tables and insert deterministic development seed data

Examples:
  ./dev.sh up
  ./dev.sh seed
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
    seed) cmd_seed ;;
    -h|--help|help|"") usage ;;
    *) echo "Unknown command: $cmd" >&2; echo; usage; exit 1 ;;
  esac
}

main "$@"
