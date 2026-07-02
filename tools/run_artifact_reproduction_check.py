#!/usr/bin/env python3
"""Run reviewer-safe artifact reproduction checks.

Default checks are no-secret, local-only, and do not run real Hermes or call
DeepSeek. They exercise local CapProof MCP artifact surfaces and record a
report.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "artifact_reports"
REPORT_MD = REPORT_DIR / "artifact_reproduction_report.md"
SUMMARY_JSON = REPORT_DIR / "artifact_reproduction_summary.json"
HEX_SECRET_RE = re.compile(r"sk-[0-9a-fA-F]{24,}")


LOCAL_COMMANDS = [
    ["bin/hermes", "--doctor"],
    ["bin/hermes", "--where-trace"],
    ["python", "tools/run_capproof_mcp_server.py", "--list-tools"],
    ["python", "tools/run_capproof_mcp_doctor.py", "--all"],
    ["python", "tools/run_capproof_trace_viewer.py", "--latest", "--last", "5"],
    ["python", "tools/run_capproof_auth_queue.py", "doctor"],
    ["python", "tools/run_mcp_compatibility_matrix.py", "--report"],
]

PACKAGING_TEST_COMMAND = [
    "pytest",
    "tests/test_mcp_compatibility_profile.py",
    "tests/test_claims_and_non_claims.py",
    "tests/test_install_local_hermes_wrapper_docs.py",
    "tests/test_artifact_reproduction_check.py",
    "-q",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local artifact reproduction checks.")
    parser.add_argument("--no-secret", action="store_true", help="assert no API key is required or written")
    parser.add_argument("--local-only", action="store_true", help="do not run real Hermes or DeepSeek")
    parser.add_argument("--report", action="store_true", help="write markdown and JSON reports")
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args(argv)

    summary = run_checks(no_secret=args.no_secret, local_only=args.local_only)
    if args.report or not args.json:
        write_reports(summary)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(format_text_summary(summary))
    return 0 if summary["passed"] else 1


def run_checks(*, no_secret: bool = True, local_only: bool = True) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT))
    env["CAPPROOF_ARTIFACT_REPRODUCTION_CHECK"] = "1"
    command_results = [run_command(command, env=env) for command in LOCAL_COMMANDS]
    packaging_tests = run_command(PACKAGING_TEST_COMMAND, env=env)
    secret_scan = scan_for_real_keys()
    tracked_forbidden = tracked_forbidden_paths()
    git_status = run_command(["git", "status", "--short"], env=env)
    passed = (
        all(result["returncode"] == 0 for result in command_results)
        and packaging_tests["returncode"] == 0
        and secret_scan["ok"]
        and not tracked_forbidden["tracked"]
    )
    return {
        "stage": "37PKG",
        "passed": passed,
        "default_no_secret": no_secret,
        "default_local_only": local_only,
        "real_hermes_run": False,
        "deepseek_called": False,
        "real_email": False,
        "real_shell": False,
        "external_mcp": False,
        "git_status_short": git_status["stdout"],
        "commands": command_results,
        "packaging_tests": packaging_tests,
        "secret_scan": secret_scan,
        "tracked_forbidden_paths": tracked_forbidden,
        "production_level_protection_claim": False,
        "all_hermes_tool_paths_covered_claim": False,
        "os_level_network_denial_claim": False,
    }


def run_command(command: list[str], *, env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout": redact(completed.stdout[-4000:]),
        "stderr": redact(completed.stderr[-4000:]),
    }


def scan_for_real_keys() -> dict[str, Any]:
    current_key = os.environ.get("DEEPSEEK_API_KEY", "")
    paths = tracked_paths()
    paths.extend(path for path in (ROOT / "artifact_reports").rglob("*") if path.is_file()) if (ROOT / "artifact_reports").exists() else None
    matches: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        label = display_path(path)
        if current_key and current_key in text:
            matches.append(label)
            continue
        if HEX_SECRET_RE.search(text):
            matches.append(label)
    return {"ok": not matches, "matches": sorted(set(matches))}


def tracked_paths() -> list[Path]:
    completed = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return []
    return [ROOT / line for line in completed.stdout.splitlines() if line.strip()]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def tracked_forbidden_paths() -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "ls-files", "external", ".venv-hermes", "node_modules", "real_agent_integrations/hermes_mcp_server/auth_queue"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    tracked = [line for line in completed.stdout.splitlines() if line.strip()]
    return {"ok": completed.returncode == 0 and not tracked, "tracked": tracked}


def redact(text: str) -> str:
    current_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if current_key:
        text = text.replace(current_key, "[REDACTED]")
    return HEX_SECRET_RE.sub("[REDACTED]", text)


def write_reports(summary: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(format_markdown(summary), encoding="utf-8")


def format_text_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"artifact_reproduction_passed={summary['passed']}",
        f"default_no_secret={summary['default_no_secret']}",
        f"default_local_only={summary['default_local_only']}",
        f"real_hermes_run={summary['real_hermes_run']}",
        f"deepseek_called={summary['deepseek_called']}",
        f"secret_scan_ok={summary['secret_scan']['ok']}",
        f"tracked_forbidden_paths={len(summary['tracked_forbidden_paths']['tracked'])}",
    ]
    return "\n".join(lines)


def format_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Artifact Reproduction Report",
        "",
        "## Summary",
        "",
        f"- passed: {summary['passed']}",
        f"- default no secret: {summary['default_no_secret']}",
        f"- default local only: {summary['default_local_only']}",
        f"- real Hermes run: {summary['real_hermes_run']}",
        f"- DeepSeek called: {summary['deepseek_called']}",
        f"- real email: {summary['real_email']}",
        f"- real shell: {summary['real_shell']}",
        f"- external MCP: {summary['external_mcp']}",
        f"- secret scan ok: {summary['secret_scan']['ok']}",
        f"- tracked forbidden paths: {len(summary['tracked_forbidden_paths']['tracked'])}",
        "",
        "## Commands",
        "",
        "| command | returncode |",
        "| --- | --- |",
    ]
    for result in summary["commands"]:
        lines.append(f"| `{result['command']}` | {result['returncode']} |")
    lines.extend(
        [
            f"| `{summary['packaging_tests']['command']}` | {summary['packaging_tests']['returncode']} |",
            "",
            "## Non-Claims",
            "",
            "- No production-level Hermes protection.",
            "- No all-Hermes-tool-paths-covered claim.",
            "- No real email.",
            "- No external MCP.",
            "- No raw shell.",
            "- No arbitrary filesystem access.",
            "- No OS-level network-denial claim.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
