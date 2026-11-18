"""حزمة القبول: معايير AC-01..AC-20 وشواهدها."""

from .criteria import CRITERIA, CRITERIA_BY_ID, Criterion, implemented_criteria, pending_criteria
from .proofs import ProofResult, run_all_proofs

__all__ = [
    "CRITERIA",
    "CRITERIA_BY_ID",
    "Criterion",
    "implemented_criteria",
    "pending_criteria",
    "ProofResult",
    "run_all_proofs",
]
