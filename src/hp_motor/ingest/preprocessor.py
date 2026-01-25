from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# -------------------------------
# Canonical schemas (minimal)
# -------------------------------

CANON_EVENT_COLUMNS = [
    "match_id",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "event_type",
    "outcome",
    "minute",
    "second",
    "timestamp_s",
    "x",
    "y",
    "end_x",
    "end_y",
    "qualifiers_json",
]

CANON_FITNESS_COLUMNS = [
    "match_id",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "window_start_s",
    "window_end_s",
    "total_distance_m",
    "hsr_distance_m",
    "sprint_count",
    "accel_count",
    "decel_count",
    "player_load",
    "raw_fields_json",
]


# -------------------------------
# Utilities
# -------------------------------

def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, str) and x.strip() == "":
            return None
        return float(x)
    except Exception:
        return None


def _safe_int(x: Any) -> Optional[int]:
    try:
        if x is None:
            return None
        if isinstance(x, str) and x.strip() == "":
            return None
        return int(float(x))
    except Exception:
        return None


def _norm_col(c: str) -> str:
    c = c.strip()
    c = c.lower()
    c = re.sub(r"[^\w]+", "_", c)
    c = re.sub(r"_+", "_", c).strip("_")
    return c


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _read_input_file(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".csv", ".tsv"]:
        sep = "\t" if ext == ".tsv" else ","
        return pd.read_csv(path, sep=sep, encoding="utf-8", engine="python")
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    if ext in [".json"]:
        # Accept JSON array of objects
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, list):
            return pd.DataFrame(obj)
        if isinstance(obj, dict):
            # common pattern: {"data":[...]}
            if "data" in obj and isinstance(obj["data"], list):
                return pd.DataFrame(obj["data"])
            # fallback: dict-of-lists
            return pd.DataFrame(obj)
        raise ValueError("Unsupported JSON structure")
    raise ValueError(f"Unsupported file extension: {ext}")


def _df_to_records_json(df: pd.DataFrame, max_rows: int = 50) -> List[Dict[str, Any]]:
    # Small sample for audits
    return df.head(max_rows).to_dict(orient="records")


# -------------------------------
# RAW store + audit report
# -------------------------------

@dataclass
class RawArtifact:
    raw_path: str
    meta_path: str
    ingest_id: str


