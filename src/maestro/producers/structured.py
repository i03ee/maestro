""" parsing منظَّم: ردّ النموذج ⇒ كائن مُتحقَّق منه.

القاعدة: الردّ يُحلَّل مرة واحدة، ويُفحص بمُدقِّق (callable) يعيد قائمة
مشاكل. أي مشكلة ⇒ **لا artefact**. لا ملء بالتخمين ولا قبول جزئي.
"""

from __future__ import annotations

import json
from typing import Any, Callable

Validator = Callable[[Any], list[str]]


class StructuredResponseError(ValueError):
    """ردّ النموذج لا يطابق العقد."""


def parse_structured(text: str, validator: Validator) -> Any:
    """يحلّل الردّ ويفحصه. أي خلل ⇒ استثناء."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise StructuredResponseError(f"الردّ ليس JSON صالحاً: {error}") from error
    problems = validator(data)
    if problems:
        raise StructuredResponseError("؛ ".join(problems))
    return data
