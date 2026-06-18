# AI 기반 정신건강 사전문진 및 Handoff Report 시스템 개발 계획

- 문서 버전: v1.0
- 작성일: 2026-06-18
- 목적: 챗봇 기반 정신건강 사전문진, 구조화 설문, 진료기록/처방기록 병합, 정신과적 응급 위험도 분류, 전문가 전달용 handoff report 생성을 위한 개발 hierarchy 정의
- 구조: Task → 기능 → Agent 구성

---

## 0. 시스템 정의

본 시스템은 사용자의 자율 대화, 구조화 사전문진, 진료기록, 약처방 기록, STT 기반 음성 transcript, OCR 기반 문서 정보, 이전 대화 및 이전 handoff report를 통합하여 정신건강 상태를 선별하고, 위험 신호를 탐지하며, 사용자 상태에 적합한 구조화 문진을 수행한 뒤 전문가 또는 의료진에게 전달 가능한 사전문진 handoff report를 생성하는 것을 목표로 한다.

본 시스템은 의학적 진단을 수행하지 않는다. AI는 병명을 확정하지 않고, 증상 기반 정신건강 영역 후보, 진료과 후보, 필요한 구조화 문진 도구, 위험도, 근거 정보를 정리하여 전문가 판단을 보조한다.

### 0.1 핵심 원칙

1. AI는 진단하지 않는다.
2. AI는 위험 신호를 놓치지 않도록 보조한다.
3. AI는 증상 영역, 진료과 후보, 구조화 문진 필요성을 제안한다.
4. AI의 모든 판단에는 source, timestamp, confidence, evidence를 연결한다.
5. 구조화 척도 점수 계산은 rule-based logic으로 수행한다.
6. LLM 판단은 보조 정보로만 사용한다.
7. 자살·자해·타해·응급 위험은 모든 기능보다 우선한다.
8. 위기 대응은 CTRS 기반 정신과적 응급 위험도 분류를 따른다.
9. CTRS 1단계가 가장 긴급하며, CTRS 5단계가 가장 안정적이다.
10. 최종 진단과 치료 결정은 전문가가 수행한다.

---

# Task 0. 회원가입/로그인 및 최초 사용자 Intake

## 기능 0-1. 회원가입/로그인 및 사용자 프로필 생성

### Agent 0-1. Auth/Profile Agent

#### 목적

사용자의 계정 생성, 로그인, 최초 사용자 여부 확인, 기본 프로필 정보 수집, 동의 상태 관리를 수행한다.

#### 주요 기능

- 회원가입/로그인
- 사용자 고유 ID 생성
- 최초 사용자 여부 확인
- 재사용자 여부 확인
- 개인정보 수집 동의 관리
- 민감정보 처리 동의 관리
- 위치정보 사용 동의 관리
- 의료진/기관 연계 동의 관리
- 진료기록/처방전/OCR/STT 자료 활용 동의 관리
- 동의 버전 관리
- 동의 철회 및 데이터 삭제 요청 관리

#### 수집 정보

- 이름
- 출생연월
- 나이 또는 연령대
- 성별
- 연락처
- 보호자 또는 비상연락처, 선택
- 현재 위치 사용 동의 여부
- 의료진 또는 기관 연계 동의 여부
- 진료기록/처방전 업로드 동의 여부
- 음성 입력 및 STT 처리 동의 여부
- 문서 이미지 OCR 처리 동의 여부

#### 주의사항

- 출생연월이 있으면 나이는 시스템에서 계산한다.
- 성별 정보는 서비스 목적상 필요한 범위에서만 수집한다.
- 위치정보는 병원/진료과 정보 제공 기능 사용 시 별도 동의를 받는다.
- 정신건강 정보는 민감정보이므로 최소수집 원칙을 적용한다.
- 보호자 또는 비상연락처는 필수가 아니라 선택 항목으로 둔다.

---

## 기능 0-2. 최초 사용자 정신건강 기초 설문

### Agent 0-2. Initial Intake Agent

#### 목적

앱 최초 사용자의 기초 정신건강 context를 수집한다. 특정 질환 영역에 한정되지 않고, 모든 정신건강 영역에서 공통적으로 필요한 일반화된 질문을 기반으로 한다.

#### 적용 조건

- 최초 사용자: 필수 수행
- 재사용자: 건너뛰기 가능
- 단, 안전 관련 gate 질문은 매 세션 유지

#### 주요 질문 영역

1. 앱 사용 목적
2. 현재 가장 큰 어려움
3. 증상 시작 시점
4. 일상생활 기능 손상 정도
5. 수면 상태
6. 식욕 및 체중 변화
7. 최근 스트레스 사건
8. 음주 사용 변화
9. 약물 사용 변화
10. 과거 정신건강 진료 이력
11. 현재 복용 중인 약물
12. 상담 또는 치료 경험
13. 가족/친구/보호자 등 지지체계 여부
14. 자살·자해 사고 여부
15. 응급상황 여부
16. 진료기록/처방전/진단서 업로드 의향

#### 기본 문항 예시

1. 오늘 앱을 사용하게 된 가장 큰 이유는 무엇인가요?
   - 기분 저하 / 불안·걱정 / 스트레스 / 수면 문제 / 음주 문제 / 약물 문제 / 대인관계 문제 / 외상 경험 / 자살·자해 생각 / 단순 상담 / 기타
2. 이 문제가 언제부터 시작되었나요?
   - 오늘 / 며칠 전 / 1–2주 전 / 1개월 이상 / 6개월 이상 / 오래됨 / 잘 모르겠음
3. 현재 어려움이 일상생활에 어느 정도 영향을 주고 있나요?
   - 거의 없음 / 조금 있음 / 꽤 있음 / 매우 큼 / 일상 유지가 어려움
4. 최근 수면 상태는 어떤가요?
   - 양호 / 잠들기 어려움 / 자주 깸 / 너무 많이 잠 / 거의 못 잠
5. 최근 술이나 약물 사용이 늘었다고 느끼시나요?
   - 아니오 / 조금 늘었음 / 많이 늘었음 / 조절이 어려움 / 응답하지 않음
6. 최근 죽고 싶다는 생각이나 사라지고 싶다는 생각을 한 적이 있나요?
   - 아니오 / 가끔 있음 / 자주 있음 / 지금도 있음 / 응답하기 어려움
