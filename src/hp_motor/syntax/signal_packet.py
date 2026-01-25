# src/hp_motor/signal/signal_packet.py

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
import uuid

SignalType = Literal["event", "fitness", "track", "doc", "constraint"]
SignalStatus = Literal["OK", "DEGRADED", "BLOCKED"]
LogicGate = Literal["Popper_Verified", "Unverified_Hypothesis"]


@dataclass
class SpatialAnchor:
    x: float
    y: float
    z: Optional[float] = None
    space_id: Optional[str] = None


@dataclass
class TemporalAnchor:
    start_s: float
    end_s: float
    frame_id: Optional[int] = None


@dataclass
class SignalPacket:
    """
    HP Motor Universal Analytic Signal
    Her veri kaynağı bu forma çevrilmeden analiz yapılamaz.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    signal_type: SignalType = "event"

    provenance: Dict[str, Any] = field(default_factory=dict)
    # örn: {"filename": "...", "line": 42, "timestamp_raw": "00:34:21"}

    payload: Dict[str, Any] = field(default_factory=dict)
    # örn:
    # {
    #   "entity": "player_10",
    #   "metric": "HSR",
    #   "value": 7.8,
    #   "unit": "m/s"
    # }

    spatial_anchor: Optional[SpatialAnchor] = None
    temporal_anchor: Optional[TemporalAnchor] = None

    meta: Dict[str, Any] = field(default_factory=lambda: {
        "confidence": 0.5,
        "logic_gate": "Unverified_Hypothesis",
        "status": "DEGRADED"
    })

    def validate(self) -> None:
        """
        Temel emniyet denetimi.
        Eksik bağlam varsa sinyal BLOCKED olur.
        """
        if not self.payload:
            self.meta["status"] = "BLOCKED"

        if self.signal_type in ["event", "track"] and self.temporal_anchor is None:
            self.meta["status"] = "BLOCKED"

        if self.signal_type == "track" and self.spatial_anchor is None:
            self.meta["status"] = "BLOCKED"

    def promote(self) -> None:
        """
        Popper Gate sonrası çağrılır.
        """
        self.meta["logic_gate"] = "Popper_Verified"
        self.meta["status"] = "OK"
        self.meta["confidence"] = min(1.0, self.meta.get("confidence", 0.5) + 0.2)