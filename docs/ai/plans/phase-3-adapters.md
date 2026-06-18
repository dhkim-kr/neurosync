# Phase 3: Adapters

> **Depends on**: Phase 1 (base classes `VendorAdapter`, `LLMAdapter`, `Settings`)
> **Blocks**: Phase 4 (ModelRouter dispatches to adapter instances), Phase 5 (agents call adapters via router)
> **Agent owner**: `developer`
> **Gate**: `qa` — every adapter passes healthcheck mock, chat/transcribe round-trip, and JSON strategy tests

---

## Objective

Implement 5 concrete vendor API adapters that subclass the Phase 1 base classes (`LLMAdapter`, `VendorAdapter`). Each adapter encapsulates a single vendor's authentication, request shaping, response normalization, error handling, and rate-limit management. No agent or route may call a vendor API directly — all traffic flows through these adapters.

### Adapter inventory

| # | Adapter class | Base class | Vendor | File |
|---|---|---|---|---|
| 1 | `SolarProAdapter` | `LLMAdapter` | Upstage Solar Pro 3 | `solar_pro.py` |
| 2 | `ExaoneAdapter` | `LLMAdapter` | LG EXAONE (Friendli Dedicated) | `exaone.py` |
| 3 | `SktAxLlmAdapter` | `LLMAdapter` | SKT A.X K1 | `skt_ax_llm.py` |
| 4 | `SktAxSttAdapter` | `VendorAdapter` | SKT A.X STT | `skt_ax_stt.py` |
| 5 | `UpstageDocParseAdapter` | `VendorAdapter` | Upstage Document Parse | `upstage_doc_parse.py` |

All files live under `apps/ai-server/src/adapters/`.

---

## Success Criteria

- [ ] All 5 adapter modules created under `apps/ai-server/src/adapters/`
- [ ] `adapters/__init__.py` re-exports all 5 adapter classes
- [ ] Every LLM adapter's `chat()` returns the normalized dict: `{"content": str, "usage": dict, "model": str, "finish_reason": str}`
- [ ] `SktAxSttAdapter.transcribe_batch()` returns `{"text": str, "segments": list}`
- [ ] `SktAxSttAdapter.transcribe_stream()` yields partial/final transcript dicts
- [ ] `UpstageDocParseAdapter.parse()` returns `{"markdown": str, "blocks": list}`
- [ ] JSON enforcement strategy is correct per vendor (native schema / json_object / prompt+parse+repair)
- [ ] Rate-limit semaphore is enforced for SKT A.X (3 RPS)
- [ ] All adapters pass `healthcheck()` with mocked HTTP
- [ ] `apps/ai-server/tests/conftest.py` provides shared fixtures
- [ ] `pytest apps/ai-server/tests/adapters/ -x` passes (all mocked, no real API calls)
- [ ] `ruff check apps/ai-server/src/adapters/` passes

---

## Step 3.1 — `SolarProAdapter` (Upstage Solar Pro 3)

**File**: `apps/ai-server/src/adapters/solar_pro.py` (new)

### Class definition

```python
"""Upstage Solar Pro 3 adapter — OpenAI-compatible Chat Completions."""

import logging
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from src.adapters.base import LLMAdapter
from src.config import Settings

logger = logging.getLogger(__name__)


class SolarProAdapter(LLMAdapter):
    """Adapter for Upstage Solar Pro 3 Chat Completions API.

    Vendor docs: docs/ai/api/Upstage_API.md
    Base URL: https://api.upstage.ai/v1
    Auth: Authorization: Bearer $UPSTAGE_API_KEY
    SDK: OpenAI Python SDK (swap base_url)
    """

    name: str = "solar-pro3"
    timeout_sec: int = 60
    max_retries: int = 2

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.upstage_api_key,
            base_url=settings.upstage_base_url,
            timeout=self.timeout_sec,
            max_retries=self.max_retries,
        )
        self._model = settings.upstage_chat_model  # "solar-pro3"

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        parallel_tool_calls: bool | None = None,
        reasoning_effort: str | None = None,
        prompt_cache_key: str | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request to Solar Pro 3.

        Solar Pro 3 supports NATIVE json_schema response_format:
            {"type": "json_schema", "json_schema": {"name": ..., "strict": True, "schema": {...}}}
        Rules: all fields required, additionalProperties: false, max nesting 3, no $ref.

        Args:
            messages: OpenAI-format message list.
            response_format: Native JSON schema enforcement. Solar supports
                {"type": "json_schema", "json_schema": {..., "strict": true}}.
            temperature: Sampling temperature.
            max_tokens: Maximum generation tokens.
            stream: If True, returns an async iterator of chunks.
            tools: OpenAI-format tool definitions for function calling.
            tool_choice: Tool selection strategy ("auto", "none", or specific).
            parallel_tool_calls: Allow parallel tool invocation.
            reasoning_effort: "minimal" | "low" | "medium" | "high".
            prompt_cache_key: Opaque key for Upstage prompt caching (latency optimization).

        Returns:
            {"content": str, "usage": dict, "model": str, "finish_reason": str,
             "tool_calls": list | None}
        """
        ...

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        tools: list[dict[str, Any]] | None = None,
        reasoning_effort: str | None = None,
        prompt_cache_key: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream chat completion tokens from Solar Pro 3.

        Yields:
            {"delta": str, "finish_reason": str | None} per chunk.
            Final chunk has finish_reason set.
        """
        ...

    async def healthcheck(self) -> dict[str, Any]:
        """Verify connectivity with a minimal completion request.

        Sends: messages=[{"role": "user", "content": "ping"}], max_tokens=1
        Returns: {"status": "ok"|"error", "vendor": "solar-pro3", "latency_ms": int}
        """
        ...
```

### Constructor → Settings mapping

| Settings field | Client parameter |
|---|---|
| `settings.upstage_api_key` | `AsyncOpenAI(api_key=...)` |
| `settings.upstage_base_url` | `AsyncOpenAI(base_url=...)` — `"https://api.upstage.ai/v1"` |
| `settings.upstage_chat_model` | `self._model` — `"solar-pro3"` |

### Vendor-specific implementation notes

1. **JSON schema enforcement**: Solar Pro 3 supports native `response_format` with `type: "json_schema"`. The `json_schema` object must include `strict: true`, all fields marked `required`, `additionalProperties: false`, maximum nesting depth of 3, and no `$ref` usage. This is the strongest JSON guarantee of the three LLM vendors.
2. **Reasoning effort**: Pass `reasoning_effort` as a top-level parameter in the API call. Valid values: `minimal`, `low`, `medium`, `high`. Omit when not needed.
3. **Prompt caching**: Pass `prompt_cache_key` as a top-level parameter. Reuse the same key across calls with identical system prompts to reduce TTFT.
4. **Tool calling**: Supports `tools`, `tool_choice`, and `parallel_tool_calls` natively. Tool definitions follow the OpenAI format.
5. **Auth**: Standard Bearer token via `Authorization: Bearer $UPSTAGE_API_KEY`.

### Error handling strategy

