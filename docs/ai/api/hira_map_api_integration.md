# HIRA 병원/약국 검색 + Map API 연동 구현 가이드

작성일: 2026-06-15  
대상 기능: 병원 찾기, 약국 찾기, 지도 marker 표시, 전화/길찾기 연결  
대상 독자: 백엔드, 앱/프론트엔드, QA 담당자

이 문서는 처음부터 병원/약국 검색과 지도 연동 기능을 구현하기 위한 독립 실행형 사양서다.

## 1. 구현 목표

사용자가 현재 위치 또는 선택한 지역을 기준으로 주변 병원과 약국을 검색하고, 앱 화면에서 목록과 지도 marker를 함께 볼 수 있게 한다.

최종 사용자 흐름:

```text
병원/약국 찾기 화면 진입
  -> 현재 위치 권한 요청
  -> 위치 허용 시 현재 좌표 기준 병원/약국 검색
  -> 위치 거부 시 시도/시군구 선택으로 병원/약국 검색
  -> 병원/약국 목록 표시
  -> 지도 위 marker 표시
  -> marker 또는 목록 item 선택
  -> 병원/약국 상세 bottom sheet 표시
  -> 전화 걸기 또는 길찾기 실행
```

핵심 원칙:

- 병원명, 주소, 전화번호, 병원 종별, 좌표는 HIRA 병원정보서비스를 기준 데이터로 사용한다.
- 약국명, 주소, 전화번호, 좌표는 HIRA 약국정보서비스를 기준 데이터로 사용한다.
- 지도 SDK는 병원/약국 데이터를 보유하지 않고 렌더링, marker 표시, 카메라 이동, 길찾기 연결만 담당한다.
- 백엔드는 특정 지도 provider에 종속되지 않는 공통 marker JSON을 제공한다.
- 응급 상황에서는 병원 검색보다 119, 1393, 보호자/비상 연락처 안내가 우선이다.

## 2. 전체 아키텍처

```text
Mobile/Web App
  -> 사용자 위치 권한 또는 지역 선택
  -> Backend 병원/약국 검색 API 호출
      -> HIRA 병원정보서비스 호출
      -> HIRA 약국정보서비스 호출
      -> 병원/약국 데이터 정규화
      -> 좌표 정리
      -> 거리 계산
      -> 반경 필터
      -> 지도 marker contract 생성
  -> App
      -> 병원/약국 목록 렌더링
      -> 지도 SDK marker 렌더링
      -> marker click / 전화 / 길찾기 처리
```

권장 책임 분리:

| Layer | 책임 |
|---|---|
| HIRA API | 병원/약국 기본 정보 제공 |
| Backend API | HIRA 호출, 데이터 정규화, 거리 계산, 앱용 응답 생성 |
| App/Web Client | 위치 권한, 지도 SDK 초기화, marker 렌더링, 사용자 상호작용 |
| Map SDK | 지도 표시, marker 표시, 카메라 이동, 길찾기 deep link |

## 3. 사전 준비

### 3.1 HIRA API Key 준비

공공데이터포털에서 HIRA 병원정보서비스와 약국정보서비스 사용 신청 후 service key를 발급받는다.

필요 항목:

- 공공데이터포털 계정
- 건강보험심사평가원 병원정보서비스 활용 신청
- 건강보험심사평가원 약국정보서비스 활용 신청
- service key

환경 변수 예시:

```env
HIRA_SERVICE_KEY=<issued_hira_service_key>
```

주의:

- 실제 key를 Git, 문서, 로그, 클라이언트 앱에 노출하지 않는다.
- HIRA service key는 백엔드 서버에서만 사용한다.
- 앱에서 HIRA API를 직접 호출하지 않는다.

### 3.2 Map Provider 선택

국내 병원/주소 UX 중심이면 Kakao Map 또는 Naver Map을 우선 검토한다. 이미 프로젝트에서 쓰는 지도 SDK가 있으면 기존 SDK를 우선한다.

| Provider | 적합한 경우 | 주의 |
|---|---|---|
| Kakao Map | 국내 장소/주소 UX, 길찾기 연동이 중요할 때 | React Native 패키지 선택 및 native 설정 필요 |
| Naver Map | 국내 지도 UX와 네이버 생태계 연동이 중요할 때 | Naver Cloud Platform 설정 필요 |
| Google Maps | 글로벌 확장, React Native 자료, cross-platform 안정성이 중요할 때 | 국내 주소/장소 UX는 Kakao/Naver보다 약할 수 있음 |

지도 SDK key 예시:

```env
KAKAO_MAP_API_KEY=<issued_kakao_key>
NAVER_MAP_CLIENT_ID=<issued_naver_client_id>
GOOGLE_MAPS_API_KEY=<issued_google_key>
```

Map key는 플랫폼별 제한을 설정한다.

- Web: 도메인 제한
- Android: package name + SHA fingerprint 제한
- iOS: bundle identifier 제한

### 3.3 Kakao Map 사용 준비

카카오맵을 provider로 선택하는 경우, 카카오 공식 시작하기 문서 기준으로 다음 설정이 필요하다.

공식 문서:

```text
https://developers.kakao.com/docs/ko/kakaomap/common
```

설정 순서:

1. 카카오디벨로퍼스에서 앱을 생성한다.
2. 사용할 플랫폼 정보를 등록한다.
3. 앱 관리 페이지에서 `[카카오맵] > [사용 설정]` 상태를 `ON`으로 변경한다.
4. 플랫폼에 맞는 앱 키를 사용한다.
5. 무료 제공 쿼터를 확인하고, 초과 사용이 예상되면 유료 API 설정을 검토한다.

