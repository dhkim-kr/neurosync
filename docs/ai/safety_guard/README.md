# Safety Guard Specification

> **Version**: 1.0
> **Created**: 2026-06-15
> **Source PRD**: `docs/ai/PRD_ai_v.0.0.0.0.md` section 6.2 (FR-005/011/022/032)
> **Status**: Implementation-Ready

---

## 1. Architecture

The Safety Guard uses a dual-classifier architecture: a rule-based keyword detector and an LLM classifier running in parallel. Both results are merged with a danger-takes-priority policy.

```
Patient message
  |
  v
┌──────────────────────────────────────────────┐
│  asyncio.gather (parallel)                   │
│                                              │
│  ┌─────────────────────────┐                 │
│  │ Rule/Keyword Detector   │  ~50ms          │
│  │ (Aho-Corasick)          │                 │
│  └──────────┬──────────────┘                 │
│             |                                │
│  ┌─────────────────────────┐                 │
│  │ LLM Safety Classifier   │  ~600ms         │
│  │ (Benchmark-selected)    │                 │
│  └──────────┬──────────────┘                 │
└─────────────┼────────────────────────────────┘
              |
              v
        Risk Merger (danger-takes-priority)
              |
              v
        ┌─────────────┐
        │  Risk Level  │
        └──────┬──────┘
               |
     ┌─────────┼──────────────┐
     v         v              v
  none/low   medium        high/critical
     |         |              |
  Continue   Safety          Interrupt
  dialogue   confirm         normal response
             question        119/109 crisis
             + risk event    + dashboard flag
             stored          + risk event stored
```

### Component Details

| Component | Technology | Latency | Purpose |
|---|---|---|---|
| Rule/Keyword Detector | Aho-Corasick multi-pattern matching | ~50ms | Catch explicit crisis keywords with zero false negatives on known patterns |
| LLM Safety Classifier | Benchmark-selected model (Solar Pro 3 / K-EXAONE / A.X K1) | ~600ms | Classify nuanced, indirect, or contextual risk expressions |
| Risk Merger | Deterministic logic | <1ms | Combine both results with danger-takes-priority policy |

### Why Dual Classification

A single LLM classifier may miss known crisis keywords due to prompt sensitivity or model variation. A single keyword list cannot catch indirect or contextual expressions. The dual approach ensures:

- Known crisis phrases are never missed (rule detector)
- Nuanced expressions are caught (LLM classifier)
- Total safety latency stays under 1,000ms (PRD metric target)

---

## 2. Risk Levels

Five risk levels with defined system actions (PRD section 6.2).

| Risk Level | Definition | System Action |
|---|---|---|
| `none` | No risk signals detected | Normal intake dialogue continues |
| `low` | Depression, anxiety, or stress expressions present, but no immediate danger | Dialogue continues. Optionally surface help resources. |
| `medium` | Ambiguous self-harm or harm-to-others expressions, hopelessness, safety check needed | Ask a safety-check question. Store `risk_event`. |
| `high` | Suicidal or self-harm intent with specific means, plan, or timeline implied | **Interrupt normal response**. Deliver 119/109 crisis resources. Flag clinician dashboard. Store `risk_event`. |
| `critical` | Imminent execution risk or current life/body danger | **Emergency mode**. Deliver 119 resources. Notify guardian/clinician per consent policy. Store `risk_event`. |

### Escalation Rules

- `high` and `critical` immediately block `DialogueAgent` invocation (SAF-3).
- `medium` does not block dialogue but prepends a safety-check question.
- `none` and `low` have no effect on dialogue flow.
- Once a session enters `high`/`critical`, subsequent messages in that session continue to receive safety-first handling until a clinician reviews and clears the flag.

---

## 3. Merge Policy: Danger-Takes-Priority

The merge function combines the rule detector result and the LLM classifier result.

### Core Rule

```
final_risk_level = max(rule_level, llm_level)
```

Risk levels are ordered: `none < low < medium < high < critical`.

### Special Case: SAF-2

If the rule detector returns a keyword hit (any level) but the LLM returns `none`, the final risk is kept at `medium` or above. The system never downgrades a keyword hit to `none`.

```python
def merge_risk(rule_level: RiskLevel, llm_level: RiskLevel, llm_confidence: float) -> MergedResult:
    merged = max(rule_level, llm_level)

    # SAF-2: rule hit + LLM none -> keep >= medium
    if rule_level > RiskLevel.NONE and llm_level == RiskLevel.NONE:
        merged = max(merged, RiskLevel.MEDIUM)

    # Conservative default on low confidence
    if llm_confidence < 0.5:
        merged = max(merged, RiskLevel.HIGH)

    # Flag disagreement for human review
    needs_review = (
        rule_level != llm_level
        or llm_confidence < 0.5
    )

    return MergedResult(
        risk_level=merged,
        requires_human_review=needs_review,
    )
```

### Merge Decision Table

