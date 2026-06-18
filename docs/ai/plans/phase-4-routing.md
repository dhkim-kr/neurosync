# Phase 4: Routing

> **Depends on**: Phase 1 (config, base classes, `ModelSelection` schema), Phase 3 (LLM adapters registered)
> **Blocks**: Phase 5 (all agents call `ModelRouter.select_model()`), Phase 7 (routes inject router)
> **Agent owner**: `developer`
> **Gate**: `qa` — registry loads, fallback chain fires correctly, JSON-mode warning emitted for ak-llm

---

## Objective

Implement the model routing layer that sits between agents and adapters. Every agent asks `ModelRouter` for an adapter — never hardcodes a model name. The router reads a YAML registry (because AI server cannot access DB), supports exponential-backoff fallback, and flags JSON-schema incompatibility for A.X K1.

## Success Criteria

- [ ] `from src.routing import ModelRouter, FallbackPolicy` imports cleanly
- [ ] `agent_model_registry.yaml` contains all 12 agents from PRD §3.3
- [ ] `ModelRouter.select_model("dialogue_agent")` returns a `ModelSelection` with `adapter_name`
- [ ] `ModelRouter.get_fallback("dialogue_agent")` returns secondary, then fallback, then raises `NoFallbackError`
- [ ] `ModelRouter.select_model("stt_agent")` returns fixed `skt-ak-stt` with no fallback chain
- [ ] `ModelRouter.select_model("ocr_agent")` returns fixed `solar-document-parse` with no fallback chain
- [ ] `FallbackPolicy.should_fallback(error)` returns `True` for: `timeout`, `429`, `5xx`, `invalid_json`, `safety_uncertain`, `evidence_verification_failed`
- [ ] `FallbackPolicy.next_delay(attempt)` returns 1s, 2s, 4s exponential backoff
- [ ] When `require_json=True` and selected model is `ak-llm`, `ModelRouter` emits a `json_unsupported` warning in the `ModelSelection` result
- [ ] `pytest tests/routing/ -x` passes
- [ ] `ruff check src/routing/ tests/routing/` passes

---

## Step 4.1 — Create `apps/ai-server/src/routing/__init__.py`

**File**: `apps/ai-server/src/routing/__init__.py` (new)

```python
"""Model routing layer — YAML registry, fallback policy, adapter dispatch.

The AI server cannot access the database directly (PRD §4.2).
Model selection is driven by a YAML config file that is updated
offline after benchmark runs.
"""

from src.routing.fallback_policy import FallbackPolicy
from src.routing.model_router import ModelRouter

__all__ = ["ModelRouter", "FallbackPolicy"]
```

---

## Step 4.2 — Create `apps/ai-server/src/routing/agent_model_registry.yaml`

**File**: `apps/ai-server/src/routing/agent_model_registry.yaml` (new)
**PRD reference**: §3.3, §3.4, §3.5

This is the single source of truth for model selection at runtime. The `PromptEvalAgent` / offline eval harness updates this file after benchmark runs. Fields mirror the DB schema in PRD §3.5 minus DB-only columns (`selected_at`, `selected_by`, `is_active`).