플랫폼별 key 사용:

| 개발 플랫폼 | 사용해야 하는 앱 키 |
|---|---|
| Web JavaScript SDK | JavaScript 키 |
| Android SDK | 네이티브 앱 키 |
| iOS SDK | 네이티브 앱 키 |

주의:

- JavaScript SDK에서 REST API 키를 사용하면 안 된다.
- Android/iOS 네이티브 SDK에서도 REST API 키가 아니라 네이티브 앱 키를 사용한다.
- 2024년 12월 1일부터 신규로 카카오맵 API를 호출하는 앱은 카카오맵 사용 설정이 필요하다.
- 무료 쿼터를 모두 사용하면 `429 Too Many Request`가 발생할 수 있다.
- 쿼터 사용량은 카카오디벨로퍼스 앱 관리 페이지의 통계/쿼터 메뉴에서 확인한다.

권장 환경 변수명:

```env
KAKAO_MAP_JAVASCRIPT_KEY=<issued_kakao_javascript_key>
KAKAO_NATIVE_APP_KEY=<issued_kakao_native_app_key>
```

## 4. HIRA 병원/약국 정보서비스

### 4.1 사용할 API

```text
Base URL: https://apis.data.go.kr/B551182/hospInfoServicev2
Operation: getHospBasisList
Method: GET
```

대표 요청 형태:

```http
GET https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList
  ?serviceKey=<HIRA_SERVICE_KEY>
  &pageNo=1
  &numOfRows=20
  &sidoCd=110000
  &sgguCd=110022
  &_type=json
```

권장:

- `_type=json`을 요청해서 JSON 파싱을 우선 사용한다.
- JSON 응답이 불안정하거나 XML로 내려오는 경우 XML parser fallback을 준비한다.
- `numOfRows`는 MVP에서 20~100 범위로 제한한다.

### 4.2 주요 Query Parameter

| Parameter | 설명 | 예시 |
|---|---|---|
| `serviceKey` | HIRA service key | `<HIRA_SERVICE_KEY>` |
| `pageNo` | 페이지 번호 | `1` |
| `numOfRows` | 페이지당 결과 수 | `20` |
| `sidoCd` | 시도 코드 | 서울 `110000` |
| `sgguCd` | 시군구 코드 | 노원구 `110022` |
| `yadmNm` | 병원명 검색어 | `서울대병원` |
| `dgsbjtCd` | 진료과목 코드 | 정신건강의학과 코드 |
| `clCd` | 의료기관 종별 코드 | 상급종합/종합병원/의원 등 |
| `_type` | 응답 형식 | `json` |

### 4.3 HIRA 응답 필드 매핑

HIRA 원본 필드는 앱에서 바로 쓰기 어렵기 때문에 백엔드에서 정규화해서 내려준다.

| HIRA field | 정규화 field | 설명 |
|---|---|---|
| `ykiho` | `id` 또는 `encrypted_ykiho` | 암호화 요양기호. 내부 식별자 후보 |
| `yadmNm` | `name` | 병원명 |
| `addr` | `address` | 주소 |
| `telno` | `phone` | 대표 전화번호 |
| `clCd` | `type_code` | 의료기관 종별 코드 |
| `clCdNm` | `type_name` | 의료기관 종별명 |
| `sidoCd` | `sido_code` | 시도 코드 |
| `sidoCdNm` | `sido_name` | 시도명 |
| `sgguCd` | `sggu_code` | 시군구 코드 |
| `sgguCdNm` | `sggu_name` | 시군구명 |
| `dgsbjtCd` | `subject_code` | 진료과목 코드 |
| `dgsbjtCdNm` | `subject_name` | 진료과목명 |
| `XPos` | `lng`, `longitude` | 경도 |
| `YPos` | `lat`, `latitude` | 위도 |

좌표 주의:

- `XPos`는 longitude, 즉 경도다.
- `YPos`는 latitude, 즉 위도다.
- 지도 SDK는 보통 `{ latitude, longitude }` 순서를 쓰므로 필드 순서를 혼동하지 않는다.

### 4.4 HIRA 약국정보서비스

약국 검색은 HIRA 약국정보서비스를 사용한다. 병원정보서비스와 같은 위치 기반 구조로 구현할 수 있다.

```text
Base URL: https://apis.data.go.kr/B551182/pharmacyInfoService
Operation: getParmacyBasisList
Method: GET
```

주의:

- 공식 operation 이름은 `getParmacyBasisList`다.
- `Pharmacy`가 아니라 `Parmacy`로 표기되어 있으므로 path를 임의로 고치지 않는다.
- 응답 구조는 병원정보서비스와 유사하게 공통 envelope 안의 `items.item` 목록을 파싱한다.

대표 요청 형태:

```http
GET https://apis.data.go.kr/B551182/pharmacyInfoService/getParmacyBasisList
  ?serviceKey=<HIRA_SERVICE_KEY>
  &pageNo=1
  &numOfRows=20
  &sidoCd=110000
  &sgguCd=110022
  &_type=json
```

주요 Query Parameter:

| Parameter | 설명 | 예시 |
|---|---|---|
| `serviceKey` | HIRA service key | `<HIRA_SERVICE_KEY>` |
| `pageNo` | 페이지 번호 | `1` |
| `numOfRows` | 페이지당 결과 수 | `20` |
| `sidoCd` | 시도 코드 | 서울 `110000` |
| `sgguCd` | 시군구 코드 | 노원구 `110022` |
| `yadmNm` | 약국명 검색어 | `온누리` |
| `_type` | 응답 형식 | `json` |

