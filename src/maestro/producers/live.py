"""المسار الحيّ: من مطالبة ⇒ إلى artefact حقيقي، بتكلفة مسجَّلة وشاهد أدلة.

الفرق بين هذا المسار وشاهد الآلية: هنا **النموذج الحقيقي** ينتج، والردّ
يدخل نفس المُدقِّق الذي يستعمله الشاهد الآليّ. فإذا خالف النموذج العقد
⇒ لا artefact، ويُبلَّغ الفشل.

كل ما يُنفَّق يُكتب في سجل الأدلة (hash-chain) ⇒ بعد التشغيل نعرف:
أي مزوّد، أي نموذج، كم رمزاً، كم دولاراً، كم محاولة قبل النجاح.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..routing.base import CompletionRequest
from ..routing.router import ModelRouter
from .idea import PrdResult, produce_prd, write_prd
from .prompts import PROMPT_BUILDERS
from .research import (
    CandidateResult,
    CompetitorResult,
    produce_candidates,
    produce_competitors,
    write_candidates,
    write_competitors,
)
from .structured import parse_structured

#: سقف الرموز لكل قدرة: النماذجُ المستنتِجة تحتاج room للتنفس.
MAX_OUTPUT_TOKENS: dict[str, int] = {
    # النماذج المستنتِجة تستهلك رموزاً في reasoning قبل الإجابة، فالسقف
    # يجب أن يتسع للاثنين معاً — قياس حيّ: 3000 رمز لم تكفِ PRD،
    # وانقطع النصّ في منتصفه.
    "idea.prd": 8000,
    "research.competitors": 8000,
    "research.candidates": 8000,
}

#: (الدالة التي تحوّل الردّ، والدالة التي تكتب المخرجات) لكل قدرة.
_HANDLERS: dict[str, tuple[Callable[[str], Any], Callable[[Any, Path], Any]]] = {
    "idea.prd": (produce_prd, lambda result, root: write_prd(result, root)),
    "research.competitors": (
        produce_competitors,
        lambda result, root: write_competitors(result, root),
    ),
    "research.candidates": (
        produce_candidates,
        lambda result, root: write_candidates(result, root),
    ),
}


@dataclass(frozen=True)
class LiveOutcome:
    """نتيجة إنتاج حيّ."""

    capability: str
    provider: str
    model: str
    cost_usd: float
    tokens_in: int
    tokens_out: int
    elapsed_ms: int
    fallback_used: bool
    artefacts: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """صيغة قابلة للتسلسل في تقرير الجولة."""
        return {
            "capability": self.capability,
            "provider": self.provider,
            "model": self.model,
            "cost_usd": round(self.cost_usd, 8),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "elapsed_ms": self.elapsed_ms,
            "fallback_used": self.fallback_used,
            "artefacts": list(self.artefacts),
        }


def run_live(
    router: ModelRouter,
    capability: str,
    payload: dict[str, Any],
    root: str | Path,
) -> LiveOutcome:
    """يشغّل قدرةً حيةً واحدة ويُخرج artefactها.

    الفشل (لا مفتاح، أو ردّ مخالف للعقد، أو فشل كل النماذج) ⇒ استثناء
    صريح. **لا artefact ناقص، ولا artefact من ردّ لم يجتز الفحص.**
    """
    if capability not in PROMPT_BUILDERS:
        raise ValueError(
            f"قدرة حيّة غير معروفة: {capability}. "
            f"المعروفة: {'، '.join(sorted(PROMPT_BUILDERS))}."
        )
    builder, validator = PROMPT_BUILDERS[capability]
    prompt = builder(payload)

    started = time.perf_counter()
    result = router.run(
        CompletionRequest(
            capability=capability,
            prompt=prompt,
            max_output_tokens=MAX_OUTPUT_TOKENS[capability],
        )
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    # فحص مسبق بالمدقّق المرتبط بالقدرة: خطأ صريح باسم القدرة.
    parse_structured(result.text, validator)
    # ثم الإنتاج نفسه — وهو يفحص بنفس المدقّق مرّة أخرى.
    produce_fn, writer = _HANDLERS[capability]
    artefact = produce_fn(result.text)
    written = writer(artefact, Path(root))
    if isinstance(written, dict):
        paths = tuple(sorted(str(path) for path in written.values()))
    else:
        paths = (str(written),)

    return LiveOutcome(
        capability=capability,
        provider=result.provider,
        model=result.model,
        cost_usd=result.cost_usd,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        elapsed_ms=elapsed_ms,
        fallback_used=result.fallback_used,
        artefacts=paths,
    )
