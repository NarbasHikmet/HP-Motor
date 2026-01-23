from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import pandas as pd


@dataclass
class BiomechanicVerdict:
    metric_id: str
    value: Optional[float]
    status: str
    note: str
    evidence: Dict[str, Any]


class BiomechanicGate:
    """
    Biomechanic Gate (v1):
    - Defense: 45° side-on vs square-on
    - Receiving: half-turn (open body) vs closed body proxy
    Works only if angle-related columns exist. Otherwise returns ABSTAINED.
    """

    # We accept multiple possible column names (provider variance).
    ANGLE_COL_CANDIDATES: List[str] = [
        "orientation_deg",
        "body_orientation_deg",
        "body_angle_deg",
        "hips_angle_deg",
        "stance_angle_deg",
        "player_body_angle_deg",
    ]

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

        avg_angle = float(pd.to_numeric(data[angle_col], errors="coerce").dropna().mean())
        if pd.isna(avg_angle):
            return BiomechanicVerdict(
                metric_id="defense_45deg_gate",
                value=None,
                status="ABSTAINED",
                note="Angle values are non-numeric or missing.",
                evidence={"angle_col": angle_col},
            )

        if abs(avg_angle - ideal_deg) <= elite_band:
            status = "ELITE_SIDE_ON"
            note = "Side-on posture consistent with 45° rule (better reaction/containment geometry)."
        elif square_on_min <= avg_angle <= square_on_max:
            status = "SQUARE_ON_RISK"
            note = "Square-on posture detected; biomechanical reaction window tends to be riskier."
        else:
            status = "NEUTRAL"
            note = "Angle is neither elite side-on nor square-on band."

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
        else => NEUTRAL
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

        avg_angle = float(pd.to_numeric(data[angle_col], errors="coerce").dropna().mean())
        if pd.isna(avg_angle):
            return BiomechanicVerdict(
                metric_id="half_turn_gate",
                value=None,
                status="ABSTAINED",
                note="Angle values are non-numeric or missing.",
                evidence={"angle_col": angle_col},
            )

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