| Error | Action |
|---|---|
| `openai.AuthenticationError` (401) | Log + raise `AdapterAuthError`. Do NOT retry. |
| `openai.RateLimitError` (429) | Respect `Retry-After` header. Retry up to `max_retries`. |
| `openai.APITimeoutError` | Retry up to `max_retries` with exponential backoff (1s, 2s). |
| `openai.BadRequestError` (400) | Log payload (redacted). Raise `AdapterRequestError`. Check if `json_schema` violated nesting/ref rules. |
| `openai.APIStatusError` (5xx) | Retry up to `max_retries`. If exhausted, raise `AdapterVendorError`. |
| JSON schema violation in response | Should not occur with `strict: true`. If it does, log as anomaly and return raw content. |

---

## Step 3.2 — `ExaoneAdapter` (LG EXAONE / Friendli Dedicated)

**File**: `apps/ai-server/src/adapters/exaone.py` (new)

### Class definition

```python
"""LG EXAONE adapter — Friendli Dedicated OpenAI-compatible endpoint."""

import logging
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from src.adapters.base import LLMAdapter
from src.config import Settings

logger = logging.getLogger(__name__)


# Friendli extra_body defaults — CRITICAL: must always be passed
_FRIENDLI_REASONING_OFF: dict[str, Any] = {
    "parse_reasoning": True,
    "include_reasoning": False,
    "chat_template_kwargs": {"enable_thinking": False},
}

_FRIENDLI_REASONING_ON: dict[str, Any] = {
    "parse_reasoning": True,
    "include_reasoning": True,
    "chat_template_kwargs": {"enable_thinking": True},
}


class ExaoneAdapter(LLMAdapter):
    """Adapter for LG EXAONE via Friendli Dedicated endpoints.

    Vendor docs: docs/ai/api/EXAONE_API.md
    Base URL: https://api.friendli.ai/dedicated/v1
    Auth: Authorization: Bearer $LG_K_EXAONE_API_KEY
    Model field: $LG_K_EXAONE_ENDPOINT_ID (endpoint ID, NOT model name)
    SDK: OpenAI Python SDK with extra_body for Friendli-specific fields

    CRITICAL CONSTRAINTS:
    - response_format supports ONLY {"type": "json_object"}, NOT json_schema.
    - tools and response_format CANNOT be used together.
    - When reasoning ON: temperature=1.0, top_p=1.0
    - When reasoning OFF: temperature=0.0
    """

    name: str = "exaone"
    timeout_sec: int = 60
    max_retries: int = 2

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.lg_k_exaone_api_key,
            base_url=settings.lg_k_exaone_base_url,
            timeout=self.timeout_sec,
            max_retries=self.max_retries,
        )
        # EXAONE uses endpoint ID as the model field, NOT a model name
        self._model = settings.lg_k_exaone_endpoint_id

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        stream: bool = False,
        enable_reasoning: bool = False,
    ) -> dict[str, Any]:
        """Send a chat completion request to EXAONE.

        JSON enforcement: ONLY {"type": "json_object"} is supported.
        If the caller passes a json_schema-style response_format, this adapter
        MUST downgrade it to {"type": "json_object"} and log a warning.

        When enable_reasoning=True:
            - temperature is forced to 1.0
            - top_p is forced to 1.0
            - extra_body uses _FRIENDLI_REASONING_ON
        When enable_reasoning=False:
            - temperature is forced to 0.0 (overrides caller)
            - extra_body uses _FRIENDLI_REASONING_OFF

        CONSTRAINT: tools and response_format cannot be used together.
        If both are needed, prefer tools and enforce JSON via prompt instructions.

        Args:
            messages: OpenAI-format message list.
            response_format: Only {"type": "json_object"} supported.
                json_schema types are auto-downgraded with a warning.
            temperature: Ignored when enable_reasoning is set (overridden by vendor rules).
            max_tokens: Maximum generation tokens.
            stream: If True, returns streaming response.
            enable_reasoning: Toggle Friendli reasoning mode.

        Returns:
            {"content": str, "usage": dict, "model": str, "finish_reason": str}
        """
        ...

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        max_tokens: int = 512,
        enable_reasoning: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream chat completion tokens from EXAONE.

        Yields:
            {"delta": str, "finish_reason": str | None} per chunk.
        """
        ...

    def _build_extra_body(self, enable_reasoning: bool) -> dict[str, Any]:
        """Build the Friendli-specific extra_body dict.

        Args:
            enable_reasoning: Whether to enable EXAONE thinking mode.

        Returns:
            extra_body dict with parse_reasoning, include_reasoning,
            and chat_template_kwargs.
        """
        ...

    def _sanitize_response_format(
        self, response_format: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Downgrade json_schema to json_object if needed.

        EXAONE only supports {"type": "json_object"}.
        If caller passes {"type": "json_schema", ...}, this method:
        1. Logs a warning with the original schema name
        2. Returns {"type": "json_object"}

        Returns:
            None, or {"type": "json_object"}.
        """
        ...

    async def healthcheck(self) -> dict[str, Any]:
        """Verify connectivity with a minimal completion request.

        Returns: {"status": "ok"|"error", "vendor": "exaone", "latency_ms": int}
        """
        ...
```

### Constructor → Settings mapping

| Settings field | Client parameter |
|---|---|
| `settings.lg_k_exaone_api_key` | `AsyncOpenAI(api_key=...)` |
| `settings.lg_k_exaone_base_url` | `AsyncOpenAI(base_url=...)` — `"https://api.friendli.ai/dedicated/v1"` |
| `settings.lg_k_exaone_endpoint_id` | `self._model` (endpoint ID, NOT model name) |

### Vendor-specific implementation notes

1. **JSON strategy**: ONLY `{"type": "json_object"}` is supported. If a caller passes `json_schema`, the adapter silently downgrades to `json_object` and logs a warning. The calling agent must include "Respond in JSON" in the system prompt when using `json_object` mode (OpenAI SDK requirement).
2. **Reasoning toggle**: Friendli Dedicated exposes reasoning via `extra_body`. When reasoning is ON, temperature and top_p are forced to `1.0`. When OFF, temperature is forced to `0.0`. The adapter overrides caller-supplied temperature.
3. **extra_body is mandatory**: Every request MUST include `extra_body` with `parse_reasoning`, `include_reasoning`, and `chat_template_kwargs`. Omitting these causes undefined behavior.
4. **tools vs response_format**: These are mutually exclusive. The adapter must raise `ValueError` if both are passed.
5. **Model field is endpoint ID**: Unlike Solar and A.X K1, the `model` parameter is the Friendli endpoint ID from the environment variable, not a model name string.

### Error handling strategy

| Error | Action |
|---|---|
| `openai.AuthenticationError` (401) | Log + raise `AdapterAuthError`. Check if endpoint ID is correct. |
| `openai.RateLimitError` (429) | Retry with exponential backoff. Friendli Dedicated has per-endpoint limits. |
| `openai.APITimeoutError` | Retry up to `max_retries`. |
| `openai.BadRequestError` (400) | Check if `tools` + `response_format` were both sent. Log + raise `AdapterRequestError`. |
| `openai.APIStatusError` (5xx) | Retry up to `max_retries`. If exhausted, raise `AdapterVendorError`. |
| Response not valid JSON (when `json_object` requested) | Parse error. Attempt 1 repair retry with "Fix the following JSON" appended to messages. If still invalid, raise `AdapterResponseError`. |

---

## Step 3.3 — `SktAxLlmAdapter` (SKT A.X K1)