```yaml
# agent_model_registry.yaml
# ---------------------------------------------------------------
# SSOT for runtime model routing.  Updated by offline eval harness.
# AI server reads this on startup; hot-reload on SIGHUP.
#
# policy values:
#   fixed        — single vendor, no fallback chain
#   benchmarked  — primary/secondary/fallback from eval results
#   offline      — eval-only agent, not called at runtime
# ---------------------------------------------------------------

version: "1.0"

agents:

  # ── Fixed agents ──────────────────────────────────────────────

  stt_agent:
    task_name: speech_to_text
    policy: fixed
    primary: skt-ak-stt
    secondary: null
    fallback: null
    notes: "SKT A.X STT — fixed per PRD §3.1. Streaming + batch."

  ocr_agent:
    task_name: document_parse
    policy: fixed
    primary: solar-document-parse
    secondary: null
    fallback: null
    notes: "Solar Document Parse — fixed per PRD §3.1."

  # ── Benchmarked agents ────────────────────────────────────────

  input_normalizer_agent:
    task_name: stt_noise_correction
    policy: benchmarked
    primary: solar-pro-3
    secondary: k-exaone
    fallback: ak-llm
    notes: "STT transcript cleanup. Selection: latency + accuracy."

  safety_classifier_agent:
    task_name: safety_classification
    policy: benchmarked
    primary: k-exaone
    secondary: solar-pro-3
    fallback: ak-llm
    notes: "Rule ensemble + LLM. Selection: high/critical recall >= 0.95."

  dialogue_agent:
    task_name: dialogue_intake
    policy: benchmarked
    primary: solar-pro-3
    secondary: ak-llm
    fallback: k-exaone
    notes: "Korean naturalness + safety + slot completion."

  clinical_slot_agent:
    task_name: clinical_slot_extraction
    policy: benchmarked
    primary: solar-pro-3
    secondary: k-exaone
    fallback: ak-llm
    notes: "Slot F1 + evidence alignment."

  orchestrator_agent:
    task_name: workflow_routing
    policy: benchmarked
    primary: k-exaone
    secondary: solar-pro-3
    fallback: ak-llm
    notes: "JSON reliability + routing accuracy + tool-use accuracy."

  temporal_retriever_agent:
    task_name: temporal_retrieval_summary
    policy: benchmarked
    primary: solar-pro-3
    secondary: k-exaone
    fallback: ak-llm
    notes: "Internal RAG + LLM summary. Selection: retrieval relevance."

  temporal_summary_agent:
    task_name: temporal_delta_summary
    policy: benchmarked
    primary: solar-pro-3
    secondary: k-exaone
    fallback: ak-llm
    notes: "Delta factuality + temporal consistency."

  handoff_generator_agent:
    task_name: handoff_generation
    policy: benchmarked
    primary: solar-pro-3
    secondary: k-exaone
    fallback: ak-llm
    notes: "Unsupported claim count + clinician score."

  evidence_verifier_agent:
    task_name: evidence_verification
    policy: benchmarked
    primary: k-exaone
    secondary: solar-pro-3
    fallback: ak-llm
    notes: "False-negative unsupported claim rate."

  # ── Offline-only agent ────────────────────────────────────────

  prompt_eval_agent:
    task_name: prompt_model_regression
    policy: offline
    primary: solar-pro-3
    secondary: k-exaone
    fallback: ak-llm
    notes: "Eval harness only. Not called at runtime via ModelRouter."
```

**Design notes**:
- `primary`/`secondary`/`fallback` values are adapter names that must match keys registered in `ModelRouter.register_adapters()`
- `null` means no fallback — only used for `fixed` policy agents
- Initial primary assignments are provisional placeholders. The offline eval harness will update them after the first benchmark run
- The `temporal_retriever_agent` is included because its summary sub-step uses an LLM, even though retrieval itself is internal pgvector

---

## Step 4.3 — Create `apps/ai-server/src/routing/model_router.py`

**File**: `apps/ai-server/src/routing/model_router.py` (new)

