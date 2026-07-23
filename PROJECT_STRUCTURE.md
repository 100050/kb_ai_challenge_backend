# 프로젝트 구조

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── db.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       ├── analyses.py
│   │       ├── evaluations.py
│   │       └── chat.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── analysis.py
│   │   ├── evaluation.py
│   │   └── chat.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── evaluation.py
│   │   └── conversation.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── evaluation.py
│   │   └── conversation.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── evaluation.py
│   │   ├── affordability.py
│   │   ├── repayment.py
│   │   ├── risk.py
│   │   └── chat.py
│   │
│   └── ai/
│       ├── __init__.py
│       ├── ports.py
│       ├── schemas.py
│       ├── agent.py
│       └── adapters/
│           ├── __init__.py
│           └── provider.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   └── services/
│   │       ├── test_affordability.py
│   │       ├── test_repayment.py
│   │       └── test_risk.py
│   ├── api/
│   │   ├── test_analyses.py
│   │   ├── test_evaluations.py
│   │   └── test_chat.py
│   └── integration/
│       ├── repositories/
│       ├── test_migrations.py
│       ├── test_transactions.py
│       └── test_sse.py
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
├── compose.yaml
├── pyproject.toml
├── uv.lock
├── .env
├── .env.example
├── AGENTS.md
├── Housing_AI_API_List.md
└── README.md
```

## 디렉터리 책임

- `app/main.py`: FastAPI 애플리케이션 생성 및 최상위 라우터 등록
- `app/db.py`: 비동기 SQLAlchemy 엔진, 세션 팩토리, `Base`, 세션 의존성 제공
- `app/core/`: 환경변수와 애플리케이션 공통 설정
- `app/api/`: HTTP 요청 처리, 검증 오류 변환, 서비스 호출 및 응답 생성
- `app/schemas/`: Pydantic 요청·응답 모델
- `app/models/`: SQLAlchemy 영속성 모델
- `app/repositories/`: PostgreSQL 조회 및 저장
- `app/services/`: 분석 흐름과 결정론적 금융 계산
- `app/ai/`: AI 에이전트, 구조화 출력, 제공자별 어댑터
- `tests/unit/`: DB나 외부 AI 없이 실행되는 도메인 단위 테스트
- `tests/api/`: FastAPI 요청, 응답 및 유효성 검사 테스트
- `tests/integration/`: 저장소, 트랜잭션, 마이그레이션 및 SSE 통합 테스트
- `alembic/versions/`: 적용 순서가 보존되는 데이터베이스 스키마 변경 이력

## 의존 방향

```text
API router
    └── service
        ├── repository
        │   └── database
        ├── deterministic financial calculation
        └── AI port
            └── provider adapter
```

라우터는 요청 검증과 응답 처리만 담당하고 비즈니스 로직은 서비스에 위임한다.
금융 수치 계산은 AI가 아닌 `services/`의 결정론적 코드에서 수행한다.
AI는 승인된 데이터와 계산 결과를 바탕으로 설명을 생성한다.

## 구조 확장 기준

- `db.py`가 엔진과 세션 제공만 담당하는 동안에는 단일 파일로 유지한다.
- 읽기·쓰기 DB 분리, 트랜잭션 관리자 또는 여러 세션 정책이 필요해지면 `app/db/` 패키지로 분리한다.
- 각 영역의 파일이 커지면 `analysis.py` 같은 단일 파일을 동일한 이름의 패키지로 확장한다.
- 사용하지 않는 폴더와 추상화는 미리 생성하지 않고, 해당 기능의 테스트를 작성할 때 추가한다.

## 표준 명령

```bash
docker compose up -d db
uv sync
uv run pytest
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8080
```
