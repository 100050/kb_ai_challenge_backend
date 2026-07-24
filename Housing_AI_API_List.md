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
        "field": "after_tax_monthly_income",
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
  "current_step": "cash_flow",
  "progress": 0,
  "created_at": "2026-07-23T03:00:00Z"
}
```

### `GET /analyses/{analysis_id}`

저장된 입력과 진행 상태를 조회합니다. 아직 입력하지 않은 공통 입력 단계는 `null`이며, 저장된 매물이 없으면 `housing_plans`는 빈 배열입니다.
`housing_plans`에는 매물 목록 조회와 동일한 요약 정보가 포함됩니다.

`200 OK`

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "current_step": "financial_goals",
  "progress": 33,
  "cash_flow": {
    "after_tax_monthly_income": 3500000,
    "monthly_living_expenses_excluding_housing_and_transport": 1300000,
    "existing_loan_monthly_payment": 200000,
    "target_monthly_savings": 700000,
    "monthly_safety_margin": 300000
  },
  "financial_goals": null,
  "housing_plans": [],
  "created_at": "2026-07-23T03:00:00Z",
  "updated_at": "2026-07-23T03:20:00Z"
}
```

### `DELETE /analyses/{analysis_id}`

분석과 연결된 임시 데이터 및 대화를 삭제합니다.

`204 No Content` — 응답 본문 없음

## 2. 단계별 입력

입력 순서는 `소득·생활비 → 자산·재무 목표 → 후보 매물·대출·추가 비용`입니다.
모든 `PATCH` 요청은 JSON에 포함된 필드만 수정하고 생략한 필드는 기존 값을 유지합니다.
필드에 `null`을 명시하면 저장된 값을 비웁니다.
따라서 동일한 API를 입력 중 임시저장과 완성된 값 수정에 함께 사용합니다.
매물은 별도 CRUD API로 생성하고 각 매물의 `PATCH` 요청으로 수정합니다.

### `PATCH /analyses/{analysis_id}/cash-flow`

1단계에서 반복적으로 발생하는 월 현금유입과 월 현금유출 목표를 입력합니다.

- `after_tax_monthly_income`: 매월 반복적으로 확보할 수 있는 세후 현금유입
- `monthly_living_expenses_excluding_housing_and_transport`: 주거비와 교통비를 제외한 월 생활비
- `existing_loan_monthly_payment`: 입주 이후에도 계속 납부하는 기존 대출의 월 원리금 상환액

일회성 용돈이나 당첨금 등은 월 현금유입으로 입력하지 않습니다. 이미 수령해 실제로 사용할 수 있는 금액은 `available_cash`에 포함합니다.

요청:

```json
{
  "after_tax_monthly_income": 3500000,
  "monthly_living_expenses_excluding_housing_and_transport": 1300000,
  "existing_loan_monthly_payment": 200000
}
```

`200 OK`:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "cash_flow": {
    "after_tax_monthly_income": 3500000,
    "monthly_living_expenses_excluding_housing_and_transport": 1300000,
    "existing_loan_monthly_payment": 200000
  },
  "current_step": "financial_goals",
  "progress": 33
}
```

### `PATCH /analyses/{analysis_id}/financial-goals`

2단계에서 새 계약에 사용할 수 있는 현금성 자산과 반드시 남겨둘 자금을 입력합니다.

- `target_monthly_savings`: 적금, 청약, 투자 등 매월 유지하려는 저축·투자 금액
- `monthly_safety_margin`: 예정 지출과 목표 저축 이후에도 남겨두려는 월 완충 금액
- `available_cash`: 새 계약에 실제로 사용할 수 있는 현금성 자산
- `minimum_emergency_fund`: 입주 후에도 보유하려는 최소 유동자산
- `recoverable_existing_rental_deposit`: 새 계약 보증금 지급 전까지 반환받을 수 있는 기존 임차보증금

요청:

```json
{
  "target_monthly_savings": 700000,
  "monthly_safety_margin": 300000,
  "available_cash": 75000000,
  "minimum_emergency_fund": 10000000,
  "recoverable_existing_rental_deposit": 20000000
}
```

`200 OK`:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "financial_goals": {
    "target_monthly_savings": 700000,
    "monthly_safety_margin": 300000,
    "available_cash": 75000000,
    "minimum_emergency_fund": 10000000,
    "recoverable_existing_rental_deposit": 20000000
  },
  "current_step": "housing_plan",
  "progress": 67
}
```

