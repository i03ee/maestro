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

    def render_prompt(self, intent: str, context: str = "") -> str:
        """يبني نص الطلب من النيّة والسياق.

        `context` هو حمولة `inputs` من مستند IR بصيغة JSON — الذي يجعل
        النموذج يعرف **ماذا** يحرّر. بلا سياق، المطالبة نيّة بلا بيانات،
        فيخترع النموذج ما لم يُعطَ إياه.
        """
        # استبدال نصّي لا `str.format`: قوالب المطالبة تحمل أقواس JSON
        # حرّةً، و`format` كان يظنّها رموزاً ويRaise.
        return (
            self.prompt_template_ar.replace("{intent}", intent).replace("{context}", context)
        )
