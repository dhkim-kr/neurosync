---
patient_id: VP-002
vendor: exaone
model: depmkuykpfon9lg
latency_ms: 6972
tokens: 2309
finish_reason: stop
generated_at: 2026-06-16T14:56:14+09:00
data_type: synthetic
quality_pass: True
sections_present: 11/11
evidence_citations: 17
diagnosis_violations: 0
risk_match: True
---

## Handoff Summary

### 1. One-line Summary  
환자는 시험 및 발표 상황에서 반복. 심장 두근거림, 호흡 곤란, 손 떨림, 수면 장애 및 사회적 회피를 호소하며, PHQ-9 12점(중등도), GAD-าร 14점(중등도 이상)으로 평가됨 [ev_msg_002][ev_scale_001][ev_scale_002]

### 2. Chief Complaint (주호소)  
- 시험 및 발표 상황에서 심장 두근거림, 숨 막힘, 손 떨림, 호흡 곤란이 반복됨 [ev_msg_002]

### 3. History of Present Illness (현병력)  
증상은 한 달 전 중간시험부터 시작되었으며, 발표나 지도교수 미팅과 같은 스트레스 상황에서 유발됨. 증상은 10~20분 지속되며, 이후 불안으로 인해 수면 장애 발생. 증상 회피 행동으로 인해 연구실 출석 감소, 사회적 고립 증가 [ev_msg_002][ev_msg_004][ev_msg_006]

### 4. 주요 증상  

| 영역 | 상태 | 근거 |
|------|------|------|
| 수면 | 불안으로 인해 수면 장애 발생 | [ev_msg_002] |
| 식욕 | 정보 미수집 | 정보 미수집 |
| 기분 | 불안 및 회피 행동으로 인한 고립감 | [ev_msg_006] |
| 불안 | 발표 및 시험 상황에서 신체 증상 및 회피 행동 | [ev_msg_002][ev_msg_004] |
| 집중력 | 정보 미수집 | 정보 미수집 |
| 기능 손상 | 연구실 출석 및 사회적 활동 감소 | [ev_msg_006] |

### 5. PHQ-9 / GAD-7  
- **PHQ-9**: 총점 12점 (27점 만점), 중등도 우울 증상 [ev_scale_001]  
  - 문항별 점수: [2, 1, 1, 2, 2, 1, 1, 1, 1]  
- **GAD-7**: 총점 14점 (21점 만점), 중등도 이상 불안 증상 [ev_scale_002]  
  - 문항별 점수: [2, 2, 2, 2, 2, 2, 2]

### 6. Risk & Safety Flags  
현재 직접적 위험 신호 없음 [ev_risk_001]

### 7. Medication / Past History  
- 복용 중인 약물: 정보 미수집  
- 과거 정신건강 진료 이력: 정보 미수집  
  → 환자 발화 기준, 약물 관련 언급 없음

### ες. Uploaded Documents  
없음 [ev_doc_001]

### 9. Longitudinal Delta  
해당 없음 (초진) [ev_prior_001]

### 10. Missing Information  
- 현재 복용 중인 약물 정보  
- 과거 정신건강 진료 이력  
- 수면 및 식욕 변화에 대한 구체적 기술  
- 자해 또는 타해 위험 여부  
- 일상 기능 손상의 구체적 범위 (예: 학업 수행도 변화)  

### 11. Evidence Table  

| ID | 유형 | 출처 | 내용 요약 |
|-----|------|------|-----------|
| ev_msg_001 | message | assistant | 환자에게 증상 빈도 질문 |
| ev_msg_002 | message | user | 증상 시작 시점, 유발 상황, 지속 시간, 수면 장애 언급 |
| ev_msg_003 | message | assistant | 증상 빈도 질문 |
| ev_msg_004 | message | user | 주 2~3회 발생, 발표 회피 시 악화, 사회적 고립 시작 |
| ev_msg_005 | message | assistant | 사회적 활동 변화 질문 |
| ev_msg_006 | message | user | 연구실 출석 감소, 지도교수 미팅 회피, 친구 만남 감소, 고립감 |
| ev_scale_001 | scale | PHQ-9 결과 | 총점 12점, 중등도 우울 증상 |
| ev_scale_002 | scale | GAD-7 결과 | 총점 14점, 중등도 이상 불안 증상 |
| ev_risk_001 | risk_event | 위험 이벤트 | 없음 |
| ev_doc_001 | document_block | 업로드 문서 | 없음 |