# 가격 적정성 외부 API 사용 가이드

가격 적정성 계산에 사용하는 외부 데이터와 호출 방법을 정리한다.
인증키의 실제 값은 커밋하지 않고 프로젝트 루트의 `.env`에만 저장한다.

```env
DATA_GO_KR_API_KEY=
R_ONE_API_KEY=
```

## 1. 국토교통부 전월세 실거래가 API

법정동 코드 API와 아래 네 실거래가 API는 공공데이터포털에서
활용신청한 뒤 발급받은 `DATA_GO_KR_API_KEY`를 사용한다.

공통 요청 인자는 다음과 같다.

| 인자 | 의미 | 예시 |
|---|---|---|
| `serviceKey` | 공공데이터포털 인증키 | `.env`의 `DATA_GO_KR_API_KEY` |
| `LAWD_CD` | 법정동 코드 앞 5자리인 시군구 코드 | `11680` |
| `DEAL_YMD` | 계약 연월 6자리 | `202506` |
| `pageNo` | 페이지 번호 | `1` |
| `numOfRows` | 페이지당 결과 수 | `1000` |

응답은 XML이다. 금액의 쉼표와 공백을 제거한 뒤 원 단위 정수로
변환하고, 면적은 제곱미터 단위 숫자로 변환한다.

```bash
curl --get \
  "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent" \
  --data-urlencode "serviceKey=${DATA_GO_KR_API_KEY}" \
  --data-urlencode "LAWD_CD=11680" \
  --data-urlencode "DEAL_YMD=202506" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=1000"
```

공공데이터포털 키가 이미 URL 인코딩된 형태라면 이중 인코딩되지 않게
주의한다. 애플리케이션에서는 키를 로그에 남기지 않는다.

### 1.1 아파트

- 상세: <https://www.data.go.kr/data/15126474/openapi.do>
- 주소:
  `https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent`
- 적용 대상: `apartment`
- 비교값: 보증금, 월세, 전용면적, 층, 건축연도, 법정동, 계약일

### 1.2 연립·다세대

- 상세: <https://www.data.go.kr/data/15126473/openapi.do>
- 주소:
  `https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent`
- 적용 대상: `row_house`, `multi_family`
- 비교값: 보증금, 월세, 전용면적, 층, 건축연도, 법정동, 계약일

### 1.3 오피스텔

- 상세: <https://www.data.go.kr/data/15126475/openapi.do>
- 주소:
  `https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent`
- 적용 대상: `officetel`
- 비교값: 보증금, 월세, 전용면적, 층, 건축연도, 법정동, 계약일

### 1.4 단독·다가구

- 상세: <https://www.data.go.kr/data/15126472/openapi.do>
- 주소:
  `https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent`
- 적용 대상: `detached_house`, `multi_household`
- 비교값: 보증금, 월세, 연면적 또는 계약면적, 법정동, 계약일
- 지번 일부가 제공되지 않을 수 있어 다른 유형보다 비교 조건이
  제한될 수 있다.

## 2. 행정안전부 법정동 코드 API

실거래가 API의 `LAWD_CD`에는 법정동 코드 전체가 아니라 앞 5자리인
시군구 코드를 전달한다.

```text
법정동 코드: 1168010100
LAWD_CD:     11680
```

공공데이터포털의 법정동 코드 API를 활용신청하고
`DATA_GO_KR_API_KEY`로 호출한다.

- 상세: <https://www.data.go.kr/data/15077871/openapi.do>
- 주소:
  `https://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList`
- 응답 형식: JSON 또는 XML

| 인자 | 의미 | 예시 |
|---|---|---|
| `ServiceKey` | 공공데이터포털 인증키 | `.env`의 `DATA_GO_KR_API_KEY` |
| `pageNo` | 페이지 번호 | `1` |
| `numOfRows` | 페이지당 결과 수 | `100` |
| `type` | 응답 형식 | `json` |
| `locatadd_nm` | 검색할 지역주소명 | `서울특별시 강남구 역삼동` |

```bash
curl --get \
  "https://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList" \
  --data-urlencode "ServiceKey=${DATA_GO_KR_API_KEY}" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=100" \
  --data-urlencode "type=json" \
  --data-urlencode "locatadd_nm=서울특별시 강남구 역삼동"
```