```python
"""ModelRouter — agent-to-adapter dispatch via YAML registry.

Responsibilities:
1. Load agent_model_registry.yaml on init (and on SIGHUP for hot-reload)
2. select_model(agent_name) → ModelSelection
3. get_fallback(agent_name, current_adapter) → ModelSelection or raise
4. Track registered adapters and return the concrete adapter instance
5. Flag JSON-schema incompatibility when require_json=True and model is ak-llm
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from src.schemas.common import ModelSelection

logger = logging.getLogger(__name__)

# A.X K1 does not support native JSON schema (response_format).
# When an agent requires JSON output and the selected model is ak-llm,
# ModelRouter must set a warning so the caller can add prompt-level
# JSON instructions instead.
_JSON_UNSUPPORTED_ADAPTERS = frozenset({"ak-llm"})


class NoFallbackError(Exception):
    """Raised when the fallback chain is exhausted for an agent."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        super().__init__(f"No remaining fallback for agent '{agent_name}'")


class RegistryEntry:
    """Parsed entry from agent_model_registry.yaml."""

    def __init__(
        self,
        agent_name: str,
        task_name: str,
        policy: str,
        primary: str | None,
        secondary: str | None,
        fallback: str | None,
        notes: str = "",
    ) -> None:
        self.agent_name = agent_name
        self.task_name = task_name
        self.policy = policy  # "fixed" | "benchmarked" | "offline"
        self.chain: list[str] = [
            m for m in (primary, secondary, fallback) if m is not None
        ]
        self.notes = notes

    def next_after(self, current: str) -> str | None:
        """Return the next adapter in the fallback chain after `current`.

        Returns None if `current` is the last entry or not found.
        """
        try:
            idx = self.chain.index(current)
            if idx + 1 < len(self.chain):
                return self.chain[idx + 1]
        except ValueError:
            pass
        return None


class ModelRouter:
    """Central model routing dispatcher.

    Usage:
        router = ModelRouter(registry_path="src/routing/agent_model_registry.yaml")
        router.register_adapters({"solar-pro-3": solar_adapter, ...})
        selection = router.select_model("dialogue_agent")
        adapter = router.get_adapter(selection.adapter_name)
    """

    def __init__(self, registry_path: str | Path) -> None:
        self._registry_path = Path(registry_path)
        self._entries: dict[str, RegistryEntry] = {}
        self._adapters: dict[str, Any] = {}
        self._load_registry()

    # ── Public API ──────────────────────────────────────────────

    def select_model(
        self,
        agent_name: str,
        *,
        require_json: bool = False,
    ) -> ModelSelection:
        """Select the primary model for the given agent.

        Args:
            agent_name: Key from agent_model_registry.yaml (e.g. "dialogue_agent").
            require_json: If True and the selected model lacks native JSON schema
                          support, `json_unsupported_warning` is set on the result.

        Returns:
            ModelSelection with adapter_name populated.

        Raises:
            KeyError: If agent_name is not in the registry.
        """
        entry = self._get_entry(agent_name)
        adapter_name = entry.chain[0]
        warning = self._check_json_support(adapter_name, require_json)

        return ModelSelection(
            adapter_name=adapter_name,
            is_fallback=False,
            fallback_reason=None,
            json_unsupported_warning=warning,
        )

    def get_fallback(
        self,
        agent_name: str,
        current_adapter: str,
        *,
        reason: str = "",
        require_json: bool = False,
    ) -> ModelSelection:
        """Get the next fallback adapter after `current_adapter`.

        Args:
            agent_name: Agent requesting fallback.
            current_adapter: The adapter that just failed.
            reason: Why fallback was triggered (for logging/tracing).
            require_json: Propagate JSON-support check to the fallback.

        Returns:
            ModelSelection for the next adapter in the chain.

        Raises:
            NoFallbackError: If the chain is exhausted.
        """
        entry = self._get_entry(agent_name)
        next_adapter = entry.next_after(current_adapter)

        if next_adapter is None:
            raise NoFallbackError(agent_name)

        warning = self._check_json_support(next_adapter, require_json)
        fallback_reason = reason or f"fallback from {current_adapter}"

        logger.warning(
            "Fallback triggered for agent=%s: %s -> %s (reason: %s)",
            agent_name,
            current_adapter,
            next_adapter,
            fallback_reason,
        )

        return ModelSelection(
            adapter_name=next_adapter,
            is_fallback=True,
            fallback_reason=fallback_reason,
            json_unsupported_warning=warning,
        )

    def register_adapters(self, adapters: dict[str, Any]) -> None:
        """Register adapter instances by name.

        Args:
            adapters: Mapping of adapter name -> adapter instance.
                      Names must match values used in the YAML registry
                      (e.g. "solar-pro-3", "k-exaone", "ak-llm",
                       "skt-ak-stt", "solar-document-parse").
        """
        self._adapters.update(adapters)
        logger.info("Registered adapters: %s", list(adapters.keys()))

    def get_adapter(self, adapter_name: str) -> Any:
        """Retrieve a registered adapter instance by name.

        Args:
            adapter_name: Must match a key passed to register_adapters().

        Returns:
            The adapter instance (LLMAdapter, VendorAdapter, etc.).

        Raises:
            KeyError: If the adapter is not registered.
        """
        if adapter_name not in self._adapters:
            raise KeyError(
                f"Adapter '{adapter_name}' not registered. "
                f"Available: {list(self._adapters.keys())}"
            )
        return self._adapters[adapter_name]

    def list_agents(self) -> list[str]:
        """Return all agent names in the registry."""
        return list(self._entries.keys())

    def get_entry(self, agent_name: str) -> RegistryEntry:
        """Public access to a registry entry (for introspection/eval)."""
        return self._get_entry(agent_name)

    def reload(self) -> None:
        """Hot-reload the YAML registry (call on SIGHUP)."""
        self._load_registry()
        logger.info("Registry reloaded from %s", self._registry_path)

    # ── Private helpers ─────────────────────────────────────────

    def _load_registry(self) -> None:
        """Parse agent_model_registry.yaml into RegistryEntry objects."""
        with open(self._registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        agents_data: dict[str, dict] = data.get("agents", {})
        entries: dict[str, RegistryEntry] = {}

        for agent_name, spec in agents_data.items():
            entries[agent_name] = RegistryEntry(
                agent_name=agent_name,
                task_name=spec.get("task_name", ""),
                policy=spec.get("policy", "benchmarked"),
                primary=spec.get("primary"),
                secondary=spec.get("secondary"),
                fallback=spec.get("fallback"),
                notes=spec.get("notes", ""),
            )

        self._entries = entries
        logger.info(
            "Loaded %d agent entries from registry (version=%s)",
            len(entries),
            data.get("version", "unknown"),
        )

    def _get_entry(self, agent_name: str) -> RegistryEntry:
        """Retrieve entry or raise KeyError with helpful message."""
        if agent_name not in self._entries:
            raise KeyError(
                f"Agent '{agent_name}' not in registry. "
                f"Available: {self.list_agents()}"
            )
        return self._entries[agent_name]

    @staticmethod
    def _check_json_support(adapter_name: str, require_json: bool) -> str | None:
        """Return a warning string if adapter lacks native JSON schema support."""
        if require_json and adapter_name in _JSON_UNSUPPORTED_ADAPTERS:
            return (
                f"Adapter '{adapter_name}' does not support native JSON schema "
                f"(response_format). Use prompt-level JSON instructions instead."
            )
        return None
```

