# Handoff Report Quality Comparison — Upstage Solar Pro 3 vs EXAONE

> Generated: 2026-06-16
> Data type: Synthetic (합성 데이터 — 실제 환자 아님)
> System prompt: `docs/ai/prompts/handoff_generator/v1.system.md`
> Test script: `scripts/test_handoff_report.py`

## Performance Summary

| Metric | Upstage Solar Pro 3 | EXAONE (Friendli) |
|---|---|---|
| Latency | 9,019ms | 9,728ms |
| Total tokens | 2,804 | 2,785 |
| Finish reason | stop | stop |

## Section Completeness (11 mandatory sections)

| Section | Solar Pro 3 | EXAONE |
|---|---|---|
| 1. One-line Summary | Present, with evidence IDs | Present, with evidence IDs |
| 2. Chief Complaint | 4 items, all cited | 4 items, all cited |
| 3. History of Present Illness | Comprehensive paragraph, all evidence cited | Comprehensive paragraph, all evidence cited |
| 4. 주요 증상 (table) | 6 rows, all with evidence | 6 rows, all with evidence |
| 5. PHQ-9 / GAD-7 | Both scores + severity + item scores | Both scores + severity + item scores |
| 6. Risk & Safety | "현재 직접적 위험 신호 없음" | "현재 직접적 위험 신호 없음" + 신체증상 언급 |
| 7. Medication / Past History | Both cited [ev_msg_013] | Both cited [ev_msg_013] |
| 8. Uploaded Documents | "없음" | "없음" |
| 9. Longitudinal Delta | "해당 없음 (초진)" | "해당 없음 (초진)" |
| 10. Missing Information | 6 items | 5 items |
| 11. Evidence Table | 10 entries, well-structured | 13 entries, some errors |

Both models: **11/11 sections complete**

## Evidence Citation Quality

| Criterion | Solar Pro 3 | EXAONE |
|---|---|---|
| All claims have evidence IDs | Yes | Yes |
| Evidence IDs are consistent | Yes — `[ev_msg_001]` format | Yes — `[ev_msg_001]` format |
| Evidence table matches citations | All 10 match | Has typos (see below) |
| No fabricated evidence | Correct | Correct |
| No diagnosis statements | Correct | Correct |
| No treatment instructions | Correct | Correct |

## Issues Found

### EXAONE Issues
1. **Typo in evidence table**: Line 63 — `환자 발 viewpoint` instead of `환자 발화`
2. **Typo in evidence table**: Line 73 — `ev_risk_0ện` (garbled ID with Vietnamese character)
3. **Typo in symptoms table**: Line 29 — `[ev자_007]` instead of `[ev_msg_007]`
4. **Duplicate evidence ID**: `ev_scale_001` used for both PHQ-9 and GAD-7 (should be `ev_scale_001` and `ev_scale_002`)

### Solar Pro 3 Issues
1. **Phantom evidence IDs**: `[ev_doc_001]` and `[ev_prior_handoff_001]` are cited for "없음" sections — technically these aren't real evidence, just placeholders
2. **Risk event ID**: `[ev_risk_001]` cited for "없음" — same issue as above

## Verdict

| Criterion | Winner |
|---|---|
| **Section completeness** | Tie — both 11/11 |
| **Evidence citation accuracy** | Solar Pro 3 — no typos or garbled characters |
| **Clinical content quality** | Tie — both cover all symptoms with appropriate language |
| **Safety compliance** | Tie — neither diagnoses nor prescribes |
| **Missing information awareness** | Solar Pro 3 — includes "가족력" and "신체 건강" |
| **Table formatting** | Solar Pro 3 — cleaner evidence table |
| **Latency** | Solar Pro 3 (9.0s vs 9.7s) |

**Recommendation**: Solar Pro 3 as initial primary for HandoffGeneratorAgent, EXAONE as secondary. EXAONE's character-level hallucinations in evidence IDs need prompt engineering attention.

## Next Steps

1. Add Pydantic post-validation to verify all evidence IDs in report match the Evidence Table
2. Test with A.X K1 (prompt-only JSON — expect lower structured output quality)
3. Test with risk scenarios (high/critical safety flags)
4. Test with OCR document input
5. Expand eval dataset to 100 synthetic cases per PRD §10.3