응답의 주요 필드는 다음과 같다.

| 필드 | 의미 |
|---|---|
| `region_cd` | 10자리 지역코드 |
| `sido_cd` | 2자리 시도코드 |
| `sgg_cd` | 3자리 시군구코드 |
| `umd_cd` | 3자리 읍면동코드 |
| `ri_cd` | 2자리 리코드 |
| `locatadd_nm` | 전체 지역주소명 |
| `locathigh_cd` | 상위 지역코드 |

실거래가 조회에 사용할 `LAWD_CD`는 `region_cd`의 앞 5자리 또는
`sido_cd + sgg_cd`로 만든다. 동일 주소명이 여러 건 반환될 수 있으므로
문자열 첫 번째 결과를 바로 사용하지 않고 전체 주소명이 일치하는 행을
선택한다.

법정동 결과는 변경 빈도가 낮으므로 API 응답을 캐시할 수 있다. 매물
저장 시 확정한 10자리 법정동 코드와 5자리 시군구 코드를 함께 저장한다.

## 3. 한국부동산원 R-ONE 전월세전환율

- 소개:
  <https://www.reb.or.kr/r-one/portal/openapi/openApiIntroPage.do>
- 개발 가이드:
  <https://www.reb.or.kr/r-one/portal/openapi/openApiDevPage.do>
- 주소:
  `https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do`

R-ONE에서 별도로 발급받은 인증키를 `R_ONE_API_KEY`에 저장한다.

| 인자 | 의미 | 예시 |
|---|---|---|
| `KEY` | R-ONE 인증키 | `.env`의 `R_ONE_API_KEY` |
| `Type` | 응답 형식 | `json` |
| `pIndex` | 페이지 번호 | `1` |
| `pSize` | 페이지당 결과 수 | `1000` |
| `STATBL_ID` | 통계표 ID | `A_2024_00156` |
| `DTACYCLE_CD` | 자료 주기 | `MM` |
| `WRTTIME_IDTFR_ID` | 작성 시점 | `202506` |

```bash
curl --get \
  "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do" \
  --data-urlencode "KEY=${R_ONE_API_KEY}" \
  --data-urlencode "Type=json" \
  --data-urlencode "pIndex=1" \
  --data-urlencode "pSize=1000" \
  --data-urlencode "STATBL_ID=A_2024_00156" \
  --data-urlencode "DTACYCLE_CD=MM" \
  --data-urlencode "WRTTIME_IDTFR_ID=202506"
```

| 대상 | 통계표 ID |
|---|---|
| 종합주택 fallback | `A_2024_00155` |
| 아파트 | `A_2024_00156` |
| 연립·다세대 | `A_2024_00157` |
| 단독주택 | `A_2024_00158` |
| 오피스텔 | `T241163133546529` |

오피스텔 표는 다른 표와 분류 및 시점 코드 구조가 다를 수 있다.
구현 전에 R-ONE의 `통계코드 검색`에서 해당 표의 `DTACYCLE_CD`,
지역 분류 코드와 작성 시점 값을 확인한다.

전환율 선택 우선순위는 다음과 같다.

1. 매물 유형과 지역이 모두 같은 최신 월의 전환율
2. 매물 유형은 같고 더 넓은 상위 지역의 최신 전환율
3. 종합주택 전환율

## 4. 가격 비교 적용

실거래 보증금과 월세를 전월세전환율로 표준화한다.

```text
환산 월 임대비용
= 월세 + 보증금 × (연 전월세전환율 / 100) / 12
```

동일 유형·지역·유사 면적의 최근 실거래를 비교군으로 만들고 다음 값을
매물별 결과로 반환한다.

```text
중앙값
중앙값과 가격 차액
중앙값과 가격 차이율
백분위
```

```text
가격 차액 = 후보 매물 환산 월 임대비용 - 비교군 중앙값
가격 차이율 = 가격 차액 / 비교군 중앙값 × 100
백분위 = 후보 매물 이하인 비교군 수 / 전체 비교군 수 × 100
```

외부 API 오류, 전환율 부재 또는 비교 표본 부족은 재무관리 계산까지
실패시키지 않고 가격 비교 결과만 `unavailable`로 처리한다.