**File**: `apps/ai-server/src/adapters/skt_ax_llm.py` (new)

### Class definition

```python
"""SKT A.X K1 LLM adapter — OpenAI-compatible with NO native JSON enforcement."""

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from src.adapters.base import LLMAdapter
from src.config import Settings

logger = logging.getLogger(__name__)

# Team-wide rate limit: 3 RPS shared across all A.X K1 calls
_skt_ax_semaphore = asyncio.Semaphore(3)


class SktAxLlmAdapter(LLMAdapter):
    """Adapter for SKT A.X K1 LLM.

    Vendor docs: docs/ai/api/SKT_A_X_API.md
    Base URL: https://awf-gw.adot.ai/v1
    Auth: Authorization: Bearer $SKT_A_X_API_KEY
    Model: "A.X-K1"
    SDK: OpenAI Python SDK (swap base_url)

    CRITICAL CONSTRAINTS:
    - NO native response_format or JSON schema enforcement.
    - JSON strategy: prompt instruction -> JSON parse -> Pydantic validate -> 1 repair retry -> error.
    - RPS limit: 3 per team — enforced via asyncio.Semaphore(3).
    - Retry: 1s -> 2s -> 4s exponential backoff (no Retry-After header from vendor).
    - Context: 128K chars (~64K tokens), but 32K+ input = TTFT seconds to minutes.
    - Service expires 2026-11-23.
    """

    name: str = "skt-ax-k1"
    timeout_sec: int = 120  # Higher timeout due to slow TTFT on large inputs
    max_retries: int = 3    # 3 retries with exponential backoff

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.skt_a_x_api_key,
            base_url=f"{settings.skt_a_x_rest_base_url}/v1",
            timeout=self.timeout_sec,
            max_retries=0,  # We handle retries ourselves for backoff control
        )
        self._model = settings.skt_a_x_llm_model  # "A.X-K1"
        self._semaphore = _skt_ax_semaphore

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        stream: bool = False,
        json_schema_model: type[BaseModel] | None = None,
        enable_reasoning: bool = False,
    ) -> dict[str, Any]:
        """Send a chat completion request to A.X K1.

        JSON enforcement strategy (NO native support):
        1. If json_schema_model is provided, inject JSON instruction into system prompt:
           "You MUST respond with valid JSON matching this schema: {schema}"
        2. Parse response as JSON via json.loads()
        3. Validate via json_schema_model.model_validate(parsed)
        4. On parse/validation failure: append error message + original response,
           retry ONCE with repair prompt
        5. On second failure: raise AdapterResponseError

        Rate limiting:
        All calls go through asyncio.Semaphore(3) to respect the team-wide 3 RPS limit.

        Args:
            messages: OpenAI-format message list.
            response_format: IGNORED for A.X K1 (no native support). Logged as warning.
            temperature: Sampling temperature.
            max_tokens: Maximum generation tokens.
            stream: If True, returns streaming response.
            json_schema_model: Pydantic model class for JSON validation.
                If provided, the adapter injects schema instructions and validates output.
            enable_reasoning: Toggle reasoning via extra_body.chat_template_kwargs.

        Returns:
            {"content": str, "usage": dict, "model": str, "finish_reason": str,
             "parsed": BaseModel | None}
            "parsed" is set only when json_schema_model was provided and validation succeeded.
        """
        ...

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 512,
        enable_reasoning: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream chat completion tokens from A.X K1.

        NOTE: Streaming is incompatible with JSON repair strategy.
        Use non-streaming chat() when JSON output is required.

        Yields:
            {"delta": str, "finish_reason": str | None} per chunk.
        """
        ...

    async def _call_with_rate_limit(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        enable_reasoning: bool,
    ) -> Any:
        """Execute a single API call within the rate-limit semaphore.

        Acquires the semaphore (max 3 concurrent), then calls the OpenAI client.
        On failure, implements exponential backoff: 1s -> 2s -> 4s.

        Returns:
            Raw OpenAI ChatCompletion response object.

        Raises:
            AdapterVendorError: After all retries exhausted.
        """
        ...

    def _inject_json_instruction(
        self,
        messages: list[dict[str, str]],
        schema_model: type[BaseModel],
    ) -> list[dict[str, str]]:
        """Prepend JSON schema instruction to the system message.

        If no system message exists, creates one. If one exists, appends
        the JSON instruction to its content.

        The instruction format:
            "You MUST respond with valid JSON. Schema:\n```json\n{schema}\n```\n
             Do NOT include any text outside the JSON object."

        Args:
            messages: Original message list (not mutated).
            schema_model: Pydantic model whose .model_json_schema() is injected.

        Returns:
            New message list with JSON instruction prepended/appended to system message.
        """
        ...

    def _validate_and_repair(
        self,
        raw_content: str,
        schema_model: type[BaseModel],
    ) -> tuple[BaseModel | None, str | None]:
        """Attempt to parse and validate JSON response.

        Steps:
        1. json.loads(raw_content) — may need to strip markdown code fences first
        2. schema_model.model_validate(parsed_dict)
        3. Return (validated_model, None) on success
        4. Return (None, error_message) on failure

        Args:
            raw_content: Raw LLM response string.
            schema_model: Pydantic model for validation.

        Returns:
            Tuple of (validated_model_or_None, error_message_or_None).
        """
        ...

    def _build_repair_messages(
        self,
        original_messages: list[dict[str, str]],
        raw_response: str,
        error_msg: str,
    ) -> list[dict[str, str]]:
        """Build the repair prompt for the single retry attempt.

        Appends the original assistant response and an error correction
        user message to the conversation.

        Args:
            original_messages: The original conversation.
            raw_response: The invalid assistant response.
            error_msg: The parse/validation error description.

        Returns:
            New message list for the repair call.
        """
        ...

    async def healthcheck(self) -> dict[str, Any]:
        """Verify connectivity with a minimal completion request.

        Returns: {"status": "ok"|"error", "vendor": "skt-ax-k1", "latency_ms": int}
        """
        ...
```

### Constructor → Settings mapping

| Settings field | Client parameter |
|---|---|
| `settings.skt_a_x_api_key` | `AsyncOpenAI(api_key=...)` |
| `settings.skt_a_x_rest_base_url` | `AsyncOpenAI(base_url=...)` — `"https://awf-gw.adot.ai/v1"` |
| `settings.skt_a_x_llm_model` | `self._model` — `"A.X-K1"` |

### Vendor-specific implementation notes

1. **JSON strategy (CRITICAL)**: A.X K1 has NO native `response_format` support. The adapter implements a 4-step fallback: (a) inject JSON schema instruction into system prompt, (b) `json.loads()` the response (strip markdown fences if present), (c) `Pydantic.model_validate()`, (d) on failure, build a repair prompt with the error and retry ONCE. If the second attempt also fails, raise `AdapterResponseError`.
2. **Rate limiting**: Team-wide 3 RPS limit enforced via a module-level `asyncio.Semaphore(3)`. All instances share the same semaphore. The semaphore is acquired before each API call and released after the response.
3. **Retry with exponential backoff**: Since A.X K1 does not return a `Retry-After` header, the adapter implements its own backoff: 1s, 2s, 4s delays between retries. The OpenAI SDK's built-in retry is disabled (`max_retries=0`).
4. **High timeout**: Default timeout is 120s (vs 60s for Solar/EXAONE) because inputs over 32K chars cause TTFT in the seconds-to-minutes range.
5. **Context limit awareness**: 128K chars (~64K tokens). The adapter should log a warning if input exceeds 100K chars.
6. **Reasoning toggle**: Passed via `extra_body={"chat_template_kwargs": {"enable_thinking": enable_reasoning}}`.
7. **Service expiry**: This adapter will stop working on 2026-11-23. Add a startup warning log if the current date is within 30 days of expiry.
8. **`response_format` parameter**: Accepted for interface compatibility but IGNORED. Logs a warning if passed.

