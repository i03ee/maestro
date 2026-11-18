"""حارس الميزانية: سقف صلب يُمنع عنده، لا نسبة تُسامح بها."""

from __future__ import annotations

from dataclasses import dataclass


class BudgetExceeded(RuntimeError):
    """تجاوز السقف: يُوقف التنفيذ ولا يُسقَط إلى نموذج أرخص."""


@dataclass
class BudgetGuard:
    """سقف تكلفة ورموز لمهمة واحدة.

    القاعدة: تجاوز السقف يوقف المسار كاملاً. الإسقاط إلى نموذج أرخص قرار
    تشغيلي، لا بديل عن رفض طلب يتجاوز ما اتُّفق عليه.
    """

    max_cost_usd: float = 1.0
    max_tokens: int = 100_000
    spent_cost_usd: float = 0.0
    spent_tokens: int = 0

    @property
    def remaining_cost_usd(self) -> float:
        return max(0.0, self.max_cost_usd - self.spent_cost_usd)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.spent_tokens)

    def authorize(self, estimated_cost_usd: float, estimated_tokens: int = 0) -> None:
        """يرفض الطلب إذا تجاوز التقدير السقف المتبقي."""
        if estimated_cost_usd > self.remaining_cost_usd:
            raise BudgetExceeded(
                f"التكلفة المقدّرة {estimated_cost_usd:.4f}$ تتجاوز المتبقي {self.remaining_cost_usd:.4f}$"
            )
        if estimated_tokens > self.remaining_tokens:
            raise BudgetExceeded(
                f"الرموز المقدّرة {estimated_tokens} تتجاوز المتبقي {self.remaining_tokens}"
            )

    def consume(self, cost_usd: float, tokens: int = 0) -> None:
    # noqa: D401 — ثبّت الاستهلاك بعد التنفيذ الفعلي.
        """تسجيل الاستهلاك الفعلي بعد تنفيذ الطلب."""
        self.spent_cost_usd += cost_usd
        self.spent_tokens += tokens
