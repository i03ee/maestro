"""مزوّد اختباري حتمي: لا شبكة، ولا عشوائية، ولا اعتماد على الوقت."""

from __future__ import annotations

from dataclasses import dataclass

from .base import CompletionRequest, CompletionResponse, ModelProfile


@dataclass
class ScriptedProvider:
    """مزوّد يُعاد توجيهه إلى سيناريوهات مُعدّة مسبقاً.

    كل عنصر في ``script`` إما ردّ جاهز أو استثناء يجب أن يُطلَق. عند نفاد
    السيناريو يُطلَق ``LookupError`` — لا قيمة افتراضية صامتة.
    """

    name: str
    script: list[CompletionResponse | Exception]
    calls: list[CompletionRequest] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.calls is None:
            self.calls = []

    def complete(self, request: CompletionRequest, profile: ModelProfile) -> CompletionResponse:
        self.calls.append(request)
        if not self.script:
            raise LookupError(f"لا يوجد سيناريو متبقٍ للمزوّد {self.name}")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
