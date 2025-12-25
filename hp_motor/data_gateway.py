from __future__ import annotations

from io import BytesIO
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from lxml import etree

from hp_motor.schema import normalize_columns

_DELIMS: tuple[str, ...] = (",", ";", "\t", "|")


def _decode_best_effort(b: bytes) -> str:
    """UTF-8 BOM -> UTF-8 -> Latin-1 fallback (lossless byte mapping)."""
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("latin-1")


def _detect_delim(sample_text: str, candidates: Iterable[str] = _DELIMS) -> str:
    """Pick delimiter via stability across first ~20 non-empty lines."""
    lines = [ln for ln in sample_text.splitlines()[:20] if ln.strip()]
    if not lines:
        return ","

    best = ","
    best_score = -10**18
    for d in candidates:
        counts = [len(ln.split(d)) for ln in lines]
        score = (min(counts) * 100) - (max(counts) - min(counts))
        if score > best_score:
            best_score = score
            best = d
    return best


def read_csv_bytes(b: bytes, *, normalize: bool = True) -> pd.DataFrame:
    """
    Read CSV-like bytes with delimiter auto-detection and tolerant decoding.
    normalize=True => columns canonicalized (recommended for downstream schema).
    """
    text = _decode_best_effort(b)
    delim = _detect_delim(text)
    df = pd.read_csv(BytesIO(text.encode("utf-8")), sep=delim)
    return normalize_columns(df) if normalize else df


def _flatten_element(el: etree._Element, prefix: str = "") -> Dict[str, str]:
    """
    Flatten XML element into key-value pairs by leaf paths.
    - attributes become path@attr
    - leaf text becomes path
    """
    out: Dict[str, str] = {}

    # attributes
    for k, v in el.attrib.items():
        key = f"{prefix}{el.tag}@{k}" if prefix else f"{el.tag}@{k}"
        out[key] = str(v)

    children = list(el)
    if not children:
        text = (el.text or "").strip()
        key = f"{prefix}{el.tag}" if prefix else el.tag
        if text != "":
            out[key] = text
        return out

    for ch in children:
        ch_prefix = f"{prefix}{el.tag}__" if prefix else f"{el.tag}__"
        out.update(_flatten_element(ch, prefix=ch_prefix))

    return out


def _select_record_nodes(root: etree._Element) -> List[etree._Element]:
    """
    Heuristic to find 'row/record' nodes:
    - If root has multiple children of same tag => treat those as records
    - Else if root has a single child, and that child has repeating children => treat repeating as records
    - Else treat root as single record
    """
    kids = list(root)
    if not kids:
        return [root]

    tags = [k.tag for k in kids]
    # case: repeating children at root
    if len(set(tags)) == 1 and len(kids) >= 2:
        return kids

    # case: container -> repeating grandchildren
    if len(kids) == 1:
        gkids = list(kids[0])
        if gkids:
            gtags = [g.tag for g in gkids]
            if len(set(gtags)) == 1 and len(gkids) >= 2:
                return gkids
        return [kids[0]]

    # mixed: treat each direct child as record
    return kids


def read_xml_bytes(b: bytes, *, normalize: bool = True) -> pd.DataFrame:
    """
    Read XML bytes into a DataFrame via deterministic flattening.
    Strategy:
    - pick record nodes using _select_record_nodes()
    - flatten leaves into path keys (joined by '__')
    normalize=True => columns canonicalized.
    """
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(b, parser=parser)

    records = []
    for rec in _select_record_nodes(root):
        flat = _flatten_element(rec, prefix="")
        records.append(flat)

    df = pd.DataFrame(records)
    return normalize_columns(df) if normalize else df
