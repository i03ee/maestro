"""طبقة التشغيل: قدرة واحدة، وكيل واحد، جزء واحد."""

from .registry import CapabilityRegistry, CapabilitySpec
from .runner import CapabilityRunner, ExecutionReport

__all__ = ["CapabilityRegistry", "CapabilitySpec", "CapabilityRunner", "ExecutionReport"]
