# 청년 주거 금융 도우미 API 명세

## 기본 규칙

- Base URL: `/api/v1`
- 요청 및 일반 응답: `application/json`
- 챗봇 및 진행 이벤트: `text/event-stream`
- 금액 단위: 원(KRW), 소수점 없는 정수
- 비율 단위: 퍼센트(%), 예: `3.5`는 연 3.5%
- 날짜와 시간: ISO 8601 UTC 문자열
- 아직 구현 전인 초안 계약이며 개발 중 변경 시 프론트엔드와 함께 갱신합니다.

## 공통 오류 응답

모든 오류는 같은 형태를 사용합니다.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해 주세요.",
    "details": [
      {
        "field": "monthly_income",
        "reason": "0보다 커야 합니다."
      }
    ]
  }
}
```

주요 상태 코드는 `400` 잘못된 요청, `404` 분석 없음, `409` 현재 상태와 충돌, `422` 필드 검증 실패, `500` 서버 오류입니다.

## 1. 분석 생성 및 조회

### `POST /analyses`

새 분석을 생성합니다. 요청 본문은 없습니다.

`201 Created`

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "current_step": "properties",
  "progress": 0,
  "created_at": "2026-07-23T03:00:00Z"
}
```

### `GET /analyses/{analysis_id}`

저장된 입력과 진행 상태를 조회합니다. 아직 입력하지 않은 단계는 `null`입니다.

`200 OK`

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "current_step": "financial_goals",
  "progress": 50,
  "properties": [
    {
      "property_id": "property-1",
      "name": "역삼 원룸",
      "address": "서울특별시 강남구 역삼동",
      "housing_type": "monthly_rent",
      "deposit": 10000000,
      "monthly_rent": 700000,
      "maintenance_fee": 100000,
      "area_m2": 24.5
    }
  ],
  "cash_flow": {
    "monthly_income": 3500000,
    "monthly_living_expenses": 1500000,
    "monthly_debt_payment": 200000
  },
  "financial_goals": null,
  "loan_plan": null,
  "created_at": "2026-07-23T03:00:00Z",
  "updated_at": "2026-07-23T03:20:00Z"
}
```

### `DELETE /analyses/{analysis_id}`

분석과 연결된 임시 데이터 및 대화를 삭제합니다.

`204 No Content` — 응답 본문 없음

## 2. 단계별 입력

각 `PATCH` 요청은 해당 단계 전체를 교체하며 저장된 최신 값을 반환합니다.

### `PATCH /analyses/{analysis_id}/properties`

후보 매물은 1개 이상 3개 이하입니다. `housing_type`은 `jeonse`, `monthly_rent`, `purchase` 중 하나입니다.

요청:

```json
{
  "properties": [
    {
      "property_id": "property-1",
      "name": "역삼 원룸",
      "address": "서울특별시 강남구 역삼동",
      "housing_type": "monthly_rent",
      "deposit": 10000000,
      "monthly_rent": 700000,
      "purchase_price": null,
      "maintenance_fee": 100000,
      "area_m2": 24.5
    },
    {
      "property_id": "property-2",
      "name": "신림 오피스텔",
      "address": "서울특별시 관악구 신림동",
      "housing_type": "jeonse",
      "deposit": 180000000,
      "monthly_rent": 0,
      "purchase_price": null,
      "maintenance_fee": 130000,
      "area_m2": 29.8
    }
  ]
}
```

`200 OK`:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "properties": [
    {
      "property_id": "property-1",
      "name": "역삼 원룸",
      "address": "서울특별시 강남구 역삼동",
      "housing_type": "monthly_rent",
      "deposit": 10000000,
      "monthly_rent": 700000,
      "purchase_price": null,
      "maintenance_fee": 100000,
      "area_m2": 24.5
    },
    {
      "property_id": "property-2",
      "name": "신림 오피스텔",
      "address": "서울특별시 관악구 신림동",
      "housing_type": "jeonse",
      "deposit": 180000000,
      "monthly_rent": 0,
      "purchase_price": null,
      "maintenance_fee": 130000,
      "area_m2": 29.8
    }
  ],
  "current_step": "cash_flow",
  "progress": 25
}
```

### `PATCH /analyses/{analysis_id}/cash-flow`

요청:

```json
{
  "monthly_income": 3500000,
  "monthly_living_expenses": 1500000,
  "monthly_debt_payment": 200000
}
```

`200 OK`:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "cash_flow": {
    "monthly_income": 3500000,
    "monthly_living_expenses": 1500000,
    "monthly_debt_payment": 200000
  },
  "current_step": "financial_goals",
  "progress": 50
}
```

### `PATCH /analyses/{analysis_id}/financial-goals`

요청:

```json
{
  "current_assets": 50000000,
  "emergency_fund_target": 10000000,
  "monthly_savings_target": 700000,
  "housing_goal": "monthly_cost_reduction",
  "target_move_in_date": "2026-10-01"
}
```

`housing_goal`은 `monthly_cost_reduction`, `asset_growth`, `commute`, `stability` 중 하나입니다.

`200 OK`:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "financial_goals": {
    "current_assets": 50000000,
    "emergency_fund_target": 10000000,
    "monthly_savings_target": 700000,
    "housing_goal": "monthly_cost_reduction",
    "target_move_in_date": "2026-10-01"
  },
  "current_step": "loan_plan",
  "progress": 75
}
```

