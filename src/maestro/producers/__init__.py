"""منتجات الأفعال: من فكرة أو بحث إلى artefact مسمّى.

كل منتِج Takes **ردّ نموذج منظَّماً** (JSON) ويتحقق منه قبل الكتابة:
لا artefact يُكتب من ردّ ناقص أو بلا مصدر.
"""

from .idea import PrdResult, produce_prd
from .live import LiveOutcome, run_live
from .prompts import PROMPT_BUILDERS
from .research import (
    CandidateResult,
    CompetitorResult,
    produce_candidates,
    produce_competitors,
)

__all__ = [
    "LiveOutcome",
    "PROMPT_BUILDERS",
    "PrdResult",
    "run_live",
    "produce_prd",
    "CandidateResult",
    "CompetitorResult",
    "produce_candidates",
    "produce_competitors",
]
