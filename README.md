# KB Housing AI Backend

청년 사용자가 후보 매물과 재무 정보를 비교하고 주거 의사결정을 내릴 수 있도록 지원하는 FastAPI 백엔드입니다. 개발 서버는 기본적으로 `http://localhost:8080`에서 실행하며 API 계약은 `Housing_AI_API_List.md`를 참고합니다.

## 요구 사항

- Python 3.10 이상
- [uv](https://docs.astral.sh/uv/)
- Docker 및 Docker Compose

PostgreSQL을 운영체제에 직접 설치할 필요는 없습니다. 로컬 DB는 `compose.yaml`의 PostgreSQL 컨테이너를 사용합니다.

## 로컬 실행

저장소 루트가 아닌 `backend/`에서 다음 명령을 실행합니다.

```bash
uv sync
cp .env.example .env
docker compose up -d db
docker compose ps
uv run fastapi dev main.py --port 8080
```

서버가 실행되면 다음 주소를 확인합니다.

- API: `http://localhost:8080`
- Swagger UI: `http://localhost:8080/docs`
- OpenAPI JSON: `http://localhost:8080/openapi.json`

현재 애플리케이션에는 기본 루트 엔드포인트만 구현되어 있습니다. 문서에 정의된 `/api/v1` 엔드포인트는 개발 과정에서 추가합니다.

## PostgreSQL 초기화

최초 `docker compose up -d db` 실행 시 다음 기본값으로 데이터베이스와 사용자가 생성됩니다.

| 항목 | 기본값 |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `housing_ai` |
| User | `housing_ai` |
| Password | `.env`의 `POSTGRES_PASSWORD` |

컨테이너 상태와 접속을 확인합니다.

```bash
docker compose ps
docker compose exec db pg_isready -U housing_ai -d housing_ai
docker compose exec db psql -U housing_ai -d housing_ai
```

`psql`을 종료하려면 `\q`를 입력합니다. DB를 중지해도 named volume에 데이터가 유지됩니다.

```bash
docker compose down
```

로컬 데이터를 완전히 삭제하고 새 DB로 초기화할 때만 다음 명령을 사용합니다.

```bash
docker compose down -v
docker compose up -d db
```

`down -v`는 로컬 PostgreSQL 데이터를 복구할 수 없게 삭제하므로 필요한 데이터가 없는지 먼저 확인합니다.

## 환경변수

`.env.example`을 복사해 `.env`를 만들고 실제 비밀값은 커밋하지 않습니다.

```env
DATABASE_URL=postgresql+asyncpg://housing_ai:local_dev_password@localhost:5432/housing_ai
AI_API_KEY=
```

운영에서는 `DATABASE_URL`을 AWS RDS PostgreSQL 주소로 교체합니다. Docker Compose는 로컬 개발에서만 사용합니다.

## 스키마 마이그레이션

SQLAlchemy, asyncpg, Alembic은 아직 프로젝트 의존성에 추가되지 않았습니다. 도입 후에는 모든 테이블 변경을 Alembic revision으로 관리하고 다음 명령을 표준으로 사용합니다.

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe schema change"
```

애플리케이션 시작 시 임의로 테이블을 생성하지 말고, 로컬과 RDS에 동일한 migration을 적용합니다.
