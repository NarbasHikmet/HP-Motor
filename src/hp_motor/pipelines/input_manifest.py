from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class InputManifest:
    """
    Runtime input inventory.
    No guessing: only explicit flags/paths or provided df count as present.
    """
    has_event: bool = False
    has_spatial: bool = False
    has_fitness: bool = False
    has_video: bool = False
    has_tracking: bool = False
    has_doc: bool = False
    notes: Optional[str] = None

    @staticmethod
    def from_kwargs(df_provided: bool, kwargs: Dict[str, Any]) -> "InputManifest":
        def truthy(x: Any) -> bool:
            if x is None:
                return False
            if isinstance(x, bool):
                return x
            if isinstance(x, (list, tuple, dict, set)):
                return len(x) > 0
            if isinstance(x, str):
                return len(x.strip()) > 0
            return True

        # Explicit flags win
        has_event_flag = truthy(kwargs.get("has_event"))
        has_fitness_flag = truthy(kwargs.get("has_fitness"))
        has_video_flag = truthy(kwargs.get("has_video"))
        has_tracking_flag = truthy(kwargs.get("has_tracking"))
        has_doc_flag = truthy(kwargs.get("has_doc"))
        has_spatial_flag = truthy(kwargs.get("has_spatial"))

        # Paths count as explicit provision
        has_event_path = any(truthy(kwargs.get(k)) for k in ["event_path", "csv_path", "xml_path"])
        has_fitness_path = any(truthy(kwargs.get(k)) for k in ["xlsx_path", "fitness_path"])
        has_video_path = any(truthy(kwargs.get(k)) for k in ["mp4_path", "video_path"])
        has_tracking_path = truthy(kwargs.get("tracking_path"))

        doc_keys = ["doc_paths", "pdf_path", "doc_path", "txt_path", "md_path", "html_path"]
        has_doc_path = any(truthy(kwargs.get(k)) for k in doc_keys)

        # DataFrame means EVENT evidence is present for this run (but spatial must be asserted by validator)
        has_event_df = bool(df_provided)

        return InputManifest(
            has_event=(has_event_flag or has_event_path or has_event_df),
            has_spatial=has_spatial_flag,  # can be upgraded after SOT validation
            has_fitness=(has_fitness_flag or has_fitness_path),
            has_video=(has_video_flag or has_video_path),
            has_tracking=(has_tracking_flag or has_tracking_path),
            has_doc=(has_doc_flag or has_doc_path),
            notes=kwargs.get("input_notes"),
        )

    def with_spatial(self, has_spatial: bool, notes: Optional[str] = None) -> "InputManifest":
        return InputManifest(
            has_event=self.has_event,
            has_spatial=has_spatial,
            has_fitness=self.has_fitness,
            has_video=self.has_video,
            has_tracking=self.has_tracking,
            has_doc=self.has_doc,
            notes=notes or self.notes,
        )