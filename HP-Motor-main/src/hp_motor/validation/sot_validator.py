from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "WARN"  # WARN | ERROR


class SOTValidator:
    """
    Contract-first gate (Engine → Motor port).

    Rules:
      - NO silent drop of rows.
      - 0.0 is valid.
      - Returns a data quality report only (no destructive transform).
    """

    def __init__(self, provider_contract: str = "sportsbase", required_columns: List[str] | None = None) -> None:
        self.provider_contract = provider_contract

        self.required_columns = required_columns or [
            "team_id",
            "event_type",
            "timestamp_s",
        ]

        # Canonical pitch from contract (default 105x68)
        self.pitch = (105.0, 68.0)

    def validate(self, df: pd.DataFrame) -> Dict:
        issues: List[ValidationIssue] = []

        missing = [c for c in self.required_columns if c not in df.columns]
        if missing:
            issues.append(
                ValidationIssue(
                    code="MISSING_REQUIRED_COLUMNS",
                    message=f"Missing required columns: {missing}",
                    severity="ERROR",
                )
            )

        null_map = df.isnull().sum().to_dict()

        bounds_report: Dict[str, int] = {"x_out_of_bounds": 0, "y_out_of_bounds": 0}

        if "x" in df.columns:
            x = pd.to_numeric(df["x"], errors="coerce")
            out_x = ((x < -1) | (x > self.pitch[0] + 1)).sum()
            bounds_report["x_out_of_bounds"] = int(out_x)

            if out_x > 0:
                issues.append(
                    ValidationIssue(
                        code="COORD_OUT_OF_BOUNDS_X",
                        message=f"{int(out_x)} rows have x outside expected pitch bounds (0..{self.pitch[0]}).",
                        severity="WARN",
                    )
                )

        if "y" in df.columns:
            y = pd.to_numeric(df["y"], errors="coerce")
            out_y = ((y < -1) | (y > self.pitch[1] + 1)).sum()
            bounds_report["y_out_of_bounds"] = int(out_y)

            if out_y > 0:
                issues.append(
                    ValidationIssue(
                        code="COORD_OUT_OF_BOUNDS_Y",
                        message=f"{int(out_y)} rows have y outside expected pitch bounds (0..{self.pitch[1]}).",
                        severity="WARN",
                    )
                )

        if "timestamp_s" in df.columns:
            ts = pd.to_numeric(df["timestamp_s"], errors="coerce")
            bad_ts = ts.isna().sum()
            if bad_ts > 0:
                issues.append(
                    ValidationIssue(
                        code="BAD_TIMESTAMP_COERCION",
                        message=f"{int(bad_ts)} rows have non-numeric timestamp_s.",
                        severity="WARN",
                    )
                )

        ok = not any(i.severity == "ERROR" for i in issues)

        return {
            "ok": ok,
            "provider_contract": self.provider_contract,
            "issues": [i.__dict__ for i in issues],
            "null_map": null_map,
            "bounds_report": bounds_report,
        }