| Rule Result | LLM Result | LLM Confidence | Final Level | Human Review |
|---|---|---|---|---|
| none | none | >= 0.5 | none | No |
| none | medium | >= 0.5 | medium | No |
| medium | none | >= 0.5 | medium (SAF-2) | Yes (disagreement) |
| high | none | >= 0.5 | high (SAF-2) | Yes (disagreement) |
| none | high | >= 0.5 | high | No |
| low | medium | >= 0.5 | medium | Yes (disagreement) |
| high | high | >= 0.5 | high | No |
| any | any | < 0.5 | max(merged, high) | Yes (low confidence) |

---

## 4. Korean Crisis Keyword List

The rule-based detector uses Aho-Corasick for multi-pattern matching across the following keyword categories. All keywords are Korean (ko-KR), the primary locale for Neuro-Sync.

### 4.1 Direct Suicidal/Self-Harm Expressions

| Keyword | Category |
|---|---|
| 자살 | suicidal_ideation |
| 죽고 싶 | suicidal_ideation |
| 자해 | self_harm |
| 목숨을 끊 | suicidal_ideation |
| 끝내고 싶 | suicidal_ideation |

### 4.2 Indirect Expressions (BUG-005 Additions)

These are indirect expressions of suicidal ideation that a keyword-only system previously missed. They were added after BUG-005 analysis revealed that patients frequently use euphemistic language.

| Keyword | Category | Notes |
|---|---|---|
| 살 이유가 없 | suicidal_ideation | "No reason to live" |
| 없어지고 싶 | suicidal_ideation | "Want to disappear" |
| 짐이 되고 싶지 않 | suicidal_ideation | "Don't want to be a burden" |
| 이렇게 살아야 하나 | suicidal_ideation | "Do I have to live like this" |
| 여기 있을 이유가 | suicidal_ideation | "No reason to be here" |
| 내가 없으면 | suicidal_ideation | "If I were gone" |
| 모든 게 끝났으면 | suicidal_ideation | "Wish it were all over" |
| 사라지고 싶 | suicidal_ideation | "Want to vanish" |
| 다 포기하고 싶 | suicidal_ideation | "Want to give up on everything" |
| 살고 싶지 않 | suicidal_ideation | "Don't want to live" |

### 4.3 Harm-to-Others Expressions

| Keyword | Category |
|---|---|
| 죽이고 싶 | harm_to_others |
| 해치고 싶 | harm_to_others |
| 때리고 싶 | harm_to_others |

### 4.4 Active Crisis / Preparation Indicators

These indicate the patient may have already taken steps toward self-harm. These are always classified as `high` or `critical`.

| Keyword | Category | Min Risk Level |
|---|---|---|
| 방법을 알아봤 | crisis_preparation | high |
| 준비를 하고 있 | crisis_preparation | high |
| 유서를 썼 | crisis_preparation | critical |
| 약을 모아 | crisis_preparation | critical |

### Keyword Matching Rules

- Matching is substring-based via Aho-Corasick (not exact word boundary).
- Negation handling: simple negation prefixes (e.g., "자살 생각은 없어요") are handled by the LLM classifier, not the rule detector. The rule detector intentionally fires on any match. The merge policy ensures the LLM can de-escalate from `medium` but never from `none` (SAF-2).
- New keywords are added through the prompt registry version control process with red-team regression testing.

---

## 5. Crisis Response Templates

Response templates are locale-specific (Korean) and matched to risk level. The template ID is returned in the safety output (`user_safe_message_template_id`).

### Risk Level: medium

**Template ID**: `kr_safety_check_v1`

```
지금 말씀하신 부분이 걱정이 됩니다.
혹시 스스로를 해치고 싶은 생각이 드시나요?
솔직하게 말씀해 주셔도 괜찮습니다. 도움을 드리기 위해 여쭤보는 것입니다.
```

Purpose: Ask a direct safety-check question. Do not continue normal intake dialogue until the patient responds.

### Risk Level: high

**Template ID**: `kr_crisis_109_v1`

```
지금 많이 힘드시다는 것을 알겠습니다.
지금 바로 도움을 받으실 수 있습니다.

정신건강 위기상담 전화: 109 (24시간)
자살예방 상담전화: 1393 (24시간)
응급 상황: 119

전문 상담사가 24시간 대기하고 있습니다.
지금 전화하시는 것을 권합니다.
```

Purpose: Interrupt normal dialogue. Provide crisis resources. Do not ask further intake questions.

### Risk Level: critical

**Template ID**: `kr_crisis_emergency_v1`

```
지금 매우 위험한 상황일 수 있습니다.
즉시 도움을 요청해 주세요.

응급 전화: 119
정신건강 위기상담: 109 (24시간)
자살예방 상담전화: 1393 (24시간)

지금 안전한 곳에 계신가요?
주변에 도움을 줄 수 있는 분이 계시면 함께 계셔 주세요.
```

Purpose: Emergency mode. Provide immediate emergency resources. If consent policy permits, trigger guardian/clinician notification.

### Template Rules

- Templates never ask for details about methods, means, or plans (PRD section 11.1).
- Templates always include at least one 24-hour crisis hotline number.
- Templates are stored in the prompt registry (`docs/ai/prompts/safety_classifier/crisis_templates.ko.md`) and version-controlled.
- Template selection is deterministic based on `risk_level`. No LLM generation is involved in crisis responses.