### Error handling strategy

| Error | Action |
|---|---|
| `openai.AuthenticationError` (401) | Log + raise `AdapterAuthError`. |
| `openai.APITimeoutError` | Retry with exponential backoff (1s, 2s, 4s). Common for large inputs. |
| `openai.APIStatusError` (5xx) | Retry with exponential backoff. |
| `openai.APIConnectionError` | Retry with exponential backoff. |
| `json.JSONDecodeError` | Trigger repair retry (step 4 of JSON strategy). |
| `pydantic.ValidationError` | Trigger repair retry (step 4 of JSON strategy). |
| Repair retry also fails | Raise `AdapterResponseError` with both the original and repair errors. |
| Semaphore timeout (optional) | If caller uses `asyncio.wait_for()`, raise `AdapterRateLimitError`. |

---

## Step 3.4 — `SktAxSttAdapter` (SKT A.X STT)

**File**: `apps/ai-server/src/adapters/skt_ax_stt.py` (new)

### Class definition

```python
"""SKT A.X STT adapter — streaming WebSocket + batch REST transcription."""

import asyncio
import base64
import json
import logging
from typing import Any, AsyncIterator

import httpx

from src.adapters.base import VendorAdapter
from src.config import Settings

logger = logging.getLogger(__name__)


class SktAxSttAdapter(VendorAdapter):
    """Adapter for SKT A.X STT (Speech-to-Text).

    Vendor docs: docs/ai/api/SKT_A_X_API.md
    Auth: X-API-Key header (NOT Bearer — different from LLM!)
    Same API key as LLM: $SKT_A_X_API_KEY

    Two modes:
    1. Streaming: WebSocket at wss://awf-gw.adot.ai/v1/stt/realtime
    2. Batch: 3-step REST (upload-token -> upload -> transcript)

    CRITICAL CONSTRAINTS:
    - Auth header is X-API-Key (NOT Authorization: Bearer).
    - WebSocket sends base64 JSON audio chunks (NOT binary frames).
    - Keepalive required within 30s of no audio.
    - NO confidence score in response — quality inferred from empty text/VAD absence.
    - Max 100MB or 30 min per file for batch.
    """

    name: str = "skt-ax-stt"
    timeout_sec: int = 300  # Batch transcription can take minutes

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.skt_a_x_api_key
        self._rest_base_url = settings.skt_a_x_rest_base_url  # "https://awf-gw.adot.ai"
        self._ws_base_url = settings.skt_a_x_ws_base_url      # "wss://awf-gw.adot.ai"
        self._streaming_model = settings.skt_a_x_stt_streaming_model  # "A.X_STT_note_streaming"
        self._batch_model = settings.skt_a_x_stt_batch_model          # "A.X_STT_note_batch"
        self._http_client = httpx.AsyncClient(
            base_url=self._rest_base_url,
            headers={"X-API-Key": self._api_key},
            timeout=self.timeout_sec,
        )

    # ── Streaming transcription ──────────────────────────────────────

    async def transcribe_stream(
        self,
        audio_chunks: AsyncIterator[bytes],
        *,
        audio_format: str = "pcm_16k",
        keywords: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream audio for real-time transcription via WebSocket.

        Protocol:
        1. Connect to wss://awf-gw.adot.ai/v1/stt/realtime
        2. Send "create" message with model, audio_format, keywords
        3. For each audio chunk: base64-encode, send as JSON {"audio": "base64..."}
        4. Receive partial (partial=true) and final (final=true) transcript messages
        5. Send keepalive if no audio for 25s (within 30s server timeout)
        6. Send "stop" message when audio ends, wait for "stopped" confirmation

        Args:
            audio_chunks: Async iterator of raw audio bytes.
            audio_format: One of "pcm_8k", "pcm_16k", "speex_16k", "opus_16k".
            keywords: Optional word boosting list (e.g., domain terms).

        Yields:
            {"text": str, "is_partial": bool, "is_final": bool}
            is_partial=True for intermediate results, is_final=True for final segment.
        """
        ...

    async def _send_keepalive(self, ws: Any, interval: float = 25.0) -> None:
        """Background task: send keepalive within 30s of no audio.

        Runs as an asyncio.Task alongside the audio send loop.
        Sends a keepalive JSON message every `interval` seconds
        unless audio was sent more recently.

        Args:
            ws: WebSocket connection object.
            interval: Seconds between keepalives (must be < 30).
        """
        ...

    # ── Batch transcription ──────────────────────────────────────────

    async def transcribe_batch(
        self,
        audio_data: bytes,
        *,
        audio_format: str = "wav",
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """Transcribe an audio file via the 3-step batch REST API.

        Step 1: GET /v1/stt/upload-token?fileSize={SIZE}
            Headers: X-API-Key
            Response: {"upload_token": "..."}

        Step 2: PUT /v1/stt/upload/{upload_token}
            Headers: X-API-Key, Content-Type: application/octet-stream
            Body: raw audio bytes

        Step 3: POST /v1/stt/transcript
            Headers: X-API-Key
            Body: {"upload_token": "...", "speech_model": "A.X_STT_note_batch", ...}
            Response: {"text": "...", "segments": [...]}

        Args:
            audio_data: Raw audio file bytes. Max 100MB.
            audio_format: Audio format string (e.g., "wav", "mp3").
            keywords: Optional keyword boosting list.

        Returns:
            {"text": str, "segments": list[dict], "confidence": None}
            confidence is always None — A.X STT does not provide confidence scores.

        Raises:
            AdapterRequestError: If file exceeds 100MB.
            AdapterVendorError: If any of the 3 steps fails.
        """
        ...

    async def _get_upload_token(self, file_size: int) -> str:
        """Step 1: Acquire an upload token for the given file size.

        GET /v1/stt/upload-token?fileSize={file_size}
        Headers: X-API-Key: {self._api_key}

        Args:
            file_size: Size of the audio file in bytes.

        Returns:
            Upload token string.
        """
        ...

    async def _upload_audio(self, upload_token: str, audio_data: bytes) -> None:
        """Step 2: Upload raw audio bytes to the token URL.

        PUT /v1/stt/upload/{upload_token}
        Headers: X-API-Key, Content-Type: application/octet-stream
        Body: raw bytes

        Args:
            upload_token: Token from step 1.
            audio_data: Raw audio bytes.
        """
        ...

    async def _request_transcript(
        self,
        upload_token: str,
        keywords: list[str] | None,
    ) -> dict[str, Any]:
        """Step 3: Request transcription of the uploaded file.

        POST /v1/stt/transcript
        Headers: X-API-Key
        Body: {"upload_token": ..., "speech_model": "A.X_STT_note_batch", ...}

        Args:
            upload_token: Token from step 1 (same token used in step 2).
            keywords: Optional keyword list.

        Returns:
            Raw transcript response dict.
        """
        ...

    # ── Lifecycle ────────────────────────────────────────────────────

    async def healthcheck(self) -> dict[str, Any]:
        """Verify connectivity by requesting an upload token for 1 byte.

        GET /v1/stt/upload-token?fileSize=1
        If 200, the API key and endpoint are valid.

        Returns: {"status": "ok"|"error", "vendor": "skt-ax-stt", "latency_ms": int}
        """
        ...

    async def close(self) -> None:
        """Close the httpx client. Call on application shutdown."""
        await self._http_client.aclose()
```

