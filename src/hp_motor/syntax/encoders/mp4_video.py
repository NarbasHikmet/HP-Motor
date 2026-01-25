from __future__ import annotations

from typing import Any, Dict, List, Sequence

from ..codec import BaseEncoder, EncodeResult
from ..signal_packet import SignalPacket, Payload, Provenance


class MP4VideoEncoder(BaseEncoder):
    """
    MP4 -> track/doc-like signals.
    IMPORTANT:
      - This encoder MUST NOT hallucinate CV outputs.
      - If OpenCV is not available, only emit "video_present" with DEGRADED status.
      - Downstream capability matrix will still require MP4 to allow CV products, but actual CV needs extra modules.

    This satisfies your rule:
      "Video yokken video-türevi analiz asla çalışmasın."
    """

    @property
    def file_kinds(self) -> Sequence[str]:
        return ["MP4_VIDEO"]

    def can_handle(self, filename: str) -> bool:
        return filename.lower().endswith(".mp4")

    def encode_bytes(self, filename: str, data: bytes) -> EncodeResult:
        # Do not decode heavy. Try metadata only.
        fps = None
        frames = None
        extracted = False

        try:
            import cv2  # type: ignore
            import tempfile
            # Write temp file for cv2
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
                tmp.write(data)
                tmp.flush()
                cap = cv2.VideoCapture(tmp.name)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    extracted = True
                cap.release()
        except Exception:
            extracted = False

        packets: List[SignalPacket] = []
        if extracted:
            packets.append(
                SignalPacket(
                    signal_type="track",
                    provenance=Provenance(filename=filename),
                    payload=Payload(entity="global", metric="video_meta_fps", value=float(fps) if fps else 0.0, unit="fps"),
                    meta={"confidence": 0.7, "logic_gate": "Unverified_Hypothesis", "status": "OK", "source_hint": "mp4_meta"},
                )
            )
            packets.append(
                SignalPacket(
                    signal_type="track",
                    provenance=Provenance(filename=filename),
                    payload=Payload(entity="global", metric="video_meta_frames", value=int(frames) if frames else 0, unit="count"),
                    meta={"confidence": 0.7, "logic_gate": "Unverified_Hypothesis", "status": "OK", "source_hint": "mp4_meta"},
                )
            )
        else:
            packets.append(
                SignalPacket(
                    signal_type="track",
                    provenance=Provenance(filename=filename),
                    payload=Payload(entity="global", metric="video_present", value="true", unit=None),
                    meta={"confidence": 0.5, "logic_gate": "Unverified_Hypothesis", "status": "DEGRADED", "source_hint": "mp4_present_only"},
                )
            )

        return EncodeResult(
            packets=packets,
            meta={"file_kind": "MP4_VIDEO", "status": "OK", "meta_extracted": bool(extracted)},
        )