# Phase 1: Foundation

> **Depends on**: Nothing (starting point)
> **Blocks**: Phase 2, Phase 3
> **Agent owner**: `developer`
> **Gate**: `qa` — all imports clean, config loads from env, base classes instantiable

---

## Objective

Establish the foundational abstractions that every subsequent phase depends on: application config, base agent/adapter classes, common schema types, and updated dependencies.

## Success Criteria

- [ ] `from src.config import get_settings` loads with defaults when no `.env` exists
- [ ] `from src.agents.base import BaseAgent, AgentInput, AgentOutput` imports cleanly
- [ ] `from src.adapters.base import VendorAdapter, LLMAdapter` imports cleanly
- [ ] `from src.schemas.common import RiskLevel, EvidenceSource, EvidencePacket` imports cleanly
- [ ] `pytest tests/test_config.py tests/test_schemas.py -x` passes
- [ ] `ruff check src/config.py src/agents/base.py src/adapters/base.py src/schemas/common.py` passes

---

## Step 1.1 — Update `apps/ai-server/pyproject.toml`

**File**: `apps/ai-server/pyproject.toml`
**Action**: Add 3 new dependencies to the `dependencies` list.

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "httpx>=0.27.0",
    "neuro-sync-contracts",
    # --- NEW ---
    "openai>=1.40.0",           # OpenAI SDK — all 3 LLM adapters + STT batch
    "pyyaml>=6.0",              # YAML-based agent_model_registry
    "aiofiles>=24.1.0",         # Async file reads for prompt loader
]
```

**Why each dependency**:
- `openai`: Solar Pro 3, EXAONE, A.X K1 all use OpenAI-compatible Chat Completions API
- `pyyaml`: `agent_model_registry.yaml` is read by `ModelRouter` (Phase 4)
- `aiofiles`: `PromptLoader` reads versioned `.md` prompt files asynchronously (Phase 7)

After editing, run: `cd apps/ai-server && uv lock`

---

## Step 1.2 — Create `apps/ai-server/src/config.py`

**File**: `apps/ai-server/src/config.py` (new)

```python
"""Application configuration. All secrets from environment variables only."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """AI server settings. Never hardcode API keys."""

    # --- Upstage Solar Pro 3 ---
    upstage_api_key: str = ""
    upstage_base_url: str = "https://api.upstage.ai/v1"
    upstage_v2_base_url: str = "https://api.upstage.ai/v2"
    upstage_chat_model: str = "solar-pro3"

    # --- EXAONE / Friendli Dedicated ---
    lg_k_exaone_api_key: str = ""
    lg_k_exaone_endpoint_id: str = ""
    lg_k_exaone_base_url: str = "https://api.friendli.ai/dedicated/v1"

    # --- SKT A.X (LLM + STT share one key, different auth headers) ---
    skt_a_x_api_key: str = ""
    skt_a_x_rest_base_url: str = "https://awf-gw.adot.ai"
    skt_a_x_ws_base_url: str = "wss://awf-gw.adot.ai"
    skt_a_x_llm_model: str = "A.X-K1"
    skt_a_x_stt_streaming_model: str = "A.X_STT_note_streaming"
    skt_a_x_stt_batch_model: str = "A.X_STT_note_batch"

    # --- Internal paths ---
    model_registry_path: str = "src/routing/agent_model_registry.yaml"
    prompts_base_dir: str = "docs/ai/prompts"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Factory function for dependency injection."""
    return Settings()
