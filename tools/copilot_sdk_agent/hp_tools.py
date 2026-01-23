from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def repo_path(rel: str) -> Path:
    return REPO_ROOT / rel


def exists(rel: str) -> bool:
    return repo_path(rel).exists()


def read_text(rel: str, limit_chars: int = 4000) -> str:
    p = repo_path(rel)
    if not p.exists():
        return ""
    txt = p.read_text(encoding="utf-8", errors="replace")
    return txt[:limit_chars]


def validate_required_files() -> List[CheckResult]:
    required = [
        ".github/copilot-instructions.md",
        "requirements.txt",
        "src/hp_motor/registries/master_registry.yaml",
        "src/hp_motor/pipelines/analysis_objects/player_role_fit.yaml",
    ]
    out: List[CheckResult] = []
    for rel in required:
        out.append(CheckResult(rel, exists(rel), "OK" if exists(rel) else "MISSING"))
    return out


def contract_hint() -> Dict[str, List[str]]:
    """
    This is NOT executing code. It's a static hint for the agent to follow contract rules.
    """
    return {
        "orchestrator_execute_output_must_include": [
            "status",
            "metrics",
            "evidence_graph",
            "tables",
            "lists",
            "figure_objects (optional)",
        ]
    }