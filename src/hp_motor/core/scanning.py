from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


def compute_decision_speed(df: pd.DataFrame, entity_id: Optional[str] = None) -> Dict[str, Any]:
    """
    SportsBase benzeri event verisinde karar hızı proxy’si.
    Beklenen kolonlar (en az bir set):
      - (t1, t2)  veya
      - (timestamp_start, timestamp_end)

    Çıktı:
      avg_decision_speed_sec, status, note
    """
    if df is None or df.empty:
        return {
            "avg_decision_speed_sec": None,
            "status": "UNKNOWN",
            "note": "Empty DF",
        }

    work = df.copy()

    if "t1" in work.columns and "t2" in work.columns:
        work["delta_t"] = pd.to_numeric(work["t2"], errors="coerce") - pd.to_numeric(work["t1"], errors="coerce")
    elif "timestamp_start" in work.columns and "timestamp_end" in work.columns:
        work["delta_t"] = pd.to_numeric(work["timestamp_end"], errors="coerce") - pd.to_numeric(work["timestamp_start"], errors="coerce")
    else:
        return {
            "avg_decision_speed_sec": None,
            "status": "UNKNOWN",
            "note": "No (t1,t2) or (timestamp_start,timestamp_end) columns found.",
        }

    if entity_id is not None:
        # player_id varsa filtrele
        if "player_id" in work.columns:
            work = work[work["player_id"].astype(str) == str(entity_id)]

    val = work["delta_t"].dropna()
    if val.empty:
        return {
            "avg_decision_speed_sec": None,
            "status": "UNKNOWN",
            "note": "delta_t computed but empty after filtering/NaNs.",
        }

    avg = float(val.mean())

    # Jordet proxy eşikleri (senin atlasına uygun)
    if avg < 0.8:
        status = "ELITE"
    elif avg < 1.2:
        status = "AVERAGE"
    else:
        status = "SLOW"

    return {
        "avg_decision_speed_sec": avg,
        "status": status,
        "note": "Decision speed proxy from timestamps; scanning inference is indirect.",
    }