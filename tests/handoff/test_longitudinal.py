"""First chat vs longitudinal chat comparison tests."""

from __future__ import annotations

import pytest

from src.agents.evidence_verifier import EvidenceVerifierInput
from src.schemas.handoff import HandoffInput, SlotData, ScaleScore

from tests.handoff.fixtures.patients import load_fixture


@pytest.mark.asyncio
async def test_longitudinal_has_more_evidence(handoff_agent):
    """TC-006: Longitudinal input should produce more evidence citations."""
    fixture = load_fixture("longitudinal_pair.json")

    first_inp = HandoffInput(
        session_id=fixture["first_chat_input"]["session_id"],
        slots=SlotData(**fixture["first_chat_input"]["slots"]),
        conversation_history=fixture["first_chat_input"]["conversation_history"],
        scale_scores=[ScaleScore(**s) for s in fixture["first_chat_input"].get("scale_scores", [])],
        risk_events=fixture["first_chat_input"].get("risk_events", []),
        ocr_documents=fixture["first_chat_input"].get("ocr_documents", []),
        prior_handoff=fixture["first_chat_input"].get("prior_handoff"),
        is_first_visit=fixture["first_chat_input"].get("is_first_visit", True),
    )

    longi_inp = HandoffInput(
        session_id=fixture["longitudinal_input"]["session_id"],
        slots=SlotData(**fixture["longitudinal_input"]["slots"]),
        conversation_history=fixture["longitudinal_input"]["conversation_history"],
        scale_scores=[ScaleScore(**s) for s in fixture["longitudinal_input"].get("scale_scores", [])],
        risk_events=fixture["longitudinal_input"].get("risk_events", []),
        ocr_documents=fixture["longitudinal_input"].get("ocr_documents", []),
        prior_handoff=fixture["longitudinal_input"].get("prior_handoff"),
        is_first_visit=fixture["longitudinal_input"].get("is_first_visit", False),
    )

    first_out = await handoff_agent.run(first_inp)
    longi_out = await handoff_agent.run(longi_inp)

    assert len(longi_out.evidence_packets) > len(first_out.evidence_packets), (
        f"Longitudinal ({len(longi_out.evidence_packets)} evidence) should have more "
        f"than first-chat ({len(first_out.evidence_packets)} evidence)"
    )


@pytest.mark.asyncio
async def test_longitudinal_fewer_missing_slots(handoff_agent):
    """TC-006: Longitudinal input (all slots filled) should have fewer missing slots."""
    fixture = load_fixture("longitudinal_pair.json")

    first_inp = HandoffInput(
        session_id=fixture["first_chat_input"]["session_id"],
        slots=SlotData(**fixture["first_chat_input"]["slots"]),
        conversation_history=fixture["first_chat_input"]["conversation_history"],
        scale_scores=[ScaleScore(**s) for s in fixture["first_chat_input"].get("scale_scores", [])],
        risk_events=fixture["first_chat_input"].get("risk_events", []),
        ocr_documents=[],
        prior_handoff=None,
        is_first_visit=True,
    )

    longi_inp = HandoffInput(
        session_id=fixture["longitudinal_input"]["session_id"],
        slots=SlotData(**fixture["longitudinal_input"]["slots"]),
        conversation_history=fixture["longitudinal_input"]["conversation_history"],
        scale_scores=[ScaleScore(**s) for s in fixture["longitudinal_input"].get("scale_scores", [])],
        risk_events=fixture["longitudinal_input"].get("risk_events", []),
        ocr_documents=fixture["longitudinal_input"].get("ocr_documents", []),
        prior_handoff=fixture["longitudinal_input"].get("prior_handoff"),
        is_first_visit=False,
    )

    first_out = await handoff_agent.run(first_inp)
    longi_out = await handoff_agent.run(longi_inp)

    assert len(longi_out.missing_slots) < len(first_out.missing_slots), (
        f"Longitudinal ({len(longi_out.missing_slots)} missing) should have fewer missing "
        f"than first-chat ({len(first_out.missing_slots)} missing)"
    )


@pytest.mark.asyncio
async def test_longitudinal_has_delta_section(handoff_agent):
    """TC-006: Longitudinal report must contain delta/change section."""
    fixture = load_fixture("longitudinal_pair.json")

    longi_inp = HandoffInput(
        session_id=fixture["longitudinal_input"]["session_id"],
        slots=SlotData(**fixture["longitudinal_input"]["slots"]),
        conversation_history=fixture["longitudinal_input"]["conversation_history"],
        scale_scores=[ScaleScore(**s) for s in fixture["longitudinal_input"].get("scale_scores", [])],
        risk_events=fixture["longitudinal_input"].get("risk_events", []),
        ocr_documents=fixture["longitudinal_input"].get("ocr_documents", []),
        prior_handoff=fixture["longitudinal_input"].get("prior_handoff"),
        is_first_visit=False,
    )

    longi_out = await handoff_agent.run(longi_inp)
    report = longi_out.report_markdown.lower()

    has_delta = any(
        kw in report
        for kw in ["종단", "변화", "이전", "delta", "previous", "longitudinal", "비교"]
    )
    assert has_delta, "Longitudinal report should contain delta/change section"


@pytest.mark.asyncio
async def test_both_pass_evidence_verification(handoff_agent, evidence_verifier):
    """TC-006: Both first-chat and longitudinal reports must pass evidence verification."""
    fixture = load_fixture("longitudinal_pair.json")

    for key, label in [("first_chat_input", "first-chat"), ("longitudinal_input", "longitudinal")]:
        raw = fixture[key]
        inp = HandoffInput(
            session_id=raw["session_id"],
            slots=SlotData(**raw["slots"]),
            conversation_history=raw["conversation_history"],
            scale_scores=[ScaleScore(**s) for s in raw.get("scale_scores", [])],
            risk_events=raw.get("risk_events", []),
            ocr_documents=raw.get("ocr_documents", []),
            prior_handoff=raw.get("prior_handoff"),
            is_first_visit=raw.get("is_first_visit", True),
        )

        output = await handoff_agent.run(inp)

        verifier_inp = EvidenceVerifierInput(
            session_id=raw["session_id"],
            report_markdown=output.report_markdown,
            evidence_packets=output.evidence_packets,
        )
        v_out = await evidence_verifier.run(verifier_inp)

        assert v_out.diagnosis_violation_count == 0, (
            f"{label}: Found diagnosis violations"
        )
        assert v_out.treatment_violation_count == 0, (
            f"{label}: Found treatment violations"
        )
