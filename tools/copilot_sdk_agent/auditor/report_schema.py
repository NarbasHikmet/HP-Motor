from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Finding:
    code: str
    severity: str  # INFO | WARN | ERROR
    title: str
    detail: str
    file: Optional[str] = None
    hint: Optional[str] = None


@dataclass
class AuditReport:
    report_id: str
    status: str  # OK | WARN | FAIL
    summary: str
    stats: Dict[str, Any] = field(default_factory=dict)
    findings: List[Finding] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)  # paths to written outputs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "status": self.status,
            "summary": self.summary,
            "stats": self.stats,
            "findings": [
                {
                    "code": f.code,
                    "severity": f.severity,
                    "title": f.title,
                    "detail": f.detail,
                    "file": f.file,
                    "hint": f.hint,
                }
                for f in self.findings
            ],
            "risks": self.risks,
            "next_actions": self.next_actions,
            "artifacts": self.artifacts,
        }


def severity_rank(sev: str) -> int:
    s = (sev or "INFO").upper()
    return {"INFO": 0, "WARN": 1, "ERROR": 2}.get(s, 0)


def derive_status(findings: List[Finding]) -> str:
    if any((f.severity or "").upper() == "ERROR" for f in findings):
        return "FAIL"
    if any((f.severity or "").upper() == "WARN" for f in findings):
        return "WARN"
    return "OK" 