약국 필드 매핑:

| HIRA field | 정규화 field | 설명 |
|---|---|---|
| `ykiho` | `id` 또는 `encrypted_ykiho` | 암호화 요양기호. 내부 식별자 후보 |
| `yadmNm` | `name` | 약국명 |
| `addr` | `address` | 주소 |
| `telno` | `phone` | 대표 전화번호 |
| `sidoCd` | `sido_code` | 시도 코드 |
| `sidoCdNm` | `sido_name` | 시도명 |
| `sgguCd` | `sggu_code` | 시군구 코드 |
| `sgguCdNm` | `sggu_name` | 시군구명 |
| `XPos` | `lng`, `longitude` | 경도 |
| `YPos` | `lat`, `latitude` | 위도 |

약국은 병원처럼 진료과목이나 의료기관 종별 필터가 핵심이 아니다. MVP에서는 지역, 약국명, 현재 위치 기반 거리순 검색에 집중한다.

## 5. Backend API 설계

앱은 HIRA API를 직접 호출하지 않고 자체 백엔드 API를 호출한다.

### 5.1 Endpoint

```http
GET /api/v1/hospitals/search
GET /api/v1/pharmacies/search
```

### 5.2 병원 검색 Query Parameters

| Parameter | Type | Required | 설명 |
|---|---:|---:|---|
| `hospital_name` | string | no | 병원명 검색어 |
| `sido_cd` | string | no | HIRA 시도 코드 |
| `sggu_cd` | string | no | HIRA 시군구 코드 |
| `subject_code` | string | no | 진료과목 코드 |
| `hospital_type_code` | string | no | 의료기관 종별 코드 |
| `lat` | number | no | 사용자 현재 위도 |
| `lng` | number | no | 사용자 현재 경도 |
| `radius_km` | number | no | 사용자 좌표 기준 반경 km |
| `page_no` | number | no | 페이지 번호. 기본 `1` |
| `num_of_rows` | number | no | 페이지당 결과 수. 권장 최대 `100` |
| `emergency` | boolean | no | 응급 병원 우선 의도. 기본 병원정보 API만으로 확정 불가 |

요청 예시:

```http
GET /api/v1/hospitals/search?sido_cd=110000&sggu_cd=110022&lat=37.61955&lng=127.05983&radius_km=3&num_of_rows=100
```

### 5.3 약국 검색 Query Parameters

| Parameter | Type | Required | 설명 |
|---|---:|---:|---|
| `pharmacy_name` | string | no | 약국명 검색어. HIRA `yadmNm`으로 전달 |
| `sido_cd` | string | no | HIRA 시도 코드 |
| `sggu_cd` | string | no | HIRA 시군구 코드 |
| `lat` | number | no | 사용자 현재 위도 |
| `lng` | number | no | 사용자 현재 경도 |
| `radius_km` | number | no | 사용자 좌표 기준 반경 km |
| `page_no` | number | no | 페이지 번호. 기본 `1` |
| `num_of_rows` | number | no | 페이지당 결과 수. 권장 최대 `100` |

요청 예시:

```http
GET /api/v1/pharmacies/search?sido_cd=110000&sggu_cd=110022&lat=37.61955&lng=127.05983&radius_km=1&num_of_rows=100
```

병원 상세 화면에서 주변 약국을 찾는 경우:

```http
GET /api/v1/pharmacies/search?lat={hospital.lat}&lng={hospital.lng}&radius_km=1&num_of_rows=30
```

### 5.4 병원 Response Contract

```json
{
  "source": "HIRA getHospBasisList",
  "page_no": 1,
  "num_of_rows": 20,
  "total_count": 770,
  "hospitals": [
    {
      "id": "encrypted-ykiho-or-generated-id",
      "name": "예원내과의원",
      "address": "서울특별시 노원구 광운로 45, (월계동)",
      "phone": "02-943-7715",
      "type_code": "31",
      "type_name": "의원",
      "sido_code": "110000",
      "sido_name": "서울",
      "sggu_code": "110022",
      "sggu_name": "노원구",
      "subject_code": null,
      "subject_name": null,
      "lat": 37.6214962,
      "lng": 127.0590702,
      "latitude": 37.6214962,
      "longitude": 127.0590702,
      "distance_km": 0.227,
      "emergency_available": null,
      "map_marker": {
        "id": "encrypted-ykiho-or-generated-id",
        "title": "예원내과의원",
        "lat": 37.6214962,
        "lng": 127.0590702,
        "address": "서울특별시 노원구 광운로 45, (월계동)",
        "phone": "02-943-7715",
        "distance_km": 0.227
      }
    }
  ],
  "map": {
    "provider": "client_map_sdk",
    "coordinate_source": "HIRA XPos/YPos",
    "markers": [
      {
        "id": "encrypted-ykiho-or-generated-id",
        "title": "예원내과의원",
        "lat": 37.6214962,
        "lng": 127.0590702,
        "address": "서울특별시 노원구 광운로 45, (월계동)",
        "phone": "02-943-7715",
        "distance_km": 0.227
      }
    ]
  },
  "query": {
    "sido_cd": "110000",
    "sggu_cd": "110022",
    "lat": 37.61955,
    "lng": 127.05983,
    "radius_km": 3,
    "emergency": false
  },
  "notice": "병원 기본 정보입니다. 응급 또는 위기 상황이면 119, 1393 또는 가까운 응급실 안내를 우선하세요."
}
```

### 5.5 약국 Response Contract

