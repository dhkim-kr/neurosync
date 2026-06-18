"""Handoff health report evaluator modules.

Each checker is a stateless class that validates one aspect of a handoff report.
CompositeEvaluator orchestrates all checkers and returns a unified result.
"""

from .composite import CompositeEvaluator, HandoffEvalResult
from .evidence_checker import EvidenceCheckResult, EvidenceChecker
from .longitudinal_checker import LongitudinalCheckResult, LongitudinalChecker
from .risk_checker import RiskCheckResult, RiskChecker
from .safety_checker import SafetyCheckResult, SafetyChecker
from .section_checker import SectionCheckResult, SectionChecker
from .violation_checker import ViolationCheckResult, ViolationChecker

__all__ = [
    # Composite
    "CompositeEvaluator",
    "HandoffEvalResult",
    # Individual checkers
    "SectionChecker",
    "SectionCheckResult",
    "EvidenceChecker",
    "EvidenceCheckResult",
    "ViolationChecker",
    "ViolationCheckResult",
    "RiskChecker",
    "RiskCheckResult",
    "SafetyChecker",
    "SafetyCheckResult",
    "LongitudinalChecker",
    "LongitudinalCheckResult",
]
