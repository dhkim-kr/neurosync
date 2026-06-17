# PromptEvalAgent

> **Role**: Evaluate prompt and model regressions offline before deployment
> **Model Policy**: Offline (Solar Pro 3 / K-EXAONE / A.K)
> **System Prompt**: `docs/ai/prompts/prompt_eval/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/prompt_eval.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| eval_dataset | object | Yes | Evaluation dataset containing test cases with inputs, expected outputs, and evaluation criteria |

## Output

| Field | Type | Description |
|---|---|---|
| metrics | object | Aggregated evaluation metrics (e.g., accuracy, recall, precision, F1, safety scores, unsupported claim rate) |
| fail_cases | list[object] | Individual test cases that failed, each with `case_id`, `input`, `expected`, `actual`, `failure_reason` |
| release_decision | string | One of: `pass`, `block`, `review_required` |

## Behavior

1. Receive an evaluation dataset containing test cases for one or more agents.
2. For each test case, run the target agent's prompt + model combination against the input.
3. Compare the actual output against expected outputs using the defined evaluation criteria.
4. Compute aggregated metrics per agent function:
   - Safety agents: high/critical recall, false positive rate.
   - Dialogue agents: safety score, naturalness, slot completion.
   - Slot extraction: slot F1, evidence alignment.
   - Handoff: unsupported claim rate, clinician score.
   - Evidence verification: false-negative unsupported claim rate.
5. Identify all failing test cases with detailed failure reasons.
6. Determine the release decision:
   - `pass`: All metrics meet or exceed thresholds.
   - `block`: Any safety-critical metric falls below threshold (e.g., safety recall < 0.95).
   - `review_required`: Non-critical metrics are marginal.

## Safety Constraints

- Must block release if safety-critical metrics fall below defined thresholds.
- Must evaluate worst-case safety scenarios (red-team test cases) for every prompt change.
- Must never skip safety regression tests, even for non-safety agents.
- Evaluation must cover all three model candidates (Solar Pro 3, K-EXAONE, A.K) when performing model comparison.
- Must not use production patient data for evaluation; only approved synthetic/anonymized datasets.

## Failure Fallback

When the evaluation harness fails (infrastructure error, dataset loading failure):
- **Block the release** until the evaluation can be completed successfully.
- Log the failure and alert the AI Research team.
- No partial evaluation results are used for release decisions.

## Model Selection

This agent runs **offline** and is not subject to real-time ModelRouter selection. All three candidate models (Solar Pro 3, K-EXAONE, A.K) are evaluated in parallel during comparison runs. The evaluation results are written to `agent_model_registry` and `eval_runs` to inform ModelRouter selections for production agents.

## Dependencies

- **Eval Harness**: Infrastructure for running offline evaluations (`apps/ai-server/src/eval/`).
- **Eval Datasets**: Test datasets stored in `apps/ai-server/src/eval/datasets/`.
- **agent_model_registry**: Evaluation results are written here to update model selections.
- **All other agents**: PromptEvalAgent evaluates prompts and models for every agent in the pipeline.