### Constructor → Settings mapping

| Settings field | Client parameter |
|---|---|
| `settings.skt_a_x_api_key` | `self._api_key` — used in `X-API-Key` header (NOT Bearer!) |
| `settings.skt_a_x_rest_base_url` | `httpx.AsyncClient(base_url=...)` — `"https://awf-gw.adot.ai"` |
| `settings.skt_a_x_ws_base_url` | `self._ws_base_url` — `"wss://awf-gw.adot.ai"` for WebSocket |
| `settings.skt_a_x_stt_streaming_model` | `self._streaming_model` — `"A.X_STT_note_streaming"` |
| `settings.skt_a_x_stt_batch_model` | `self._batch_model` — `"A.X_STT_note_batch"` |

### Vendor-specific implementation notes

1. **Auth header difference (CRITICAL)**: STT uses `X-API-Key: {key}` header, NOT `Authorization: Bearer {key}`. This is different from the A.X K1 LLM adapter which uses Bearer auth via the OpenAI SDK.
2. **WebSocket protocol**: Audio is sent as base64-encoded JSON objects, NOT binary WebSocket frames. Each message is `{"audio": "<base64-data>"}`.
3. **Keepalive**: The server closes the WebSocket if no message is received for 30 seconds. The adapter must send keepalive messages at 25-second intervals when no audio is being sent. Implement as a background `asyncio.Task`.
4. **No confidence score**: A.X STT does not return confidence scores. The adapter always returns `confidence: None`. Quality must be inferred from: empty text (no speech detected), VAD absence, or format mismatch.
5. **Batch file limits**: Maximum 100MB file size and 30 minutes audio duration. The adapter must validate file size before step 1.
6. **3-step batch flow**: Upload token -> Upload audio -> Request transcript. All three steps use `X-API-Key` header. The upload token is reused across steps 2 and 3.
7. **Streaming create message format**: `{"type": "create", "model": "A.X_STT_note_streaming", "audio_format": "pcm_16k", "keywords": [...]}`.
8. **Streaming stop/stopped**: Send `{"type": "stop"}` when audio ends. Wait for `{"type": "stopped"}` confirmation before closing the WebSocket.

### Error handling strategy

| Error | Action |
|---|---|
| HTTP 401 on any REST step | Log + raise `AdapterAuthError`. Verify `X-API-Key` header (not Bearer). |
| HTTP 413 (file too large) | Raise `AdapterRequestError` with file size info. |
| WebSocket connection refused | Log + raise `AdapterVendorError`. |
| WebSocket closed unexpectedly | Log last received message. Raise `AdapterVendorError`. |
| Keepalive timeout (server closed) | Log "keepalive missed". Raise `AdapterVendorError`. |
| Upload step 2 fails | Raise `AdapterVendorError`. Token may be expired — do not reuse. |
| Transcript step 3 timeout | Retry once after 5s. Batch jobs can be slow. |
| Empty text in response | Return normally with `text: ""`. Log warning "no speech detected". |

---

## Step 3.5 — `UpstageDocParseAdapter` (Upstage Document Parse)

**File**: `apps/ai-server/src/adapters/upstage_doc_parse.py` (new)

### Class definition

```python
"""Upstage Document Parse adapter — document digitization + information extraction."""

import logging
from typing import Any

import httpx

from src.adapters.base import VendorAdapter
from src.config import Settings

logger = logging.getLogger(__name__)

# Supported file formats for Document Parse
_SUPPORTED_FORMATS = frozenset({
    "jpeg", "jpg", "png", "bmp", "pdf", "tiff", "tif",
    "heic", "docx", "pptx", "xlsx", "hwp", "hwpx",
})

# Max file size: 50MB
_MAX_FILE_SIZE = 50 * 1024 * 1024

# Sync page limit: 100 pages
_SYNC_PAGE_LIMIT = 100

# Async page limit: 1000 pages
_ASYNC_PAGE_LIMIT = 1000


class UpstageDocParseAdapter(VendorAdapter):
    """Adapter for Upstage Document Parse and Information Extraction.

    Vendor docs: docs/ai/api/Upstage_API.md
    Endpoint: POST /v1/document-digitization
    Auth: Authorization: Bearer $UPSTAGE_API_KEY
    Input: multipart/form-data with file + model field
    Output: markdown or HTML with structured blocks

    Also supports:
    - POST /v1/information-extraction (schema-based key-value extraction)
    - POST /v1/document-digitization/async (async variant for large docs)
    """

    name: str = "upstage-doc-parse"
    timeout_sec: int = 120  # Document parsing can be slow for large files

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.upstage_api_key
        self._base_url = settings.upstage_base_url  # "https://api.upstage.ai/v1"
        self._http_client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self.timeout_sec,
        )

    async def parse(
        self,
        file_data: bytes,
        *,
        filename: str = "document.pdf",
        output_format: str = "markdown",
    ) -> dict[str, Any]:
        """Parse a document via the sync Document Digitization endpoint.

        POST /v1/document-digitization
        Content-Type: multipart/form-data
        Fields: file (binary), model ("document-parse")

        Args:
            file_data: Raw file bytes. Max 50MB.
            filename: Original filename (used for format detection and Content-Disposition).
            output_format: "markdown" or "html".

        Returns:
            {
                "markdown": str,          # Full document as markdown
                "blocks": list[dict],     # Structured blocks (text, table, image, chart)
                "page_count": int,
                "vendor": "upstage-doc-parse",
            }

        Raises:
            AdapterRequestError: If file exceeds 50MB or format unsupported.
            AdapterVendorError: If API returns non-200.
        """
        ...

    async def parse_async(
        self,
        file_data: bytes,
        *,
        filename: str = "document.pdf",
        output_format: str = "markdown",
    ) -> dict[str, Any]:
        """Parse a large document via the async endpoint.

        POST /v1/document-digitization/async
        For documents exceeding 100 pages (up to 1000 pages).

        Returns a job ID. Polls for completion.

        Args:
            file_data: Raw file bytes. Max 50MB.
            filename: Original filename.
            output_format: "markdown" or "html".

        Returns:
            Same structure as parse(), but may take longer.

        Raises:
            AdapterRequestError: If file exceeds 50MB or format unsupported.
            AdapterVendorError: If job fails or times out.
        """
        ...

    async def extract_info(
        self,
        file_data: bytes,
        *,
        filename: str = "document.pdf",
        extraction_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Extract structured key-value pairs via Information Extraction.

        POST /v1/information-extraction
        Schema-based extraction for specific fields (e.g., patient name, date, dosage).

        Args:
            file_data: Raw file bytes. Max 50MB.
            filename: Original filename.
            extraction_schema: JSON schema defining fields to extract.
                Example: {"patient_name": "string", "diagnosis": "string", "date": "string"}

        Returns:
            {
                "fields": dict[str, Any],     # Extracted key-value pairs
                "vendor": "upstage-doc-parse",
            }
        """
        ...

    def _validate_file(self, file_data: bytes, filename: str) -> None:
        """Validate file size and format before upload.

        Args:
            file_data: Raw file bytes.
            filename: Filename for extension extraction.

        Raises:
            AdapterRequestError: If file exceeds 50MB or extension not in _SUPPORTED_FORMATS.
        """
        ...

    async def healthcheck(self) -> dict[str, Any]:
        """Verify connectivity by sending a tiny 1x1 PNG for parsing.

        Returns: {"status": "ok"|"error", "vendor": "upstage-doc-parse", "latency_ms": int}
        """
        ...

    async def close(self) -> None:
        """Close the httpx client. Call on application shutdown."""
        await self._http_client.aclose()
```

