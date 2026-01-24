from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd


@dataclass
class BiomechGateResult:
    ok: bool
    confidence_band: str  # low | medium | high
    supporting: List[str]
    contradicting: List[str]
    note: str
    issues: List[Dict[str, Any]]


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
    """

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