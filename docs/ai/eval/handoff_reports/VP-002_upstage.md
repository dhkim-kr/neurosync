---
patient_id: VP-002
vendor: upstage
model: solar-pro3
latency_ms: 7340
tokens: 2385
finish_reason: stop
generated_at: 2026-06-16T14:56:07+09:00
data_type: synthetic
quality_pass: True
sections_present: 11/11
evidence_citations: 13
diagnosis_violations: 0
risk_match: True
---

## Handoff Summary

### 1. One-line Summary
시험 및 발표 전후 불안 증상으로 인한 심계항진, 호흡 곤란, 수면 장애가 지속되고 있으며, 회피 행동으로 일상 기능 저하 및 고립감이 나타나고 있음 [ev_msg_002, ev_msg_004, ev_msg_006]

### 2. Chief Complaint (주호소)
- 시험 및 발표 전후로 심장이 빨리 뛰고 숨이 막히는 느낌이 반복되며, 이로 인해 잠을 잘 못 자고 있음 [ev_msg_002]

### 3. History of Present Illness (현병력)
- 한 달 전 중간시험 때부터 증상이 시작되었으며, 발표 전이나 지도교수님 미팅 전에도 동일한 증상이 나타남
- 증상 지속 시간은 10분에서 20분 정도이며, 심장이 막 뛰고 손이 떨리며 숨이 차는 신체적 증상이 동반됨
- 발표나 시험을 피하려고 하면서 증상이 점점 더 빈번해지고 있으며, 발표 생각만으로도 심장이 두근거리는 상태임
- 회피 행동으로 인해 연구실 출석이 줄어들고 지도교수님 미팅도 피하게 되었으며, 친구들과의 사회 활동도 감소하여 자취방에서 혼자 있는 시간이 많아짐 [ev_msg_002, ev_msg_004, ev_msg_006]

### 4. 주요 증상
| 영역 | 상태 | 근거 |
|---|---|---|
| 수면 | 수면 장애 (불안으로 인해 잠을 잘 못 잠) | [ev_msg_002] |
| 식욕 | 정보 미수집 | [ev_msg_002] |
| 기분 | 정보 미수집 | [ev_msg_002] |
| 불안 | 시험 및 발표 전후 불안 증상 (심계항진, 호흡 곤란, 손 떨림) | [ev_msg_002, ev_msg_004] |
| 집중력 | 정보 미수집 | [ev_msg_002] |
| 기능 손상 | 연구실 출석 감소, 지도교수님 미팅 회피, 사회 활동 감소, 고립감 증가 | [ev_msg_006] |

### 5. PHQ-9 / GAD-7
- PHQ-9 총점: 12점 (moderate) [ev_scale_001]
- GAD-7 총점: 14점 (moderate_severe) [ev_scale_002]

### 6. Risk & Safety Flags
- 현재 직접적 위험 신호 없음 [ev_risk_001]

### 7. Medication / Past History
- 정보 미수집 [ev_msg_001]

### 8. Uploaded Documents
- 없음 [ev_doc_001]

### 9. Longitudinal Delta
- 해당 없음 (초진) [ev_prior_handoff_001]

### 10. Missing Information
- 식욕 상태
- 기분 상태
- 집중력 상태
- 약물 복용 이력
- 과거 정신건강 진료 이력
- 이전 세션 기록 (약물 관련 발화 참조) [ev_msg_001]

### 11. Evidence Table
| ID | 유형 | 출처 | 내용 요약 |
|---|---|---|---|
| ev_msg_001 | message | 환자 발화 | "안녕하세요, 이준혁님. 최근에 시험이나 발표 전후로 심장이 빨리 뛰고 숨이 막히는 느낌이 반복된다고 하셨는데, 그게 얼마나 자주 있으신가요?" |
| ev_msg_002 | message | 환자 발화 | "한 달 전부터 중간시험 때부터 시작됐어요. 발표 전에도 그렇고, 지도교수님 미팅 때도 그렇고. 심장이 막 뛰는데 손도 떨리고 숨이 차서 10분에서 20분 정도 지속되죠. 그때마다 불안해서 잠을 잘 못 자요." |
| ev_msg_003 | message | 환자 발화 | "그럼 지금은 그 증상이 얼마나 자주 나타나고 있나요? 하루에 몇 번 정도인가요?" |
| ev_msg_004 | message | 환자 발화 | "주 2~3번 정도? 발표가 있거나 시험 전 날이면 더 자주. 근데 발표를 피하려고 하니까 점점 더 많아지고 있어요. 발표 생각만 해도 심장이 두근거려서." |
| ev_msg_005 | message | 환자 발화 | "발표나 시험을 피하게 되면 일상 생활에서 어떤 변화가 생기나요? 예를 들어 연구실 출석이나 사회 활동은 어떻게 달라졌나요?" |
| ev_msg_006 | message | 환자 발화 | "아 그게, 연구실 출석이 많이 줄었어요. 발표 안 나가니까 지도교수님 미팅도 피하고, 친구들이랑도 잘 안 만나죠. 자취방에서 혼자 있는 시간이 많아져서 점점 고립되는 느낌이에요." |
| ev_scale_001 | scale | PHQ-9 | 총점 12점 (moderate) |
| ev_scale_002 | scale | GAD-7 | 총점 14점 (moderate_severe) |