### 매물별 입력

3단계의 후보 매물은 분석에 종속된 별도 리소스로 저장합니다.

- 하나의 분석은 0개 이상의 임시 매물을 저장할 수 있습니다.
- 평가를 시작하려면 완성된 매물이 1개 이상 N개 이하이어야 합니다. N은 서비스에서 정한 최대 비교 가능 매물 수입니다.
- 서버가 매물을 생성할 때 UUID 형식의 `property_id`를 발급합니다.
- 매물 조회, 수정 및 삭제 시 `analysis_id`와 `property_id`가 모두 일치해야 합니다.
- 분석을 삭제하면 해당 분석에 연결된 모든 매물도 함께 삭제됩니다.
- 구매는 고려하지 않으며 `housing_type`은 `jeonse`, `monthly_rent` 중 하나입니다.
- `monthly_rent`는 전세인 경우 `0`입니다.
- `utilities`는 관리비에 포함되지 않은 월 공과금입니다.
- `transportation_cost`는 해당 매물에 입주했을 때 예상되는 월 교통비입니다.
- 대출 계획과 중개보수, 이사비, 기타 입주비는 매물마다 별도로 저장합니다.
- 보증금 대출은 만기일시상환 방식만 고려합니다. 대출원금은 월 현금유출에 포함하지 않고 월 이자만 반영합니다.
- 대출을 사용하지 않는 매물은 `loan_plan.deposit_loan_amount`와 `loan_plan.annual_interest_rate`를 모두 `0`으로 입력합니다.
- `name`, `address`, `housing_type`, 모든 비용 필드, `loan_plan`, `additional_costs`가 유효하게 입력되면 `is_complete`가 `true`가 됩니다.

매물 초안이 하나라도 미완성 상태이면 `current_step`은 `housing_plan`, `progress`는 `67`입니다.
1개 이상의 모든 저장 매물이 완성되면 `current_step`은 `confirmation`, `progress`는 `100`입니다.

#### `POST /analyses/{analysis_id}/housing-plans`

분석에 연결된 매물 초안을 생성합니다. 서버가 `property_id`를 발급하므로 요청에 ID를 포함하지 않습니다.
임시저장을 위해 요청 본문은 비어 있거나 일부 필드만 포함할 수 있습니다.
저장된 매물이 N개이면 `409 HOUSING_PLAN_LIMIT_REACHED`를 반환합니다.

요청:

```json
{
  "name": "역삼 원룸"
}
```

