"""تشغيل غير متزامن من داخل واجهة متزامنة.

طبقة الوكلاء (PydanticAI) غير متزامنة أصلاً، بينما واجهة `Provider` في
النواة متزامنة. هذا الجسر هو الحدّ الفاصل.

قاعدة: لا يُستدعى من داخل حلقة أحداث قائمة — الخطأ يُبلَّغ صراحةً بدل أن
يُنتج طلباً نصف معلّق.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class AgentLayerError(RuntimeError):
    """خطأ في طبقة الوكلاء: إعداد خاطئ أو استدعاء في غير موضعه."""


def run_sync(factory: Callable[[], Any]) -> Any:
    """ينفّذ عملية غير متزامنة حتى تمامها، من خارج حلقة أحداث."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())
    raise AgentLayerError(
        "طبقة الوكلاء لا تُستدعى من داخل حلقة أحداث قائمة؛ استدعِها من مسار متزامن."
    )
