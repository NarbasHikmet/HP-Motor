from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from tools.copilot_sdk_agent.auditor.registry_auditor import RegistryAuditor


def run_registry_audit(repo_root: Path) -> Dict[str, Any]:
    auditor = RegistryAuditor(repo_root=repo_root)
    report = auditor.run()
    report = auditor.write_artifacts(report)
    return report.to_dict()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]  # repo root
    out = run_registry_audit(repo_root)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()