---

## 6. Confidence Handling

### Low Confidence Default

If the LLM classifier returns `confidence < 0.5`, the system defaults to `high` risk (conservative). This ensures that uncertain classifications are never treated as safe.

```
if llm_confidence < 0.5:
    final_risk = max(final_risk, RiskLevel.HIGH)
    requires_human_review = True
```

### Confidence Thresholds

| Confidence Range | Interpretation | Action |
|---|---|---|
| >= 0.8 | High confidence | Use LLM result directly in merge |
| 0.5 - 0.8 | Moderate confidence | Use LLM result in merge; flag for review if rule disagrees |
| < 0.5 | Low confidence | Override to `high` risk; flag for human review |

### Model Selection for Safety

The safety LLM is selected from Solar Pro 3 / K-EXAONE / A.X K1 with `recall_high_critical` as the primary metric (SAF-5). The release gate requires recall >= 95% (PRD section 10.1). Precision is a secondary metric (target >= 80%).

---

## 7. Human Review Flag

The `requires_human_review` flag is set to `true` in the following conditions:

| Condition | Rationale |
|---|---|
| Rule detector and LLM classifier disagree on risk level | Conflicting signals need human judgment |
| LLM confidence < 0.5 | Model is uncertain; human should verify |
| Risk level is `high` or `critical` | All high-risk events should be reviewed by a clinician |
| `medium` risk with ambiguous context | Safety-check question was asked; clinician should monitor |

### Human Review Workflow

1. Safety result includes `requires_human_review: true`.
2. `risk_event` is stored in the database with full evidence.
3. Clinician dashboard displays the flag with the patient's message, risk level, and evidence.
4. Clinician can confirm, escalate, or de-escalate the risk level.
5. De-escalation by a clinician is the only way to clear a `high`/`critical` flag.

---

## 8. Output Schema

The `SafetyClassifierAgent` returns the following JSON structure (PRD section 6.2):

```json
{
  "risk_level": "high",
  "risk_categories": ["suicidal_ideation"],
  "evidence": ["죽고 싶다는 생각"],
  "confidence": 0.91,
  "recommended_action": "interrupt_and_route_to_crisis_help",
  "user_safe_message_template_id": "kr_crisis_109_v1",
  "requires_human_review": true,
  "model_used": "agent_registry_selected_model",
  "rule_detector_result": {
    "matched_keywords": ["죽고 싶"],
    "rule_risk_level": "high"
  },
  "llm_classifier_result": {
    "llm_risk_level": "high",
    "llm_confidence": 0.91
  },
  "merge_policy_applied": "danger_takes_priority"
}
```

### Field Descriptions

| Field | Type | Description |
|---|---|---|
| `risk_level` | enum | Final merged risk level: none/low/medium/high/critical |
| `risk_categories` | list[str] | Categories detected: suicidal_ideation, self_harm, harm_to_others, crisis_preparation, acute_psychosis, medical_emergency |
| `evidence` | list[str] | Excerpts from the patient message that triggered the classification |
| `confidence` | float | LLM classifier confidence (0.0-1.0) |
| `recommended_action` | str | Action for the orchestrator: continue, ask_safety_question, interrupt_and_route_to_crisis_help, emergency_mode |
| `user_safe_message_template_id` | str | Template ID for the patient-facing crisis response |
| `requires_human_review` | bool | Whether a clinician should review this event |
| `model_used` | str | Model selected by ModelRouter for the LLM classifier |
| `rule_detector_result` | object | Raw output from the keyword detector |
| `llm_classifier_result` | object | Raw output from the LLM classifier |
| `merge_policy_applied` | str | Which merge policy was used |

---

## 9. Acceptance Criteria (from PRD)

| Given | When | Then |
|---|---|---|
| Patient inputs direct suicidal expression | Safety executes | Classified as high/critical. Normal response generation is blocked. |
| Keyword detector hits, LLM returns none | Risk merge | Final risk kept at medium or above. Safety check or interrupt issued. |
| LLM candidates evaluated for safety | Model selection | Model with highest high/critical recall is registered as Primary. |
| Safety prompt changed | Before deployment | Red-team regression test must pass or release is blocked. |
| Patient uses indirect expression from BUG-005 list | Safety executes | Keyword detector matches. LLM provides contextual classification. Merge produces appropriate risk level. |
| LLM confidence is 0.3 | Risk merge | Final risk defaults to high. Human review flag is set. |

---

## 10. Performance Targets

| Metric | Target | Source |
|---|---|---|
| Safety latency p95 | < 1,000ms | PRD section 14 |
| high/critical recall | >= 95% | PRD section 14, SAF-5 |
| high/critical precision | >= 80% | PRD section 14 |
| Rule detector latency | ~50ms | Aho-Corasick benchmark |
| LLM classifier latency | ~600ms | Benchmark target |
| Worst-case safety recall (prompt robustness) | >= 95% | PRD section 10.1 |
