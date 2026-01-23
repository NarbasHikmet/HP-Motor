from __future__ import annotations

from typing import Any, Dict


class ProtocolManager:
    """
    Protokol 1-10: v1 iskeleti.
    Her protokol falsifiable olmalı: girdi sinyali -> karar/flag.
    """

    def run_all(self, event: Dict[str, Any], h_score: float, bio: Dict[str, Any]) -> Dict[str, Any]:
        out = {"P": {}, "summary": {}}

        out["P"]["P1_data_integrity"] = self.p1_data_integrity(event)
        out["P"]["P2_regime_gate"] = self.p2_regime_gate(h_score)
        out["P"]["P3_bio_gate"] = self.p3_bio_gate(bio)
        out["P"]["P4_risk_pass_gate"] = self.p4_risk_pass_gate(event, h_score)
        out["P"]["P5_transition_alarm"] = self.p5_transition_alarm(event, h_score)

        # v1: toplam karar
        flags = [k for k, v in out["P"].items() if isinstance(v, dict) and v.get("flag") is True]
        out["summary"] = {
            "flags": flags,
            "flag_count": len(flags),
            "h_score": float(h_score),
            "bio_status": bio.get("status", "UNKNOWN"),
        }
        return out

    def p1_data_integrity(self, event: Dict[str, Any]) -> Dict[str, Any]:
        required = ["event_type"]
        missing = [k for k in required if k not in event or event[k] in (None, "")]
        return {
            "flag": len(missing) > 0,
            "missing": missing,
            "message": "data integrity ok" if not missing else "missing required fields",
        }

    def p2_regime_gate(self, h_score: float) -> Dict[str, Any]:
        return {
            "flag": bool(h_score >= 0.80),
            "message": "chaos ceiling breach" if h_score >= 0.80 else "regime within bounds",
        }

    def p3_bio_gate(self, bio: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "flag": bool(bio.get("status") == "ALARM"),
            "message": bio.get("alarm") or "bio stable",
            "alignment": bio.get("alignment"),
        }

    def p4_risk_pass_gate(self, event: Dict[str, Any], h_score: float) -> Dict[str, Any]:
        et = str(event.get("event_type", "")).lower()
        risky = bool(event.get("is_risky")) or (str(event.get("pass_type", "")).lower() in ("through_ball", "line_break"))
        flag = (et == "pass") and risky and (h_score >= 0.60)
        return {
            "flag": flag,
            "message": "risky pass in chaos regime" if flag else "pass risk ok",
        }

    def p5_transition_alarm(self, event: Dict[str, Any], h_score: float) -> Dict[str, Any]:
        et = str(event.get("event_type", "")).lower()
        flag = (et in ("turnover", "ball_lost", "dispossessed")) and (h_score >= 0.65)
        return {
            "flag": flag,
            "message": "turnover in chaos -> transition alarm" if flag else "no transition alarm",
        }