`201 Created`:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "property_id": "43b49e66-0fa2-4e0d-aee6-2f6cbc827290",
  "name": "역삼 원룸",
  "address": null,
  "housing_type": null,
  "deposit": null,
  "monthly_rent": null,
  "maintenance_fee": null,
  "utilities": null,
  "transportation_cost": null,
  "loan_plan": null,
  "additional_costs": null,
  "is_complete": false,
  "created_at": "2026-07-23T03:21:00Z",
  "updated_at": "2026-07-23T03:21:00Z"
}
```

#### `GET /analyses/{analysis_id}/housing-plans`

분석에 저장된 모든 매물을 생성 순서대로 조회합니다.

`200 OK`:

```json
{
  "housing_plans": [
    {
      "property_id": "43b49e66-0fa2-4e0d-aee6-2f6cbc827290",
      "name": "역삼 원룸",
      "housing_type": "monthly_rent",
      "is_complete": true,
      "updated_at": "2026-07-23T03:25:00Z"
    },
    {
      "property_id": "bab7a2d4-d056-41f9-9f69-90a0bd7a72ac",
      "name": "신림 오피스텔",
      "housing_type": "jeonse",
      "is_complete": false,
      "updated_at": "2026-07-23T03:26:00Z"
    }
  ]
}
```

저장된 매물이 없으면 `housing_plans`는 빈 배열입니다.

#### `GET /analyses/{analysis_id}/housing-plans/{property_id}`

분석에 속한 매물 하나와 해당 매물의 대출 계획 및 추가 비용을 조회합니다.

`200 OK` 응답은 아래 수정 응답과 동일한 형태입니다.
해당 분석에 속하지 않는 매물이면 `404 HOUSING_PLAN_NOT_FOUND`를 반환합니다.

#### `PATCH /analyses/{analysis_id}/housing-plans/{property_id}`

매물의 입력된 필드만 부분 수정합니다. `loan_plan` 또는 `additional_costs`를 전달하면 해당 중첩 객체 전체를 교체합니다.

요청:

```json
{
  "name": "역삼 원룸",
  "address": "서울특별시 강남구 역삼동",
  "housing_type": "monthly_rent",
  "deposit": 10000000,
  "monthly_rent": 700000,
  "maintenance_fee": 100000,
  "utilities": 50000,
  "transportation_cost": 80000,
  "loan_plan": {
    "deposit_loan_amount": 0,
    "annual_interest_rate": 0
  },
  "additional_costs": {
    "brokerage_fee": 300000,
    "moving_cost": 1000000,
    "other_move_in_cost": 300000
  }
}
```

`200 OK`:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "property_id": "43b49e66-0fa2-4e0d-aee6-2f6cbc827290",
  "name": "역삼 원룸",
  "address": "서울특별시 강남구 역삼동",
  "housing_type": "monthly_rent",
  "deposit": 10000000,
  "monthly_rent": 700000,
  "maintenance_fee": 100000,
  "utilities": 50000,
  "transportation_cost": 80000,
  "loan_plan": {
    "deposit_loan_amount": 0,
    "annual_interest_rate": 0
  },
  "additional_costs": {
    "brokerage_fee": 300000,
    "moving_cost": 1000000,
    "other_move_in_cost": 300000
  },
  "is_complete": true,
  "created_at": "2026-07-23T03:21:00Z",
  "updated_at": "2026-07-23T03:25:00Z"
}
```

#### `DELETE /analyses/{analysis_id}/housing-plans/{property_id}`

분석에 속한 매물과 해당 매물의 대출 계획 및 추가 비용을 삭제합니다.

`204 No Content` — 응답 본문 없음

해당 분석에 속하지 않는 매물이면 `404 HOUSING_PLAN_NOT_FOUND`를 반환합니다.
마지막 완성 매물을 삭제하면 분석 진행 상태는 `current_step: "housing_plan"`, `progress: 67`로 돌아갑니다.

## 3. 분석 실행 및 결과

### `POST /analyses/{analysis_id}/evaluation`

저장된 입력을 검증하고 평가를 시작합니다.
완성된 공통 입력과 1개 이상 N개 이하의 완성된 매물이 필요하며, 미완성 매물이 하나라도 남아 있으면 `409 ANALYSIS_NOT_READY`를 반환합니다.
중복 실행 중이면 `409 Conflict`를 반환합니다.

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
  "recommended_property_id": "bab7a2d4-d056-41f9-9f69-90a0bd7a72ac",
  "summary": "신림 오피스텔이 월 부담과 비상자금 유지 측면에서 가장 적합합니다.",
  "candidates": [
    {
      "property_id": "43b49e66-0fa2-4e0d-aee6-2f6cbc827290",
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
        "monthly_housing_cost": 930000,
        "monthly_surplus": 70000,
        "debt_service_ratio": 5.7
      },
      "initial_cash_required": 11600000,
      "warnings": [
        "목표 저축과 월 완충금 반영 후 잔여 현금이 70000원입니다."
      ]
    },
    {
      "property_id": "bab7a2d4-d056-41f9-9f69-90a0bd7a72ac",
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
        "monthly_housing_cost": 601667,
        "monthly_surplus": 398333,
        "debt_service_ratio": 14.0
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
