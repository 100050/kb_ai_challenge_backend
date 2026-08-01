# 청년 주거 금융 도우미 API 명세

## 기본 규칙

- Base URL: `/api/v1`
- 요청 및 일반 응답: `application/json`
- 챗봇 및 진행 이벤트: `text/event-stream`
- 금액 단위: 원(KRW), 소수점 없는 정수
- 비율 단위: 퍼센트(%), 예: `3.5`는 연 3.5%
- 날짜와 시간: ISO 8601 UTC 문자열
- 현재 백엔드 구현을 기준으로 작성한 계약이며 변경 시 프론트엔드와 함께 갱신합니다.

## 공통 오류 응답

일반 JSON API의 오류는 같은 형태를 사용합니다.

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

단, 챗봇 메시지 API는 SSE 연결을 먼저 수립하므로 메시지 처리 중 발생한
오류를 HTTP 오류 응답 대신 `event: error`로 전달할 수 있습니다.

```text
event: error
data: {"code":"ANALYSIS_NOT_FOUND"}
```

### 공통 입력 검증

- 모든 금액: `0` 이상의 정수
- 연이자율: `0` 이상의 숫자이며 `3.5`는 연 3.5%를 의미
- 전용면적: `0`보다 큰 숫자, 단위는 ㎡
- 매물 이름: 1~100자
- 주소: 1~255자
- 챗봇 메시지: 1~4000자

### 상태값

| 구분 | 값 |
| --- | --- |
| 분석 상태 | `draft`, `evaluating`, `completed`, `failed` |
| 입력 단계 | `cash_flow`, `financial_goals`, `housing_plan`, `confirmation` |
| 초기자금 상태 | `insufficient_initial_funds`, `emergency_fund_shortfall`, `sufficient` |
| 월 현금흐름 상태 | `essential_expense_deficit`, `savings_target_shortfall`, `safety_margin_shortfall`, `sufficient` |
| 1년 재무목표 상태 | `below_target`, `target_met`, `above_target` |
| 가격 적정성 상태 | `available`, `unavailable` |
| 챗봇 응답 상태 | `completed`, `failed` |

### `GET /health`

백엔드 API가 요청을 받을 수 있는지 확인합니다.

`200 OK`

```json
{
  "status": "ok"
}
```

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
    "existing_loan_monthly_payment": 200000
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
- `recoverable_existing_rental_deposit`: 향후 반환받을 수 있는 기존 임차보증금
- `existing_rental_deposit_available_before_contract`: 기존 임차보증금을 새 계약일 전에 회수할 수 있는지 여부

기존 임차보증금을 계약일 전에 회수할 수 있으면 초기 가용 자기자금에
포함합니다. 회수할 수 없으면 초기자금에서는 제외하되, 계약 후 회수될
자금으로 보아 `1년 후 예상 재무자원`에는 포함합니다.

요청:

```json
{
  "target_monthly_savings": 700000,
  "monthly_safety_margin": 300000,
  "available_cash": 75000000,
  "minimum_emergency_fund": 10000000,
  "recoverable_existing_rental_deposit": 20000000,
  "existing_rental_deposit_available_before_contract": false
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
    "recoverable_existing_rental_deposit": 20000000,
    "existing_rental_deposit_available_before_contract": false
  },
  "current_step": "housing_plan",
  "progress": 67
}
```

### 매물별 입력

3단계의 후보 매물은 분석에 종속된 별도 리소스로 저장합니다.

- 하나의 분석은 0개 이상의 임시 매물을 저장할 수 있습니다.
- 하나의 분석에 저장할 수 있는 매물은 최대 10개입니다.
- 평가를 시작하려면 완성된 매물이 1개 이상 10개 이하이어야 합니다.
- 서버가 매물을 생성할 때 UUID 형식의 `property_id`를 발급합니다.
- 매물 조회, 수정 및 삭제 시 `analysis_id`와 `property_id`가 모두 일치해야 합니다.
- 분석을 삭제하면 해당 분석에 연결된 모든 매물도 함께 삭제됩니다.
- 구매는 고려하지 않으며 `housing_type`은 `jeonse`, `monthly_rent` 중 하나입니다.
- `property_type`은 `apartment`, `row_house`, `multi_family`, `officetel`,
  `detached_house`, `multi_household` 중 하나입니다.