7. 최근 스스로를 해치려는 생각, 계획, 또는 행동이 있었나요?
   - 아니오 / 생각만 있음 / 방법을 생각함 / 구체적 계획이 있음 / 실제 행동이 있었음
8. 이전에 정신건강의학과, 상담센터, 병원 진료를 받은 적이 있나요?
   - 없음 / 있음 / 현재 치료 중 / 응답하지 않음
9. 현재 복용 중인 정신건강 관련 약이 있나요?
   - 없음 / 있음 / 잘 모르겠음 / 처방전 업로드 가능
10. 진료기록, 처방전, 진단서 등을 업로드해서 더 정확한 사전문진 보고서를 만들까요?
   - 예 / 아니오 / 나중에

#### 산출물

- 사용자 초기 정신건강 profile
- 기본 위험도
- 주요 호소 영역
- 구조화 문진 필요 여부
- 기록 업로드 필요 여부
- 이후 자율 대화 및 handoff report 생성을 위한 baseline context

---

# Task 1. AI 기반 사전문진 Handoff Report 생성

## Agent 1. Orchestrator Agent

### 목적

Task 1 전체 workflow를 관리한다. 자율 대화, OCR, STT, 기록 병합, RAG 기반 정신건강 영역 후보 추론, 구조화 설문, 종단적 상태 추론, handoff report 생성을 조율한다.

### 주요 기능

- agent 간 작업 순서 제어
- 입력 source routing
- 위험 신호 우선 처리
- 자율 대화와 구조화 설문 전환 관리
- 기록 병합 요청
- RAG 기반 정신건강 영역 후보 분석 요청
- 구조화 문진 도구 선택 요청
- handoff report 생성 요청
- 의료진/원무과 dashboard alert trigger
- 오류, 중단, 재시도, fallback 관리

### 핵심 운영 원칙

1. 자살·자해·타해·응급 위험 판단이 항상 최우선이다.
2. CTRS 1–2단계는 초응급/고위험으로 보고 일반 상담 대화를 중단 또는 제한한다.
3. AI는 진단하지 않고, 증상 영역과 진료과 후보만 제시한다.
4. 모든 판단에는 근거 evidence를 남긴다.
5. OCR/STT 결과에는 confidence score를 부여한다.
6. 구조화 척도 점수 계산은 rule-based로 수행한다.
7. LLM 판단은 보조 정보이며 최종 진단이 아니다.
8. 위험도가 높은 경우 일반 대화를 중단하고 위기 대응 flow로 전환한다.

---

# 기능 1-1. 자율 대화 기반 문진

## Agent 2. Chatbot Interview Agent

### 목적

사용자와 자연어 기반 자율 대화를 수행하여 현재 상태, 주요 호소, 감정 상태, 일상 기능 손상, 위험 신호, 보호요인을 파악한다.

### 주요 기능

- 자율 대화 기반 문진
- 선 질의를 통한 사용자 상태 파악
- 사용자의 답변 및 반응 유도
- 사용자의 문진 피로도 조절
- 구조화 설문으로 자연스럽게 전환
- prompt guardrail 기반 부적절 응답 제어
- 위험 발화 감지 시 Safety/Risk Triage Agent로 즉시 전달

### 수집 정보

- 주호소
- 증상 표현
- 증상 지속 기간
- 일상생활 기능 손상
- 수면/식욕/활동 변화
- 음주/약물 변화
- 대인관계 문제
- 최근 스트레스 사건
- 자살·자해 관련 표현
- 보호요인
- 사용자의 도움 요청 의지

### 출력 예시

```json
{
  "chief_complaint": "최근 불안과 수면 문제가 심해짐",
  "symptom_mentions": ["불안", "수면 저하", "집중력 저하"],
  "duration": "2주 이상",
  "functional_impairment": "업무 집중 어려움",
  "risk_signals": [],
  "protective_factors": ["가족과 연락 가능"],
  "recommended_next_questions": ["불안 정도", "수면 패턴", "자살사고 여부"]
}
```

---

## Agent 3. OCR Document Agent

### 목적

사용자가 업로드한 진단서, 처방전, 전문의 상담기록, 검사결과, 병원 서류 등의 이미지를 OCR로 분석하여 사전문진에 활용 가능한 structured text로 변환한다.

### 주요 기능

- 이미지 기반 문서 OCR
- 진단서/처방전/상담기록/검사결과 문서 유형 분류
- 진단명 후보 추출
- 진료과 추출
- 약물명 추출
- 용량 및 복용법 추출
- 진료일자 및 처방일자 추출
- OCR confidence score 부여
- 문진 정보와 병합 가능한 structured data 생성

### 주의사항

- OCR 결과는 오류 가능성이 있으므로 confidence score를 반드시 저장한다.
- 약물명은 OCR 오류가 많으므로 약물 dictionary matching을 적용한다.
- 불명확한 항목은 “확인 필요” 상태로 저장한다.
- OCR 결과를 근거 없이 확정 정보처럼 사용하지 않는다.
- 진단서에 기재된 진단명은 “문서에 기록된 진단명”이지, AI가 새로 진단한 결과가 아니다.

### 출력 예시

```json
{
  "document_type": "prescription",
  "extracted_text": "...",
  "diagnosis_terms": ["우울증 의심"],
  "department": "정신건강의학과",
  "medications": [
    {
      "name": "SSRI 계열 약물",
      "dose": "확인 필요",
      "confidence": 0.82
    }
  ],
  "date": "2026-06-18",
  "confidence": 0.86
}
```

---

## Agent 4. STT Transcript Agent

### 목적

사용자의 음성 입력 또는 상담 음성 기록을 STT 모델로 텍스트 transcript로 변환하고, 사전문진 정보로 병합할 수 있도록 정리한다.

### 주요 기능

- 음성 입력 수집
- STT 기반 텍스트 변환
- 문장 단위 timestamp 저장
- speaker diarization 가능 시 화자 분리
- transcript confidence score 저장
- 감정 강도, pause, 반복 표현 등 부가 signal 저장 가능
- 변환된 transcript를 Chatbot Interview Agent 및 Information Fusion Agent에 전달

### 출력 예시

