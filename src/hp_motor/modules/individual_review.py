from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


@dataclass
class FieldStatus:
    value: Any
    status: str  # OK | DEGRADED | ABSTAINED
    note: str


def _first_existing_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_mean(series: pd.Series) -> Optional[float]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    return float(s.mean())


def _safe_pct(numer: float, denom: float) -> Optional[float]:
    if denom <= 0:
        return None
    return float(numer / denom * 100.0)


def _pick_time_col(df: pd.DataFrame) -> Optional[str]:
    return _first_existing_col(df, ["timestamp", "time", "seconds", "sec", "ts"])


def _pick_event_type_col(df: pd.DataFrame) -> Optional[str]:
    return _first_existing_col(df, ["event_type", "type", "action", "event"])


def _pick_outcome_col(df: pd.DataFrame) -> Optional[str]:
    return _first_existing_col(df, ["outcome", "result", "success", "is_success"])


def _as_bool_success(val: Any) -> Optional[bool]:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in {"1", "true", "t", "yes", "y", "success", "successful", "won"}:
        return True
    if s in {"0", "false", "f", "no", "n", "fail", "failed", "unsuccessful", "lost"}:
        return False
    return None


class IndividualAnalysisV22:
    """
    HP ENGINE v22.x — canonical individual player analysis module.

    Policy:
      - Never invent missing data.
      - Each field carries status:
          OK / DEGRADED / ABSTAINED
      - Produces:
          - individual analysis template dict
          - derived scouting card dict
          - derived role mismatch alarm checklist skeleton (data-driven parts if possible)

    Data expectations (optional; best-effort):
      - player_id
      - event_type/type/action
      - outcome/success
      - timestamp/time/sec
      - x,y (for zone heuristics)
      - pressure (0/1 or numeric)
    """

    def __init__(self, engine_version: str = "HP ENGINE v22.x"):
        self.engine_version = engine_version

    # ---------------------------
    # Public API
    # ---------------------------
    def generate_for_player(
        self,
        df: pd.DataFrame,
        player_id: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = context or {}

        pdf = df[df["player_id"] == player_id] if "player_id" in df.columns else df.copy()

        # Numeric profile (per 90) — only if we can infer minutes
        per90 = self._per90_profile(pdf)

        # Decision proxies
        decision = self._decision_proxies(pdf)

        # Tactical map proxies (very lightweight)
        tactical = self._tactical_effect(pdf)

        # Biomech/orientation — proxy only (do not hallucinate)
        biomech = self._biomech_proxy(pdf)

        # Psychological profile — requires human input; mark as ABSTAINED
        psych = self._psych_stub()

        # Coaching notes — derived only when we have signals; else degraded
        coaching = self._coaching_notes(pdf, tactical, decision)

        # Risk analysis — partially derived
        risk = self._risk_analysis(pdf, tactical, decision, biomech)

        # System fit — cannot compute without team model; ABSTAINED
        fit = self._system_fit_stub()

        analysis = {
            "meta": {
                "player_name": context.get("player_name", FieldStatus(None, "ABSTAINED", "Not provided").__dict__),
                "club": context.get("club", FieldStatus(None, "ABSTAINED", "Not provided").__dict__),
                "league": context.get("league", FieldStatus(None, "ABSTAINED", "Not provided").__dict__),
                "season": context.get("season", FieldStatus(None, "ABSTAINED", "Not provided").__dict__),
                "analyst": context.get("analyst", FieldStatus(None, "ABSTAINED", "Not provided").__dict__),
                "analysis_date": context.get("analysis_date", FieldStatus(None, "ABSTAINED", "Not provided").__dict__),
                "engine_version": self.engine_version,
            },
            "player_id": {"value": player_id, "status": "OK", "note": "player_id from data"},
            "player_identity": self._identity_stub(context),
            "role_definition": self._role_stub(context),
            "numerical_profile_per90": per90,
            "biomechanic_body_logic": biomech,
            "decision_tree": decision,
            "tactical_effect_map": tactical,
            "psychological_profile": psych,
            "coaching_notes": coaching,
            "risk_analysis": risk,
            "system_fit_score": fit,
            "executive_summary": self._executive_summary(per90, decision, tactical, risk),
        }

        scouting = self._derive_scouting_card(analysis)
        alarm = self._derive_role_mismatch_alarm(analysis)

        return {
            "individual_analysis_v22": analysis,
            "scouting_card": scouting,
            "role_mismatch_alarm": alarm,
        }

    # ---------------------------
    # Building blocks
    # ---------------------------
    def _identity_stub(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Mostly human-provided
        def f(key: str) -> Dict[str, Any]:
            v = context.get(key)
            if v is None:
                return FieldStatus(None, "ABSTAINED", "Not provided").__dict__
            return FieldStatus(v, "OK", "Provided").__dict__

        return {
            "age": f("age"),
            "height_weight": f("height_weight"),
            "dominant_foot": f("dominant_foot"),
            "primary_position": f("primary_position"),
            "secondary_positions": f("secondary_positions"),
            "career_stage": f("career_stage"),
            "one_line_definition": f("one_line_definition"),
        }

    def _role_stub(self, context: Dict[str, Any]) -> Dict[str, Any]:
        def f(key: str) -> Dict[str, Any]:
            v = context.get(key)
            if v is None:
                return FieldStatus(None, "ABSTAINED", "Not provided").__dict__
            return FieldStatus(v, "OK", "Provided").__dict__

        return {
            "primary_role": f("primary_role"),
            "secondary_role": f("secondary_role"),
            "unsuitable_roles": f("unsuitable_roles"),
            "role_freedom_level": f("role_freedom_level"),
        }

    def _infer_minutes(self, df: pd.DataFrame) -> Tuple[Optional[float], str]:
        """
        Best-effort minutes inference:
          - If timestamp exists: (max - min) / 60
          - Else ABSTAIN
        """
        tcol = _pick_time_col(df)
        if not tcol:
            return None, "No time/timestamp column to infer minutes."
        s = pd.to_numeric(df[tcol], errors="coerce").dropna()
        if s.empty:
            return None, "Time column exists but no numeric values."
        minutes = (float(s.max()) - float(s.min())) / 60.0
        if minutes <= 0:
            return None, "Non-positive inferred duration."
        return minutes, "Inferred from timestamp span."

    def _per90_profile(self, df: pd.DataFrame) -> Dict[str, Any]:
        minutes, note = self._infer_minutes(df)
        if minutes is None:
            return {
                "status": "ABSTAINED",
                "note": note,
                "metrics": {},
            }

        factor = 90.0 / minutes

        etcol = _pick_event_type_col(df)
        outcol = _pick_outcome_col(df)

        # Heuristic event counting
        def count_events(names: List[str]) -> float:
            if not etcol:
                return 0.0
            s = df[etcol].astype(str).str.lower()
            return float(s.isin([n.lower() for n in names]).sum())

        shots = count_events(["shot", "shots", "finish", "finishing"])
        key_pass = count_events(["key_pass", "key pass", "through_ball", "chance_created", "assist"])
        dribbles = count_events(["dribble", "take_on", "takeon", "carry_dribble"])
        turnovers = count_events(["turnover", "dispossessed", "lost_ball", "bad_touch"])

        # Dribble success % if outcome exists
        dribble_success_pct: Optional[float] = None
        if etcol and outcol:
            dr = df[df[etcol].astype(str).str.lower().isin(["dribble", "take_on", "takeon", "carry_dribble"])]
            if not dr.empty:
                succ = dr[outcol].apply(_as_bool_success).dropna()
                if not succ.empty:
                    dribble_success_pct = _safe_pct(float(succ.sum()), float(len(succ)))

        xg = _safe_mean(df["xg"]) if "xg" in df.columns else None
        xa = _safe_mean(df["xa"]) if "xa" in df.columns else None

        metrics = {
            "xg_per90": xg * factor if xg is not None else None,
            "xa_per90": xa * factor if xa is not None else None,
            "key_passes_per90_proxy": key_pass * factor,
            "shots_per90_proxy": shots * factor,
            "dribbles_per90_proxy": dribbles * factor,
            "turnovers_per90_proxy": turnovers * factor,
            "dribble_success_pct_proxy": dribble_success_pct,
        }

        degraded = []
        if etcol is None:
            degraded.append("event_type_missing")
        if outcol is None:
            degraded.append("outcome_missing (dribble success cannot be computed)")

        status = "OK" if not degraded else "DEGRADED"
        return {
            "status": status,
            "note": f"{note}" + (f" Degraded: {', '.join(degraded)}" if degraded else ""),
            "metrics": metrics,
        }

    def _decision_proxies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Decision speed:
          - Use compute_decision_speed-style proxy if timestamps exist.
          - Pressure-conditioned proxy if 'pressure' column exists.

        Scanning:
          - Not directly inferable from event data; ABSTAIN unless explicit 'scan_count' exists.
        """
        tcol = _pick_time_col(df)
        pcol = _first_existing_col(df, ["pressure", "is_pressure", "under_pressure"])

        if not tcol:
            return {
                "status": "ABSTAINED",
                "note": "No timestamp column; decision speed proxy cannot be computed.",
                "most_common_actions": FieldStatus(None, "DEGRADED", "event_type may be missing").__dict__,
                "under_pressure_behavior": FieldStatus(None, "ABSTAINED", "Requires pressure + outcome context").__dict__,
                "proxies": {},
            }

        # decision speed proxy: mean delta between consecutive events (seconds)
        s = pd.to_numeric(df[tcol], errors="coerce").dropna().sort_values()
        if len(s) < 2:
            return {
                "status": "ABSTAINED",
                "note": "Insufficient timestamp density to compute deltas.",
                "most_common_actions": FieldStatus(None, "DEGRADED", "event_type may be missing").__dict__,
                "under_pressure_behavior": FieldStatus(None, "ABSTAINED", "Requires pressure + outcome context").__dict__,
                "proxies": {},
            }

        deltas = s.diff().dropna()
        mean_dt = float(deltas.mean())

        proxies: Dict[str, Any] = {
            "decision_speed_sec_proxy": mean_dt,
        }

        status = "OK"
        note = "Decision speed computed from timestamp deltas (proxy)."

        if pcol:
            ps = pd.to_numeric(df[pcol], errors="coerce")
            if ps.notna().sum() > 0:
                # treat >0 as pressured
                pressured_mask = ps.fillna(0) > 0
                ts = pd.to_numeric(df[tcol], errors="coerce")
                t_press = ts[pressured_mask].dropna().sort_values()
                if len(t_press) >= 2:
                    proxies["decision_speed_under_pressure_sec_proxy"] = float(t_press.diff().dropna().mean())
                else:
                    proxies["decision_speed_under_pressure_sec_proxy"] = None
                    status = "DEGRADED"
                    note += " Pressure column exists but pressured timestamps insufficient."
            else:
                status = "DEGRADED"
                note += " Pressure column exists but non-numeric."

        # Most common actions
        etcol = _pick_event_type_col(df)
        if etcol:
            vc = df[etcol].astype(str).value_counts().head(5).to_dict()
            actions = FieldStatus(vc, "OK", "Top-5 action labels by frequency.").__dict__
        else:
            actions = FieldStatus(None, "DEGRADED", "Missing event_type column.").__dict__

        # Under pressure behavior (very rough): turnovers under pressure
        under_pressure = FieldStatus(None, "ABSTAINED", "Requires event_type+pressure mapping for robust claim.").__dict__
        if etcol and pcol:
            pressured_mask = pd.to_numeric(df[pcol], errors="coerce").fillna(0) > 0
            s_evt = df[etcol].astype(str).str.lower()
            turnovers = s_evt.isin(["turnover", "dispossessed", "lost_ball", "bad_touch"])
            n = int((pressured_mask & turnovers).sum())
            under_pressure = FieldStatus(
                {"turnovers_under_pressure_proxy": n},
                "DEGRADED",
                "Proxy count; depends on provider labels.",
            ).__dict__

        return {
            "status": status,
            "note": note,
            "most_common_actions": actions,
            "under_pressure_behavior": under_pressure,
            "proxies": proxies,
        }

    def _tactical_effect(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Very lightweight spatial/zone proxy:
          - Requires x,y columns. If missing -> ABSTAINED.
        """
        if not {"x", "y"}.issubset(df.columns):
            return {
                "status": "ABSTAINED",
                "note": "No x/y columns; cannot infer zones or productive areas.",
                "efficient_zones": FieldStatus(None, "ABSTAINED", "No spatial data.").__dict__,
                "inefficient_zones": FieldStatus(None, "ABSTAINED", "No spatial data.").__dict__,
                "box_contribution_type": FieldStatus(None, "ABSTAINED", "No spatial data.").__dict__,
                "production_geometry": FieldStatus(None, "ABSTAINED", "No spatial data.").__dict__,
            }

        x = pd.to_numeric(df["x"], errors="coerce")
        y = pd.to_numeric(df["y"], errors="coerce")
        valid = x.notna() & y.notna()
        if valid.sum() == 0:
            return {
                "status": "ABSTAINED",
                "note": "x/y exist but no numeric values.",
                "efficient_zones": FieldStatus(None, "ABSTAINED", "No spatial data.").__dict__,
                "inefficient_zones": FieldStatus(None, "ABSTAINED", "No spatial data.").__dict__,
                "box_contribution_type": FieldStatus(None, "ABSTAINED", "No spatial data.").__dict__,
                "production_geometry": FieldStatus(None, "ABSTAINED", "No spatial data.").__dict__,
            }

        # crude zones: thirds by x
        xq = x[valid]
        bins = pd.cut(xq, bins=[-1e9, 33.3, 66.6, 1e9], labels=["def_third", "mid_third", "att_third"])
        counts = bins.value_counts().to_dict()

        # Half-space proxy by y (assuming 0..100 scale; if not, still relative)
        yq = y[valid]
        half_space = ((yq > yq.quantile(0.33)) & (yq < yq.quantile(0.66))).sum()
        wide = (yq <= yq.quantile(0.33)).sum() + (yq >= yq.quantile(0.66)).sum()

        efficient = FieldStatus(
            {"third_counts": counts, "half_space_touch_proxy": int(half_space)},
            "DEGRADED",
            "Proxy zoning; depends on coordinate system.",
        ).__dict__

        inefficient = FieldStatus(
            {"wide_touch_proxy": int(wide)},
            "DEGRADED",
            "Proxy; depends on coordinate system.",
        ).__dict__

        return {
            "status": "DEGRADED",
            "note": "Zone inference is proxy-level. Coordinate system must be standardized for strong claims.",
            "efficient_zones": efficient,
            "inefficient_zones": inefficient,
            "box_contribution_type": FieldStatus(None, "ABSTAINED", "Needs box definition + event labels.").__dict__,
            "production_geometry": FieldStatus(None, "ABSTAINED", "Needs shot/pass endpoints.").__dict__,
        }

    def _biomech_proxy(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Biomech/orientation is not reliably inferrable from basic event logs.
        If 'orientation_deg' or similar exists, we can produce a degraded proxy.
        """
        angle_col = _first_existing_col(
            df,
            ["orientation_deg", "body_orientation_deg", "body_angle_deg", "hips_angle_deg", "stance_angle_deg"],
        )
        if not angle_col:
            return {
                "status": "ABSTAINED",
                "note": "No orientation angle columns; body logic section requires video/tracking or explicit angle signals.",
                "somatotype": FieldStatus(None, "ABSTAINED", "Human input required.").__dict__,
                "explosiveness": FieldStatus(None, "ABSTAINED", "Human input required.").__dict__,
                "max_speed": FieldStatus(None, "ABSTAINED", "Tracking required.").__dict__,
                "repeat_sprint": FieldStatus(None, "ABSTAINED", "Tracking required.").__dict__,
                "stamina": FieldStatus(None, "ABSTAINED", "Tracking required.").__dict__,
                "injury_history": FieldStatus(None, "ABSTAINED", "Medical history required.").__dict__,
                "orientation_notes": FieldStatus(None, "ABSTAINED", "No orientation telemetry.").__dict__,
            }

        mean_angle = _safe_mean(df[angle_col])
        return {
            "status": "DEGRADED",
            "note": f"Orientation proxy computed from {angle_col} mean. Provider semantics may vary.",
            "somatotype": FieldStatus(None, "ABSTAINED", "Human input required.").__dict__,
            "explosiveness": FieldStatus(None, "ABSTAINED", "Human input required.").__dict__,
            "max_speed": FieldStatus(None, "ABSTAINED", "Tracking required.").__dict__,
            "repeat_sprint": FieldStatus(None, "ABSTAINED", "Tracking required.").__dict__,
            "stamina": FieldStatus(None, "ABSTAINED", "Tracking required.").__dict__,
            "injury_history": FieldStatus(None, "ABSTAINED", "Medical history required.").__dict__,
            "orientation_notes": FieldStatus(
                {"mean_angle_deg_proxy": mean_angle, "angle_col": angle_col},
                "DEGRADED",
                "Angle-based proxy only.",
            ).__dict__,
        }

    def _psych_stub(self) -> Dict[str, Any]:
        return {
            "status": "ABSTAINED",
            "note": "Psych profile requires coach/analyst input; not inferable from event logs.",
            "role_clarity_need": FieldStatus(None, "ABSTAINED", "Human input required.").__dict__,
            "freedom_tolerance": FieldStatus(None, "ABSTAINED", "Human input required.").__dict__,
            "post_error_reaction": FieldStatus(None, "ABSTAINED", "Human input required.").__dict__,
            "confidence_performance_link": FieldStatus(None, "ABSTAINED", "Human input required.").__dict__,
        }

    def _coaching_notes(self, df: pd.DataFrame, tactical: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        notes: List[str] = []

        # If many turnovers under pressure proxy exists, suggest support
        upb = decision.get("under_pressure_behavior", {})
        if isinstance(upb, dict) and upb.get("value") and isinstance(upb["value"], dict):
            n = upb["value"].get("turnovers_under_pressure_proxy")
            if isinstance(n, int) and n >= 2:
                not