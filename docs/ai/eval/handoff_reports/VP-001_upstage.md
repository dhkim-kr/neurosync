---
patient_id: VP-001
vendor: upstage
model: solar-pro3
latency_ms: 9411
tokens: 2583
finish_reason: stop
generated_at: 2026-06-16T14:55:37+09:00
data_type: synthetic
quality_pass: True
sections_present: 11/11
evidence_citations: 24
diagnosis_violations: 0
risk_match: True
---

## Handoff Summary

### 1. One-line Summary
서연 님은 약 3주 전부터 입면 지연과 수면 시간 감소가 지속되며, 경미한 우울 및 불안 증상을 호소하고 있습니다. [ev_msg_002][ev_msg_004][ev_scale_001][ev_scale_002]

### 2. Chief Complaint (주호소)
- 잠들기 어려움 및 수면 시간 감소: 침대에 누워도 생각이 계속 돌아와서 1~2시간 소요, 총 수면 시간 5시간 [ev_msg_004][ev_msg_006]
- 출근 시 답답한 느낌: 최근 3주 전부터 점차 심해짐 [ev_msg_002]

### 3. History of Present Illness (현병력)
서연 님은 약 3주 전부터 입면 지연과 수면 시간 감소가 시작되었으며, 초기에는 가끔 발생했으나 점차 빈도가 증가하여 현재는 매일 밤 1~2시간 정도 잠드는 데 시간이 소요되고 있습니다. 침대에 누워도 생각이 계속 돌아와서 수면이 방해받는다고 표현했습니다. 총 수면 시간은 밤 12시에 잠들어 아침 6시 전에 일어나며, 약 5시간 정도로 감소했습니다. 또한 출근 시 답답한 느낌이 들며, 이는 최근 3주 전부터 점차 심해진 것으로 보고되었습니다. [ev_msg_002][ev_msg_004][ev_msg_006]

### 4. 주요 증상
| 영역 | 상태 | 근거 |
|---|---|---|
| 수면 | 입면 지연 (1~2시간 소요) 및 수면 시간 감소 (5시간) | [ev_msg_004][ev_msg_006] |
| 식욕 | 정보 미수집 | [ev_msg_007] |
| 기분 | 우울 증상 호소 (PHQ-9 문항별 점수 1점) | [ev_scale_001] |
| 불안 | 불안 증상 호소 (GAD-7 문항별 점수 1점) | [ev_scale_002] |
| 집중력 | 정보 미수집 | [ev_msg_008] |
| 기능 손상 | 출근 시 답답한 느낌, 일상 기능 저하 시사 | [ev_msg_002] |

### 5. PHQ-9 / GAD-7
- **PHQ-9**: 총점 8점 (경미), 문항별 점수: [1, 1, 1, 1, 1, 0, 1, 1, 1] [ev_scale_001]
- **GAD-7**: 총점 5점 (경미), 문항별 점수: [1, 1, 1, 0, 1, 0, 1] [ev_scale_002]

### 6. Risk & Safety Flags
현재 직접적 위험 신호 없음 [ev_risk_001]

### 7. Medication / Past History
- 복용 약물: 정보 미수집 [ev_msg_009]
- 과거 정신건강 진료 이력: 정보 미수집 [ev_msg_10]

### 8. Uploaded Documents
없음 [ev_doc_001]

### 9. Longitudinal Delta
해당 없음 (초진) [ev_prior_001]

### 10. Missing Information
- 식욕 변화
- 기분 변화 (구체적 내용)
- 불안 증상 (구체적 내용)
- 집중력 변화
- 복용 중인 약물
- 과거 정신건강 진료 이력
- 수면 패턴 (구체적 내용)

### 11. Evidence Table
| ID | 유형 | 출처 | 내용 요약 |
|---|---|---|---|
| ev_msg_001 | message | 환자 발화 | "안녕하세요, 서연 님. 처음 뵙겠습니다. 편하게 말씀해 주시면 돼요. 최근 잠을 잘 못 주무시고 출근할 때 답답한 느낌이 드신다고 하셨는데, 구체적으로 언제부터 시작되셨나요?" |
| ev_msg_002 | message | 환자 발화 | "음... 약 3주 전쯤부터 그런 것 같아요. 처음엔 가끔 그랬는데 점점 더 심해졌어요." |
| ev_msg_003 | message | 환자 발화 | "입면까지 얼마나 걸리시는 편인가요? 보통 30분 이내면 편하게 주무시는 편인데, 요즘은 어떠신가요?" |
| ev_msg_004 | message | 환자 발화 | "잠들기까지 1~2시간 정도 걸려요. 침대에 누워도 생각이 계속 돌아와서." |
| ev_msg_005 | message | 환자 발화 | "하루에 총 몇 시간 정도 주무시는 편인지 궁금해요. 보통 몇 시에 주무시고 몇 시에 일어나시나요?" |
| ev_msg_006 | message | 환자 발화 | "밤 12시쯤 자서 아침 6시 전에 일어나요. 그래서 총 수면 시간이 5시간 정도밖에 안 되죠." |
| ev_msg_007 | message | 환자 발화 | (해당 발화 없음) |
| ev_msg_008 | message | 환자 발화 | (해당 발화 없음) |
| ev_msg_009 | message | 환자 발화 | (해당 발화 없음) |
| ev_msg_010 | message | 환자 발화 | (해당 발화 없음) |
| ev_scale_001 | scale | PHQ-9 결과 | 총점 8점 (경미), 문항별 점수: [1, 1, 1, 1, 1, 0, 1, 1, 1] |
| ev_scale_002 | scale | GAD-7 결과 | 총점 5점 (경미), 문항별 점수: [1, 1, 1, 0, 1, 0, 1] |
| ev_doc_001 | document_block | 업로드 문서 | 없음 |
| ev_risk_001 | risk_event | 위험 이벤트 | 없음 |
