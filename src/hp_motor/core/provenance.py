from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RunProvenance:
    run_id: str
    registry_version: str
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def add_input(self, artifact_id: str, sha256: Optional[str], source: str) -> None:
        self.inputs.append({"artifact_id": artifact_id, "sha256": sha256, "source": source})