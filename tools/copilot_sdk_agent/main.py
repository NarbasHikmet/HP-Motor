from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from tools.copilot_sdk_agent.hp_tools import validate_required_files, read_text, contract_hint
from tools.copilot_sdk_agent.prompts import PROMPTS


def _sdk_available() -> bool:
    try:
        import github_copilot_sdk  # noqa: F401
        return True
    except Exception:
        return False


def _run_with_sdk(task_prompt: str) -> Dict[str, Any]:
    """
    Conservative placeholder runner.

    Copilot SDK integration details can vary by version.
    We keep this safe: never breaks runtime, never requires tokens in code.
    """
    try:
        import github_copilot_sdk  # noqa: F401

        return {
            "status": "SDK_AVAILABLE",
            "note": (
                "Copilot SDK is installed, but this runner intentionally uses a placeholder integration.\n"
                "Next step: wire the exact SDK session API for your installed version."
            ),
            "task_prompt_head": task_prompt[:800],
        }
    except Exception as e:
        return {
            "status": "SDK_ERROR",
            "error": str(e),
            "next_step": "Check Copilot SDK installation and API compatibility.",
        }


def cmd_validate() -> Dict[str, Any]:
    checks = validate_required_files()
    return {
        "status": "OK" if all(c.ok for c in checks) else "FAIL",
        "checks": [c.__dict__ for c in checks],
        "contract_hint": contract_hint(),
    }


def cmd_audit() -> Dict[str, Any]:
    """
    Lightweight audit that does NOT require Copilot SDK.
    If SDK exists, we additionally run the agent prompt (placeholder).
    """
    base = {
        "required_files": cmd_validate(),
        "samples": {
            "copilot_instructions": read_text(".github/copilot-instructions.md", 2000),
            "requirements_txt": read_text("requirements.txt", 2000),
            "master_registry_head": read_text("src/hp_motor/registries/master_registry.yaml", 2000),
        },
    }

    if not _sdk_available():
        base["copilot_sdk"] = {
            "status": "MISSING",
            "note": (
                "Copilot SDK not installed in this environment.\n"
                "Install: pip install -r requirements-dev.txt\n"
                "Then rerun: python tools/copilot_sdk_agent/main.py audit"
            ),
        }
        return base

    base["copilot_sdk"] = _run_with_sdk(PROMPTS.system + "\n\n" + PROMPTS.task_audit)
    return base


def cmd_registry_audit() -> Dict[str, Any]:
    """
    Runs the static registry + ontology audit and writes artifacts under ./reports/.
    This does NOT require Copilot SDK.
    """
    from tools.copilot_sdk_agent.auditor.run_audit import run_registry_audit

    repo_root = Path(__file__).resolve().parents[2]  # repo root
    return run_registry_audit(repo_root)


def cmd_show_prompts() -> Dict[str, Any]:
    return {
        "system": PROMPTS.system,
        "task_audit": PROMPTS.task_audit,
        "task_validate": PROMPTS.task_validate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="hp-copilot-agent", description="HP Motor Copilot SDK Agent Runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("audit", help="Audit repository structure & readiness (light)")
    sub.add_parser("validate", help="Validate required files exist (light)")
    sub.add_parser("registry-audit", help="Run static registry/ontology audit (writes ./reports artifacts)")
    sub.add_parser("show-prompts", help="Print prompt bundles")

    args = parser.parse_args()

    if args.cmd == "audit":
        out = cmd_audit()
    elif args.cmd == "validate":
        out = cmd_validate()
    elif args.cmd == "registry-audit":
        out = cmd_registry_audit()
    else:
        out = cmd_show_prompts()

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()