**Implementation notes**:
- `RegistryEntry.chain` flattens primary/secondary/fallback into an ordered list, filtering out `null`. This makes `next_after()` trivial
- `_JSON_UNSUPPORTED_ADAPTERS` is a frozenset checked at selection time. When `require_json=True` and the selected model is `ak-llm`, the `ModelSelection.json_unsupported_warning` field is populated. Callers (agents) use this to switch from `response_format` to prompt-level JSON instructions
- `reload()` enables hot-reload via SIGHUP without restarting the server
- All adapter types are `Any` — concrete type checking happens at the adapter layer. This avoids circular imports between routing and adapters

---

## Step 4.3a — Update `apps/ai-server/src/schemas/common.py`

**File**: `apps/ai-server/src/schemas/common.py` (modify)
**Action**: Add `json_unsupported_warning` field to `ModelSelection`.

```python
class ModelSelection(BaseModel):
    """Result of ModelRouter.select_model() (PRD §8.2)."""

    adapter_name: str
    is_fallback: bool = False
    fallback_reason: str | None = None
    json_unsupported_warning: str | None = None
```

**Why**: The router needs a structured way to communicate the A.X K1 JSON-schema limitation back to the calling agent without raising an exception (it is a warning, not an error).

---

## Step 4.4 — Create `apps/ai-server/src/routing/fallback_policy.py`

**File**: `apps/ai-server/src/routing/fallback_policy.py` (new)

