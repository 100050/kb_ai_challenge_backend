#!/usr/bin/env bash

set -Eeuo pipefail

BACKEND_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "오류: '$1' 명령을 찾을 수 없습니다." >&2
    exit 1
  fi
}

require_command docker
require_command uv
docker compose version >/dev/null

cd "${BACKEND_DIR}"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "생성: .env"
fi

echo "백엔드 의존성을 확인합니다."
uv sync

echo "PostgreSQL을 시작합니다."
docker compose up -d db

echo "PostgreSQL이 준비될 때까지 기다립니다."
for attempt in {1..30}; do
  if docker compose exec -T db \
    sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    >/dev/null 2>&1; then
    break
  fi

  if [[ "${attempt}" -eq 30 ]]; then
    echo "오류: PostgreSQL이 제한 시간 안에 준비되지 않았습니다." >&2
    exit 1
  fi
  sleep 1
done

echo "DB 마이그레이션을 적용합니다."
uv run alembic upgrade head

echo "백엔드 개발 서버를 시작합니다: http://localhost:8080"
exec uv run uvicorn app.main:app --reload --port 8080
