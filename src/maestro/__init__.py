"""MAESTRO — نواة شركة الوكلاء.

المستودع هو **النواة**، وليس المنتج. أول تطبيق تنتجه الشركة هو مشروع
«نَسمة» (Nasma) — منصة تجارة جمال عراقية — وهو مستودع منفصل.
"""

from .version import __version__, SCHEMA_VERSION

__all__ = ["__version__", "SCHEMA_VERSION"]