```json
{
  "source": "HIRA getParmacyBasisList",
  "page_no": 1,
  "num_of_rows": 20,
  "total_count": 120,
  "pharmacies": [
    {
      "id": "encrypted-ykiho-or-generated-id",
      "name": "광운약국",
      "address": "서울특별시 노원구 광운로 ...",
      "phone": "02-000-0000",
      "sido_code": "110000",
      "sido_name": "서울",
      "sggu_code": "110022",
      "sggu_name": "노원구",
      "lat": 37.6200000,
      "lng": 127.0600000,
      "latitude": 37.6200000,
      "longitude": 127.0600000,
      "distance_km": 0.145,
      "map_marker": {
        "id": "encrypted-ykiho-or-generated-id",
        "entity_type": "pharmacy",
        "title": "광운약국",
        "lat": 37.6200000,
        "lng": 127.0600000,
        "address": "서울특별시 노원구 광운로 ...",
        "phone": "02-000-0000",
        "distance_km": 0.145
      }
    }
  ],
  "map": {
    "provider": "client_map_sdk",
    "coordinate_source": "HIRA XPos/YPos",
    "markers": [
      {
        "id": "encrypted-ykiho-or-generated-id",
        "entity_type": "pharmacy",
        "title": "광운약국",
        "lat": 37.6200000,
        "lng": 127.0600000,
        "address": "서울특별시 노원구 광운로 ...",
        "phone": "02-000-0000",
        "distance_km": 0.145
      }
    ]
  },
  "query": {
    "sido_cd": "110000",
    "sggu_cd": "110022",
    "lat": 37.61955,
    "lng": 127.05983,
    "radius_km": 1
  },
  "notice": "약국 기본 정보입니다. 영업시간, 야간/휴일 운영 여부는 별도 데이터로 확인해야 합니다."
}
```

### 5.6 앱에서 사용하는 필드

병원 목록 카드:

| UI | Response field |
|---|---|
| 병원명 | `hospital.name` |
| 종별 | `hospital.type_name` |
| 주소 | `hospital.address` |
| 전화번호 | `hospital.phone` |
| 거리 | `hospital.distance_km` |
| 응급 가능 여부 | `hospital.emergency_available` |

지도 marker:

| UI | Response field |
|---|---|
| marker id | `marker.id` |
| marker title | `marker.title` |
| latitude | `marker.lat` |
| longitude | `marker.lng` |
| description | `marker.address` |

약국 목록 카드:

| UI | Response field |
|---|---|
| 약국명 | `pharmacy.name` |
| 주소 | `pharmacy.address` |
| 전화번호 | `pharmacy.phone` |
| 거리 | `pharmacy.distance_km` |

약국 지도 marker:

| UI | Response field |
|---|---|
| marker id | `marker.id` |
| entity type | `marker.entity_type` |
| marker title | `marker.title` |
| latitude | `marker.lat` |
| longitude | `marker.lng` |
| description | `marker.address` |

## 6. Backend 구현 절차

### 6.1 환경 변수 로딩

필수:

```text
HIRA_SERVICE_KEY
```

서버 시작 시 validation:

- `HIRA_SERVICE_KEY`가 없으면 HIRA 호출을 막고 서버 설정 오류를 반환한다.
- key 값은 로그에 남기지 않는다.

### 6.2 HIRA API Client 작성

병원정보서비스 의사 코드:

```python
def fetch_hospitals(params):
    hira_params = {
        "serviceKey": HIRA_SERVICE_KEY,
        "pageNo": params.page_no,
        "numOfRows": params.num_of_rows,
        "_type": "json",
    }

    if params.sido_cd:
        hira_params["sidoCd"] = params.sido_cd
    if params.sggu_cd:
        hira_params["sgguCd"] = params.sggu_cd
    if params.hospital_name:
        hira_params["yadmNm"] = params.hospital_name
    if params.subject_code:
        hira_params["dgsbjtCd"] = params.subject_code
    if params.hospital_type_code:
        hira_params["clCd"] = params.hospital_type_code

    response = http_get(
        "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList",
        params=hira_params,
        timeout=10,
    )

    return parse_hira_response(response)
```

약국정보서비스 의사 코드:

```python
def fetch_pharmacies(params):
    hira_params = {
        "serviceKey": HIRA_SERVICE_KEY,
        "pageNo": params.page_no,
        "numOfRows": params.num_of_rows,
        "_type": "json",
    }

    if params.sido_cd:
        hira_params["sidoCd"] = params.sido_cd
    if params.sggu_cd:
        hira_params["sgguCd"] = params.sggu_cd
    if params.pharmacy_name:
        hira_params["yadmNm"] = params.pharmacy_name

    response = http_get(
        "https://apis.data.go.kr/B551182/pharmacyInfoService/getParmacyBasisList",
        params=hira_params,
        timeout=10,
    )

    return parse_hira_response(response)
```

### 6.3 응답 파싱

HIRA 응답은 결과가 1개일 때 `item`이 object로 오고, 여러 개일 때 array로 올 수 있다. 항상 배열로 정규화한다.

의사 코드:

```python
def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
```

파싱 시 확인할 값:

- `resultCode`
- `resultMsg`
- `totalCount`
- `items.item`

정상 처리 기준:

- `resultCode`가 정상 코드일 때만 병원/약국 목록을 반환한다.
- API 오류, timeout, quota 초과, 인증 오류는 백엔드에서 명확한 HTTP error로 변환한다.

### 6.4 병원/약국 데이터 정규화

병원 정규화 의사 코드:

