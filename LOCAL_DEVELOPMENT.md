# 백엔드 로컬 실행

이 문서는 FastAPI 백엔드와 PostgreSQL만 로컬에서 실행하는 방법을
설명합니다. 프론트엔드는 필요하지 않습니다.

## 준비 사항

- Docker 및 Docker Compose
- Python 3.10 이상
- [uv](https://docs.astral.sh/uv/)

## 실행

`backend/` 디렉터리에서 다음 명령을 실행합니다.

```bash
./run-local.sh
```

스크립트는 다음 작업을 수행합니다.

1. `.env`가 없으면 `.env.example`을 복사합니다.
2. Python 패키지를 설치합니다.
3. PostgreSQL 컨테이너를 시작하고 준비 상태를 확인합니다.
4. Alembic 마이그레이션을 적용합니다.
5. FastAPI 개발 서버를 시작합니다.

- 백엔드 API: <http://localhost:8080>
- Swagger UI: <http://localhost:8080/docs>
- 상태 확인: <http://localhost:8080/api/v1/health>

종료하려면 실행 중인 터미널에서 `Ctrl+C`를 누릅니다. PostgreSQL은 계속
실행되며 다음 명령으로 중지할 수 있습니다.

```bash
docker compose down
```

`docker compose down -v`는 로컬 DB 데이터를 삭제하므로 데이터가 필요 없는
경우에만 사용합니다.

## 수동 실행

```bash
cp .env.example .env
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8080
```