```json
{
  "transcript": "요즘 잠을 거의 못 자고 계속 불안합니다.",
  "segments": [
    {
      "start": "00:00:01",
      "end": "00:00:05",
      "speaker": "user",
      "text": "요즘 잠을 거의 못 자고 계속 불안합니다."
    }
  ],
  "confidence": 0.91
}
```

---

## Agent 5. Safety/Risk Triage Agent

### 목적

모든 입력 source에서 자살, 자해, 타해, 폭력성, 극도의 흥분, 급성 환각·망상, 공황발작, 우울 악화, 응급 위험, 약물 과다복용, 중독/금단 등의 위험 신호를 탐지하고, CTRS 기반 정신과적 응급 위험도에 따라 대응 flow를 실행한다.

### 적용 입력

- 자율 대화
- 구조화 설문 응답
- STT transcript
- OCR 문서
- 진료기록
- 약처방 기록
- 이전 handoff report
- 의료진/관리자 메모

### CTRS 기반 위험도 분류

| CTRS 단계 | 분류 | 상태 설명 | 주요 예시 | 시스템 대응 |
|---:|---|---|---|---|
| **1단계** | **초응급** | 자해·타해 위험성이 매우 높거나, 이미 신체적 손상 또는 즉각적 위험이 발생한 상태 | 자살시도, 자해 행동, 타해 시도, 폭력 행동, 심각한 흥분, 통제 불가, 약물 과다복용 의심 | 일반 대화 중단, 즉시 119/112 안내, 보호자/의료진 긴급 알림, 응급실 이송 권고 |
| **2단계** | **고위험** | 구체적 자살·자해·타해 계획 또는 의도가 확인되며, 위험이 임박할 수 있는 상태 | 구체적 방법·장소·시간 언급, 수단 보유, 강한 충동, 현실검증력 저하, 급성 정신증 동반 위험 | 일반 대화 제한, 109/119/112 안내, dashboard 긴급 alert, human review 즉시 등록 |
| **3단계** | **급성기** | 급격한 환각, 망상, 공황발작, 우울감 악화 등으로 위기 개입이 필요한 상태 | 환청/망상 급증, 극심한 공황, 심한 불면, 우울 악화, 일상 기능 급격 저하 | 위기 개입 안내, 빠른 전문가 상담 권고, 의료진/상담자 alert, 24–48시간 내 평가 권장 |
| **4단계** | **중증/주의** | 일상생활 유지가 어렵거나 증상이 뚜렷하지만 즉각적 자·타해 위험은 명확하지 않은 상태 | 지속적 우울·불안, 기능 손상, 수면·식사 악화, 알코올/약물 사용 증가, 치료 필요성 높음 | 외래 진료/상담 권고, 구조화 문진 실시, human review queue 등록 가능 |
| **5단계** | **저위험/안정기** | 자발적 치료 의지가 있고 자·타해 위험성이 낮은 안정적 상태 | 상담 의지 있음, 보호요인 존재, 위험 발화 없음, 일상 기능 유지 가능 | 일반 문진 지속, 정신건강의학과 외래 예약 안내, 자가관리 및 재평가 계획 제공 |

### 핵심 운영 원칙

1. CTRS는 1단계가 가장 위험하고 5단계가 가장 안정적이다.
2. 기존 일반 risk score와 혼동되지 않도록 내부 변수명은 `ctrs_level`로 사용한다.
3. CTRS 1–2단계는 초응급/고위험으로 분류하고, 일반 상담형 대화를 중단하거나 제한한다.
4. CTRS 3–4단계는 급성기/중증으로 분류하고, 구조화 문진과 전문가 상담 권고를 병행한다.
5. CTRS 5단계는 저위험/안정기로 분류하고, 일반 문진 및 외래 예약 안내를 수행한다.
6. 자살·자해 위험이 감지되면 우울/불안/음주 등 다른 영역 분석보다 우선 처리한다.
7. 위험 판단 근거 문장을 반드시 저장한다.
8. 위험 판단은 LLM 단독 추론이 아니라 rule-based trigger와 LLM classifier를 병합한다.
9. 고위험 판단 시 사용자의 위치, 보호자 정보, 의료진 연계 동의 여부를 확인한다.
10. 한국 서비스 기준 자살예방 상담전화는 109를 기본으로 사용한다.

### 출력 예시

```json
{
  "ctrs_level": 2,
  "risk_category": "high_risk",
  "detected_risks": [
    "suicidal_ideation",
    "specific_plan"
  ],
  "trigger_source": "chat",
  "trigger_evidence": [
    "사용자가 구체적인 자해 방법을 언급함"
  ],
  "protective_factors": [
    "가족과 연락 가능"
  ],
  "recommended_action": [
    "limit_general_chat",
    "show_crisis_contact_109_119_112",
    "create_dashboard_alert",
    "register_human_review"
  ],
  "requires_immediate_human_review": true
}
```

---

# 기능 1-2. RAG 기반 정신건강 영역 및 진료과 후보 추론

## Agent 6. Information Fusion Agent

### 목적

자율 대화, OCR, STT, 진료기록, 약처방 기록, 이전 대화, 이전 handoff report 등 여러 source의 정보를 통합하여 현재 상태 분석에 사용할 수 있는 structured clinical context를 생성한다.

### 주요 기능

- 자율 대화 정보 병합
- OCR 문서 정보 병합
- STT transcript 정보 병합
- 진료기록 병합
- 약처방 기록 병합
- 이전 대화 기록 병합
- 이전 handoff report 병합
- 시간순 clinical timeline 생성
- source, timestamp, confidence, evidence 관리
- 중복 정보 제거
- 충돌 정보 표시

### 출력 예시

```json
{
  "timeline": [
    {
      "date": "2026-06-18",
      "source": "chat",
      "event": "사용자가 불안과 수면 저하 호소",
      "confidence": 1.0
    }
  ],
  "current_symptoms": ["불안", "수면 저하", "집중력 저하"],
  "past_history": ["정신건강의학과 진료 이력 있음"],
  "medications": ["SSRI 계열 약물 추정"],
  "previous_scores": [],
  "risk_history": [],
  "source_evidence": []
}
```

### 주의사항

- 사용자 발화, OCR 문서, 진료기록, AI 요약을 명확히 구분한다.
- confidence가 낮은 정보는 확정 정보로 사용하지 않는다.
- 정보 충돌이 있으면 QA Agent에 전달한다.

---

