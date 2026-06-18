---
patient_id: VP-005
vendor: exaone
model: depmkuykpfon9lg
latency_ms: 9794
tokens: 2245
finish_reason: stop
generated_at: 2026-06-16T14:58:42+09:00
data_type: synthetic
quality_pass: False
sections_present: 10/11
evidence_citations: 25
diagnosis_violations: 0
risk_match: True
---

## Handoff Summary

### 1. One-line Summary
최유진님은 신체 불편감과 지속적 피로감을 호소하며, 중등도 수준의 우울 및 불안 증상을 보이고 있습니다. [ev_msg_002][ev_msg_006][ev_scale_001][ev_scale_002]

### 2. Chief Complaint (주호소)
- 신체 불편감과 지속적 피로감, 일상 기능 저하 [ev_msg_002][ev_msg_006]

### 3. History of Present Illness (현병력)
- 환자는 신체 불편감과 일상 업무 수행의 어려움을 호소하며 내원하였습니다. [ev_msg_002]  
- 두통약을 주 3~4회 복용하며, 복용 후 특별한 부작용은 없으나 속이 불편하여 소화제를 병용하고 있습니다. [ev_msg_003][ev_msg_004]  
- 수면은 유지되나, 기상 후 지속적인 피로감과 신체 무거움을 호소하며, 낮 동안 졸림으로 인해 업무 수행에 어려움을 겪고 있습니다. [ev_msg_005][ev_msg_006]

### 4. 주요 증상
| 영역 | 상태 | 근거 |
|---|---|---|
| 수면 | 수면 유지되나 기상 후 피로감 지속, 낮 동안 졸림 | [ev_msg_005][ev_msg_006] |
| 식욕 | 정보 미수집 | 판단불가 |
| 기분 | 신체 불편감과 업무 부담으로 인한 스트레스 호소 | [ev_msg_002] |
| 불안 | 중등도 수준의 불안 증상 시사 (GAD-7 점수 기반) | [ev_scale_002] |
| 집중력 | 낮 동안 졸림으로 인해 업무 수행 어려움 | [ev_msg_006] |
| 기능 손상 | 업무 수행 어려움, 신체 불편감으로 인한 일상 기능 저하 | [ev_msg_002][ev_msg_006] |

### 5. PHQ-9 / GAD-7
- PHQ-9 총점: 14점 (중등도 우울 증상 시사) [ev_scale_001]  
- GAD-7 총점: 11점 (중등도 불안 증상 시사) [ev_scale_002]

### 6. Risk & Safety Flags
- 현재 직접적 위험 신호 없음 [ev_risk_001]

### 7. Medication / Past History
- 두통약 주 3~4회 복용 중, 복용 후 특별한 부작용 없음 [ev_msg_003][ev_msg_004]  
- 과거 정신건강 진료 이력은 대화 내 명시되지 않음 [판단불가]

### 8. Uploaded Documents
- 업로드된 문서 없음 [ev_doc_001]

### 9. Longitudinal Delta
- 재진 — 이전 세션 정보는 대화 내 약물 관련 발화 참조 [ev_prior_001]

### 10. Missing Information
- 식욕 변화 여부  
- 기분 변화 양상 (예: 무기력, 무기력감 등 구체적 서술)  
- 불안의 구체적 유발 상황 또는 신체 증상  
- 과거 정신건강 진료 이력  
- 약물 복용 기간 및 용량  
- 수면의 질 (입면 시간, 중간 각성 등)

###  secrecy Table
| ID | 유형 | 출처 | 내용 요약 |
|---|---|---|---|
| ev_msg_001 | message | 환자 발화 | 상담 시작 인사 및 문진 요청 |
| ev_msg_002 | message | 환자 발화 | 신체 불편감과 업무 부담 호소 |
| ev_msg_003 | message | 환자 발화 | 두통약 복용 빈도 및 부작용 없음 언급 |
| ev_msg_004 | message | 환자 발화 | 소화제 병용 복용 언급 |
| ev_msg_005 | message | 환자 발화 | 수면 유지되나 기상 후 피로감 및 낮 졸림 호소 |
| ev_msg_006 | message | 환자 발화 | 신체 무거움, 지속적 피로, 업무 수행 어려움 언급 |
| ev_scale_001 | scale | PHQ-9 결과 | 총점 14점 (중등도 우울 증상 시사) |
| ev_scale_002 | scale | GAD-7 결과 | 총점 11점 (중등도 불안 증상 시사) |
| ev_risk_001 | risk_event | 위험 이벤트 | 현재 직접적 위험 신호 없음 |
| ev_prior_001 | prior_handoff | 이전 세션 기록 | 재진, 약물 관련 발화 참조 |