#!/usr/bin/env python3
"""Doctor checks for the foreground Hermes + CapProof MCP setup.

The doctor is intentionally local-only. It does not run Hermes, call DeepSeek,
or execute authority-bearing tools beyond a local `tools/list` check.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer

import run_real_hermes_foreground_mcp_demo as foreground


ROOT = Path(__file__).resolve().parent
SERVER_SCRIPT = ROOT / "run_capproof_mcp_server.py"
STDIO_RECORDER = ROOT / "run_capproof_mcp_stdio_recorder.py"
SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]{12,}")
UX_REPORT = foreground.REPORT_DIR / "foreground_ux_report.md"
UX_SUMMARY = foreground.REPORT_DIR / "foreground_ux_summary.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check foreground Hermes CapProof MCP UX readiness.")
    parser.add_argument("--all", action="store_true", help="run all doctor checks")
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args(argv)

    summary = run_checks()
    write_reports(summary)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(format_summary(summary))
    return 0 if summary["passed"] else 1


def run_checks() -> dict[str, Any]:
    foreground.ensure_dirs()
    foreground.SANDBOX_WORKSPACE.mkdir(parents=True, exist_ok=True)
    key_present = bool(os.environ.get("DEEPSEEK_API_KEY"))
    tools_check = check_tools_list()
    trace_writable = directory_writable(foreground.TRACE_DIR)
    live_log_writable = directory_writable(foreground.REPORT_DIR)
    secret_scan = scan_for_secrets()
    stdio_check = check_stdio_stdout_pollution()
    tracked_check = check_untracked_forbidden_paths()
    checks = {
        "deepseek_api_key_present": key_present,
        "deepseek_api_key_value_redacted": True,
        "capproof_mcp_server_command_exists": SERVER_SCRIPT.exists(),
        "capproof_mcp_stdio_recorder_exists": STDIO_RECORDER.exists(),
        "run_capproof_mcp_server_import_ok": check_import_ok(),
        "tools_list_ok": tools_check["ok"],
        "tools_count": tools_check["tools_count"],
        "tools": tools_check["tools"],
        "trace_directory_writable": trace_writable,
        "live_log_directory_writable": live_log_writable,
        "sandbox_workspace_exists": foreground.SANDBOX_WORKSPACE.exists(),
        "external_venv_node_modules_not_tracked": tracked_check,
        "api_key_not_found_in_tracked_files_reports_traces": secret_scan["ok"],
        "secret_scan_matches": secret_scan["match_count"],
        "mcp_stdio_stdout_pollution_check_passes": stdio_check["ok"],
        "mcp_stdio_stdout_lines": stdio_check["stdout_lines"],
        "mcp_stdio_stderr_nonempty": stdio_check["stderr_nonempty"],
        "deepseek_not_safety_tcb": True,
        "capproof_guard_gates_tools": True,
        "production_level_protection_claim": False,
    }
    passed = all(
        bool(checks[name])
        for name in (
            "capproof_mcp_server_command_exists",
            "capproof_mcp_stdio_recorder_exists",
            "run_capproof_mcp_server_import_ok",
            "tools_list_ok",
            "trace_directory_writable",
            "live_log_directory_writable",
            "sandbox_workspace_exists",
            "external_venv_node_modules_not_tracked",
            "api_key_not_found_in_tracked_files_reports_traces",
            "mcp_stdio_stdout_pollution_check_passes",
        )
    )
    return {
        "stage": "35UX",
        "passed": passed,
        "trace_path": str(foreground.TRACE_PATH),
        "live_log_path": str(foreground.LIVE_LOG_PATH),
        "sandbox_workspace": str(foreground.SANDBOX_WORKSPACE),
        "mcp_server_command": str(SERVER_SCRIPT),
        "mcp_mode": "stdio",
        "sandboxed_real_execution": True,
        "checks": checks,
    }


def check_tools_list() -> dict[str, Any]:
    context = make_default_context(workspace=foreground.SANDBOX_WORKSPACE, trace_path=foreground.TRACE_PATH, executor_mode="sandbox")
    server = CapProofMCPServer(context=context)
    tools = server.list_tools()["tools"]
    names = [str(tool.get("name", "")) for tool in tools]
    return {"ok": len(names) == 7, "tools_count": len(names), "tools": names}


def check_import_ok() -> bool:
    try:
        __import__("run_capproof_mcp_server")
    except Exception:
        return False
    return True


def directory_writable(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(prefix=".doctor_", dir=path, delete=True) as handle:
            handle.write(b"ok")
        return True
    except OSError:
        return False


def check_untracked_forbidden_paths() -> bool:
    result = subprocess.run(
        ["git", "ls-files", "external", ".venv-hermes", "node_modules"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and not result.stdout.strip()


def scan_for_secrets() -> dict[str, Any]:
    tracked = tracked_paths()
    report_trace_paths: list[Path] = []
    for directory in (foreground.REPORT_DIR, foreground.TRACE_DIR):
        if directory.exists():
            report_trace_paths.extend(path for path in directory.rglob("*") if path.is_file())
    current_key = os.environ.get("DEEPSEEK_API_KEY", "")
    current_key_matches = 0
    report_trace_token_like_matches = 0
    seen: set[Path] = set()
    for path in tracked + report_trace_paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if current_key and current_key in text:
            current_key_matches += 1
        if path in report_trace_paths and SECRET_RE.search(text):
            report_trace_token_like_matches += 1
    return {
        "ok": current_key_matches == 0 and report_trace_token_like_matches == 0,
        "match_count": current_key_matches + report_trace_token_like_matches,
        "current_key_matches": current_key_matches,
        "report_trace_token_like_matches": report_trace_token_like_matches,
    }


def tracked_paths() -> list[Path]:
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def check_stdio_stdout_pollution() -> dict[str, Any]:
    initialize = {"jsonrpc": "2.0", "id": "init", "method": "initialize", "params": {}}
    tools_list = {"jsonrpc": "2.0", "id": "tools", "method": "tools/list", "params": {}}
    payload = json.dumps(initialize) + "\n" + json.dumps(tools_list) + "\n"
    completed = subprocess.run(
        [sys.executable, str(SERVER_SCRIPT), "--stdio"],
        cwd=ROOT,
        input=payload,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    valid_json_lines = 0
    polluted = False
    for line in completed.stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            polluted = True
            continue
        if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
            polluted = True
        valid_json_lines += 1
    return {
        "ok": completed.returncode == 0 and not polluted and valid_json_lines >= 2,
        "stdout_lines": valid_json_lines,
        "stderr_nonempty": bool(completed.stderr.strip()),
    }


def format_summary(summary: dict[str, Any]) -> str:
    checks = summary["checks"]
    lines = [
        f"doctor_passed={summary['passed']}",
        f"deepseek_api_key_present={checks['deepseek_api_key_present']}",
        "deepseek_api_key_value=REDACTED",
        f"mcp_mode={summary['mcp_mode']}",
        f"sandboxed_real_execution={summary['sandboxed_real_execution']}",
        f"tools_list_ok={checks['tools_list_ok']}",
        f"tools_count={checks['tools_count']}",
        f"trace_path={summary['trace_path']}",
        f"live_log_path={summary['live_log_path']}",
        f"sandbox_workspace={summary['sandbox_workspace']}",
        f"api_key_scan_ok={checks['api_key_not_found_in_tracked_files_reports_traces']}",
        f"mcp_stdio_stdout_pollution_check_passes={checks['mcp_stdio_stdout_pollution_check_passes']}",
        "safety_boundary=DeepSeek not safety TCB; CapProof guard gates tools",
    ]
    return "\n".join(lines)


def write_reports(summary: dict[str, Any]) -> None:
    foreground.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    UX_SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    checks = summary["checks"]
    lines = [
        "# Foreground Hermes CapProof MCP UX Report",
        "",
        "## Stage Positioning",
        "",
        "- Stage 35UX improves foreground usability; it does not change CapProof core verifier or Reference Monitor semantics.",
        "- Doctor and trace viewer do not run Hermes or call DeepSeek by default.",
        "- DeepSeek remains model-backend-only and outside the CapProof safety TCB.",
        "- CapProof guard remains the tool execution gate.",
        "- No production-level Hermes protection is claimed.",
        "",
        "## Doctor Summary",
        "",
        f"- passed: {summary['passed']}",
        f"- DeepSeek key present: {checks['deepseek_api_key_present']} (value redacted)",
        f"- MCP server command exists: {checks['capproof_mcp_server_command_exists']}",
        f"- tools/list returns 7 tools: {checks['tools_list_ok']}",
        f"- tools count: {checks['tools_count']}",
        f"- trace directory writable: {checks['trace_directory_writable']}",
        f"- live log directory writable: {checks['live_log_directory_writable']}",
        f"- sandbox workspace exists: {checks['sandbox_workspace_exists']}",
        f"- external/.venv/node_modules not tracked: {checks['external_venv_node_modules_not_tracked']}",
        f"- API key scan ok: {checks['api_key_not_found_in_tracked_files_reports_traces']}",
        f"- MCP stdio stdout pollution check passes: {checks['mcp_stdio_stdout_pollution_check_passes']}",
        "",
        "## Paths",
        "",
        f"- trace: `{summary['trace_path']}`",
        f"- live log: `{summary['live_log_path']}`",
        f"- sandbox workspace: `{summary['sandbox_workspace']}`",
    ]
    UX_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
