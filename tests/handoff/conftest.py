"""Pytest fixtures — bootstrap real agent instances with real LLM adapters."""

from __future__ import annotations

import pytest

from src.config import Settings
from src.routing.model_router import ModelRouter
from src.prompts.loader import PromptLoader
from src.agents.handoff_generator import HandoffGeneratorAgent
from src.agents.safety_classifier import SafetyClassifierAgent
from src.agents.evidence_verifier import EvidenceVerifierAgent
from src.adapters.solar_pro3 import SolarPro3Adapter
from src.adapters.k_exaone import KExaoneAdapter
from src.adapters.ak_llm import AkLlmAdapter


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def model_router(settings: Settings) -> ModelRouter:
    router = ModelRouter(settings.resolve_registry_path())
    adapters = {}
    if settings.upstage_api_key:
        adapters["solar-pro3"] = SolarPro3Adapter(settings)
    if settings.lg_k_exaone_api_key:
        adapters["k-exaone"] = KExaoneAdapter(settings)
    if settings.skt_a_x_api_key:
        adapters["ak-llm"] = AkLlmAdapter(settings)
    if not adapters:
        pytest.skip("No LLM API keys configured — set UPSTAGE_API_KEY or similar")
    router.register_adapters(adapters)
    return router


@pytest.fixture(scope="session")
def prompt_loader(settings: Settings) -> PromptLoader:
    return PromptLoader(settings.resolve_prompts_dir())


@pytest.fixture(scope="session")
def handoff_agent(model_router, prompt_loader) -> HandoffGeneratorAgent:
    return HandoffGeneratorAgent(model_router=model_router, prompt_loader=prompt_loader)


@pytest.fixture(scope="session")
def safety_agent(model_router, prompt_loader) -> SafetyClassifierAgent:
    return SafetyClassifierAgent(model_router=model_router, prompt_loader=prompt_loader)


@pytest.fixture(scope="session")
def evidence_verifier() -> EvidenceVerifierAgent:
    return EvidenceVerifierAgent()
