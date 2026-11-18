"""بطاقة القدرة: ما تعرفه الشركة عن قدرة واحدة."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilitySpec:
    """تعريف قدرة واحدة داخل الشركة.

    ability واحدة = وكيل واحد. لا تُجمع قدرتان في بطاقة واحدة: البطاقة
    هي وحدة المسؤولية، ووحدة القياس، ووحدة المراجعة.
    """

    name: str
    description_ar: str
    required_tools: tuple[str, ...] = ()
    default_authority: int = 1
    critical: bool = False
    prompt_template_ar: str = "{intent}"

    def render_prompt(self, intent: str) -> str:
        """يبني نص الطلب من النيّة."""
        return self.prompt_template_ar.format(intent=intent)
