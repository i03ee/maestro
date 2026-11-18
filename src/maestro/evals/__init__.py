"""مجموعات التقييم: هل المخرج يفي بما وُعد به؟"""

from .cases import CASES, EvalCase
from .runner import EvalOutcome, eval_registry, evaluate_case, run_all_cases

__all__ = [
    "CASES",
    "EvalCase",
    "EvalOutcome",
    "eval_registry",
    "evaluate_case",
    "run_all_cases",
]