```

**Design notes**:
- All vendor keys default to `""` so the app starts even without `.env` (for tests)
- `model_config` enables automatic `.env` loading
- SKT A.X has both REST and WS base URLs because STT streaming uses WebSocket
- Path fields use relative paths from the ai-server working directory

---

## Step 1.3 — Create `apps/ai-server/src/agents/__init__.py`

**File**: `apps/ai-server/src/agents/__init__.py` (new)

```python
"""Neuro-Sync AI agents — 12 role-specialized agents per PRD §5."""
```

---

## Step 1.4 — Create `apps/ai-server/src/agents/base.py`

**File**: `apps/ai-server/src/agents/base.py` (new)

```python
"""Abstract base classes for all 12 agents."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    """Base class for all agent input models.

    Each agent subclasses this with its specific input fields.
    """

    pass


class AgentOutput(BaseModel):
    """Base class for all agent output models.

    Common trace fields are populated by every agent.
    """

    model_used: str = ""
    prompt_version: str = ""
    latency_ms: int = 0
    reason_summary: str = Field(
        default="",
        description="Policy-level short reason. Never raw chain-of-thought.",
    )


class BaseAgent(ABC):
    """Abstract base for all 12 Neuro-Sync agents.

    Each agent MUST:
    - Define `name` and `description` class attributes
    - Implement `run()` with its specific I/O types
    - Use ModelRouter for model selection (never hardcode model names)
    - Use PromptLoader for system prompts (never inline prompt text)
    - Return `reason_summary`, never raw CoT
    """

    name: str
    description: str

    @abstractmethod
    async def run(self, input_data: AgentInput, **kwargs: Any) -> AgentOutput:
        """Execute the agent's primary task.

        Args:
            input_data: Agent-specific input (subclass of AgentInput).
            **kwargs: Additional context (session_state, risk_state, etc.)

        Returns:
            Agent-specific output (subclass of AgentOutput).
        """
        ...
```

---

## Step 1.5 — Create `apps/ai-server/src/adapters/base.py`

**File**: `apps/ai-server/src/adapters/base.py` (new)

```python
"""Abstract base classes for all vendor API adapters."""

from abc import ABC, abstractmethod
from typing import Any


class VendorAdapter(ABC):
    """Base class for all vendor API adapters.

    All external API calls MUST go through an adapter subclass.
    Direct httpx/openai calls from agents or routes are forbidden.
    """

    name: str
    timeout_sec: int = 30
    max_retries: int = 2

    @abstractmethod
    async def healthcheck(self) -> dict[str, Any]:
        """Check if the vendor API is reachable.

        Returns:
            {"status": "ok"|"error", "vendor": self.name, ...}
        """
        ...

    def estimate_cost(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Estimate cost for a request (optional, for monitoring)."""
        return {"vendor": self.name, "estimated": "unknown"}

    def redact_for_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Remove PII and sensitive content before logging.

        CRITICAL: Never log raw patient text, audio, or documents.
        """
        redacted = {**payload}
        sensitive_keys = ("content", "text", "audio", "data", "file_bytes", "messages")
        for key in sensitive_keys:
            if key in redacted:
                val = payload[key]
                if isinstance(val, (bytes, bytearray)):
                    redacted[key] = f"<redacted:bytes:{len(val)}>"
                elif isinstance(val, str):
                    redacted[key] = f"<redacted:str:{len(val)}>"
                elif isinstance(val, list):
                    redacted[key] = f"<redacted:list:{len(val)}items>"
                else:
                    redacted[key] = "<redacted>"
        return redacted


class LLMAdapter(VendorAdapter):
    """Base class for LLM vendor adapters (Solar Pro 3, EXAONE, A.X K1).

    All three vendors use OpenAI-compatible Chat Completions API.
    Differences (JSON strategy, reasoning control, auth) are handled
    in each subclass.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Send a chat completion request.

        Args:
            messages: OpenAI-format message list [{role, content}].
            response_format: JSON schema enforcement (vendor-specific support).
            temperature: Sampling temperature. 0.0 = deterministic.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream response tokens.

        Returns:
            {"content": str, "usage": dict, "model": str, "finish_reason": str}
        """
        ...
```

---

## Step 1.6 — Create `apps/ai-server/src/schemas/__init__.py`

**File**: `apps/ai-server/src/schemas/__init__.py` (new)

```python
"""Internal Pydantic schemas for agent I/O.

These are INTERNAL to ai-server. The Platform↔AI interface schemas
live in packages/shared-contracts/python/src/contracts/.
"""
```

---

## Step 1.7 — Create `apps/ai-server/src/schemas/common.py`

**File**: `apps/ai-server/src/schemas/common.py` (new)

```python
"""Common types shared across multiple agents."""

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    """Safety risk classification levels (PRD §6.2)."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceSource(StrEnum):
    """Allowed evidence sources for Handoff claims (PRD §9.3)."""

    MESSAGE = "message"
    SCALE = "scale"
    DOCUMENT_BLOCK = "document_block"
    RISK_EVENT = "risk_event"
    PRIOR_HANDOFF = "prior_handoff"


class EvidencePacket(BaseModel):
    """Single unit of retrievable evidence for RAG/Handoff (PRD §6.6)."""

    evidence_id: str
    source_type: EvidenceSource
    source_id: str
    timestamp: str = ""
    content: str = ""
    metadata: dict = Field(default_factory=dict)
    retrieval_score: float = 0.0


class ModelSelection(BaseModel):
    """Result of ModelRouter.select_model() (PRD §8.2)."""

    adapter_name: str
    is_fallback: bool = False
    fallback_reason: str | None = None
```

---

## Step 1.8 — Create tests

**File**: `apps/ai-server/tests/test_config.py` (new)

```python
"""Test Settings loads correctly."""

from src.config import Settings, get_settings


def test_settings_defaults() -> None:
    """Settings loads with empty defaults when no .env exists."""
    s = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
    assert s.upstage_base_url == "https://api.upstage.ai/v1"
    assert s.skt_a_x_llm_model == "A.X-K1"
    assert s.upstage_api_key == ""


def test_get_settings_returns_settings() -> None:
    s = get_settings()
    assert isinstance(s, Settings)
```

**File**: `apps/ai-server/tests/test_schemas.py` (new)

```python
"""Test common schema types."""

from src.schemas.common import EvidencePacket, EvidenceSource, RiskLevel


def test_risk_level_values() -> None:
    assert RiskLevel.NONE == "none"
    assert RiskLevel.CRITICAL == "critical"
    assert len(RiskLevel) == 5


def test_evidence_packet_serialization() -> None:
    ep = EvidencePacket(
        evidence_id="ev_001",
        source_type=EvidenceSource.MESSAGE,
        source_id="msg_123",
        content="test content",
    )
    data = ep.model_dump()
    assert data["evidence_id"] == "ev_001"
    assert data["source_type"] == "message"
    roundtrip = EvidencePacket.model_validate(data)
    assert roundtrip == ep
```

---

## Checklist

- [ ] `pyproject.toml` updated with `openai`, `pyyaml`, `aiofiles`
- [ ] `uv lock` succeeds
- [ ] `src/config.py` created
- [ ] `src/agents/__init__.py` + `src/agents/base.py` created
- [ ] `src/adapters/base.py` created (note: `src/adapters/__init__.py` is Phase 3)
- [ ] `src/schemas/__init__.py` + `src/schemas/common.py` created
- [ ] `tests/test_config.py` + `tests/test_schemas.py` created
- [ ] `pytest tests/test_config.py tests/test_schemas.py tests/test_health.py -x` passes
- [ ] `ruff check src/ tests/` passes