class RawStore:
    """
    No Silent Drop:
      - Always store the original file as-is under raw/
      - Store ingest metadata (provenance, hashes optional)
    """

    def __init__(self, root: str = "data"):
        self.root = root

    def persist(self, input_path: str) -> RawArtifact:
        _ensure_dir(self.root)
        raw_dir = os.path.join(self.root, "raw")
        meta_dir = os.path.join(self.root, "raw_meta")
        _ensure_dir(raw_dir)
        _ensure_dir(meta_dir)

        ingest_id = uuid.uuid4().hex
        base = os.path.basename(input_path)
        raw_path = os.path.join(raw_dir, f"{ingest_id}__{base}")

        # Copy raw bytes
        with open(input_path, "rb") as src, open(raw_path, "wb") as dst:
            dst.write(src.read())

        meta_path = os.path.join(meta_dir, f"{ingest_id}__{base}.json")
        meta = {
            "ingest_id": ingest_id,
            "source_file": input_path,
            "stored_raw": raw_path,
            "ingested_at_utc": _now_iso(),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return RawArtifact(raw_path=raw_path, meta_path=meta_path, ingest_id=ingest_id)


# -------------------------------
# Column mapping (SportsBase-first, extendable)
# -------------------------------

DEFAULT_EVENT_SYNONYMS = {
    # canonical -> possible input columns
    "match_id": ["match_id", "match", "game_id", "fixture_id"],
    "team_id": ["team_id", "teamid", "team"],
    "team_name": ["team_name", "teamname", "team"],
    "player_id": ["player_id", "playerid", "player"],
    "player_name": ["player_name", "playername", "player"],
    "event_type": ["event_type", "type", "action", "event"],
    "outcome": ["outcome", "result", "success", "is_success"],
    "minute": ["minute", "min"],
    "second": ["second", "sec"],
    "timestamp_s": ["timestamp_s", "time_s", "time_seconds", "ts_s"],
    "x": ["x", "start_x", "location_x", "pos_x"],
    "y": ["y", "start_y", "location_y", "pos_y"],
    "end_x": ["end_x", "pass_end_x", "to_x", "target_x"],
    "end_y": ["end_y", "pass_end_y", "to_y", "target_y"],
}

DEFAULT_FITNESS_SYNONYMS = {
    "match_id": ["match_id", "match", "game_id", "fixture_id"],
    "team_id": ["team_id", "teamid", "team"],
    "team_name": ["team_name", "teamname", "team"],
    "player_id": ["player_id", "playerid", "player"],
    "player_name": ["player_name", "playername", "player"],
    "window_start_s": ["window_start_s", "start_s", "start_time_s"],
    "window_end_s": ["window_end_s", "end_s", "end_time_s"],
    "total_distance_m": ["total_distance_m", "distance_m", "total_distance", "dist_m"],
    "hsr_distance_m": ["hsr_distance_m", "hsr_m", "high_speed_running_m", "hsr_distance"],
    "sprint_count": ["sprint_count", "sprints"],
    "accel_count": ["accel_count", "accelerations"],
    "decel_count": ["decel_count", "decelerations"],
    "player_load": ["player_load", "load", "playerload"],
}


def _resolve_mapping(df_cols: List[str], synonyms: Dict[str, List[str]]) -> Dict[str, Optional[str]]:
    cols_norm = {_norm_col(c): c for c in df_cols}  # norm -> original
    resolved: Dict[str, Optional[str]] = {}
    for canon, candidates in synonyms.items():
        picked = None
        for cand in candidates:
            cand_n = _norm_col(cand)
            if cand_n in cols_norm:
                picked = cols_norm[cand_n]
                break
        resolved[canon] = picked
    return resolved


# -------------------------------
# Preprocessor core
# -------------------------------

@dataclass
class PreprocessResult:
    ingest_id: str
    kind: str  # "event" or "fitness"
    canonical_df: pd.DataFrame
    audit_report: Dict[str, Any]
    canonical_path: Optional[str] = None
    audit_path: Optional[str] = None


class Preprocessor:
    """
    Black-box intake:
      - Store RAW
      - Read file
      - Normalize columns
      - Map to canonical schema
      - Keep unknown fields (no silent drop) in *_json columns
      - Write canonical artifact + audit report
    """

    def __init__(self, data_root: str = "data"):
        self.data_root = data_root
        self.raw_store = RawStore(root=data_root)

    def preprocess(self, input_path: str, kind: str, match_id: Optional[str] = None) -> PreprocessResult:
        if kind not in ("event", "fitness"):
            raise ValueError("kind must be 'event' or 'fitness'")

        raw_art = self.raw_store.persist(input_path)
        df = _read_input_file(raw_art.raw_path)
        original_cols = list(df.columns)

        # Normalize column names (create a view with normalized names)
        df_norm = df.copy()
        df_norm.columns = [_norm_col(c) for c in df_norm.columns]

        if kind == "event":
            synonyms = DEFAULT_EVENT_SYNONYMS
            canon_cols = CANON_EVENT_COLUMNS
        else:
            synonyms = DEFAULT_FITNESS_SYNONYMS
            canon_cols = CANON_FITNESS_COLUMNS

        mapping = _resolve_mapping(original_cols, synonyms)

        # Build canonical frame
        canon = pd.DataFrame({c: None for c in canon_cols})

        # Fill known mapped columns
        for canon_name, source_col in mapping.items():
            if source_col is None:
                continue
            src_norm = _norm_col(source_col)
            if src_norm in df_norm.columns:
                canon[canon_name] = df_norm[src_norm]

        # Match id override
        if match_id is not None:
            canon["match_id"] = match_id

        # Type coercions + derived timestamp_s
        if kind == "event":
            canon["minute"] = canon["minute"].apply(_safe_int)
            canon["second"] = canon["second"].apply(_safe_int)
            canon["timestamp_s"] = canon["timestamp_s"].apply(_safe_float)

            # Derive timestamp_s if missing but minute/second present
            if canon["timestamp_s"].isna().all():
                def derive_ts(row: pd.Series) -> Optional[float]:
                    m = row.get("minute")
                    s = row.get("second")
                    if m is None and s is None:
                        return None
                    m = m or 0
                    s = s or 0
                    return float(m) * 60.0 + float(s)

                canon["timestamp_s"] = canon.apply(derive_ts, axis=1)

            for k in ["x", "y", "end_x", "end_y"]:
                canon[k] = canon[k].apply(_safe_float)

            # qualifiers: keep unknown columns (no silent drop)
            known_src_norms = set(_norm_col(c) for c in mapping.values() if c is not None)
            unknown_cols = [c for c in df_norm.columns if c not in known_src_norms]
            if unknown_cols:
                canon["qualifiers_json"] = df_norm[unknown_cols].apply(lambda r: json.dumps(r.to_dict(), ensure_ascii=False), axis=1)
            else:
                canon["qualifiers_json"] = None

        else:
            canon["window_start_s"] = canon["window_start_s"].apply(_safe_float)
            canon["window_end_s"] = canon["window_end_s"].apply(_safe_float)

            for k in ["total_distance_m", "hsr_distance_m", "player_load"]:
                canon[k] = canon[k].apply(_safe_float)
            for k in ["sprint_count", "accel_count", "decel_count"]:
                canon[k] = canon[k].apply(_safe_int)

            # raw fields: keep unknown columns
            known_src_norms = set(_norm_col(c) for c in mapping.values() if c is not None)
            unknown_cols = [c for c in df_norm.columns if c not in known_src_norms]
            if unknown_cols:
                canon["raw_fields_json"] = df_norm[unknown_cols].apply(lambda r: json.dumps(r.to_dict(), ensure_ascii=False), axis=1)
            else:
                canon["raw_fields_json"] = None

        # Build audit report (SOT-adjacent)
        audit = self._build_audit(
            ingest_id=raw_art.ingest_id,
            kind=kind,
            input_path=input_path,
            raw_path=raw_art.raw_path,
            original_cols=original_cols,
            mapping=mapping,
            canonical_cols=canon_cols,
            canon_df=canon,
        )

        # Persist canonical + audit
        out_dir = os.path.join(self.data_root, "canonical")
        audit_dir = os.path.join(self.data_root, "audit")
        _ensure_dir(out_dir)
        _ensure_dir(audit_dir)

        base = os.path.basename(input_path)
        canon_path = os.path.join(out_dir, f"{raw_art.ingest_id}__{kind}__{base}.parquet")
        audit_path = os.path.join(audit_dir, f"{raw_art.ingest_id}__{kind}__{base}.audit.json")

        # Parquet is preferred; fallback to CSV if pyarrow not installed
        wrote = False
        try:
            canon.to_parquet(canon_path, index=False)
            wrote = True
        except Exception:
            canon_path = canon_path.replace(".parquet", ".csv")
            canon.to_csv(canon_path, index=False, encoding="utf-8")
            wrote = True

        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit, f, ensure_ascii=False, indent=2)

        if not wrote:
            canon_path = None

        return PreprocessResult(
            ingest_id=raw_art.ingest_id,
            kind=kind,
            canonical_df=canon,
            audit_report=audit,
            canonical_path=canon_path,
            audit_path=audit_path,
        )

    @staticmethod
    def _build_audit(
        ingest_id: str,
        kind: str,
        input_path: str,
        raw_path: str,
        original_cols: List[str],
        mapping: Dict[str, Optional[str]],
        canonical_cols: List[str],
        canon_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        missing_canon = [c for c, src in mapping.items() if src is None]
        present_canon = [c for c, src in mapping.items() if src is not None]

        # Basic bounds report for x/y if present
        bounds_report: Dict[str, Any] = {}
        if kind == "event" and "x" in canon_df.columns and "y" in canon_df.columns:
            x = canon_df["x"].dropna()
            y = canon_df["y"].dropna()
            # SportsBase pitch often in 0..100; canonical pitch could be 105x68 later.
            # Here we only do sanity checks: negative or absurd values.
            x_oob = int(((x < 0) | (x > 130)).sum()) if not x.empty else 0
            y_oob = int(((y < 0) | (y > 100)).sum()) if not y.empty else 0
            bounds_report = {
                "x_out_of_bounds": x_oob,
                "y_out_of_bounds": y_oob,
                "x_non_null": int(x.shape[0]),
                "y_non_null": int(y.shape[0]),
            }

        return {
            "ingest_id": ingest_id,
            "kind": kind,
            "ingested_at_utc": _now_iso(),
            "provenance": {
                "source_file": input_path,
                "raw_stored_path": raw_path,
            },
            "columns": {
                "original": original_cols,
                "canonical": canonical_cols,
                "mapping": mapping,
                "missing_canonical_fields": missing_canon,
                "present_canonical_fields": present_canon,
            },
            "quality": {
                "row_count": int(canon_df.shape[0]),
                "null_ratio_by_field": {c: float(canon_df[c].isna().mean()) for c in canonical_cols},
                "bounds_report": bounds_report,
            },
            "sample": {
                "canonical_head": _df_to_records_json(canon_df, max_rows=25),
            },
            "status_hint": "OK" if len(missing_canon) == 0 else "DEGRADED",
            "notes": [
                "No Silent Drop: unknown input fields preserved in *_json columns.",
                "Spatial claims must be gated: bounds_report indicates whether x/y are sane.",
            ],
        }