## Agent 7. Clinical Context RAG Agent

### 목적

Information Fusion Agent가 정리한 정보를 바탕으로 의료 DB 및 정신건강 지식베이스 RAG를 수행하여 정신건강 영역 후보, 진료과 후보, 추가 확인 질문, 권장 구조화 문진 도구를 제안한다.

### 주요 기능

- 의료 DB / 정신건강 지식베이스 검색
- 증상과 정신건강 영역 매핑
- 진료과 후보 제시
- 필요한 구조화 문진 추천
- 감별이 필요한 상태 후보 제시
- RAG retrieval source 저장
- 판단 근거 정리

### 출력 항목

- 정신건강 영역 후보
- 진료과 후보
- 필요한 구조화 설문 도구
- 추가 확인 질문
- 근거 정보
- confidence score
- RAG 검색 근거

### 출력 예시

```json
{
  "domain_candidates": [
    {
      "domain": "anxiety",
      "confidence": 0.82,
      "evidence": ["불안 호소", "수면 저하", "긴장감 표현"],
      "recommended_surveys": ["GAD-7", "PHQ-4", "WHO-5"]
    },
    {
      "domain": "depression",
      "confidence": 0.48,
      "evidence": ["흥미 저하 여부 추가 확인 필요"],
      "recommended_surveys": ["PHQ-9"]
    }
  ],
  "department_candidates": [
    {
      "department": "정신건강의학과",
      "reason": "불안 및 수면 문제가 지속됨"
    },
    {
      "department": "가정의학과",
      "reason": "신체 증상 감별 필요 가능성"
    }
  ],
  "additional_questions": [
    "최근 2주 동안 흥미나 의욕이 줄었나요?",
    "불안이 일상생활에 어느 정도 영향을 주나요?"
  ]
}
```

### 주의사항

- 병명을 확정하지 않는다.
- “우울증입니다”가 아니라 “우울 증상 평가 필요성이 높습니다”라고 표현한다.
- RAG 근거가 없는 판단은 report에 포함하지 않는다.
- 진단 후보는 전문가 검토용 보조 정보로만 사용한다.
- 제품 UI에서는 “병명 추론”보다 “정신건강 영역 후보 및 진료과 후보”로 표현한다.

---

# 기능 1-3. 구조화된 사전문진 설문

## Agent 8. Survey Planner Agent

### 목적

Clinical Context RAG Agent의 결과와 Safety/Risk Triage Agent의 CTRS 판단을 바탕으로 사용자에게 필요한 구조화 문진 도구를 선택하고 실행 순서를 결정한다.

### 주요 기능

- 문진 도구 선택
- 문진 순서 결정
- 중복 문진 방지
- 사용자 피로도 고려
- 위험 문항 우선 배치
- 설문 중단/재개 관리
- 자살위험 감지 시 Safety/Risk Triage Agent로 즉시 전환

### 기본 설문 매핑

| 영역 | 권장 도구 |
|---|---|
| 전체 기본 스크리닝 | PHQ-4, WHO-5, 안전 gate |
| 우울 | PHQ-9 |
| 불안 | GAD-7 |
| 음주 | AUDIT-C 또는 AUDIT |
| 약물 | DAST-10 또는 ASSIST |
| 자살위험 | C-SSRS 또는 ASQ 기반 flow |
| 외상/PTSD | PC-PTSD-5 |
| 수면 | ISI 또는 간단 수면 문진 |

### 운영 원칙

- 모든 사용자에게 모든 설문을 수행하지 않는다.
- 최초 사용자는 기초 설문과 기본 안전 gate를 우선 수행한다.
- 재사용자는 이전 결과와 현재 상태에 따라 필요한 설문만 수행한다.
- 자살·자해 위험 응답이 나오면 일반 설문을 중단하고 위기 평가로 전환한다.
- CTRS 1–2단계에서는 일반 설문보다 위기 대응이 우선이다.

---

## Agent 9. Survey Scoring & Interpretation Agent

### 목적

구조화 설문 응답을 기반으로 점수를 계산하고, cut-off 기준에 따라 severity를 해석하며, handoff report에 반영 가능한 형태로 결과를 정리한다.

### 주요 기능

- 설문별 점수 계산
- severity level 계산
- cut-off 적용
- 위험 문항 확인
- 이전 설문 결과와 비교
- 점수 계산 오류 검증
- 결과를 Information Fusion Agent와 Handoff Report Writer Agent에 전달

### 출력 예시

```json
{
  "survey": "PHQ-9",
  "score": 15,
  "severity": "moderately_severe",
  "critical_item_positive": false,
  "interpretation": "우울 증상 추가 평가 필요",
  "next_action": "recommend_clinician_review"
}
```

### 주의사항

- 점수 계산은 LLM이 아니라 rule-based logic으로 수행한다.
- LLM은 결과 문장화와 설명 보조에만 사용한다.
- 자살위험 관련 문항이 양성이면 Safety/Risk Triage Agent로 즉시 전달한다.

---

# 기능 1-4. 종단적 상태 추론

## Agent 10. Sentiment & Conversation Signal Agent

### 목적

사용자의 대화 기록을 기반으로 sentiment, 정서 변화, 부정 정서 반복도, 절망감, 무기력, 불안 표현 등을 분석하여 보조적인 대화 신호로 정리한다.

### 주요 기능

- 대화 sentiment 분석
- 정서 polarity 분석
- 정서 강도 분석
- 불안/우울/분노/절망 표현 탐지
- 반복 표현 탐지
- 대화 흐름 변화 분석
- 이전 대화와 비교

### 출력 예시

```json
{
  "sentiment_summary": "최근 대화에서 부정 정서와 불안 표현이 증가함",
  "dominant_emotions": ["anxiety", "sadness"],
  "signal_strength": "moderate",
  "evidence_utterances": [
    "요즘 계속 불안합니다.",
    "잠을 거의 못 잡니다."
  ]
}
```

### 주의사항

- sentiment는 임상 척도가 아니다.
- report에서는 보조 대화 신호로만 사용한다.
- 구조화 설문 점수보다 우선하지 않는다.

---

## Agent 11. Longitudinal State Tracking Agent

### 목적

이전 대화, 이전 설문 결과, 이전 handoff report, 진료기록, 약처방 기록을 시간순으로 비교하여 사용자의 정신건강 상태 변화를 추적한다.

