"""مثال «محرّك جديد» — يُضاف بلا تعديل النواة (AC-20).

هذا الملف **خارج** حزمة `maestro`: يُحمَّل من مساره، ويلتزم بواجهة
`Provider` وحدها. لو احتاج إضافة محرّك إلى تعديل نواة، فالواجهة ناقصة.

الاستعمال (كما يفعل شاهد القبول):
    import importlib.util
    spec = importlib.util.spec_from_file_location("minimal_provider", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = module.MinimalProvider()
"""

from maestro.routing.base import CompletionRequest, CompletionResponse, ModelProfile


class MinimalProvider:
    """مزوّد أبسط ما يمكن: يردّ بالطلب كما هو."""

    name = "minimal"

    def complete(self, request: CompletionRequest, profile: ModelProfile) -> CompletionResponse:
        """يردّ بالنص المطلوب مع بادئة تعريف."""
        return CompletionResponse(
            text=f"[{self.name}] {request.prompt}",
            tokens_in=max(1, len(request.prompt) // 4),
            tokens_out=max(1, len(request.prompt) // 4),
            model=profile.model,
        )