```python
"""FallbackPolicy — decides when to trigger model fallback and backoff timing.

Trigger conditions (PRD §3.4 fallback_policy):
  - timeout           : request exceeded adapter timeout_sec
  - 429               : rate-limited by vendor
  - 5xx               : vendor server error (500, 502, 503, 504)
  - invalid_json      : LLM returned unparseable JSON when JSON was required
  - safety_uncertain  : safety classifier confidence below threshold
  - evidence_verification_failed : verifier flagged unsupported claims above threshold

Backoff (per SKT API doc):
  1s → 2s → 4s exponential, base=1, factor=2
"""

from __future__ import annotations

import logging
from enum import StrEnum

logger = logging.getLogger(__name__)


class FallbackTrigger(StrEnum):
    """Enumeration of conditions that trigger a model fallback."""

    TIMEOUT = "timeout"
    RATE_LIMITED = "429"
    SERVER_ERROR = "5xx"
    INVALID_JSON = "invalid_json"
    SAFETY_UNCERTAIN = "safety_uncertain"
    EVIDENCE_VERIFICATION_FAILED = "evidence_verification_failed"


# All triggers that should cause an automatic fallback attempt.
_FALLBACK_TRIGGERS = frozenset(FallbackTrigger)

# Default backoff configuration.
_BACKOFF_BASE_SEC: float = 1.0
_BACKOFF_FACTOR: float = 2.0
_MAX_ATTEMPTS: int = 3  # primary + secondary + fallback


class FallbackPolicy:
    """Stateless policy object for fallback decisions and backoff timing.

    Usage:
        policy = FallbackPolicy()

        if policy.should_fallback(error_type="timeout", attempt=0):
            delay = policy.next_delay(attempt=0)
            await asyncio.sleep(delay)
            selection = router.get_fallback(agent_name, current_adapter, reason="timeout")
    """

    def __init__(
        self,
        *,
        max_attempts: int = _MAX_ATTEMPTS,
        backoff_base_sec: float = _BACKOFF_BASE_SEC,
        backoff_factor: float = _BACKOFF_FACTOR,
    ) -> None:
        self.max_attempts = max_attempts
        self.backoff_base_sec = backoff_base_sec
        self.backoff_factor = backoff_factor

    def should_fallback(
        self,
        error_type: str,
        attempt: int,
    ) -> bool:
        """Decide whether to attempt a fallback.

        Args:
            error_type: One of the FallbackTrigger values, or an HTTP status code string.
            attempt: Zero-based attempt index (0 = primary just failed).

        Returns:
            True if a fallback should be attempted.
        """
        if attempt + 1 >= self.max_attempts:
            logger.warning(
                "Max attempts (%d) reached — no more fallbacks for error_type=%s",
                self.max_attempts,
                error_type,
            )
            return False

        normalized = self._normalize_error_type(error_type)
        is_trigger = normalized in _FALLBACK_TRIGGERS

        if not is_trigger:
            logger.debug(
                "Error type '%s' (normalized: '%s') is not a fallback trigger",
                error_type,
                normalized,
            )

        return is_trigger

    def next_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay in seconds.

        Backoff schedule (default): 1s, 2s, 4s
        Formula: base * (factor ** attempt)

        Args:
            attempt: Zero-based attempt index.

        Returns:
            Delay in seconds before the next retry.
        """
        delay = self.backoff_base_sec * (self.backoff_factor ** attempt)
        return delay

    def classify_http_status(self, status_code: int) -> str | None:
        """Map an HTTP status code to a FallbackTrigger value.

        Args:
            status_code: HTTP response status code.

        Returns:
            FallbackTrigger value string, or None if not a fallback condition.
        """
        if status_code == 429:
            return FallbackTrigger.RATE_LIMITED
        if 500 <= status_code < 600:
            return FallbackTrigger.SERVER_ERROR
        return None

    def classify_exception(self, exc: BaseException) -> str | None:
        """Map a Python exception to a FallbackTrigger value.

        Handles common exception types from httpx and asyncio.

        Args:
            exc: The caught exception.

        Returns:
            FallbackTrigger value string, or None if not a fallback condition.
        """
        exc_type = type(exc).__name__

        # Timeout exceptions from httpx, asyncio, openai
        if "Timeout" in exc_type or "TimeoutError" in exc_type:
            return FallbackTrigger.TIMEOUT

        # Connection / server errors
        if "ConnectError" in exc_type or "RemoteProtocolError" in exc_type:
            return FallbackTrigger.SERVER_ERROR

        return None

    @staticmethod
    def _normalize_error_type(error_type: str) -> str:
        """Normalize error_type strings for comparison.

        Maps HTTP-like codes to their FallbackTrigger equivalents:
          "429" → "429"
          "500", "502", "503", "504" → "5xx"
          "timeout", "invalid_json" etc. → pass-through
        """
        # Direct match against known triggers
        if error_type in _FALLBACK_TRIGGERS:
            return error_type

        # Numeric HTTP status codes
        try:
            code = int(error_type)
            if code == 429:
                return FallbackTrigger.RATE_LIMITED
            if 500 <= code < 600:
                return FallbackTrigger.SERVER_ERROR
        except ValueError:
            pass

        return error_type
```