### Constructor → Settings mapping

| Settings field | Client parameter |
|---|---|
| `settings.upstage_api_key` | `self._api_key` — used in `Authorization: Bearer` header |
| `settings.upstage_base_url` | `httpx.AsyncClient(base_url=...)` — `"https://api.upstage.ai/v1"` |

### Vendor-specific implementation notes

1. **Multipart upload**: The document parse endpoint requires `multipart/form-data` with a `file` field (binary) and a `model` field (`"document-parse"`). Use `httpx` multipart support, not the OpenAI SDK.
2. **Supported formats**: JPEG, PNG, BMP, PDF, TIFF, HEIC, DOCX, PPTX, XLSX, HWP, HWPX. Validate file extension before upload.
3. **Sync vs async**: Sync supports up to 100 pages. For larger documents (up to 1000 pages), use the async endpoint at `/v1/document-digitization/async` which returns a job ID for polling.
4. **File size limit**: Maximum 50MB per file. Validate before upload to avoid wasting bandwidth.
5. **Information Extraction**: Separate endpoint (`/v1/information-extraction`) for schema-based key-value extraction. Useful for structured fields like patient name, diagnosis, medication.
6. **Output**: Returns markdown or HTML with structured blocks. Each block has a type (text, table, image, chart), content, and page number.
7. **Shared API key**: Same `$UPSTAGE_API_KEY` as the Solar Pro 3 LLM adapter.

### Error handling strategy

| Error | Action |
|---|---|
| HTTP 401 | Log + raise `AdapterAuthError`. |
| HTTP 400 (bad file format) | Raise `AdapterRequestError` with format info. |
| HTTP 413 (file too large) | Raise `AdapterRequestError`. Should not occur if `_validate_file` is called. |
| HTTP 422 (unprocessable) | Log + raise `AdapterRequestError`. File may be corrupted. |
| HTTP 5xx | Retry once after 2s. Raise `AdapterVendorError` on second failure. |
| Async job timeout | Poll every 5s for up to `timeout_sec`. Raise `AdapterVendorError` if exceeded. |
| Empty response blocks | Return normally. Log warning "no blocks extracted". |

---

## Step 3.6 — Custom exception classes

**File**: `apps/ai-server/src/adapters/exceptions.py` (new)

```python
"""Adapter-specific exceptions.

All adapter errors inherit from AdapterError for unified error handling
in agents and routes.
"""


class AdapterError(Exception):
    """Base exception for all adapter errors."""

    def __init__(self, vendor: str, message: str) -> None:
        self.vendor = vendor
        self.message = message
        super().__init__(f"[{vendor}] {message}")


class AdapterAuthError(AdapterError):
    """Authentication failed (401). Do not retry."""

    pass


class AdapterRequestError(AdapterError):
    """Bad request (400/413/422). Caller error — do not retry."""

    pass


class AdapterResponseError(AdapterError):
    """Response parsing/validation failed after all retries."""

    def __init__(self, vendor: str, message: str, raw_response: str = "") -> None:
        self.raw_response = raw_response
        super().__init__(vendor, message)


class AdapterVendorError(AdapterError):
    """Vendor-side error (5xx, timeout). May be transient."""

    def __init__(self, vendor: str, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(vendor, message)


class AdapterRateLimitError(AdapterError):
    """Rate limit exceeded. Retry after backoff."""

    def __init__(self, vendor: str, message: str, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(vendor, message)
```

---

## Step 3.7 — `adapters/__init__.py` with re-exports

**File**: `apps/ai-server/src/adapters/__init__.py` (new)

```python
"""Neuro-Sync vendor API adapters — 5 concrete implementations.

All external API calls MUST go through these adapters.
Direct httpx/openai calls from agents or routes are forbidden.

Adapter hierarchy:
    VendorAdapter (base)
    ├── LLMAdapter (base for chat completions)
    │   ├── SolarProAdapter      — Upstage Solar Pro 3
    │   ├── ExaoneAdapter        — LG EXAONE (Friendli Dedicated)
    │   └── SktAxLlmAdapter      — SKT A.X K1
    ├── SktAxSttAdapter          — SKT A.X STT (streaming + batch)
    └── UpstageDocParseAdapter   — Upstage Document Parse
"""

from src.adapters.exaone import ExaoneAdapter
from src.adapters.exceptions import (
    AdapterAuthError,
    AdapterError,
    AdapterRateLimitError,
    AdapterRequestError,
    AdapterResponseError,
    AdapterVendorError,
)
from src.adapters.skt_ax_llm import SktAxLlmAdapter
from src.adapters.skt_ax_stt import SktAxSttAdapter
from src.adapters.solar_pro import SolarProAdapter
from src.adapters.upstage_doc_parse import UpstageDocParseAdapter

__all__ = [
    # Adapters
    "SolarProAdapter",
    "ExaoneAdapter",
    "SktAxLlmAdapter",
    "SktAxSttAdapter",
    "UpstageDocParseAdapter",
    # Exceptions
    "AdapterError",
    "AdapterAuthError",
    "AdapterRequestError",
    "AdapterResponseError",
    "AdapterVendorError",
    "AdapterRateLimitError",
]
```

---

## Step 3.8 — Shared test fixtures

**File**: `apps/ai-server/tests/conftest.py` (new)

```python
"""Shared test fixtures for all adapter tests.

All tests use mocked HTTP — no real API calls are made.
"""

import pytest

from src.config import Settings


@pytest.fixture()
def mock_settings() -> Settings:
    """Settings with dummy API keys for testing.

    All URLs point to defaults. Keys are non-empty to pass
    client initialization but are never sent to real endpoints.
    """
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        upstage_api_key="test-upstage-key",
        lg_k_exaone_api_key="test-exaone-key",
        lg_k_exaone_endpoint_id="test-endpoint-id",
        skt_a_x_api_key="test-skt-key",
    )


@pytest.fixture()
def sample_messages() -> list[dict[str, str]]:
    """Minimal chat messages for LLM adapter tests."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello."},
    ]


@pytest.fixture()
def sample_chat_response() -> dict:
    """Mock OpenAI-compatible ChatCompletion response (as dict).

    Matches the structure returned by openai.AsyncOpenAI().chat.completions.create().
    """
    return {
        "id": "chatcmpl-test-001",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"answer": "test response"}',
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


@pytest.fixture()
def sample_audio_bytes() -> bytes:
    """Minimal WAV-like bytes for STT adapter tests."""
    # 44-byte WAV header + 100 bytes of silence
    return b"RIFF" + b"\x00" * 40 + b"\x00" * 100
```

