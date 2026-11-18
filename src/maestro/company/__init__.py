"""الشركة: نطاقاتها وقدراتها وطوبولوجيا اعتمادها."""

from .catalogue import (
    CAPABILITIES,
    COMMUNITY_GATE,
    DOMAINS,
    GATE_INVOCATIONS,
    Capability,
    Domain,
    by_domain,
    capabilities,
    capability_by_name,
    critical_capabilities,
    domains,
    gated_capabilities,
    specialization_targets,
)
from .registry import build_registry, capability_to_ir
from .topology import Edge, check_catalogue, edges, topology_report

__all__ = [
    "CAPABILITIES",
    "COMMUNITY_GATE",
    "DOMAINS",
    "GATE_INVOCATIONS",
    "Capability",
    "Domain",
    "by_domain",
    "capabilities",
    "capability_by_name",
    "critical_capabilities",
    "domains",
    "gated_capabilities",
    "specialization_targets",
    "build_registry",
    "capability_to_ir",
    "Edge",
    "check_catalogue",
    "edges",
    "topology_report",
]