### 주요 기능

- 이전 문진 점수 추적
- PHQ-9, GAD-7, WHO-5 등 점수 변화 분석
- 이전 handoff report와 현재 상태 비교
- 증상 재발 여부 탐지
- 새로운 증상 발견
- 약물 변경 전후 상태 변화 비교
- CTRS 위험도 변화 분석
- 시간/일자별 상태 변화 trend 생성
- 그래프 생성을 위한 plot-ready data 생성

### 출력 예시

```json
{
  "trend_summary": {
    "depression": "worsened",
    "anxiety": "stable",
    "ctrs_level": "worsened"
  },
  "new_symptoms": ["수면 저하"],
  "relapse_signals": ["의욕 저하 재출현"],
  "plot_data": [
    {
      "date": "2026-06-01",
      "PHQ-9": 8,
      "GAD-7": 6,
      "ctrs_level": 5
    },
    {
      "date": "2026-06-18",
      "PHQ-9": 15,
      "GAD-7": 7,
      "ctrs_level": 4
    }
  ]
}
```

### 주의사항

- 그래프 렌더링은 frontend 또는 report module에서 수행한다.
- Agent는 그래프용 structured data를 생성한다.
- 시계열 비교 시 날짜와 source를 반드시 표시한다.
- CTRS는 숫자가 낮아질수록 위험도가 높아지는 체계임을 시각화에서 명확히 표시한다.

---

# 기능 1-5. Handoff Report 생성

## Agent 12. Handoff Report Writer Agent

### 목적

Agent 1–11의 결과를 바탕으로 사용자용 요약 report, 전문가/의료진용 handoff report, PDF, JSON, FHIR 연동용 데이터를 생성한다.

### 주요 기능

- 사용자용 요약 report 생성
- 전문가/의료진용 handoff report 생성
- PDF report 생성
- JSON report 생성
- FHIR 변환용 data 생성
- 위험도 요약
- 시행된 구조화 문진 결과 정리
- 대화 기반 근거 정리
- 기록 기반 근거 정리
- 종단적 변화 요약
- 권장 다음 조치 정리

### Report 구성

1. 사용자 기본 정보
2. 평가 일시
3. 입력 source 요약
   - 자율 대화
   - 구조화 문진
   - STT transcript
   - OCR 문서
   - 진료기록
   - 약처방 기록
   - 이전 handoff report
4. 현재 주요 호소
5. 정신건강 영역 후보
6. CTRS 기반 정신과적 응급 위험도
   - CTRS level
   - 위험 근거
   - 자살·자해
   - 타해
   - 폭력성/흥분
   - 급성 환각·망상
   - 공황/우울 악화
   - 물질사용 위험
   - 기능 손상
7. 시행된 구조화 문진
   - 척도명
   - 점수
   - severity
   - 시행 일시
8. 기록 기반 근거
   - 문서에 기록된 진단명
   - 처방약
   - 진료과
   - 과거 검사 결과
9. 대화 기반 근거
   - 주요 사용자 발화
   - 반복 표현
   - 정서 변화
   - 기능 손상 표현
10. 종단적 상태 변화
    - 이전 대비 호전/악화/유지
    - 새로운 증상
    - 재발 신호
    - CTRS 변화
11. AI 판단의 한계
    - 진단 아님
    - OCR/STT 오류 가능성
    - RAG 근거 제한 가능성
    - 전문가 검토 필요
12. 권장 다음 조치
    - 자가관리
    - 재평가
    - 전문가 상담
    - 정신건강의학과 상담 고려
    - 위기지원 안내

### 출력 형식

- 사용자용 PDF
- 전문가용 PDF
- 내부 저장용 JSON
- FHIR Bundle
- Dashboard summary

### FHIR 후보 Resource

- Patient
- Encounter
- Questionnaire
- QuestionnaireResponse
- Observation
- MedicationStatement
- DocumentReference
- DiagnosticReport
- CarePlan

---

## Agent 13. QA & Consistency Checker Agent

### 목적

Handoff report 생성 전후에 점수 계산, 위험 신호, 정보 출처, RAG 근거, OCR/STT confidence, 진단 표현 여부를 검증하여 최종 report의 신뢰성을 높인다.

### 주요 기능

- 구조화 설문 점수 계산 검증
- cut-off 해석 검증
- 위험 신호 누락 확인
- PHQ-9 자살 문항 양성 여부 확인
- C-SSRS/ASQ 위험 응답 확인
- CTRS level과 대응 조치 일치 여부 확인
- OCR/STT confidence 낮은 정보 표시
- 대화 내용과 report 간 불일치 확인
- 진료기록과 사용자 발화 간 불일치 확인
- 근거 없는 RAG 출력 제거
- 진단 확정 표현 제거
- report release gate 수행

### 출력 예시

```json
{
  "qa_status": "needs_review",
  "issues": [
    "OCR 약물명 confidence 낮음",
    "자살위험 gate 응답 확인 필요",
    "CTRS 2단계이므로 dashboard critical alert 필요"
  ],
  "blocked_reason": "ctrs_level_2_requires_human_review"
}
```

---

# Task 2. 진료과/병원 정보 제공

## 기능 2-1. 진료과 후보 결정

### Agent 14. Department Matching Agent

#### 목적

Clinical Context RAG Agent와 Survey Scoring Agent의 결과를 바탕으로 사용자에게 적절한 진료과 후보를 제시한다.

#### 주요 기능

- 정신건강 영역 후보 기반 진료과 매칭
- CTRS 기반 긴급도 판단
- 신체증상 동반 시 감별 진료과 후보 제시
- 사용자 위치 기반 병원 탐색 요청
- 응급 상황 여부 판단

#### 출력 예시

```json
{
  "department_candidates": [
    {
      "department": "정신건강의학과",
      "reason": "불안 및 우울 증상 평가 필요"
    },
    {
      "department": "가정의학과",
      "reason": "수면 문제 및 신체 증상 감별 가능"
    }
  ],
  "urgency": "soon",
  "ctrs_level": 4
}
```

#### 주의사항

- “진료과 추천”보다 “진료과 후보 정보 제공”으로 표현한다.
- 응급 위험이 있으면 병원 리스트보다 119/응급실 안내가 우선이다.
- AI는 특정 병원 방문을 강제하거나 진단하지 않는다.

