from __future__ import annotations

import io
from typing import Any, Dict, List, Sequence

import pandas as pd

from ..codec import BaseEncoder, EncodeResult
from ..signal_packet import SignalPacket, Payload, Provenance, TemporalAnchor


class XLSXFitnessEncoder(BaseEncoder):
    """
    XLSX Fitness/GPS encoder (best effort):
    Emits packets for numeric columns per player.

    Assumption:
      - There is a player identifier column (Oyuncu / Player / player_name).
      - Time may be missing -> validator will mark DEGRADED for time-dependent usage.
    """

    @property
    def file_kinds(self) -> Sequence[str]:
        return ["XLSX_FITNESS"]

    def can_handle(self, filename: str) -> bool:
        lower = filename.lower()
        return lower.endswith(".xlsx") and ("fitness" in lower or "gps" in lower)

    def encode_bytes(self, filename: str, data: bytes) -> EncodeResult:
        df = pd.read_excel(io.BytesIO(data))
        packets: List[SignalPacket] = []

        entity_col = None
        for c in ["Oyuncu", "Player", "player", "player_name", "Name"]:
            if c in df.columns:
                entity_col = c
                break

        num_cols = []
        for c in df.columns:
            if c == entity_col:
                continue
            # mark numeric columns
            if pd.api.types.is_numeric_dtype(df[c]):
                num_cols.append(c)

        for idx, row in df.iterrows():
            entity = str(row[entity_col]) if entity_col else "unknown"
            for c in num_cols:
                val = row[c]
                try:
                    fval = float(val)
                except Exception:
                    continue

                packets.append(
                    SignalPacket(
                        signal_type="fitness",
                        provenance=Provenance(filename=filename, line_number=int(idx) + 1, timestamp_raw=None),
                        payload=Payload(entity=entity, metric=str(c), value=fval, unit=None),
                        temporal_anchor=TemporalAnchor(start_s=None, end_s=None, frame_id=None),
                        meta={"confidence": 0.6, "logic_gate": "Unverified_Hypothesis", "status": "OK", "source_hint": "xlsx_fitness"},
                    )
                )

        return EncodeResult(
            packets=packets,
            meta={"file_kind": "XLSX_FITNESS", "rows": int(len(df)), "columns": list(df.columns), "status": "OK"},
        )