**Implementation notes**:
- `FallbackPolicy` is stateless so it can be shared across concurrent requests
- `classify_http_status()` and `classify_exception()` are convenience helpers for adapters to translate vendor-level errors into `FallbackTrigger` values
- The backoff formula `1 * 2^attempt` produces 1s, 2s, 4s for attempts 0, 1, 2 — matching the SKT API doc recommendation
- `_normalize_error_type()` handles both string triggers and raw HTTP status codes passed as strings

---

## Step 4.5 — Create `apps/ai-server/tests/routing/__init__.py`

**File**: `apps/ai-server/tests/routing/__init__.py` (new)

```python
"""Tests for the routing module."""
```

---

## Step 4.6 — Create `apps/ai-server/tests/routing/test_model_router.py`

**File**: `apps/ai-server/tests/routing/test_model_router.py` (new)

```python
"""Tests for ModelRouter and FallbackPolicy."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from src.routing.fallback_policy import FallbackPolicy, FallbackTrigger
from src.routing.model_router import ModelRouter, NoFallbackError


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture()
def registry_path(tmp_path: Path) -> Path:
    """Write a minimal test registry and return its path."""
    data = {
        "version": "test",
        "agents": {
            "dialogue_agent": {
                "task_name": "dialogue_intake",
                "policy": "benchmarked",
                "primary": "solar-pro-3",
                "secondary": "k-exaone",
                "fallback": "ak-llm",
            },
            "stt_agent": {
                "task_name": "speech_to_text",
                "policy": "fixed",
                "primary": "skt-ak-stt",
                "secondary": None,
                "fallback": None,
            },
            "ocr_agent": {
                "task_name": "document_parse",
                "policy": "fixed",
                "primary": "solar-document-parse",
                "secondary": None,
                "fallback": None,
            },
        },
    }
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


@pytest.fixture()
def router(registry_path: Path) -> ModelRouter:
    return ModelRouter(registry_path=registry_path)


@pytest.fixture()
def policy() -> FallbackPolicy:
    return FallbackPolicy()


# ── ModelRouter tests ───────────────────────────────────────────


class TestModelRouter:
    """Tests for ModelRouter.select_model / get_fallback / adapters."""

    def test_select_model_returns_primary(self, router: ModelRouter) -> None:
        selection = router.select_model("dialogue_agent")
        assert selection.adapter_name == "solar-pro-3"
        assert selection.is_fallback is False
        assert selection.fallback_reason is None

    def test_select_model_fixed_stt(self, router: ModelRouter) -> None:
        selection = router.select_model("stt_agent")
        assert selection.adapter_name == "skt-ak-stt"
        assert selection.is_fallback is False

    def test_select_model_fixed_ocr(self, router: ModelRouter) -> None:
        selection = router.select_model("ocr_agent")
        assert selection.adapter_name == "solar-document-parse"

    def test_select_model_unknown_agent_raises(self, router: ModelRouter) -> None:
        with pytest.raises(KeyError, match="not_an_agent"):
            router.select_model("not_an_agent")

    def test_get_fallback_returns_secondary(self, router: ModelRouter) -> None:
        selection = router.get_fallback(
            "dialogue_agent", "solar-pro-3", reason="timeout"
        )
        assert selection.adapter_name == "k-exaone"
        assert selection.is_fallback is True
        assert "timeout" in (selection.fallback_reason or "")

    def test_get_fallback_returns_third(self, router: ModelRouter) -> None:
        selection = router.get_fallback(
            "dialogue_agent", "k-exaone", reason="5xx"
        )
        assert selection.adapter_name == "ak-llm"
        assert selection.is_fallback is True

    def test_get_fallback_exhausted_raises(self, router: ModelRouter) -> None:
        with pytest.raises(NoFallbackError):
            router.get_fallback("dialogue_agent", "ak-llm", reason="timeout")

    def test_get_fallback_fixed_agent_raises(self, router: ModelRouter) -> None:
        with pytest.raises(NoFallbackError):
            router.get_fallback("stt_agent", "skt-ak-stt", reason="timeout")

    def test_json_unsupported_warning_for_ak_llm(
        self, router: ModelRouter
    ) -> None:
        """When require_json=True and the model is ak-llm, a warning is set."""
        # Force fallback to ak-llm first
        selection = router.get_fallback(
            "dialogue_agent", "k-exaone", require_json=True
        )
        assert selection.adapter_name == "ak-llm"
        assert selection.json_unsupported_warning is not None
        assert "JSON schema" in selection.json_unsupported_warning

    def test_json_unsupported_warning_not_set_for_solar(
        self, router: ModelRouter
    ) -> None:
        selection = router.select_model("dialogue_agent", require_json=True)
        assert selection.adapter_name == "solar-pro-3"
        assert selection.json_unsupported_warning is None

    def test_register_and_get_adapter(self, router: ModelRouter) -> None:
        mock_adapter = object()
        router.register_adapters({"solar-pro-3": mock_adapter})
        assert router.get_adapter("solar-pro-3") is mock_adapter

    def test_get_adapter_unregistered_raises(self, router: ModelRouter) -> None:
        with pytest.raises(KeyError, match="not-registered"):
            router.get_adapter("not-registered")

    def test_list_agents(self, router: ModelRouter) -> None:
        agents = router.list_agents()
        assert "dialogue_agent" in agents
        assert "stt_agent" in agents
        assert "ocr_agent" in agents
        assert len(agents) == 3

    def test_reload(self, router: ModelRouter, registry_path: Path) -> None:
        """Reload picks up changes to the YAML file."""
        data = yaml.safe_load(registry_path.read_text())
        data["agents"]["dialogue_agent"]["primary"] = "k-exaone"
        registry_path.write_text(yaml.dump(data), encoding="utf-8")
        router.reload()
        selection = router.select_model("dialogue_agent")
        assert selection.adapter_name == "k-exaone"


# ── FallbackPolicy tests ───────────────────────────────────────


class TestFallbackPolicy:
    """Tests for FallbackPolicy.should_fallback / next_delay / classify."""

    @pytest.mark.parametrize(
        "error_type",
        [
            "timeout",
            "429",
            "5xx",
            "invalid_json",
            "safety_uncertain",
            "evidence_verification_failed",
        ],
    )
    def test_should_fallback_known_triggers(
        self, policy: FallbackPolicy, error_type: str
    ) -> None:
        assert policy.should_fallback(error_type, attempt=0) is True

    def test_should_fallback_unknown_trigger(
        self, policy: FallbackPolicy
    ) -> None:
        assert policy.should_fallback("unknown_error", attempt=0) is False

    def test_should_fallback_max_attempts_exceeded(
        self, policy: FallbackPolicy
    ) -> None:
        # max_attempts=3, so attempt=2 means we've used all 3 slots
        assert policy.should_fallback("timeout", attempt=2) is False

    def test_should_fallback_http_500_normalized(
        self, policy: FallbackPolicy
    ) -> None:
        assert policy.should_fallback("500", attempt=0) is True
        assert policy.should_fallback("502", attempt=0) is True
        assert policy.should_fallback("503", attempt=0) is True

    def test_next_delay_exponential_backoff(
        self, policy: FallbackPolicy
    ) -> None:
        assert policy.next_delay(attempt=0) == 1.0
        assert policy.next_delay(attempt=1) == 2.0
        assert policy.next_delay(attempt=2) == 4.0

    def test_classify_http_status_429(self, policy: FallbackPolicy) -> None:
        assert policy.classify_http_status(429) == FallbackTrigger.RATE_LIMITED

    def test_classify_http_status_500(self, policy: FallbackPolicy) -> None:
        assert policy.classify_http_status(500) == FallbackTrigger.SERVER_ERROR

    def test_classify_http_status_200_returns_none(
        self, policy: FallbackPolicy
    ) -> None:
        assert policy.classify_http_status(200) is None

    def test_classify_exception_timeout(self, policy: FallbackPolicy) -> None:
        assert (
            policy.classify_exception(TimeoutError("timed out"))
            == FallbackTrigger.TIMEOUT
        )

    def test_classify_exception_unknown(self, policy: FallbackPolicy) -> None:
        assert policy.classify_exception(ValueError("bad")) is None


# ── Full registry validation ────────────────────────────────────


class TestFullRegistry:
    """Validate the actual agent_model_registry.yaml shipped with the project."""

    @pytest.fixture()
    def full_router(self) -> ModelRouter:
        """Load the real registry file."""
        registry = Path(__file__).resolve().parents[2] / "src" / "routing" / "agent_model_registry.yaml"
        if not registry.exists():
            pytest.skip("Full registry not yet created")
        return ModelRouter(registry_path=registry)

    def test_all_12_agents_present(self, full_router: ModelRouter) -> None:
        agents = full_router.list_agents()
        expected = {
            "stt_agent",
            "ocr_agent",
            "input_normalizer_agent",
            "safety_classifier_agent",
            "dialogue_agent",
            "clinical_slot_agent",
            "orchestrator_agent",
            "temporal_retriever_agent",
            "temporal_summary_agent",
            "handoff_generator_agent",
            "evidence_verifier_agent",
            "prompt_eval_agent",
        }
        assert set(agents) == expected, f"Missing: {expected - set(agents)}"

    def test_fixed_agents_have_no_fallback(
        self, full_router: ModelRouter
    ) -> None:
        for name in ("stt_agent", "ocr_agent"):
            entry = full_router.get_entry(name)
            assert entry.policy == "fixed"
            assert len(entry.chain) == 1

    def test_benchmarked_agents_have_full_chain(
        self, full_router: ModelRouter
    ) -> None:
        benchmarked = [
            "input_normalizer_agent",
            "safety_classifier_agent",
            "dialogue_agent",
            "clinical_slot_agent",
            "orchestrator_agent",
            "temporal_retriever_agent",
            "temporal_summary_agent",
            "handoff_generator_agent",
            "evidence_verifier_agent",
        ]
        for name in benchmarked:
            entry = full_router.get_entry(name)
            assert entry.policy == "benchmarked"
            assert len(entry.chain) == 3, (
                f"{name} should have 3 models in chain, got {len(entry.chain)}"
            )

    def test_offline_agent_exists(self, full_router: ModelRouter) -> None:
        entry = full_router.get_entry("prompt_eval_agent")
        assert entry.policy == "offline"

    def test_all_adapter_names_are_valid(
        self, full_router: ModelRouter
    ) -> None:
        valid_adapters = {
            "solar-pro-3",
            "k-exaone",
            "ak-llm",
            "skt-ak-stt",
            "solar-document-parse",
        }
        for agent_name in full_router.list_agents():
            entry = full_router.get_entry(agent_name)
            for adapter in entry.chain:
                assert adapter in valid_adapters, (
                    f"Agent '{agent_name}' references unknown adapter '{adapter}'"
                )
```