---

## 기능 2-2. 병원/기관 탐색 및 지도 출력

### Agent 15. Hospital Search Agent

#### 목적

사용자의 현재 위치와 진료과 후보를 바탕으로 공공의료기관 API 및 지도 API를 활용하여 근처 병원/기관 정보를 제공한다.

#### 주요 기능

- 사용자 현재 위치 확인
- 위치정보 이용 동의 확인
- 심평원 API 또는 공공데이터 기반 병원 탐색
- 카카오 맵 API 기반 지도 출력
- 진료과, 거리, 운영시간, 응급 여부 기준 정렬
- 정신건강복지센터, 상담센터 등 기관 정보 제공 가능
- 사용자가 선택한 병원 상세 정보 제공

#### 출력 정보

- 병원명
- 진료과
- 주소
- 전화번호
- 거리
- 운영시간
- 응급실 여부
- 지도 좌표
- 길찾기 링크
- 비고

#### 주의사항

- 광고/제휴 병원 우선 노출 시 반드시 표시한다.
- 위치정보는 별도 동의 후 사용한다.
- 의료기관 정보는 최신성이 중요하므로 API 응답 시간을 저장한다.
- CTRS 1–2단계에서는 병원 리스트보다 119/112/응급실 이송 안내가 우선이다.
- CTRS 3단계에서는 빠른 정신건강의학과 평가 또는 위기 개입 안내를 우선한다.

---

# Task 3. 위기 관리 알림

## 기능 3-1. 위기 알림 생성

### Agent 16. Crisis Notification Agent

#### 목적

Safety/Risk Triage Agent가 CTRS 1–3단계 위험 신호를 감지한 경우, 의료진/원무과/상담자용 웹 대시보드에 위기 알림을 생성한다.

#### Alert 생성 기준

| CTRS 단계 | Alert 여부 | Alert 우선순위 | 대응 |
|---:|---|---|---|
| **1단계** | 필수 | Critical | 즉시 확인 필요, 119/112/응급실 이송 권고 |
| **2단계** | 필수 | Critical | 즉시 human review, 위기상담/응급 대응 안내 |
| **3단계** | 필수 | High | 빠른 위기 개입, 전문가 평가 권장 |
| **4단계** | 선택 | Medium | human review queue 등록 가능 |
| **5단계** | 불필요 | Low | 일반 기록만 저장 |

#### 주요 기능

- CTRS 1–3단계 감지 시 dashboard alert 생성
- CTRS 4단계는 조건부 alert 또는 review queue 등록
- 알림 우선순위 설정
- 담당자 배정
- 미확인 알림 escalation
- 알림 확인 여부 추적
- 조치 결과 기록
- audit log 저장

#### Alert 정보

```json
{
  "alert_id": "uuid",
  "user_id": "uuid",
  "ctrs_level": 1,
  "alert_priority": "critical",
  "trigger_source": "chat",
  "trigger_evidence": [
    "사용자가 자살시도 직후 상황을 언급함"
  ],
  "recommended_action": [
    "call_119",
    "call_112_if_violence_or_immediate_danger",
    "emergency_room_transfer",
    "notify_clinician_dashboard"
  ],
  "status": "new",
  "created_at": "2026-06-18T18:30:00+09:00"
}
```

#### 주의사항

- 위험 알림은 반드시 audit log에 기록한다.
- 알림이 발생했을 때 누가 언제 확인했는지 기록한다.
- 알림만 생성하고 대응 체계가 없으면 위험하므로, 운영상 대응 SLA를 정의해야 한다.

---

## 기능 3-2. 위기 대응 Workflow

### Agent 17. Crisis Workflow Agent

#### 목적

CTRS 1–4단계 위험 신호가 감지되었을 때 사용자에게 적절한 위기 대응 정보를 제공하고, 의료진/관리자 대응 workflow를 실행한다.

#### 주요 기능

- 사용자에게 위기 안내 메시지 제공
- 일반 상담 대화 중단 또는 제한
- 109/119/112 안내
- 보호자 또는 의료진 연계 동의 확인
- 의료진/원무과 dashboard alert 생성
- 담당자 확인 여부 추적
- follow-up task 생성
- 조치 결과 기록

#### CTRS 단계별 대응

| CTRS 단계 | 사용자 대응 | 내부 대응 |
|---:|---|---|
| **1단계 초응급** | 일반 대화 중단. 즉시 119 또는 112 안내. 응급실 이송 권고. | Critical alert 생성, 의료진/관리자 즉시 알림, human review 최우선 등록 |
| **2단계 고위험** | 일반 상담 제한. 109/119/112 안내. 혼자 있지 않도록 안내. | Critical alert 생성, 보호자/의료진 연계 확인, human review 즉시 등록 |
| **3단계 급성기** | 위기상담 109 안내, 빠른 정신건강의학과 평가 권고. | High alert 생성, 24–48시간 내 follow-up task 생성 |
| **4단계 중증/주의** | 외래 진료 또는 상담 권고, 구조화 문진 지속 가능. | Medium review queue 등록 가능, 재평가 일정 생성 |
| **5단계 저위험/안정기** | 일반 문진 지속, 자가관리 및 외래 예약 안내. | 일반 기록 저장 |

#### 위기 안내 문구 예시

##### CTRS 1–2단계

```text
지금은 안전이 가장 중요합니다. 현재 스스로를 해치거나 다른 사람을 해칠 위험이 있거나, 이미 행동으로 옮겼다면 즉시 119 또는 112에 연락해 주세요. 자살이나 자해 충동이 강하다면 국번 없이 109 자살예방상담전화로 바로 연락할 수 있습니다. 가능하다면 지금 혼자 있지 말고, 가까운 사람이나 의료진에게 즉시 도움을 요청해 주세요.
```

##### CTRS 3단계

```text
현재 상태는 빠른 도움이 필요한 위기 상태일 수 있습니다. 지금 당장 위험한 상황이 아니라도, 환각, 망상, 공황발작, 심한 우울 악화가 있다면 빠른 시일 내 정신건강의학과 진료나 위기상담을 받는 것이 좋습니다. 자살이나 자해 생각이 강해지면 109, 119, 112로 즉시 도움을 요청해 주세요.
```

##### CTRS 4–5단계

