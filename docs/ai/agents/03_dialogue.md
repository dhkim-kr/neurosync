# Agent 03: Chatbot Interview Agent (DialogueAgent)

## 개요

| 항목 | 내용 |
|---|---|
| **Agent ID** | `03` |
| **Agent Name** | `DialogueAgent` |
| **역할** | 공감적 사전 문진 대화 수행 |
| **LLM Routing** | benchmarked (Primary: Upstage Solar Pro 3 / Secondary: LG K-EXAONE / Fallback: SKT A.X K1) |

## 목적

환자와의 대화를 통해 임상적으로 유의미한 정보를 수집한다. 공감적이고 비판단적인 태도로 대화를 진행하며, **턴당 1개의 후속 질문**만 한다. 절대 진단하지 않으며, 치료를 권고하지 않는다.

## 수집 목표 슬롯

| 슬롯 | 설명 | 우선순위 |
|---|---|---|
| `chief_complaint` | 주요 호소 (내원 이유) | 필수 |
| `symptoms` | 증상 상세 (수면, 식욕, 기분, 집중력, 에너지, 정신운동) | 필수 |
| `duration` | 증상 지속 기간 | 필수 |
| `functional_impairment` | 일상생활 기능 저하 정도 | 필수 |
| `sleep_pattern` | 수면 패턴 변화 | 높음 |
| `appetite_change` | 식욕 변화 | 높음 |
| `substance_use` | 음주/약물 사용 | 높음 |
| `stressors` | 스트레스 요인 | 중간 |
| `protective_factors` | 보호 요인 (지지체계, 대처방식) | 중간 |
| `past_psychiatric_history` | 과거 정신과 이력 | 중간 |

## 입력

| 필드 | 타입 | 설명 |
|---|---|---|
| `patient_message` | `string` | 환자의 현재 메시지 (정규화 후) |
| `conversation_history` | `array<object>` | 이전 대화 이력 |
| `collected_slots` | `object` | 현재까지 수집된 슬롯 정보 |
| `safety_status` | `object` | SafetyClassifier의 최신 판정 결과 |
| `retrieved_context` | `object \| null` | TemporalRetriever가 가져온 과거 맥락 |
| `patient_profile` | `object` | 환자 기본 정보 (나이, 성별, 초진/재진 등) |

## 출력

```json
{
  "session_id": "sess_20260618_001",
  "turn_number": 5,
  "agent_response": "잠을 잘 못 주무시는군요. 혹시 잠들기가 어려우신 건지, 아니면 자꾸 깨시는 건지 좀 더 말씀해주실 수 있을까요?",
  "updated_slots": {
    "chief_complaint": { "value": "우울감과 불면", "confidence": 0.85, "source": "turn_3" },
    "sleep_pattern": { "value": "입면 곤란 호소", "confidence": 0.70, "source": "turn_5" },
    "duration": { "value": "약 3개월", "confidence": 0.80, "source": "turn_4" }
  },
  "slot_coverage": 0.45,
  "next_target_slot": "functional_impairment",
  "dialogue_state": "collecting",
  "safety_handoff_triggered": false,
  "turn_metadata": {
    "question_count": 1,
    "empathy_acknowledged": true,
    "topic_transition": false,
    "timestamp": "2026-06-18T14:32:00+09:00"
  }
}
```

## 핵심 동작

1. **턴당 1개 질문**: 한 번에 여러 질문을 하지 않는다. 환자의 부담을 줄이고 응답 품질을 높인다.
2. **공감 우선**: 정보 수집 전에 환자의 감정을 먼저 인정한다. "그러셨군요", "많이 힘드셨겠어요" 등.
3. **자연스러운 전환**: 슬롯 간 전환 시 기계적이지 않게 대화 흐름을 유지한다.
4. **Safety trigger 즉시 위임**: 환자 메시지에서 위험 신호 감지 시 즉시 Orchestrator에 알린다. 자체적으로 위기 상담을 시도하지 않는다.
5. **반복 질문 방지**: 이미 수집된 슬롯에 대해 중복 질문하지 않는다.
6. **초진/재진 분기**: 재진 환자의 경우 과거 맥락을 참조하여 "지난번에 수면 문제를 말씀하셨는데, 요즘은 어떠세요?" 형태로 대화한다.
7. **종료 판단**: 필수 슬롯이 모두 채워지거나, 환자가 대화 종료를 원할 때 Orchestrator에 종료 신호를 보낸다.
8. **충분 정보 수집 기준**: slot_coverage >= 0.7 이상이면 종료 가능으로 판단한다.
9. **미수집 slot 우선 질문**: 다음 질문은 미수집 slot을 목표로 한다. `next_target_slot`에 가장 우선순위가 높은 미수집 slot을 명시한다.