---

## Step 3.9 — Test files

### 3.9.1 — `test_solar_pro.py`

**File**: `apps/ai-server/tests/adapters/test_solar_pro.py` (new)

Test cases:

| # | Test name | What it verifies |
|---|---|---|
| 1 | `test_chat_basic_response` | `chat()` returns normalized dict with `content`, `usage`, `model`, `finish_reason` |
| 2 | `test_chat_with_json_schema` | `response_format={"type": "json_schema", ...}` is passed through to the OpenAI client |
| 3 | `test_chat_with_tools` | `tools` and `tool_choice` parameters are forwarded correctly |
| 4 | `test_chat_with_reasoning_effort` | `reasoning_effort="high"` is included in the API call |
| 5 | `test_chat_with_prompt_cache_key` | `prompt_cache_key` is included in the API call |
| 6 | `test_chat_stream_yields_chunks` | `chat_stream()` yields delta dicts with final `finish_reason` |
| 7 | `test_healthcheck_ok` | `healthcheck()` returns `{"status": "ok", "vendor": "solar-pro3"}` on success |
| 8 | `test_healthcheck_auth_error` | `healthcheck()` returns `{"status": "error"}` on 401 |
| 9 | `test_constructor_settings_mapping` | Adapter reads correct Settings fields for API key, base URL, model |
| 10 | `test_redact_for_log` | Inherited `redact_for_log()` redacts message content |

### 3.9.2 — `test_exaone.py`

**File**: `apps/ai-server/tests/adapters/test_exaone.py` (new)

Test cases:

| # | Test name | What it verifies |
|---|---|---|
| 1 | `test_chat_basic_response` | `chat()` returns normalized dict |
| 2 | `test_chat_reasoning_off_forces_temp_zero` | When `enable_reasoning=False`, temperature is forced to 0.0 regardless of caller |
| 3 | `test_chat_reasoning_on_forces_temp_one` | When `enable_reasoning=True`, temperature is forced to 1.0 and top_p to 1.0 |
| 4 | `test_extra_body_reasoning_off` | `_build_extra_body(False)` returns correct Friendli fields with `enable_thinking: False` |
| 5 | `test_extra_body_reasoning_on` | `_build_extra_body(True)` returns correct Friendli fields with `enable_thinking: True` |
| 6 | `test_sanitize_json_schema_downgrade` | `_sanitize_response_format({"type": "json_schema", ...})` returns `{"type": "json_object"}` |
| 7 | `test_sanitize_json_object_passthrough` | `_sanitize_response_format({"type": "json_object"})` returns unchanged |
| 8 | `test_sanitize_none_passthrough` | `_sanitize_response_format(None)` returns `None` |
| 9 | `test_model_is_endpoint_id` | `self._model` equals `settings.lg_k_exaone_endpoint_id`, not a model name |
| 10 | `test_healthcheck_ok` | `healthcheck()` returns `{"status": "ok", "vendor": "exaone"}` |
| 11 | `test_tools_and_response_format_raises` | Passing both `tools` and `response_format` raises `ValueError` |

### 3.9.3 — `test_skt_ax_llm.py`

**File**: `apps/ai-server/tests/adapters/test_skt_ax_llm.py` (new)

Test cases:

| # | Test name | What it verifies |
|---|---|---|
| 1 | `test_chat_basic_response` | `chat()` returns normalized dict |
| 2 | `test_chat_json_schema_model_injects_instruction` | When `json_schema_model` is provided, system prompt includes JSON schema instruction |
| 3 | `test_chat_json_valid_response_parses` | Valid JSON response is parsed and `parsed` field contains the Pydantic model |
| 4 | `test_chat_json_invalid_triggers_repair` | Invalid JSON triggers exactly 1 repair retry |
| 5 | `test_chat_json_repair_succeeds` | Repair retry with corrected JSON returns valid `parsed` model |
| 6 | `test_chat_json_repair_fails_raises` | Both original and repair fail -> raises `AdapterResponseError` |
| 7 | `test_rate_limit_semaphore` | Concurrent calls are limited to 3 via semaphore |
| 8 | `test_retry_exponential_backoff` | Failed calls retry with 1s, 2s, 4s delays |
| 9 | `test_response_format_ignored_with_warning` | Passing `response_format` logs a warning and is ignored |
| 10 | `test_large_input_warning` | Input over 100K chars logs a context-length warning |
| 11 | `test_reasoning_toggle_extra_body` | `enable_reasoning=True` sets correct `extra_body.chat_template_kwargs` |
| 12 | `test_healthcheck_ok` | `healthcheck()` returns `{"status": "ok", "vendor": "skt-ax-k1"}` |
| 13 | `test_service_expiry_warning` | Startup logs a warning if date is within 30 days of 2026-11-23 |

### 3.9.4 — `test_skt_ax_stt.py`

**File**: `apps/ai-server/tests/adapters/test_skt_ax_stt.py` (new)

Test cases:

| # | Test name | What it verifies |
|---|---|---|
| 1 | `test_batch_full_flow` | 3-step batch: upload-token -> upload -> transcript returns `{"text": ..., "segments": ...}` |
| 2 | `test_batch_get_upload_token` | Step 1 sends correct `X-API-Key` header (NOT Bearer) and `fileSize` param |
| 3 | `test_batch_upload_audio` | Step 2 sends `Content-Type: application/octet-stream` with raw bytes |
| 4 | `test_batch_request_transcript` | Step 3 sends correct `speech_model` field |
| 5 | `test_batch_file_too_large` | File > 100MB raises `AdapterRequestError` before any API call |
| 6 | `test_batch_confidence_always_none` | Response always has `confidence: None` |
| 7 | `test_stream_yields_partial_and_final` | `transcribe_stream()` yields `is_partial=True` and `is_final=True` messages |
| 8 | `test_stream_sends_base64_json` | Audio chunks are base64-encoded and sent as JSON (not binary frames) |
| 9 | `test_stream_keepalive_sent` | Keepalive is sent within 30s of no audio |
| 10 | `test_stream_stop_message` | "stop" message is sent at end, "stopped" confirmation is awaited |
| 11 | `test_auth_header_is_x_api_key` | All REST requests use `X-API-Key` header, NOT `Authorization: Bearer` |
| 12 | `test_healthcheck_ok` | `healthcheck()` returns `{"status": "ok", "vendor": "skt-ax-stt"}` |
| 13 | `test_empty_text_returns_normally` | Empty transcript returns `text: ""` without error |

### 3.9.5 — `test_upstage_doc_parse.py`

**File**: `apps/ai-server/tests/adapters/test_upstage_doc_parse.py` (new)

Test cases:

| # | Test name | What it verifies |
|---|---|---|
| 1 | `test_parse_returns_markdown_and_blocks` | `parse()` returns `{"markdown": str, "blocks": list}` |
| 2 | `test_parse_sends_multipart` | Request uses `multipart/form-data` with `file` and `model` fields |
| 3 | `test_parse_model_field_is_document_parse` | `model` field in multipart is `"document-parse"` |
| 4 | `test_parse_auth_is_bearer` | Request uses `Authorization: Bearer` header |
| 5 | `test_validate_file_size_limit` | File > 50MB raises `AdapterRequestError` |
| 6 | `test_validate_unsupported_format` | Unsupported extension (e.g., `.exe`) raises `AdapterRequestError` |
| 7 | `test_validate_supported_formats` | All 12 supported formats pass validation |
| 8 | `test_extract_info_with_schema` | `extract_info()` sends extraction schema and returns `{"fields": dict}` |
| 9 | `test_parse_async_large_doc` | `parse_async()` calls the async endpoint for large documents |
| 10 | `test_healthcheck_ok` | `healthcheck()` returns `{"status": "ok", "vendor": "upstage-doc-parse"}` |
| 11 | `test_empty_blocks_returns_normally` | Empty block list returns without error |
| 12 | `test_close_shuts_down_client` | `close()` calls `httpx.AsyncClient.aclose()` |

### 3.9.6 — `test_exceptions.py`

**File**: `apps/ai-server/tests/adapters/test_exceptions.py` (new)

Test cases:

| # | Test name | What it verifies |
|---|---|---|
| 1 | `test_adapter_error_str_format` | `str(AdapterError("vendor", "msg"))` == `"[vendor] msg"` |
| 2 | `test_all_exceptions_inherit_adapter_error` | All 5 subclasses are `isinstance(..., AdapterError)` |
| 3 | `test_response_error_preserves_raw` | `AdapterResponseError` stores `raw_response` attribute |
| 4 | `test_vendor_error_preserves_status_code` | `AdapterVendorError` stores `status_code` attribute |
| 5 | `test_rate_limit_error_preserves_retry_after` | `AdapterRateLimitError` stores `retry_after` attribute |

### 3.9.7 — `tests/adapters/__init__.py`

**File**: `apps/ai-server/tests/adapters/__init__.py` (new)

```python
"""Adapter test package."""
```

---

## Step 3.10 — File listing summary

### Production files

| # | Path | Status |
|---|---|---|
| 1 | `apps/ai-server/src/adapters/__init__.py` | new |
| 2 | `apps/ai-server/src/adapters/exceptions.py` | new |
| 3 | `apps/ai-server/src/adapters/solar_pro.py` | new |
| 4 | `apps/ai-server/src/adapters/exaone.py` | new |
| 5 | `apps/ai-server/src/adapters/skt_ax_llm.py` | new |
| 6 | `apps/ai-server/src/adapters/skt_ax_stt.py` | new |
| 7 | `apps/ai-server/src/adapters/upstage_doc_parse.py` | new |

### Test files

| # | Path | Status |
|---|---|---|
| 1 | `apps/ai-server/tests/conftest.py` | new |
| 2 | `apps/ai-server/tests/adapters/__init__.py` | new |
| 3 | `apps/ai-server/tests/adapters/test_solar_pro.py` | new |
| 4 | `apps/ai-server/tests/adapters/test_exaone.py` | new |
| 5 | `apps/ai-server/tests/adapters/test_skt_ax_llm.py` | new |
| 6 | `apps/ai-server/tests/adapters/test_skt_ax_stt.py` | new |
| 7 | `apps/ai-server/tests/adapters/test_upstage_doc_parse.py` | new |
| 8 | `apps/ai-server/tests/adapters/test_exceptions.py` | new |

---

## JSON enforcement strategy comparison

| Vendor | Strategy | Reliability | Notes |
|---|---|---|---|
| **Solar Pro 3** | Native `json_schema` with `strict: true` | Highest | All fields required, no additionalProperties, max nesting 3, no $ref |
| **EXAONE** | Native `json_object` | Medium-high | System prompt must say "respond in JSON". No schema enforcement — validate with Pydantic after. |
| **A.X K1** | Prompt instruction + parse + validate + 1 repair retry | Medium | No native support. Full 4-step fallback. Most fragile of the three. |

---

## Implementation order

Implement in this order to build up complexity incrementally:

1. `exceptions.py` — needed by all adapters
2. `solar_pro.py` — simplest LLM adapter (native JSON, standard auth)
3. `exaone.py` — adds extra_body complexity, json_object downgrade
4. `skt_ax_llm.py` — adds rate limiting, JSON repair, exponential backoff
5. `skt_ax_stt.py` — different protocol (WebSocket + REST), different auth header
6. `upstage_doc_parse.py` — different protocol (multipart), file validation
7. `__init__.py` — re-exports after all adapters exist
8. `conftest.py` + all test files

---

## Checklist

- [ ] `src/adapters/exceptions.py` created with 5 exception classes
- [ ] `src/adapters/solar_pro.py` created — `SolarProAdapter` with `chat()`, `chat_stream()`, `healthcheck()`
- [ ] `src/adapters/exaone.py` created — `ExaoneAdapter` with `chat()`, `chat_stream()`, `_build_extra_body()`, `_sanitize_response_format()`, `healthcheck()`
- [ ] `src/adapters/skt_ax_llm.py` created — `SktAxLlmAdapter` with `chat()`, `chat_stream()`, `_call_with_rate_limit()`, `_inject_json_instruction()`, `_validate_and_repair()`, `_build_repair_messages()`, `healthcheck()`
- [ ] `src/adapters/skt_ax_stt.py` created — `SktAxSttAdapter` with `transcribe_stream()`, `transcribe_batch()`, `_get_upload_token()`, `_upload_audio()`, `_request_transcript()`, `_send_keepalive()`, `healthcheck()`, `close()`
- [ ] `src/adapters/upstage_doc_parse.py` created — `UpstageDocParseAdapter` with `parse()`, `parse_async()`, `extract_info()`, `_validate_file()`, `healthcheck()`, `close()`
- [ ] `src/adapters/__init__.py` re-exports all 5 adapters + all exceptions
- [ ] `tests/conftest.py` provides `mock_settings`, `sample_messages`, `sample_chat_response`, `sample_audio_bytes`
- [ ] `tests/adapters/__init__.py` created
- [ ] `tests/adapters/test_solar_pro.py` — 10 test cases
- [ ] `tests/adapters/test_exaone.py` — 11 test cases
- [ ] `tests/adapters/test_skt_ax_llm.py` — 13 test cases
- [ ] `tests/adapters/test_skt_ax_stt.py` — 13 test cases
- [ ] `tests/adapters/test_upstage_doc_parse.py` — 12 test cases
- [ ] `tests/adapters/test_exceptions.py` — 5 test cases
- [ ] All tests pass: `pytest apps/ai-server/tests/adapters/ -x`
- [ ] Linting passes: `ruff check apps/ai-server/src/adapters/`
- [ ] No real API calls in any test (all mocked)
- [ ] `from src.adapters import SolarProAdapter, ExaoneAdapter, SktAxLlmAdapter, SktAxSttAdapter, UpstageDocParseAdapter` imports cleanly
- [ ] Auth headers verified: Bearer for Solar/EXAONE/A.X-LLM, X-API-Key for A.X-STT, Bearer for Upstage DocParse
- [ ] SKT A.X K1 rate-limit semaphore(3) is module-level and shared across instances
- [ ] SKT A.X K1 service expiry warning for 2026-11-23 is implemented
- [ ] `critic` review confirms all vendor-specific constraints are respected