```text
현재 상태를 조금 더 정확히 파악하기 위해 구조화된 사전문진을 진행하겠습니다. 문진 결과에 따라 정신건강의학과 외래 진료, 상담, 자가관리 방법, 재평가 일정을 안내할 수 있습니다.
```

---

# 공통 모듈

## Common Module 1. Consent & Privacy Module

### 목적

정신건강 정보, 진료기록, 약처방 기록, 위치정보, 음성, OCR 문서 등 민감정보 처리에 대한 동의와 철회를 관리한다.

### 주요 기능

- 개인정보 수집 동의
- 민감정보 처리 동의
- 의료정보 활용 동의
- 제3자 제공 동의
- 위치정보 이용 동의
- STT 처리 동의
- OCR 처리 동의
- 의료진/기관 연계 동의
- 동의 철회
- 데이터 삭제 요청

---

## Common Module 2. Evidence Store

### 목적

AI 판단의 근거를 source 단위로 저장한다.

### 저장 항목

- 사용자 발화 원문
- 구조화 설문 응답
- OCR 추출 결과
- STT transcript
- 진료기록 근거
- 약처방 기록 근거
- RAG 검색 결과
- 위험 판단 trigger 문장
- CTRS 판단 근거
- 설문 점수 계산 결과
- report 생성 근거

### 원칙

- 모든 AI 판단에는 evidence가 연결되어야 한다.
- evidence 없는 추론은 report에 포함하지 않는다.
- 사용자 발화와 AI 요약을 분리 저장한다.
- OCR/STT confidence가 낮은 정보는 별도로 표시한다.

---

## Common Module 3. Audit Log

### 목적

시스템 내 주요 이벤트, agent 판단, 사용자 동의, report 생성, dashboard alert, 의료진 확인 기록을 추적한다.

### 저장 항목

- 로그인 기록
- 동의 변경 기록
- agent decision log
- survey execution log
- score calculation log
- RAG retrieval log
- CTRS triage log
- report generation log
- alert generation log
- dashboard access log
- clinician action log

---

## Common Module 4. Human Review Queue

### 목적

AI 판단만으로 처리하기 어려운 고위험 또는 불확실 사례를 사람이 검토할 수 있도록 대기열에 등록한다.

### Review Queue 등록 조건

- CTRS 1–3단계
- CTRS 4단계 중 보호요인 약함 또는 기능 손상 심함
- PHQ-9 자살 문항 양성
- C-SSRS 또는 ASQ 고위험
- OCR confidence 낮은 진단/약물 정보
- STT confidence 낮은 위험 발화
- RAG 근거 부족
- 진료기록과 사용자 발화 불일치
- 약물 중단 또는 과다복용 가능성
- report QA fail
- 사용자가 직접 전문가 연결 요청

---

## Common Module 5. Knowledge Base & RAG Governance

### 목적

정신건강 지식베이스, 의료 DB, 구조화 문진 도구, 진료과 매핑 정보를 안전하게 관리한다.

### 주요 기능

- 정신건강 영역별 knowledge base 구축
- 문진 도구별 scoring guide 저장
- 진료과 매핑 rule 저장
- RAG retrieval source 저장
- 근거 문서 버전 관리
- 오래된 문서 비활성화
- 검색 결과와 최종 판단 분리 저장

### 주의사항

- RAG가 반환한 정보는 진단이 아니다.
- 근거 문서가 없으면 report에 포함하지 않는다.
- 의료 DB 정보는 최신성 검증이 필요하다.
- 임상적 판단은 human review와 전문가 평가를 전제로 한다.

---

# 개발 우선순위

## MVP 1차: 기본 사전문진 및 Handoff Report

### 포함 기능

- 회원가입/로그인
- 최초 사용자 intake
- 기본 정신건강 기초 설문
- 자율 대화 기반 문진
- CTRS 기반 Safety/Risk Triage
- PHQ-4
- PHQ-9
- GAD-7
- WHO-5
- Survey Planner
- Survey Scoring
- Handoff Report Writer
- QA & Consistency Checker

### 제외 기능

- OCR
- STT
- RAG
- 병원 탐색
- FHIR export
- 위기관리 dashboard

---

## MVP 2차: 기록 및 음성/문서 정보 병합

### 포함 기능

- OCR Document Agent
- STT Transcript Agent
- Information Fusion Agent
- 이전 대화 기록 병합
- 이전 handoff report 병합
- Longitudinal State Tracking Agent

---

## MVP 3차: RAG 기반 정신건강 영역 및 진료과 후보 분석

### 포함 기능

- Clinical Context RAG Agent
- 의료 DB / 정신건강 지식베이스 구축
- 정신건강 영역 후보 추론
- 진료과 후보 추론
- 구조화 문진 추천 고도화
- RAG 근거 저장
- Knowledge Base & RAG Governance

---

## MVP 4차: 병원/기관 정보 제공 및 지도 연동

### 포함 기능

- Department Matching Agent
- Hospital Search Agent
- 심평원 API 또는 공공데이터 API 연동
- 카카오 맵 API 연동
- 위치 기반 병원/기관 정보 제공

---

## MVP 5차: 위기 관리 Dashboard 및 운영 Workflow

### 포함 기능

- Crisis Notification Agent
- Crisis Workflow Agent
- 의료진/원무과 웹 dashboard
- human review queue
- alert escalation
- audit log
- 운영 대응 SLA 관리

---

## MVP 6차: 의료정보 표준 연동 및 고도화

### 포함 기능

- FHIR Bundle 생성
- QuestionnaireResponse 매핑
- Observation 매핑
- DiagnosticReport 매핑
- MedicationStatement 매핑
- DocumentReference 매핑
- 기관 EMR 연동 검토

---

# 시스템 전체 Hierarchy 요약