**Test design notes**:
- `TestModelRouter` and `TestFallbackPolicy` use a minimal `tmp_path` registry for isolation
- `TestFullRegistry` loads the real `agent_model_registry.yaml` and validates all 12 agents, policies, chain lengths, and adapter name validity. It is skipped if the file does not yet exist (so CI does not fail during Phase 1-3)
- The parametrized `test_should_fallback_known_triggers` covers all 6 trigger types from PRD §3.4

---

## Checklist

- [ ] `src/routing/__init__.py` created, exports `ModelRouter` and `FallbackPolicy`
- [ ] `src/routing/agent_model_registry.yaml` created with all 12 agents from PRD §3.3
- [ ] `src/routing/model_router.py` created with `ModelRouter`, `RegistryEntry`, `NoFallbackError`
- [ ] `src/routing/fallback_policy.py` created with `FallbackPolicy`, `FallbackTrigger`
- [ ] `src/schemas/common.py` updated — `ModelSelection.json_unsupported_warning` field added
- [ ] `tests/routing/__init__.py` created
- [ ] `tests/routing/test_model_router.py` created with 3 test classes (25+ test cases)
- [ ] `pytest tests/routing/ -x` passes
- [ ] `ruff check src/routing/ tests/routing/` passes
- [ ] Fixed agents (`stt_agent`, `ocr_agent`) have single-entry chains with no fallback
- [ ] Benchmarked agents have 3-entry chains (primary / secondary / fallback)
- [ ] `prompt_eval_agent` has `policy: offline`
- [ ] A.X K1 JSON-schema warning fires when `require_json=True` selects `ak-llm`
- [ ] Exponential backoff produces 1s → 2s → 4s