```python
def normalize_hospital(item):
    lat = to_float(item.get("YPos"))
    lng = to_float(item.get("XPos"))

    hospital_id = item.get("ykiho") or stable_hash(
        item.get("yadmNm"),
        item.get("addr"),
        item.get("telno"),
    )

    return {
        "id": hospital_id,
        "name": item.get("yadmNm"),
        "address": item.get("addr"),
        "phone": item.get("telno"),
        "type_code": item.get("clCd"),
        "type_name": item.get("clCdNm"),
        "sido_code": item.get("sidoCd"),
        "sido_name": item.get("sidoCdNm"),
        "sggu_code": item.get("sgguCd"),
        "sggu_name": item.get("sgguCdNm"),
        "subject_code": item.get("dgsbjtCd"),
        "subject_name": item.get("dgsbjtCdNm"),
        "lat": lat,
        "lng": lng,
        "latitude": lat,
        "longitude": lng,
        "emergency_available": None,
    }
```

약국 정규화 의사 코드:

```python
def normalize_pharmacy(item):
    lat = to_float(item.get("YPos"))
    lng = to_float(item.get("XPos"))

    pharmacy_id = item.get("ykiho") or stable_hash(
        item.get("yadmNm"),
        item.get("addr"),
        item.get("telno"),
    )

    return {
        "id": pharmacy_id,
        "name": item.get("yadmNm"),
        "address": item.get("addr"),
        "phone": item.get("telno"),
        "sido_code": item.get("sidoCd"),
        "sido_name": item.get("sidoCdNm"),
        "sggu_code": item.get("sgguCd"),
        "sggu_name": item.get("sgguCdNm"),
        "lat": lat,
        "lng": lng,
        "latitude": lat,
        "longitude": lng,
    }
```

### 6.5 거리 계산

사용자 좌표가 있을 때만 `distance_km`를 계산한다.

Haversine 공식:

```python
from math import radians, sin, cos, sqrt, atan2

def distance_km(lat1, lng1, lat2, lng2):
    radius = 6371.0

    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius * c
```

처리 규칙:

- 사용자 `lat/lng`와 병원 `lat/lng`가 모두 있을 때만 계산한다.
- 계산값은 소수점 3자리 정도로 반올림한다.
- `radius_km`가 있으면 반경 밖 병원은 제외한다.
- 거리 계산이 가능한 병원은 `distance_km` 오름차순으로 정렬한다.

### 6.6 Marker 생성

좌표가 있는 병원/약국만 marker로 만든다.

```python
def build_marker(place, entity_type):
    if place["lat"] is None or place["lng"] is None:
        return None

    return {
        "id": place["id"],
        "entity_type": entity_type,
        "title": place["name"],
        "lat": place["lat"],
        "lng": place["lng"],
        "address": place["address"],
        "phone": place["phone"],
        "distance_km": place.get("distance_km"),
    }
```

## 7. 지역 코드 전략

HIRA 병원정보서비스와 약국정보서비스는 `서울`, `노원구` 같은 문자열보다 `sidoCd`, `sgguCd` 코드 기반 검색이 안정적이다.

권장 구현:

```http
GET /api/v1/hospitals/codes/regions
GET /api/v1/hospitals/codes/districts?sido_cd=110000
GET /api/v1/hospitals/codes/subjects
GET /api/v1/hospitals/codes/types
```

약국도 동일한 지역 코드 endpoint를 재사용한다. 약국 전용으로 별도 지역 코드 endpoint를 만들 필요는 없다.

앱 흐름:

```text
사용자 지역 선택
  -> 서울 선택
  -> 노원구 선택
  -> 내부 값 sido_cd=110000, sggu_cd=110022 확보
  -> 병원 탭이면 /api/v1/hospitals/search 호출
  -> 약국 탭이면 /api/v1/pharmacies/search 호출
```

MVP에서는 자주 쓰는 지역 코드만 정적 JSON으로 시작해도 된다. 이후 HIRA 코드 API나 운영 DB로 확장한다.

## 8. Map SDK 연동 절차

### 8.1 Kakao Map 연동 시 앱 설정 체크

카카오맵을 선택했다면 코드 작성 전에 다음 설정을 먼저 완료한다.

Web:

- 카카오디벨로퍼스 앱에 Web 플랫폼을 등록한다.
- 실제 서비스 도메인, 개발 도메인, 로컬 테스트 도메인을 등록한다.
- JavaScript SDK는 JavaScript 키로 초기화한다.

Android:

- 카카오디벨로퍼스 앱에 Android 플랫폼을 등록한다.
- package name과 key hash/SHA 정보를 등록한다.
- Android SDK는 네이티브 앱 키로 초기화한다.

iOS:

- 카카오디벨로퍼스 앱에 iOS 플랫폼을 등록한다.
- bundle identifier를 등록한다.
- iOS SDK는 네이티브 앱 키로 초기화한다.

공통:

- 앱 관리 페이지에서 카카오맵 사용 설정이 `ON`인지 확인한다.
- 429가 발생하면 쿼터 소진 여부를 먼저 확인한다.
- 지도 SDK key는 HIRA service key와 분리해서 관리한다.

### 8.2 공통 Marker Type

앱은 백엔드의 `map.markers`를 지도 SDK에 맞게 변환한다.

```ts
type PlaceMarker = {
  id: string;
  entity_type: "hospital" | "pharmacy";
  title: string;
  lat: number;
  lng: number;
  address: string;
  phone: string | null;
  distance_km: number | null;
};

type MapMarker = {
  id: string;
  entityType: "hospital" | "pharmacy";
  title: string;
  coordinate: {
    latitude: number;
    longitude: number;
  };
  description: string;
};

function toMapMarker(marker: PlaceMarker): MapMarker {
  return {
    id: marker.id,
    entityType: marker.entity_type,
    title: marker.title,
    coordinate: {
      latitude: marker.lat,
      longitude: marker.lng,
    },
    description: marker.address,
  };
}
```

