---
patient_id: VP-004
vendor: exaone
model: depmkuykpfon9lg
latency_ms: 12787
tokens: 2876
finish_reason: stop
generated_at: 2026-06-16T14:57:36+09:00
data_type: synthetic
quality_pass: True
sections_present: 11/11
evidence_citations: 30
diagnosis_violations: 0
risk_match: True
---

## Handoff Summary

### 1. One-line Summary  
환자는 세르트랄린 50mg을 3개월 복용 중이며, 기분과 신체 상태는 초기 대비 일부 호전되었으나 아침 기상 곤란과 의욕 저하가 지속되고 있음 [ev_msg_002][ev_msg_004][ev_msg_016].

### 0. Chief Complaint (주호소)  
- 아침에 일어나는 것이 여전히 힘들며, 의욕이 부족함 [ev_msg_002][ev_msg_004][ev_msg_016].

### 3. History of Present Illness (현병력)  
환자는 세르트랄린 50mg을 3개월간 복용 중이며, 초기 오심은 사라졌으나 아침 기상 곤란과 피로감이 지속되고 있음. 입면은 이전보다 나아졌으나 새벽 5시경 각성 후 재입면이 어려움. 독서 및 학원 수업은 큰 어려움 없이 진행 중이나 아침 피로로 인해 다소 힘든 순간이 있음 [ev_msg_002][ev_msg_004][ev_msg_006][ev_msg_014].

### 4. 주요 증상  
| 영역 | 상태 | 근거 |
|------|------|------|
| 수면 | 입면은 개선되었으나 새벽 5시경 각성 후 재입면 어려움 | [ev_msg_004] |
| 식욕 | 식욕 정상, 체중 유지 | [ev_msg_008] |
| 기분 | 초기 대비 일부 호전되었으나 아침 무기력과 의욕 저하 지속 | [ev_msg_002][ev_msg_004][ev_msg_016] |
| 불안 | 경미한 걱정은 있으나 공황 증상 없음 | [ev_msg_010] |
| 집중력 | 독서 및 학원 수업 가능, 큰 어려움 없음 | [ev_msg_006] |
| 기능 손상 | 일상 활동 수행 가능하나 아침 피로로 인해 제한적 어려움 있음 | [ev_msg_006][ev_msg_016] |

### 5. PHQ-9 / GAD-7  
- **PHQ-9**: 총점 10점 (27점 만점), 심각도 moderate. 문항별 점수: [1, 1, 2, 1, 1, 1, 1, 1, 1] [ev_scale_001]  
- **GAD-7**: 총점 8점 (21점 만점), 심각도 mild. 문항별 점수: [1, 1, 2, 1, 1, 1, 1] [ev_scale_002]

### 6. Risk & Safety Flags  
현재 직접적 위험 신호 없음. 경미한 걱정은 있으나 공황 증상이나 자해/자살 생각 없음 [ev_msg_010].

### 7. Medication / Past History  
- 현재 복용 중인 약물: 세르트랄린 50mg, 3개월째 복용 [ev_msg_002][ev_msg_014]  
- 과거 정신건강 진료 이력: 자녀 독립 후 공허감 경험, 현재 서서히 적응 중 [ev_msg_012]  
- 약물 복용 준수: 꾸준히 복용 중 [ev_msg_014]

### 8. Uploaded Documents  
없음 [ev_doc_001]

### 9. Longitudinal Delta  
재진 — 이전 대비 기분과 입면은 일부 호전되었으나 아침 기상 곤란과 피로감은 지속됨 [ev_msg_002][ev_msg_004][ev_msg_016].

### 10. Missing Information  
- 수면 주기 및 수면 위생 습관 (예: 취침 시간, 스마트폰 사용 여부)  
- 우울 증상의 구체적 일상 영향 (예: 업무, 가사 수행 능력)  
- 세르트랄린 외 복용 중인 기타 약물 또는 보조제  
- 최근 스트레스 요인 변화 여부  
- 자살 또는 자해 생각 여부 (직접 언급 없음)

### 11. Evidence Table  
| ID | 유형 | 출처 | 내용 요약 |
|-----|------|------|-----------|
| ev_msg_001 | message | 환자 발화 | 세르트랄린 복용 후 기분 및 신체 상태 변화 문의 |
| ev_msg_002 | message | 환자 발화 | 세르트랄린 50mg 3개월 복용, 아침 기상 곤란과 의욕 부족 지속 |
| ev_msg_004 | message | 환자 발화 | 입면은 나아졌으나 새벽 5시 각성 후 재입면 어려움 |
| ev_msg_006 | message | 환자 발화 | 독서 및 학원 수업 가능, 아침 피로로 다소 힘듦 |
| ev_msg_008 | message | 환자 발화 | 식욕 정상, 체중 유지 |
| ev_msg_010 | message | 환자 발화 | 경미한 걱정은 있으나 공황 증상 없음 |
| ev_msg_012 | message | 환자 발화 | 자녀 독립 후 공허감 있었으나 현재 서서히 적응 중 |
| ev_msg_014 | message | 환자 발화 | 초기 오심 사라짐, 현재 부작용 없음, 약 꾸준히 복용 |
| ev_msg_016 | message | 환자 발화 | 아침 일찍 깨는 문제 제기, 생활 습관 조절 가능성 문의 |
| ev_msg_017 | message | 의료진 발화 | 생활 리듬 조정 제안, 약 복용 유지 권고 |
| ev_scale_001 | scale | PHQ-9 결과 | 총점 10점, 심각도 moderate |
| ev_scale_002 | scale | GAD-7 결과 | 총점 8점, 심각도 mild |
| ev_risk_001 | risk_event | 위험 이벤트 | 없음 (직접적 위험 신호 없음) |
| ev_doc_001 | document_block | 업로드 문서 | 없음 |