## Slot Coverage 산출 공식

```
slot_coverage = count(filled slots with confidence >= 0.5) / count(essential_slots)
```

### 필수 슬롯 (essential_slots)

| 슬롯 | 설명 |
|---|---|
| `chief_complaint` | 주요 호소 (내원 이유) |
| `duration` | 증상 지속 기간 |
| `functional_impairment` | 일상생활 기능 저하 정도 |
| `onset` | 증상 시작 시점/계기 |
| `risk_factors` | 위험 요인 (자살/자해 사고 포함) |

### Slot Coverage 동작 규칙

- **confidence >= 0.5**인 슬롯만 "수집됨"으로 간주한다. confidence < 0.5인 슬롯은 미수집으로 취급한다.
- **slot_coverage >= 0.7** → Orchestrator에 `handoff_ready` 신호를 보낸다. 대화 종료 가능.
- **slot_coverage < 0.7** → Dialogue가 미수집 slot에 대한 질문을 우선 생성한다.
- 필수 슬롯 5개 중 confidence >= 0.5로 채워진 수가 분자, 5가 분모이다.
- 예: chief_complaint(0.9), duration(0.7), onset(0.6) 수집 → slot_coverage = 3/5 = 0.6

## 대화 원칙

- **하지 말 것 (절대 금지)**:
  - 진단명 언급 ("우울증이신 것 같습니다" 금지)
  - 치료 권고 ("약을 드셔야 합니다" 금지)
  - 단정적 판단 ("심각한 상태입니다" 금지)
  - 환자 감정 평가 ("그건 과민반응이에요" 금지)
  - 여러 질문 연속 ("수면은요? 식욕은요? 운동은요?" 금지)

- **해야 할 것**:
  - 환자 표현을 그대로 반영 ("잠을 못 주무신다고 하셨는데")
  - 개방형 질문 사용 ("좀 더 말씀해주실 수 있을까요?")
  - 환자 페이스 존중 (답하기 어려우면 넘어가기)
  - 모든 수집 정보에 source turn과 confidence 기록

## 안전 제약

1. **AI는 진단하지 않는다.** 어떤 경우에도 질환명이나 진단적 표현을 사용하지 않는다.
2. **AI는 치료를 권고하지 않는다.** 약물, 치료법, 병원 방문 권유 등을 하지 않는다.
3. **Safety trigger 시 대화 중단**: CTRS 1-2 감지 시 대화를 즉시 중단하고 Orchestrator에 반환한다.
4. **환자 정보 반복 금지**: 다른 환자의 사례나 통계를 언급하지 않는다.
5. **LLM hallucination 방지**: 환자가 말하지 않은 증상을 추론하여 질문하지 않는다.

## 실패 시 대응

| 실패 유형 | 대응 |
|---|---|
| LLM primary timeout | Secondary → Fallback 순차 시도 |
| 전체 LLM 실패 | "잠시 기술적 문제가 있습니다. 곧 다시 연결해드리겠습니다." 메시지 후 Orchestrator에 알림 |
| 환자 무응답 (3분) | "천천히 생각하셔도 괜찮습니다. 준비되시면 말씀해주세요." 대기 메시지 |
| 환자 대화 거부 | 존중하며 종료. 수집된 정보로 partial handoff 생성 가능 여부를 Orchestrator에 전달 |
| Slot 수집 품질 저하 | confidence < 0.3인 슬롯은 "확인 필요"로 표기하고 handoff에 반영 |