권장:

- 병원 marker와 약국 marker는 색상 또는 아이콘을 구분한다.
- 병원은 `entity_type="hospital"`, 약국은 `entity_type="pharmacy"`로 내려준다.
- mixed map 화면에서는 marker id 충돌을 피하기 위해 `hospital:{id}`, `pharmacy:{id}`처럼 prefix를 붙여도 된다.

### 8.3 지도 초기 카메라 위치

우선순위:

1. 사용자 현재 위치
2. 검색 결과 marker들의 bounding box 중심
3. 선택 지역의 대표 좌표
4. 기본 좌표

예시:

```ts
const initialCenter = userLocation ?? getMarkerBoundsCenter(markers) ?? SEOUL_CENTER;
```

### 8.4 Marker 클릭

권장 UI:

```text
marker click
  -> 선택 병원 id 저장
  -> 지도 marker active style 적용
  -> bottom sheet 열기
  -> 병원명/약국명, 주소, 전화, 거리 표시
  -> 전화 버튼 / 길찾기 버튼 표시
```

### 8.5 전화 연결

전화번호가 있을 때만 전화 버튼을 활성화한다.

```ts
function openPhone(phone: string | null) {
  if (!phone) return;
  Linking.openURL(`tel:${phone}`);
}
```

### 8.6 길찾기 Deep Link

백엔드는 길찾기 URL을 만들지 않는다. 앱에서 선택한 지도 provider 기준으로 생성한다.

Kakao 예시:

```ts
function openKakaoRoute(marker: PlaceMarker) {
  const url = `kakaomap://route?ep=${marker.lat},${marker.lng}&by=CAR`;
  Linking.openURL(url);
}
```

Naver 예시:

```ts
function openNaverRoute(marker: PlaceMarker) {
  const name = encodeURIComponent(marker.title);
  const url = `nmap://route/car?dlat=${marker.lat}&dlng=${marker.lng}&dname=${name}`;
  Linking.openURL(url);
}
```

Google Maps 예시:

```ts
function openGoogleRoute(marker: PlaceMarker) {
  const url = `https://www.google.com/maps/dir/?api=1&destination=${marker.lat},${marker.lng}`;
  Linking.openURL(url);
}
```

실제 앱에서는 provider 앱 미설치 fallback을 준비한다.

## 9. 좌표 보정 전략

1차 좌표는 HIRA `XPos/YPos`를 그대로 사용한다.

좌표가 없거나 명확히 이상할 때만 geocoding을 보조로 사용한다.

보정 우선순위:

1. HIRA `XPos/YPos`
2. Kakao/Naver geocoding by address
3. Google geocoding by address
4. 좌표 없음으로 목록에만 표시

보정 결과 저장 시 권장 field:

```json
{
  "lat": 37.6214962,
  "lng": 127.0590702,
  "coordinate_source": "hira",
  "coordinate_verified_at": "2026-06-15T00:00:00+09:00"
}
```

주의:

- geocoding 결과를 HIRA 좌표보다 무조건 우선하지 않는다.
- 좌표 source를 남겨야 추후 품질 검증이 가능하다.
- marker는 좌표가 있는 병원/약국만 생성한다.

## 10. 응급 병원 안내 제약

HIRA `getHospBasisList`는 병원 기본정보 API다. 이 API만으로 다음 정보를 확정하면 안 된다.

- 현재 응급실 운영 여부
- 야간 진료 여부
- 휴일 진료 여부
- 실시간 진료 가능 여부
- 입원 가능 여부
- 자살/자해/타해 위기 대응 가능 여부

따라서 기본 응답은 다음처럼 둔다.

```json
{
  "emergency_available": null
}
```

앱 표시 규칙:

- `null`이면 "응급 가능"으로 표시하지 않는다.
- "응급 여부 확인 필요" 또는 표시 생략이 적절하다.
- 위기/응급 플로우에서는 병원 검색보다 즉시 연락 수단을 우선 표시한다.

위기 상황 우선 안내:

```text
자살/자해/타해 위험 또는 응급 의료 위험 감지
  -> 119
  -> 1393 자살예방상담전화
  -> 보호자/비상 연락처
  -> 현재 혼자 있는지 확인
  -> 필요 시 가까운 응급실 안내