- 프론트엔드는 `legal_dong_code`를 입력하지 않습니다. 백엔드가 매물의
  `address`를 이용해 행정안전부 법정동 코드 API를 조회하고, 가격
  적정성 계산에 필요한 지역 코드를 자동으로 결정합니다.
- 응답의 `legal_dong_code`는 서버 내부 처리와 기존 데이터 호환을 위한
  보조 필드이며 `null`일 수 있습니다. 프론트엔드는 이 필드에 의존하지
  않습니다.
- `exclusive_area_m2`는 가격 비교에 사용하는 제곱미터 단위 전용면적입니다.
- `monthly_rent`는 전세인 경우 `0`입니다.
- `utilities`는 관리비에 포함되지 않은 월 공과금입니다.
- `transportation_cost`는 해당 매물에 입주했을 때 예상되는 월 교통비입니다.
- `memo`는 역세권, 엘리베이터, 채광, 소음 등 정량화하기 어려운 매물의
  특징을 기록하는 선택 입력이며 최대 2,000자입니다. 재무 계산에는
  사용하지 않고 매물 조회, 평가 결과와 챗봇 설명에 제공합니다.
- 대출 계획과 중개보수, 이사비, 기타 입주비는 매물마다 별도로 저장합니다.
- 보증금 대출은 만기일시상환 방식만 고려합니다. 대출원금은 월 현금유출에 포함하지 않고 월 이자만 반영합니다.
- 대출을 사용하지 않는 매물은 `loan_plan.deposit_loan_amount`와 `loan_plan.annual_interest_rate`를 모두 `0`으로 입력합니다.
- `name`, `address`, `housing_type`, 모든 비용 필드, `loan_plan`, `additional_costs`가 유효하게 입력되면 `is_complete`가 `true`가 됩니다.
- `property_type`, `exclusive_area_m2`가 없어도 재무 평가는 실행할 수
  있지만 해당 매물의 가격 적정성은 `unavailable`이 될 수 있습니다.
- 주소로 법정동 코드를 찾을 수 없는 경우에도 재무 평가는 유지되고 가격
  적정성만 `unavailable`이 됩니다.

매물 초안이 하나라도 미완성 상태이면 `current_step`은 `housing_plan`, `progress`는 `67`입니다.
1개 이상의 모든 저장 매물이 완성되면 `current_step`은 `confirmation`, `progress`는 `100`입니다.

#### `POST /analyses/{analysis_id}/housing-plans`

분석에 연결된 매물 초안을 생성합니다. 서버가 `property_id`를 발급하므로 요청에 ID를 포함하지 않습니다.
임시저장을 위해 요청 본문은 빈 JSON 객체 `{}`이거나 일부 필드만 포함할
수 있습니다. 요청 본문 자체를 생략하면 `422 VALIDATION_ERROR`를
반환합니다.
저장된 매물이 10개이면 `409 HOUSING_PLAN_LIMIT_REACHED`를 반환합니다.

요청:

```json
{
  "name": "역삼 원룸",
  "memo": "역세권, 엘리베이터 있음"
}
```

