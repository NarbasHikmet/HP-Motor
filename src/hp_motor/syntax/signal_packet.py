from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SpatialAnchor:
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    zone_id: Optional[str] = None
    space_id: Optional[str] = None


@dataclass
class TemporalAnchor:
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    frame_id: Optional[int] = None


@dataclass
class Provenance:
    source_file: str
    source_line: Optional[int] = None
    raw_timestamp: Optional[str] = None


@dataclass
class Payload:
    entity: str
    metric: str
    value: Any
    unit: Optional[str] = None


@dataclass
class Meta:
    confidence: float = 1.0
    logic_gate: str = "Unverified_Hypothesis"  # Unverified_Hypothesis | Popper_Verified
    status: str = "OK"  # OK | DEGRADED | BLOCKED
    logic_notes: Optional[str] = None


@dataclass
class SignalPacket:
    """
    HP Motor Universal Transport: SignalPacket (SSOT runtime object)
    """
    id: str
    signal_type: str  # event | fitness | track | doc | constraint
    provenance: Provenance
    payload: Payload

    spatial_anchor: Optional[SpatialAnchor] = None
    temporal_anchor: Optional[TemporalAnchor] = None
    meta: Meta = field(default_factory=Meta)

    # No Silent Drop: keep raw for traceability
    raw: Optional[Dict[str, Any]] = None