```text
Task 0. 회원가입/로그인 및 최초 Intake
  기능 0-1. 회원가입/로그인 및 사용자 프로필 생성
    Agent 0-1. Auth/Profile Agent
  기능 0-2. 최초 사용자 정신건강 기초 설문
    Agent 0-2. Initial Intake Agent

Task 1. AI 기반 사전문진 Handoff Report 생성
  Agent 1. Orchestrator Agent

  기능 1-1. 자율 대화 기반 문진
    Agent 2. Chatbot Interview Agent
    Agent 3. OCR Document Agent
    Agent 4. STT Transcript Agent
    Agent 5. Safety/Risk Triage Agent

  기능 1-2. RAG 기반 정신건강 영역 및 진료과 후보 추론
    Agent 6. Information Fusion Agent
    Agent 7. Clinical Context RAG Agent

  기능 1-3. 구조화된 사전문진 설문
    Agent 8. Survey Planner Agent
    Agent 9. Survey Scoring & Interpretation Agent

  기능 1-4. 종단적 상태 추론
    Agent 10. Sentiment & Conversation Signal Agent
    Agent 11. Longitudinal State Tracking Agent

  기능 1-5. Handoff Report 생성
    Agent 12. Handoff Report Writer Agent
    Agent 13. QA & Consistency Checker Agent

Task 2. 진료과/병원 정보 제공
  기능 2-1. 진료과 후보 결정
    Agent 14. Department Matching Agent
  기능 2-2. 병원/기관 탐색 및 지도 출력
    Agent 15. Hospital Search Agent

Task 3. 위기 관리 알림
  기능 3-1. 위기 알림 생성
    Agent 16. Crisis Notification Agent
  기능 3-2. 위기 대응 Workflow
    Agent 17. Crisis Workflow Agent

Common Modules
  Common Module 1. Consent & Privacy Module
  Common Module 2. Evidence Store
  Common Module 3. Audit Log
  Common Module 4. Human Review Queue
  Common Module 5. Knowledge Base & RAG Governance
```

---

# 데이터 구조 예시

```json
{
  "user_id": "uuid",
  "session_id": "uuid",
  "is_first_use": true,
  "profile": {
    "name": "홍길동",
    "birth_year_month": "1995-03",
    "age": 31,
    "sex": "unspecified"
  },
  "input_sources": [
    {
      "source_type": "chat",
      "timestamp": "2026-06-18T18:00:00+09:00",
      "content": "요즘 잠을 거의 못 자고 불안합니다.",
      "confidence": 1.0
    },
    {
      "source_type": "ocr_prescription",
      "timestamp": "2026-06-18T18:03:00+09:00",
      "content": "...",
      "confidence": 0.86
    }
  ],
  "safety_triage": {
    "ctrs_level": 4,
    "ctrs_category": "moderate_severe_attention",
    "risk_domains": ["depression", "anxiety"],
    "immediacy": "non_imminent",
    "violence_risk": false,
    "psychosis_risk": false,
    "substance_related_risk": false,
    "trigger_source": "chat",
    "trigger_evidence": ["일상생활 유지가 어렵다고 표현"],
    "protective_factors": ["가족과 연락 가능"],
    "recommended_action": ["structured_survey", "outpatient_consultation"],
    "created_at": "2026-06-18T18:30:00+09:00"
  },
  "domain_hypotheses": [
    {
      "domain": "anxiety",
      "confidence": 0.82,
      "evidence": ["불안 호소", "수면 저하"],
      "recommended_tools": ["GAD-7", "WHO-5"]
    }
  ],
  "survey_results": [
    {
      "tool": "GAD-7",
      "score": 12,
      "severity": "moderate",
      "date": "2026-06-18"
    }
  ],
  "handoff_report_status": "draft"
}
```

---

# 최종 개발 정의

본 시스템은 AI가 사용자를 진단하는 시스템이 아니다. 본 시스템은 대화, 기록, 설문, 음성, 문서 정보를 통합하여 정신건강 위험 신호와 주요 증상 영역을 선별하고, 사용자 상태에 적합한 구조화 문진을 수행하며, 전문가가 빠르게 이해할 수 있는 근거 기반 handoff report를 생성하는 시스템이다.

AI의 핵심 역할은 다음과 같다.

1. 위험 신호를 놓치지 않는다.
2. CTRS 기반 정신과적 응급 위험도를 분류한다.
3. 사용자의 상태에 맞는 문진 도구를 선택한다.
4. 대화와 기록을 구조화한다.
5. 구조화 설문 결과를 정확히 계산한다.
6. 이전 상태와 현재 상태를 비교한다.
7. 전문가에게 전달 가능한 report를 생성한다.
8. 고위험 상황에서는 즉시 위기 대응 workflow로 전환한다.

의학적 진단과 치료 결정은 전문가가 수행한다.

---

# 참고 근거 및 개발 참고 자료

1. 국립정신건강센터, 정신과적 응급상황에서의 현장대응안내 2.0  
   https://www.ncmh.go.kr/mentalhealth/board/boardView.do?no=8392&fno=106&menu_cd=04_02_00_03

2. Crisis Triage Rating Scale 관련 국내 정신위기개입 응급출동 연구  
   https://jknpa.org/DOIx.php?id=10.4306%2Fjknpa.2024.63.4.260

3. 보건복지부, 자살예방 상담전화 109 통합 운영 안내  
   https://www.mohw.go.kr/board.es?act=view&bid=0027&list_no=1479607&mid=a10503010100&nPage=1&tag=

4. 보건복지상담센터 자살예방상담전화 109 안내  
   https://www.129.go.kr/109

5. 식품의약품안전처, 인공지능기술이 적용된 디지털의료기기의 허가·심사 가이드라인  
   https://www.mfds.go.kr/brd/m_1060/view.do?seq=15657

6. HL7 FHIR QuestionnaireResponse  
   https://fhir.hl7.org/fhir/questionnaireresponse.html

7. HL7 FHIR Observation  
   https://build.fhir.org/observation.html

8. HL7 FHIR DiagnosticReport  
   https://build.fhir.org/diagnosticreport.html

9. SAMHSA SBIRT  
   https://www.samhsa.gov/substance-use/treatment/sbirt

10. PHQ-9 원 논문  
    Kroenke K, Spitzer RL, Williams JBW. The PHQ-9: Validity of a Brief Depression Severity Measure. Journal of General Internal Medicine. 2001.

11. GAD-7 원 논문  
    Spitzer RL, Kroenke K, Williams JBW, Löwe B. A Brief Measure for Assessing Generalized Anxiety Disorder: The GAD-7. Archives of Internal Medicine. 2006.

12. PHQ-4 원 논문  
    Kroenke K, Spitzer RL, Williams JBW, Löwe B. An Ultra-Brief Screening Scale for Anxiety and Depression: The PHQ-4. Psychosomatics. 2009.