```

정확한 응급 병원 기능을 추가하려면 별도 응급의료기관 데이터 또는 실시간 응급실 정보 API를 연동해야 한다.

### 10.1 약국 운영 정보 제약

HIRA `getParmacyBasisList`는 약국 기본정보 API다. 이 API만으로 다음 정보를 확정하면 안 된다.

- 현재 영업 중 여부
- 야간 운영 여부
- 휴일 운영 여부
- 조제 가능 여부
- 특정 의약품 재고 여부
- 응급/심야 약국 여부

따라서 약국 응답에는 운영 상태를 단정하는 필드를 넣지 않거나 `null`로 둔다.

```json
{
  "open_now": null,
  "night_service_available": null,
  "holiday_service_available": null
}
```

앱 표시 규칙:

- `open_now=null`이면 "영업 중"으로 표시하지 않는다.
- 약국 전화번호가 있으면 방문 전 전화 확인을 유도한다.
- 심야/휴일 약국 안내가 필요하면 별도 공공데이터 또는 지자체/응급의료 포털 데이터를 추가 연동한다.

## 11. 오류 처리

| 상황 | Backend response | Client 처리 |
|---|---|---|
| HIRA key 없음 | `500` 또는 `502` | 운영 환경 설정 오류 |
| HIRA 인증 실패 | `502` | "검색 정보를 불러오지 못했습니다" |
| HIRA timeout | `502` | 재시도 버튼 표시 |
| HIRA quota 초과 | `429` 또는 `502` | 잠시 후 재시도 안내 |
| Kakao Map 429 | client SDK error | 카카오맵 쿼터 확인, 유료 API 설정 검토 |
| Kakao Map key 오류 | client SDK error | 플랫폼별 앱 키와 플랫폼 등록 정보 확인 |
| 결과 없음 | `200`, `hospitals: []` | empty state 표시 |
| 약국 결과 없음 | `200`, `pharmacies: []` | empty state 표시 |
| 좌표 없음 | 목록에는 포함, marker 제외 | 지도에는 표시하지 않음 |
| 위치 권한 거부 | 정상 흐름 | 지역 선택 UI 표시 |
| `emergency=true` | `notice` 포함 | 응급 가능 확정 표현 금지 |

권장 error shape:

```json
{
  "error": {
    "code": "HIRA_UPSTREAM_ERROR",
    "message": "검색 정보를 불러오지 못했습니다.",
    "retryable": true
  }
}
```

## 12. 캐싱 전략

HIRA 병원 기본정보는 실시간성이 낮기 때문에 캐싱이 가능하다.
HIRA 약국 기본정보도 동일하게 캐싱이 가능하다.

권장:

- 같은 query에 대해 10분~24시간 캐시
- 지역 코드 목록은 장기 캐시
- 병원/약국 좌표 보정 결과는 DB 저장
- 사용자 위치 좌표는 저장하지 않거나 최소화한다.

캐시 key 예시:

```text
hospitals:sido=110000:sggu=110022:subject=:type=:page=1:rows=100
pharmacies:sido=110000:sggu=110022:name=:page=1:rows=100
```

주의:

- `lat/lng` 기준 거리 정렬은 사용자별로 달라질 수 있다.
- 병원/약국 원본 목록은 캐시하고 거리 계산은 요청 시 수행하는 구조가 좋다.

## 13. 보안 및 개인정보

보안 원칙:

- HIRA service key는 백엔드 환경 변수로만 관리한다.
- 지도 SDK key는 provider별 플랫폼 제한을 적용한다.
- Kakao Map JavaScript SDK는 JavaScript 키, Android/iOS SDK는 네이티브 앱 키를 사용한다.
- 서버 로그에 service key, Authorization header, 사용자 정밀 위치를 남기지 않는다.
- 사용자 좌표를 DB에 저장해야 한다면 명시적 목적, 보관 기간, 삭제 정책을 둔다.

로그 예시:

```text
OK: GET /hospitals/search sido_cd=110000 sggu_cd=110022 rows=20
BAD: serviceKey=actual-secret-value
BAD: user_lat=37.xxxxxx user_lng=127.xxxxxx user_id=...
```

## 14. 테스트 체크리스트

### 14.1 HIRA 연동 테스트

- [ ] service key가 없을 때 명확한 설정 오류가 발생한다.
- [ ] `sidoCd=110000` 요청이 정상 응답을 반환한다.
- [ ] `sgguCd=110022` 요청이 지역 필터링된 결과를 반환한다.
- [ ] 병원정보서비스 `getHospBasisList` 요청이 정상 응답을 반환한다.
- [ ] 약국정보서비스 `getParmacyBasisList` 요청이 정상 응답을 반환한다.
- [ ] 결과가 1개일 때도 배열로 정규화된다.
- [ ] 결과가 0개일 때 empty array를 반환한다.
- [ ] HIRA timeout 시 retryable error로 변환된다.

### 14.2 데이터 정규화 테스트

- [ ] `yadmNm`이 `name`으로 매핑된다.
- [ ] `addr`가 `address`로 매핑된다.
- [ ] `telno`가 `phone`으로 매핑된다.
- [ ] `XPos`가 `lng`으로 매핑된다.
- [ ] `YPos`가 `lat`으로 매핑된다.
- [ ] 병원은 `entity_type=hospital` marker로 변환된다.
- [ ] 약국은 `entity_type=pharmacy` marker로 변환된다.
- [ ] 좌표가 숫자로 변환된다.
- [ ] 좌표가 없는 병원/약국도 목록에는 남는다.

### 14.3 거리/반경 테스트

- [ ] 사용자 좌표가 없으면 `distance_km`가 `null`이다.
- [ ] 사용자 좌표가 있으면 `distance_km`가 계산된다.
- [ ] `radius_km=3`이면 3km 밖 병원이 제외된다.
- [ ] 거리 계산 가능한 병원이 가까운 순으로 정렬된다.

### 14.4 지도 테스트

- [ ] 병원 검색의 `map.markers`는 좌표가 있는 병원만 포함한다.
- [ ] 약국 검색의 `map.markers`는 좌표가 있는 약국만 포함한다.
- [ ] 병원/약국 mixed map에서 marker id가 충돌하지 않는다.
- [ ] 병원 marker와 약국 marker가 UI에서 구분된다.
- [ ] marker latitude/longitude가 뒤바뀌지 않는다.
- [ ] marker 클릭 시 병원 상세가 열린다.
- [ ] 약국 marker 클릭 시 약국 상세가 열린다.
- [ ] 전화번호가 없으면 전화 버튼이 비활성화된다.
- [ ] 길찾기 deep link가 provider별로 동작한다.
- [ ] 지도 앱 미설치 시 web fallback이 동작한다.

### 14.5 Kakao Map 설정 테스트

- [ ] 카카오디벨로퍼스 앱이 생성되어 있다.
- [ ] 카카오맵 사용 설정이 `ON`이다.
- [ ] Web 사용 시 JavaScript 키를 사용한다.
- [ ] Android/iOS 사용 시 네이티브 앱 키를 사용한다.
- [ ] REST API 키를 지도 SDK 초기화에 사용하지 않는다.
- [ ] Web 도메인, Android package/key hash, iOS bundle identifier가 등록되어 있다.
- [ ] 429 발생 시 카카오맵 쿼터 소진 여부를 확인할 수 있다.

### 14.6 안전성 테스트

- [ ] `emergency_available=null`을 응급 가능으로 표시하지 않는다.
- [ ] `open_now=null`을 영업 중으로 표시하지 않는다.
- [ ] `emergency=true` 요청 시 응급 데이터 한계를 안내한다.
- [ ] 자살/자해/타해 위험 플로우에서는 병원 검색보다 emergency UI가 우선한다.

## 15. 광운대학교 인근 테스트 시나리오

테스트 기준 좌표:

```text
광운대학교 인근: lat=37.61955, lng=127.05983
서울: sidoCd=110000
노원구: sgguCd=110022
```

요청:

```http
GET /api/v1/hospitals/search?sido_cd=110000&sggu_cd=110022&lat=37.61955&lng=127.05983&radius_km=3&num_of_rows=100
```

기대 결과:

- 서울 노원구 병원 목록이 반환된다.
- 좌표가 있는 병원은 `map.markers`에 포함된다.
- `distance_km`가 생성된다.
- 결과는 가까운 병원 순으로 정렬된다.
- 응급 가능 여부는 확정하지 않는다.

샘플 결과 예시:

| 거리 | 기관명 | 종별 | 주소 |
|---:|---|---|---|
| 0.227km | 예원내과의원 | 의원 | 서울특별시 노원구 광운로 45 |
| 0.261km | 선진한의원 | 한의원 | 서울특별시 노원구 광운로 52 |
| 0.345km | 고려가정의학과의원 | 의원 | 서울특별시 노원구 광운로 57 |

### 15.1 광운대학교 인근 약국 검색

요청:

```http
GET /api/v1/pharmacies/search?sido_cd=110000&sggu_cd=110022&lat=37.61955&lng=127.05983&radius_km=1&num_of_rows=100
```

기대 결과:

- 서울 노원구 약국 목록이 반환된다.
- 좌표가 있는 약국은 `map.markers`에 포함된다.
- marker의 `entity_type`은 `pharmacy`다.
- `distance_km`가 생성된다.
- 결과는 가까운 약국 순으로 정렬된다.
- 영업 중 여부, 심야/휴일 운영 여부는 확정하지 않는다.

병원 상세 화면에서 사용하는 경우:

```text
사용자 병원 선택
  -> 선택 병원의 lat/lng 확보
  -> /api/v1/pharmacies/search?lat={hospital.lat}&lng={hospital.lng}&radius_km=1 호출
  -> 주변 약국 목록과 marker 표시