`201 Created`:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "property_id": "43b49e66-0fa2-4e0d-aee6-2f6cbc827290",
  "name": "역삼 원룸",
  "memo": "역세권, 엘리베이터 있음",
  "address": null,
  "property_type": null,
  "legal_dong_code": null,
  "exclusive_area_m2": null,
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
      "memo": "역세권, 엘리베이터 있음",
      "housing_type": "monthly_rent",
      "is_complete": true,
      "updated_at": "2026-07-23T03:25:00Z"
    },
    {
      "property_id": "bab7a2d4-d056-41f9-9f69-90a0bd7a72ac",
      "name": "신림 오피스텔",
      "memo": null,
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
  "memo": "역세권, 엘리베이터 있음, 채광 좋음",
  "address": "서울특별시 강남구 역삼동",
  "property_type": "apartment",
  "exclusive_area_m2": 59.8,
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
  "memo": "역세권, 엘리베이터 있음, 채광 좋음",
  "address": "서울특별시 강남구 역삼동",
  "property_type": "apartment",
  "legal_dong_code": null,
  "exclusive_area_m2": 59.8,
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

입력값과 매물 정보가 직전 완료 평가 이후 변경되지 않았고 결과 생성 후
24시간이 지나지 않았다면 저장된 평가의 `evaluation_id`와 결과를 그대로
재사용합니다. 24시간 이상 지났다면 저장된 재무 적합성 결과는 유지하고,
외부 실거래가·전월세전환율 API를 사용하는 매물별 가격 적정성만 갱신한
뒤 `generated_at`을 현재 서버 시각으로 변경합니다. 실제 입력값이
변경되거나 매물이 추가·수정·삭제되면 기존 평가는 무효화되고 전체를 새로
분석합니다. 동일한 값을 다시 `PATCH`하는 것은 변경으로 처리하지 않습니다.

저장된 입력을 검증하고 평가를 시작합니다.
완성된 공통 입력과 1개 이상 10개 이하의 완성된 매물이 필요하며,
미완성 매물이 하나라도 남아 있으면 `409 ANALYSIS_NOT_READY`를
반환합니다.
보증금 대출액이 보증금을 초과한 매물이 있어도
`409 ANALYSIS_NOT_READY`를 반환합니다.
재무 계산은 결정론적으로 수행합니다. 가격 적정성은 법정동 코드,
실거래가 및 전월세전환율 API를 이용하고 결과를 함께 PostgreSQL에
저장합니다. 외부 API 오류는 재무 계산을 실패시키지 않으며 해당 매물의
가격 적정성만 `unavailable`로 반환합니다.

가격 적정성 비교 표본은 해당 매물과 같은 주택 유형의 최근 24개월
전월세 실거래 중 전용면적이 후보 매물의 ±15% 범위인 거래로 구성합니다.
전월세전환율은 먼저 해당 시·군·구의 주택 유형별 값을 조회합니다. 값이
없으면 그 시·군·구를 포함하는 상위 시·도의 동일 주택 유형 전환율을
사용합니다. 두 값이 모두 없으면 같은 지역 순서로 종합주택 전환율을
조회합니다.
주소의 첫 지역명이 `부산시`, `세종시`와 같은 광역자치단체 축약형이면
법정동 조회 전에 `부산광역시`, `세종특별자치시` 등의 공식 명칭으로
자동 변환합니다.

`202 Accepted`

```json
{
  "evaluation_id": "43ddb4d5-2872-40eb-9a44-f341c0b16275",
  "status": "completed",
  "progress": 100
}
```

### `GET /analyses/{analysis_id}/evaluation`

`200 OK`

```json
{
  "evaluation_id": "43ddb4d5-2872-40eb-9a44-f341c0b16275",
  "status": "completed",
  "current_stage": "financial_management",
  "progress": 100,
  "error": null,
  "updated_at": "2026-07-24T03:30:00Z"
}
```

`status`는 `queued`, `processing`, `completed`, `failed` 중 하나입니다.

### `GET /analyses/{analysis_id}/evaluation/events`

현재 평가는 요청 안에서 즉시 완료되므로 저장된 완료 상태를 SSE로 전송하고 스트림을 종료합니다.

```text
event: completed
data: {"status":"completed","stage":"financial_management","progress":100}
```

### `GET /analyses/{analysis_id}/result`

평가 결과가 없으면 `404 EVALUATION_NOT_FOUND`를 반환합니다.

`200 OK`

```json
{
  "result_version": 5,
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "candidates": [
    {
      "property_id": "43b49e66-0fa2-4e0d-aee6-2f6cbc827290",
      "name": "역삼 원룸",
      "memo": "역세권, 엘리베이터 있음, 채광 좋음",
      "initial_funds": {
        "available_cash": 75000000,
        "available_own_funds": 75000000,
        "initial_cash_required": 11600000,
        "post_move_liquid_assets": 63400000,
        "minimum_emergency_fund": 10000000,
        "emergency_fund_gap": 53400000,
        "status": "sufficient"
      },
      "monthly_cash_flow": {
        "monthly_income": 3500000,
        "monthly_housing_and_transport_cost": 930000,
        "essential_monthly_outflow": 2430000,
        "base_monthly_balance": 1070000,
        "target_monthly_savings": 700000,
        "actual_monthly_balance": 370000,
        "monthly_budget_margin": 70000,
        "status": "sufficient"
      },
      "annual_goal": {
        "annual_financial_target": 18400000,
        "expected_resources_after_one_year": 96240000,
        "annual_financial_surplus": 77840000,
        "annual_goal_achievement_rate": 523.04,
        "status": "above_target"
      },
      "overall_financial_status": "all_satisfied",
      "price_appropriateness": {
        "status": "available",
        "sample_count": 38,
        "comparison_mode": "median",
        "median_equivalent_monthly_cost": 880000,
        "difference_from_median": 40000,
        "difference_rate_from_median": 4.55,
        "price_percentile": 72.2,
        "candidate_equivalent_monthly_cost": 920000,
        "comparison_criteria": {
          "lookback_months": 12,
          "district_name": "강남구",
          "property_type": "apartment",
          "area_tolerance_percent": 15
        },
        "samples": [],
        "reason": null
      },
      "ai_interpretation": {
        "summary": [
          "환산 월 임대비용이 비교군 중앙값보다 4.55% 높습니다.",
          "초기자금과 최소 비상자금을 모두 충족합니다.",
          "현재 조건이 유지되면 1년 재무목표를 초과할 것으로 예상됩니다."
        ],
        "strengths": {
          "title": "초기자금·비상자금·재무목표 충족",
          "detail": "입주 후 유동자산과 재무목표 달성률을 근거로 한 해설입니다."
        },
        "burdens": {
          "title": "비교군보다 높은 환산 월 임대비용",
          "detail": "중앙값 대비 가격 차액과 차이율을 함께 확인하세요."
        },
        "things_to_check": {
          "title": "정성적 주거 조건 확인",
          "detail": "매물 메모의 역세권·엘리베이터·채광 정보를 현장에서 확인하세요."
        },
        "evidence_count": 6,
        "suggested_questions": [
          "왜 가격 부담이 높나요?",
          "월세가 5만 원 오르면 어떻게 되나요?",
          "다른 매물과 차이를 정리해줘"
        ]
      },
      "calculation_details": {
        "available_own_funds": 75000000,
        "initially_available_existing_deposit": 0,
        "deferred_existing_deposit": 20000000,
        "self_funded_deposit": 10000000,
        "monthly_deposit_loan_interest": 0,
        "monthly_housing_cash_outflow": 850000,
        "base_monthly_balance": 1070000
      },
      "warnings": []
    }
  ],
  "generated_at": "2026-07-24T03:31:00Z"
}
```

`result_version`은 결과 화면 계약 버전입니다. 현재 버전은 `5`이며 이전
형식으로 저장된 결과는 다음 분석 요청에서 자동으로 다시 계산합니다.

결과는 매물마다 초기자금·유동성, 월 현금흐름, 1년 재무목표의 세 카드를 제공합니다.
프론트엔드는 `initial_funds.available_own_funds`를 계약 활용 가능 총자금,
`monthly_cash_flow.monthly_income`을 월 현금유입으로 표시할 수 있습니다.
`overall_financial_status`가 `all_satisfied`이면 세 재무 기준을 모두
충족한 상태입니다. 그 밖에는 가장 우선해서 확인할 항목을 다음 값 중
하나로 제공합니다.

- `initial_funds_shortfall`
- `emergency_fund_shortfall`
- `essential_expense_deficit`
- `savings_target_shortfall`
- `safety_margin_shortfall`
- `annual_goal_shortfall`

`annual_financial_target`이 `0`이면 0으로 나눌 수 없으므로
`annual_goal_achievement_rate`는 계산하지 않고 `null`로 반환합니다.
`expected_resources_after_one_year`와 `annual_financial_surplus`는 계속
계산합니다.

가격 비교가 가능한 매물에는 비교군의 환산 월 임대비용 중앙값,
중앙값과의 가격 차액·차이율 및 백분위를 추가로 제공합니다.
백분위는 `후보 매물 이하 비교군 수 ÷ 전체 비교군 수 × 100`입니다.
`comparison_criteria`는 가격 비교에 실제 사용한 조회 개월 수, 지역,
주택유형 및 최종 면적 허용범위를 제공합니다. 15% 표본이 부족해 20%로
확장했다면 `area_tolerance_percent`는 `20`입니다.

`ai_interpretation`은 Pydantic AI의 구조화 출력이며 매물별 가격·재무
결과와 사용자가 작성한 매물 메모만 근거로 생성합니다. 임의의 재무 수치를
계산하거나 계약·추천 여부를 결정하지 않습니다. AI 호출에 실패하면 해당
값은 `null`이지만 가격 및 재무 분석 결과는 정상적으로 반환됩니다.
저장된 결과의 가격 적정성을 24시간 후 갱신할 때 AI 종합 해설도 함께
갱신합니다. `suggested_questions`는 기존 챗봇 메시지 API에 그대로 보낼
수 있는 추천 질문입니다.

`sample_count`는 조회된 실거래 중 전용면적 허용 범위를 통과한 최종
비교 표본 수입니다. 먼저 후보 매물 전용면적의 ±15% 범위로 비교하고,
표본이 30개 미만이면 ±20% 범위로 한 번 확장합니다. 확장 후 표본 수에
따라 응답 형태가 달라집니다.

- 표본이 30개 이상이면 `comparison_mode`는 `median`입니다.
  `median_equivalent_monthly_cost`, `difference_from_median`,
  `difference_rate_from_median`, `price_percentile`을 제공하고
  `samples`는 빈 배열입니다.
- ±20%로 확장한 뒤에도 표본이 1~29개이면 `comparison_mode`는
  `individual_samples`입니다.
  표본 수가 적어 중앙값 비교 지표는 모두 `null`이며 `samples`에 모든
  비교 표본의 매물명, 주소, 계약 정보와 환산 월 임대비용을 제공합니다.
  `candidate_equivalent_monthly_cost`에는 사용자 후보 매물의 환산 월
  임대비용을 제공합니다.

표본이 30개 미만인 경우:

```json
{
  "status": "available",
  "sample_count": 2,
  "comparison_mode": "individual_samples",
  "median_equivalent_monthly_cost": null,
  "difference_from_median": null,
  "difference_rate_from_median": null,
  "price_percentile": null,
  "candidate_equivalent_monthly_cost": 900000,
  "comparison_criteria": {
    "lookback_months": 12,
    "district_name": "강남구",
    "property_type": "apartment",
    "area_tolerance_percent": 20
  },
  "samples": [
    {
      "name": "비교 아파트 A",
      "address": "서울특별시 강남구 역삼동 123-4",
      "deposit": 10000000,
      "monthly_rent": 700000,
      "exclusive_area_m2": 58.0,
      "contract_date": "2026-07-01",
      "equivalent_monthly_cost": 741667
    },
    {
      "name": "비교 아파트 B",
      "address": "서울특별시 강남구 도곡동 55",
      "deposit": 20000000,
      "monthly_rent": 800000,
      "exclusive_area_m2": 62.0,
      "contract_date": "2026-07-02",
      "equivalent_monthly_cost": 883333
    }
  ],
  "reason": null
}
```

`equivalent_monthly_cost`는 각 표본의
`월세 + 보증금 × 연 전월세전환율 ÷ 100 ÷ 12`를 원 단위로 반올림한
금액입니다. `candidate_equivalent_monthly_cost`도 같은 전월세전환율과
공식으로 계산합니다. 공공데이터에 건물·단지명이 없는 주택 유형은
표본의 `name`이 `null`일 수 있습니다.

챗봇에서 말하는 `내 집의 환산 월세`, `후보 매물 환산 월세` 및
`환산 월세`는 `candidate_equivalent_monthly_cost`와 같은 값입니다.
후보가 여러 개이면 챗봇은 매물명별 값을 구분해 설명합니다.

필요한 비교 필드가 없거나 외부 데이터를 구하지 못하면
`price_appropriateness.status`는 `unavailable`이고 `reason`에 원인이
들어갑니다. 이 경우 `comparison_mode`는 `null`, 중앙값 비교 필드는
`null`, `samples`는 빈 배열입니다. 이미 비교 표본까지 조회한 뒤
전월세전환율을 얻지 못한 경우에는 `sample_count`만 실제 표본 수로
제공될 수 있습니다.
임의 점수, 등급 또는 추천 순위는 계산하지 않습니다.
보증금 대출 월 이자는 `대출액 × 연이자율 ÷ 100 ÷ 12`로 계산하고 원 단위에서 반올림합니다.
초기자금이 부족해도 이후 계산은 계약 체결을 가정한 참고값으로 제공하며 `warnings`에 이를 표시합니다.

## 4. 챗봇

### `POST /analyses/{analysis_id}/chat/messages`

요청:

```json
{
  "content": "각 매물의 재무 결과를 쉽게 설명해 줘."
}
```

`200 OK`, `text/event-stream`:

```text
event: message_start
data: {"analysis_id":"6b5a52cd-b081-4c38-97e2-1d8b0711cd82"}

event: message_delta
data: {"content":"저장된 재무 분석 결과를 설명합니다."}

event: message_end
data: {"turn_id":"...","role":"assistant","content":"...","status":"completed","created_at":"2026-07-27T03:40:00Z"}
```

Pydantic AI의 전체 메시지 이력은 PostgreSQL에 저장됩니다. 사용자가
나중에 다시 접속해 메시지를 보내면 저장된 이력을 복원하여 같은 대화를
계속합니다. 마지막 채팅 이후 단계별 PATCH 또는 다른 화면에서 분석
입력값이 바뀌었다면 다음 채팅 요청 시 이전 입력 스냅샷과 비교하여 변경된
필드의 이전 값과 최신 값을 AI 메시지 이력에 추가합니다. 챗봇 Tool로
변경한 값은 Tool 실행 결과와 최신 입력 스냅샷으로 저장됩니다.

사용자가 소득·생활비, 자산·재무목표 또는 매물별 입력 변경을 요청하면
에이전트가 기존 단계별 PATCH와 동일한 서비스 및 검증을 사용하는 수정
Tool을 즉시 실행합니다. 별도의 사용자 승인 요청이나 승인 API는 없습니다.
입력 변경으로 기존 평가 결과는 삭제되며 새 결과를 보려면 평가 API를
다시 실행해야 합니다.

사용자가 분석 지표의 계산식이나 계산 기준을 질문하면 챗봇은 읽기 전용
`get_calculation_formula` Tool로 서버 계산식, 변수와 반올림 기준을
조회합니다. 특정 매물의 실제 계산 과정을 질문하면
`get_calculation_breakdown` Tool로 해당 `housing_plan_id`의 저장된
입력값·중간값·최종 결과를 조회합니다. AI는 Tool이 반환한 값만 설명하며
새로운 재무 수치를 임의로 계산하지 않습니다. 계산식 조회 Tool은 DB를
변경하지 않으며 별도의 사용자 승인이 필요하지 않습니다.

### `GET /analyses/{analysis_id}/chat/messages`

`200 OK`

```json
{
  "conversation_id": "4c48783c-1723-49b6-b39f-419ace3622ac",
  "messages": [
    {
      "turn_id": "4d694b39-e6e3-4ce2-a893-d54319a62c6f",
      "user_content": "각 매물의 재무 결과를 설명해 줘.",
      "assistant_content": "저장된 재무 분석 결과를 설명합니다.",
      "status": "completed",
      "created_at": "2026-07-27T03:40:00Z"
    }
  ]
}
```

### `DELETE /analyses/{analysis_id}/chat/messages`

현재 분석의 대화 기록을 초기화합니다. 분석 입력과 평가 결과는 삭제하지 않습니다.

`204 No Content` — 응답 본문 없음
