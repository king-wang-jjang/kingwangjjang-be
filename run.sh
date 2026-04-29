#!/usr/bin/env bash

set -euo pipefail

COMPOSE_CMD="docker compose"
NETWORK_NAME="kingwangjjang-network"

has_cmd() {
	command -v "$1" >/dev/null 2>&1
}

detect_compose() {
	if docker compose version >/dev/null 2>&1; then
		COMPOSE_CMD="docker compose"
		return
	fi
	if has_cmd docker-compose; then
		COMPOSE_CMD="docker-compose"
		return
	fi
	echo "[ERROR] Docker Compose가 설치되어 있지 않습니다. Docker Desktop 또는 docker-compose를 설치하세요." >&2
	exit 1
}

ensure_network() {
	if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
		echo "[INFO] 네트워크가 없어 생성합니다: $NETWORK_NAME"
		docker network create "$NETWORK_NAME"
	fi
}

ensure_logs_dir() {
	mkdir -p logs
}

ensure_env() {
	if [[ ! -f .env ]]; then
		if [[ -f .env.example ]]; then
			echo "[INFO] .env가 없어 .env.example을 복사합니다"
			cp .env.example .env
		else
			echo "[WARN] .env 파일이 없습니다. 필요 시 루트에 .env를 생성하세요." >&2
		fi
	fi
}

cmd_up() {
	detect_compose
	ensure_logs_dir
	ensure_network
	ensure_env
	$COMPOSE_CMD up -d
	$COMPOSE_CMD ps
}

cmd_down() {
	detect_compose
	$COMPOSE_CMD down
}

cmd_restart() {
	detect_compose
	$COMPOSE_CMD down
	cmd_up
}

cmd_logs() {
	detect_compose
	$COMPOSE_CMD logs -f --tail=200
}

cmd_ps() {
	detect_compose
	$COMPOSE_CMD ps
}

cmd_pull() {
	detect_compose
	$COMPOSE_CMD pull
}

cmd_clean() {
	detect_compose
	$COMPOSE_CMD down -v --remove-orphans
}

usage() {
	cat <<'USAGE'
사용법: ./run.sh <command>

명령어:
  up        컨테이너 실행 (백그라운드)
  down      컨테이너 종료
  restart   재시작 (down → up)
  logs      전체 로그 팔로우
  ps        서비스 상태 확인
  pull      최신 이미지 받기
  clean     모든 볼륨/고아 컨테이너 포함 정리

예시:
  ./run.sh up
  ./run.sh logs
USAGE
}

main() {
	cmd="${1:-}"
	case "$cmd" in
		up) shift; cmd_up "$@" ;;
		down) shift; cmd_down "$@" ;;
		restart) shift; cmd_restart "$@" ;;
		logs) shift; cmd_logs "$@" ;;
		ps) shift; cmd_ps "$@" ;;
		pull) shift; cmd_pull "$@" ;;
		clean) shift; cmd_clean "$@" ;;
		-h|--help|help|"") usage ;;
		*) echo "알 수 없는 명령어: $cmd" >&2; echo; usage; exit 1 ;;
	 esac
}

main "$@"


