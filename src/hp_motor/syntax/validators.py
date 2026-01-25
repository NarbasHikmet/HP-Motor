from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .signal_packet import SignalPacket


@dataclass(frozen=True)
class ValidationReport:
    status: str  # HEALTHY / DEGRADED / BLOCKED
    issues: List[Dict[str, Any]]


class SOTPacketValidator:
    """
    Minimal SOT discipline for SignalPacket:
      - No silent drops: packets remain, but can be marked DEGRADED/BLOCKED.
      - Unit sanity: metric without unit for numeric values -> DEGRADED (unless metric is known unitless).
      - Temporal sanity: if temporal required by metric family but missing -> DEGRADED.
    """

    UNITLESS_METRICS = {
        "PPDA", "FieldTilt", "xT", "PackingRate",
        "Pass_Acc", "Duel_Success", "Aerial_Success",
        "TSI_PACE", "TSI_BURST", "TSI_TRANSITION", "TSI_DUEL", "TSI_AERIAL", "TSI_STABILITY", "TSI_OVERALL",
    }

    def validate(self, packets: List[SignalPacket]) -> Tuple[ValidationReport, List[SignalPacket]]:
        issues: List[Dict[str, Any]] = []
        status = "HEALTHY"

        for p in packets:
            p.set_meta_defaults()

            # numeric without unit (unless unitless metric)
            is_numeric = isinstance(p.payload.value, (int, float))
            if is_numeric and (not p.payload.unit) and (p.payload.metric not in self.UNITLESS_METRICS):
                p.mark("DEGRADED", note="UNIT_MISSING: numeric payload without unit.")
                status = "DEGRADED"
                issues.append({"code": "UNIT_MISSING", "packet_id": p.id, "metric": p.payload.metric})

            # temporal required for event/track/fitness
            if p.signal_type in ("event", "track", "fitness"):
                if p.temporal_anchor is None or p.temporal_anchor.start_s is None:
                    p.mark("DEGRADED", note="TIME_MISSING: temporal anchor missing for time-dependent signal.")
                    status = "DEGRADED"
                    issues.append({"code": "TIME_MISSING", "packet_id": p.id, "signal_type": p.signal_type})

            # spatial required for track-like signals
            if p.signal_type in ("track",) and p.spatial_anchor is None:
                p.mark("DEGRADED", note="SPACE_MISSING: spatial anchor missing for track signal.")
                status = "DEGRADED"
                issues.append({"code": "SPACE_MISSING", "packet_id": p.id})

        return ValidationReport(status=status, issues=issues), packets


class PopperContradictionGate:
    """
    Minimal contradiction detector (v0):
      - Example rule: If a player has "HighPressIntent=1" from doc/constraint but fitness shows very low HSR
        in same window -> mark DEGRADED, logic_gate stays Unverified.
    This is a scaffold. You will expand with real cross-evidence rules.
    """

    def verify(self, packets: List[SignalPacket]) -> Tuple[ValidationReport, List[SignalPacket]]:
        issues: List[Dict[str, Any]] = []
        status = "HEALTHY"

        # naive indexes
        # entity -> list packets
        by_entity: Dict[str, List[SignalPacket]] = {}
        for p in packets:
            by_entity.setdefault(p.payload.entity, []).append(p)

        for entity, ps in by_entity.items():
            # Find intent constraints
            intents = [p for p in ps if p.signal_type in ("doc", "constraint") and str(p.payload.metric).lower() in ("intent", "press_intent", "high_press_intent")]
            # Find HSR
            hsr = [p for p in ps if str(p.payload.metric).upper() == "HSR" and isinstance(p.payload.value, (int, float))]

            if intents and hsr:
                # If any intent says aggressive/high and HSR extremely low -> contradiction candidate
                for i in intents:
                    intent_val = str(i.payload.value).lower()
                    if intent_val in ("high", "aggressive", "1", "true"):
                        for h in hsr:
                            if float(h.payload.value) <= 0.1:  # placeholder threshold
                                # mark both
                                i.mark("DEGRADED", logic_gate="Unverified_Hypothesis", note="POPPER_CONTRADICTION: high press intent vs very low HSR.")
                                h.mark("DEGRADED", logic_gate="Unverified_Hypothesis", note="POPPER_CONTRADICTION: very low HSR vs declared high intent.")
                                status = "DEGRADED"
                                issues.append({"code": "POPPER_CONTRADICTION", "entity": entity, "intent_packet": i.id, "hsr_packet": h.id})

        # Promote packets with no contradiction + healthy SOT
        if status == "HEALTHY":
            for p in packets:
                p.set_meta_defaults()
                # if packet not already degraded/blocked, mark as verified
                if p.meta.get("status") == "OK":
                    p.meta["logic_gate"] = "Popper_Verified"
                    p.meta["confidence"] = max(float(p.meta.get("confidence", 0.5)), 0.7)

        return ValidationReport(status=status, issues=issues), packets