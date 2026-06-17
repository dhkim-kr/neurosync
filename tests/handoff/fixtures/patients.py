"""Fixture loader and HandoffInput/SafetyInput factory functions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.schemas.handoff import HandoffInput, SlotData, ScaleScore
from src.schemas.safety import SafetyInput

FIXTURES_DIR = Path(__file__).parent


def load_fixture(name: str) -> dict[str, Any]:
    """Load a fixture JSON file by name and normalize field names."""
    path = FIXTURES_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalize: test_id → case_id, description → case_name
    if "case_id" not in data and "test_id" in data:
        data["case_id"] = data["test_id"]
    if "case_name" not in data:
        data["case_name"] = data.get("description", name)

    # Auto-generate safety_input from last user message if not present
    if "safety_input" not in data and "handoff_input" in data:
        hi = data["handoff_input"]
        user_msgs = [
            m for m in hi.get("conversation_history", [])
            if m.get("role") == "user"
        ]
        last_user_msg = user_msgs[-1]["content"] if user_msgs else ""
        data["safety_input"] = {
            "session_id": hi.get("session_id", "test-session"),
            "user_message": last_user_msg,
            "conversation_history": hi.get("conversation_history", [])[-4:],
        }

    return data


def fixture_to_handoff_input(fixture: dict[str, Any]) -> HandoffInput:
    """Convert fixture dict to HandoffInput, constructing nested models."""
    raw = fixture["handoff_input"]
    return HandoffInput(
        session_id=raw["session_id"],
        slots=SlotData(**raw["slots"]),
        conversation_history=raw["conversation_history"],
        scale_scores=[ScaleScore(**s) for s in raw.get("scale_scores", [])],
        risk_events=raw.get("risk_events", []),
        ocr_documents=raw.get("ocr_documents", []),
        prior_handoff=raw.get("prior_handoff"),
        is_first_visit=raw.get("is_first_visit", True),
    )


def fixture_to_safety_input(fixture: dict[str, Any]) -> SafetyInput:
    """Convert fixture dict to SafetyInput."""
    raw = fixture["safety_input"]
    return SafetyInput(
        session_id=raw["session_id"],
        user_message=raw["user_message"],
        conversation_history=raw.get("conversation_history", []),
    )


def list_fixtures() -> list[str]:
    """List all .json fixture files in the fixtures directory."""
    return sorted(p.name for p in FIXTURES_DIR.glob("*.json"))
