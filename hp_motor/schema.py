from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


def _clean_name(s: str) -> str:
    s = s.strip().lower()
    # boşluk ve tireleri underscore yap
    s = re.sub(r"[\s\-]+", "_", s)
    # Türkçe karakterleri stabil hale getir (min set)
    s = (
        s.replace("ı", "i")
        .replace("İ", "i")
        .replace("ş", "s")
        .replace("Ş", "s")
        .replace("ğ", "g")
        .replace("Ğ", "g")
        .replace("ü", "u")
        .replace("Ü", "u")
        .replace("ö", "o")
        .replace("Ö", "o")
        .replace("ç", "c")
        .replace("Ç", "c")
    )
    # alfanümerik + underscore dışını at
    s = re.sub(r"[^a-z0-9_]+", "", s)
    # ardışık underscore sadeleştir
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Canonical column naming:
    - lower_snake_case
    - TR chars normalized (ı->i, ş->s, etc.)
    - non-alnum removed
    """
    out = df.copy()
    out.columns = [_clean_name(str(c)) for c in out.columns]
    return out


def require_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
