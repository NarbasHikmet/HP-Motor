from __future__ import annotations

import io
from typing import Any, Dict, List, Sequence

import pandas as pd

from ..codec import BaseEncoder, EncodeResult
from ..signal_packet import SignalPacket, Payload, Provenance, SpatialAnchor, TemporalAnchor


class CSVEventsEncoder(BaseEncoder):
    """
    Generic CSV event encoder.
    Expected columns (best effort):
      - team/player/event_type/timestamp/x/y/end_x/end_y
    """

    @property
    def file_kinds(self) -> Sequence[str]:
        return ["CSV_EVENTS"]

    def can_handle(self, filename: str) -> bool:
        lower = filename.lower()
        return lower.endswith(".csv") and ("maçın tamamı" in lower or "events" in lower or "event" in lower)

    def encode_bytes(self, filename: str, data: bytes) -> EncodeResult:
        df = pd.read_csv(io.BytesIO(data))
        packets: List[SignalPacket] = []

        # soft mapping
        def pick(cols):
            for c in cols:
                if c in df.columns:
                    return c
            return None

        col_ts = pick(["timestamp_s", "timestamp", "time", "sec", "seconds"])
        col_player = pick(["player_id", "player", "player_name", "Oyuncu"])
        col_team = pick(["team", "team_name", "Takım"])
        col_type = pick(["event_type", "type", "EventType", "Aksiyon"])
        col_x = pick(["x", "X", "start_x", "pos_x"])
        col_y = pick(["y", "Y", "start_y", "pos_y"])

        for idx, row in df.iterrows():
            entity = str(row[col_player]) if col_player else (str(row[col_team]) if col_team else "unknown")
            metric = str(row[col_type]) if col_type else "event"
            ts = None
            if col_ts:
                try:
                    ts = float(row[col_ts])
                except Exception:
                    ts = None

            sp = None
            if col_x and col_y:
                try:
                    sp = SpatialAnchor(x=float(row[col_x]), y=float(row[col_y]), z=None, space_id=None)
                except Exception:
                    sp = None

            p = SignalPacket(
                signal_type="event",
                provenance=Provenance(filename=filename, line_number=int(idx) + 1, timestamp_raw=str(row[col_ts]) if col_ts else None),
                payload=Payload(entity=entity, metric=metric, value=1, unit="count"),
                spatial_anchor=sp,
                temporal_anchor=TemporalAnchor(start_s=ts, end_s=ts, frame_id=None),
                meta={"confidence": 0.6, "logic_gate": "Unverified_Hypothesis", "status": "OK", "source_hint": "csv_events"},
            )
            packets.append(p)

        return EncodeResult(
            packets=packets,
            meta={
                "file_kind": "CSV_EVENTS",
                "rows": int(len(df)),
                "columns": list(df.columns),
                "status": "OK",
            },
        )