```

## 16. MVP 구현 순서

### P0

1. HIRA service key 발급 및 백엔드 환경 변수 설정
2. HIRA `getHospBasisList` client 구현
3. HIRA `getParmacyBasisList` client 구현
4. 병원/약국 데이터 정규화
5. `/api/v1/hospitals/search` 구현
6. `/api/v1/pharmacies/search` 구현
7. 사용자 좌표 기준 거리 계산
8. `map.markers` contract 반환
9. 앱에서 병원/약국 목록 렌더링
10. 카카오디벨로퍼스 앱 생성 및 카카오맵 사용 설정 `ON`
11. 플랫폼별 Kakao Map key 등록
12. 앱에서 지도 marker 렌더링
13. marker 클릭 bottom sheet 구현
14. 전화 연결 구현

### P1

1. 시도/시군구 코드 선택 UI
2. 진료과목/병원 종별 필터
3. 병원 상세 화면의 주변 약국 탭
4. 길찾기 deep link
5. 좌표 누락 병원/약국 geocoding 보정
6. 검색 결과 캐싱

### P2

1. 응급의료기관 데이터 연동
2. 야간/휴일 진료 데이터 연동
3. 심야/휴일 약국 데이터 연동
4. 정신건강 진료 가능 기관 필터 고도화
5. 챗봇 문진 결과 기반 병원/약국 검색 query 추천

## 17. 완료 기준

기능 완료로 판단하려면 다음이 모두 만족되어야 한다.

- HIRA 병원정보서비스에서 병원 목록을 가져온다.
- HIRA 약국정보서비스에서 약국 목록을 가져온다.
- 앱은 HIRA service key 없이 자체 백엔드만 호출한다.
- 병원/약국 목록과 지도 marker가 같은 데이터 source를 기준으로 표시된다.
- 현재 위치가 있으면 거리순 정렬이 된다.
- 위치 권한을 거부해도 지역 선택으로 검색할 수 있다.
- marker 클릭, 전화, 길찾기 흐름이 동작한다.
- 응급 가능 여부를 HIRA 기본 병원정보만으로 단정하지 않는다.
- 약국 영업 중 여부를 HIRA 기본 약국정보만으로 단정하지 않는다.
- API key와 사용자 정밀 위치가 로그/문서/클라이언트에 노출되지 않는다.