### `PATCH /analyses/{analysis_id}/loan-plan`

대출을 사용하지 않으면 `loan_amount`를 `0`으로 전송합니다.

요청:

```json
{
  "loan_amount": 100000000,
  "annual_interest_rate": 3.5,
  "term_months": 24,
  "repayment_type": "equal_payment",
  "brokerage_fee": 600000,
  "moving_cost": 1000000,
  "other_initial_cost": 300000
}
```

`repayment_type`은 `equal_payment`, `equal_principal`, `bullet` 중 하나입니다.

`200 OK`:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "loan_plan": {
    "loan_amount": 100000000,
    "annual_interest_rate": 3.5,
    "term_months": 24,
    "repayment_type": "equal_payment",
    "brokerage_fee": 600000,
    "moving_cost": 1000000,
    "other_initial_cost": 300000
  },
  "current_step": "confirmation",
  "progress": 100
}
```

## 3. 분석 실행 및 결과

### `POST /analyses/{analysis_id}/evaluation`

저장된 입력을 검증하고 평가를 시작합니다. 중복 실행 중이면 `409 Conflict`를 반환합니다.

`202 Accepted`

```json
{
  "evaluation_id": "eval-7d590a34",
  "status": "queued",
  "progress": 0
}
```

### `GET /analyses/{analysis_id}/evaluation`

`200 OK`

```json
{
  "evaluation_id": "eval-7d590a34",
  "status": "processing",
  "current_stage": "financial_suitability",
  "progress": 60,
  "error": null,
  "updated_at": "2026-07-23T03:30:00Z"
}
```

`status`는 `queued`, `processing`, `completed`, `failed` 중 하나입니다.

### `GET /analyses/{analysis_id}/evaluation/events`

각 SSE 메시지는 `event`와 JSON `data`로 구성됩니다.

```text
event: progress
data: {"status":"processing","stage":"price_fairness","progress":30}

event: completed
data: {"status":"completed","progress":100}
```

실패 시 `event: failed`를 전송하고 스트림을 종료합니다.

### `GET /analyses/{analysis_id}/result`

평가가 끝나지 않았으면 `409 Conflict`를 반환합니다.

`200 OK`

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "recommended_property_id": "property-2",
  "summary": "신림 오피스텔이 월 부담과 비상자금 유지 측면에서 가장 적합합니다.",
  "candidates": [
    {
      "property_id": "property-1",
      "rank": 2,
      "total_score": 72,
      "price_fairness": {
        "status": "reasonable",
        "score": 76,
        "comment": "입력된 조건에서 보증금과 월세가 허용 범위에 있습니다."
      },
      "financial_suitability": {
        "status": "caution",
        "score": 68,
        "monthly_housing_cost": 800000,
        "monthly_surplus": 300000,
        "debt_service_ratio": 28.6
      },
      "initial_cash_required": 11900000,
      "warnings": [
        "월 저축 목표를 400000원 초과합니다."
      ]
    },
    {
      "property_id": "property-2",
      "rank": 1,
      "total_score": 84,
      "price_fairness": {
        "status": "reasonable",
        "score": 82,
        "comment": "전세 보증금 대비 예상 금융비용이 적정합니다."
      },
      "financial_suitability": {
        "status": "suitable",
        "score": 87,
        "monthly_housing_cost": 421667,
        "monthly_surplus": 678333,
        "debt_service_ratio": 12.0
      },
      "initial_cash_required": 81900000,
      "warnings": []
    }
  ],
  "generated_at": "2026-07-23T03:31:00Z"
}
```

평가 수치와 순위는 결정론적 도메인 로직이 계산합니다. AI는 저장된 결과의 설명만 생성합니다.

## 4. 챗봇

### `POST /analyses/{analysis_id}/chat/messages`

요청:

```json
{
  "message": "추천 매물을 선택한 이유를 쉽게 설명해 줘."
}
```

`200 OK`, `text/event-stream`:

```text
event: message_start
data: {"message_id":"msg-a831","role":"assistant"}

event: message_delta
data: {"message_id":"msg-a831","content":"신림 오피스텔은 "}

event: message_delta
data: {"message_id":"msg-a831","content":"매달 남는 금액이 더 많습니다."}

event: message_end
data: {"message_id":"msg-a831","created_at":"2026-07-23T03:40:00Z"}
```

### `GET /analyses/{analysis_id}/chat/messages`

`200 OK`

```json
{
  "messages": [
    {
      "message_id": "msg-a830",
      "role": "user",
      "content": "추천 매물을 선택한 이유를 쉽게 설명해 줘.",
      "created_at": "2026-07-23T03:39:58Z"
    },
    {
      "message_id": "msg-a831",
      "role": "assistant",
      "content": "신림 오피스텔은 매달 남는 금액이 더 많습니다.",
      "created_at": "2026-07-23T03:40:00Z"
    }
  ]
}
```

### `DELETE /analyses/{analysis_id}/chat/messages`

현재 분석의 대화 기록을 초기화합니다. 분석 입력과 평가 결과는 삭제하지 않습니다.

`204 No Content` — 응답 본문 없음
