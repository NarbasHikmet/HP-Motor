from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


# ============================================================
# Existing soft-gate result (kept for backward compatibility)
# ============================================================

@dataclass
class BiomechGateResult:
    ok: bool
    confidence_band: str  # low | medium | high
    supporting: List[str]
    contradicting: List[str]
    note: str
    issues: List[Dict[str, Any]]


# ============================================================
# Added verdict-style output (imported from the duplicate tree)
# ============================================================

@dataclass
class BiomechanicVerdict:
    metric_id: str
    value: Optional[float]
    status: str
    note: str
    evidence: Dict[str, Any]


class BiomechanicGate:
    """
    Biomechanic / orientation gate (soft).

    v1 policy:
      - Never blocks execution unless df is empty (handled upstream).
      - Produces confidence adjustments + explicit limitations.
      - If columns exist, uses them; otherwise degrades confidence and writes notes.

    Expected (optional) columns:
      - defender_side_on_score (0..1)
      - square_on_rate (0..1)
      - channeling_to_wing_rate (0..1)
      - body_orientation_open (0/1)
      - reception_open (0/1)

    v1.1 additions (kayıpsız birleşim):
      - validate_defender_45_degree(): angle-based 45° side-on proxy (provider-variance tolerant)
      - validate_half_turn_receiving(): angle-based half-turn / open-body proxy
      - These methods ABSTAIN if no usable angle column exists.
    """

    # Provider variance: multiple possible names for a body-angle column
    ANGLE_COL_CANDIDATES: List[str] = [
        "orientation_deg",
        "body_orientation_deg",
        "body_angle_deg",
        "hips_angle_deg",
        "stance_angle_deg",
        "player_body_angle_deg",
    ]

    # ------------------------------------------------------------
    # PRIMARY API (already used by the project): evaluate()
    # Keep semantics intact.
    # ------------------------------------------------------------
    def evaluate(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or df.empty:
            return BiomechGateResult(
                ok=False,
                confidence_band="low",
                supporting=[],
                contradicting=[],
                note="empty_df",
                issues=[{"code": "DF_EMPTY", "severity": "ERROR", "message": "Input dataframe is empty."}],
            ).__dict__

        cols = set(df.columns)

        has_orientation = any(
            c in cols
            for c in [
                "defender_side_on_score",
                "square_on_rate",
                "channeling_to_wing_rate",
                "body_orientation_open",
                "reception_open",
            ]
        )

        issues: List[Dict[str, Any]] = []
        supporting: List[str] = []
        contradicting: List[str] = []

        if not has_orientation:
            issues.append(
                {
                    "code": "NO_ORIENTATION_SIGNALS",
                    "severity": "WARN",
                    "message": "No orientation/biomech proxy columns found. Video/tracking is required for strong claims.",
                }
            )
            return BiomechGateResult(
                ok=True,
                confidence_band="low",
                supporting=[],
                contradicting=[],
                note="no_orientation_columns",
                issues=issues,
            ).__dict__

        # If signals exist, check plausibility (0..1 range rates)
        plaus_ok = True
        for c in ["defender_side_on_score", "square_on_rate", "channeling_to_wing_rate"]:
            if c in cols:
                s = pd.to_numeric(df[c], errors="coerce")

                if s.notna().sum() == 0:
                    issues.append({"code": "ORIENT_ALL_NAN", "severity": "WARN", "message": f"{c} exists but all NaN."})
                    plaus_ok = False
                else:
                    oob = int(((s < 0) | (s > 1)).fillna(False).sum())
                    if oob > 0:
                        issues.append(
                            {
                                "code": "ORIENT_OOB",
                                "severity": "WARN",
                                "message": f"{c} has {oob} values outside 0..1; check provider mapping.",
                            }
                        )
                        plaus_ok = False
                    else:
                        supporting.append(c)

        band = "high" if plaus_ok and len(supporting) >= 2 else "medium"
        note = "orientation_signals_present" if supporting else "orientation_columns_present_but_weak"

        return BiomechGateResult(
            ok=True,
            confidence_band=band,
            supporting=supporting,
            contradicting=contradicting,
            note=note,
            issues=issues,
        ).__dict__

    # ------------------------------------------------------------
    # v1.1 additions (from the smaller/alternate file): angle verdicts
    # ------------------------------------------------------------
    def _find_angle_col(self, df: pd.DataFrame) -> Optional[str]:
        for c in self.ANGLE_COL_CANDIDATES:
            if c in df.columns:
                return c
        return None

    def validate_defender_45_degree(
        self,
        df: pd.DataFrame,
        defender_id: Optional[int] = None,
        ideal_deg: float = 45.0,
        square_on_min: float = 75.0,
        square_on_max: float = 105.0,
        elite_band: float = 15.0,
    ) -> BiomechanicVerdict:
        """
        If angle is near 45° (+/- elite_band) => ELITE_SIDE_ON
        If angle is in [square_on_min, square_on_max] => SQUARE_ON_RISK
        Otherwise => NEUTRAL

        ABSTAIN if no usable angle column exists.
        """
        angle_col = self._find_angle_col(df)
        if angle_col is None:
            return BiomechanicVerdict(
                metric_id="defense_45deg_gate",
                value=None,
                status="ABSTAINED",
                note="Angle column not found; cannot assess 45° rule.",
                evidence={"needed_one_of": self.ANGLE_COL_CANDIDATES},
            )

        data = df
        if defender_id is not None and "player_id" in df.columns:
            data = df[df["player_id"] == defender_id]

        if data.empty:
            return BiomechanicVerdict(
                metric_id="defense_45deg_gate",
                value=None,
                status="ABSTAINED",
                note="No rows for defender_id; cannot assess.",
                evidence={"defender_id": defender_id},
            )

        s = pd.to_numeric(data[angle_col], errors="coerce").dropna()
        if s.empty:
            return BiomechanicVerdict(
                metric_id="defense_45deg_gate",
                value=None,
                status="ABSTAINED",
                note="Angle values are non-numeric or missing.",
                evidence={"angle_col": angle_col},
            )

        avg_angle = float(s.mean())

        if abs(avg_angle - ideal_deg) <= elite_band:
            status = "ELITE_SIDE_ON"
            note = "45° side-on band detected (good for channeling + forward control)."
        elif square_on_min <= avg_angle <= square_on_max:
            status = "SQUARE_ON_RISK"
            note = "Square-on band detected (risk: getting pinned / limited turning window)."
        else:
            status = "NEUTRAL"
            note = "Angle not in elite 45° band nor square-on risk band."

        return BiomechanicVerdict(
            metric_id="defense_45deg_gate",
            value=avg_angle,
            status=status,
            note=note,
            evidence={
                "angle_col": angle_col,
                "ideal_deg": ideal_deg,
                "elite_band": elite_band,
                "square_on_band": [square_on_min, square_on_max],
            },
        )

    def validate_half_turn_receiving(
        self,
        df: pd.DataFrame,
        player_id: Optional[int] = None,
        open_min: float = 90.0,
        open_max: float = 130.0,
        closed_max: float = 60.0,
    ) -> BiomechanicVerdict:
        """
        Half-turn proxy:
          - avg angle in [open_min, open_max] => OPEN_HALF_TURN
          - avg angle <= closed_max => CLOSED_BODY_RISK
          - else => NEUTRAL

        ABSTAIN if no usable angle column exists.
        """
        angle_col = self._find_angle_col(df)
        if angle_col is None:
            return BiomechanicVerdict(
                metric_id="half_turn_gate",
                value=None,
                status="ABSTAINED",
                note="Angle column not found; cannot assess half-turn.",
                evidence={"needed_one_of": self.ANGLE_COL_CANDIDATES},
            )

        data = df
        if player_id is not None and "player_id" in df.columns:
            data = df[df["player_id"] == player_id]

        if data.empty:
            return BiomechanicVerdict(
                metric_id="half_turn_gate",
                value=None,
                status="ABSTAINED",
                note="No rows for player_id; cannot assess.",
                evidence={"player_id": player_id},
            )

        s = pd.to_numeric(data[angle_col], errors="coerce").dropna()
        if s.empty:
            return BiomechanicVerdict(
                metric_id="half_turn_gate",
                value=None,
                status="ABSTAINED",
                note="Angle values are non-numeric or missing.",
                evidence={"angle_col": angle_col},
            )

        avg_angle = float(s.mean())

        if open_min <= avg_angle <= open_max:
            status = "OPEN_HALF_TURN"
            note = "Half-turn/open body orientation band detected (better forward options)."
        elif avg_angle <= closed_max:
            status = "CLOSED_BODY_RISK"
            note = "Closed body orientation likely limits forward options under pressure."
        else:
            status = "NEUTRAL"
            note = "Angle not clearly open-half-turn nor closed band."

        return BiomechanicVerdict(
            metric_id="half_turn_gate",
            value=avg_angle,
            status=status,
            note=note,
            evidence={
                "angle_col": angle_col,
                "open_band": [open_min, open_max],
                "closed_max": closed_max,
            },
        )