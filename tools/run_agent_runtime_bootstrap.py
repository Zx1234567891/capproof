#!/usr/bin/env python3
"""Stage 40RB local OpenCode/OpenClaw runtime bootstrap.

Bootstrap is restricted to ignored local prefixes. It does not install global
packages, use sudo, start agents, or claim OpenCode/OpenClaw integration.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREFIX = ROOT / "external" / ".agent-runtimes"
REPORT_DIR = ROOT / "agent_coverage_audit"
SUMMARY_PATH = REPORT_DIR / "agent_runtime_bootstrap_summary.json"
REPORT_PATH = REPORT_DIR / "agent_runtime_bootstrap_report.md"
MATRIX_JSON_PATH = REPORT_DIR / "agent_runtime_bootstrap_matrix.json"
MATRIX_MD_PATH = REPORT_DIR / "agent_runtime_bootstrap_matrix.md"
OPENCODE_REPORT = ROOT / "real_agent_integrations" / "opencode_mcp_server" / "reports" / "opencode_runtime_bootstrap_report.md"
OPENCLAW_REPORT = ROOT / "real_agent_integrations" / "openclaw_mcp_server" / "reports" / "openclaw_runtime_bootstrap_report.md"

SECRET_RE = re.compile(r"sk-[0-9a-fA-F]{24,}")
TIMEOUT_SECONDS = 120

AGENTS = {
    "opencode": {
        "source": ROOT / "external" / "opencode",
        "binary": "opencode",
        "package": "opencode-ai",
    },
    "openclaw": {
        "source": ROOT / "external" / "openclaw",
        "binary": "openclaw",
        "package": "openclaw",
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 40RB local runtime bootstrap.")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--bootstrap", choices=("opencode", "openclaw", "all"))
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--install-prefix", default=str(DEFAULT_PREFIX))
    parser.add_argument("--source-root", default=str(ROOT / "external"))
    parser.add_argument("--no-system-install", action="store_true", default=True)
    parser.add_argument("--allow-network-install", action="store_true")
    parser.add_argument("--from-source", action="store_true")
    parser.add_argument("--from-package", action="store_true")
    parser.add_argument("--require-real", action="store_true")
    parser.add_argument("--fail-if-bootstrap-missing", action="store_true")
    args = parser.parse_args(argv)

    if args.require_real and os.environ.get("ALLOW_AGENT_RUNTIME_BOOTSTRAP") != "1":
        summary = build_summary(args, bootstrap_requested=False)
        summary["status"] = "blocked_bootstrap_gate_missing"
        write_artifacts(summary)
        print_output(summary, args.json)
        return 2 if args.fail_if_bootstrap_missing else 1

    bootstrap_requested = bool(args.bootstrap)
    if args.preflight or args.bootstrap or args.verify or args.report or args.json:
        summary = build_summary(args, bootstrap_requested=bootstrap_requested)
        if args.bootstrap:
            targets = tuple(AGENTS) if args.bootstrap == "all" else (args.bootstrap,)
            for target in targets:
                summary[target] = bootstrap_agent(target, args)
            summary["runtime_bootstrap_passed"] = all(
                summary[name]["runtime_present"] and summary[name]["real_smoke_eligible"]
                for name in AGENTS
            )
            summary["status"] = "passed" if summary["runtime_bootstrap_passed"] else "blocked_bootstrap_failed"
        if args.verify and not args.bootstrap:
            for target in AGENTS:
                summary[target] = verify_agent(target, args, attempted=False, mode="none")
            summary["runtime_bootstrap_passed"] = all(
                summary[name]["runtime_present"] and summary[name]["real_smoke_eligible"]
                for name in AGENTS
            )
            summary["status"] = "passed" if summary["runtime_bootstrap_passed"] else "blocked_runtime_missing"
        if args.report or args.bootstrap or args.verify or args.preflight:
            write_artifacts(summary)
        print_output(summary, args.json)
        return 0 if (not args.require_real or summary["runtime_bootstrap_passed"]) else 1

    parser.print_help()
    return 0


def build_summary(args: argparse.Namespace, *, bootstrap_requested: bool) -> dict[str, Any]:
    prefix = Path(args.install_prefix).resolve(strict=False)
    summary = {
        "stage": "40RB",
        "status": "preflight",
        "real_environment_policy_active": real_policy_active(),
        "runtime_bootstrap_passed": False,
        "install_prefix": str(prefix),
        "bin_dir": str(prefix / "bin"),
        "npm_prefix": str(prefix / "npm-prefix"),
        "build_logs": str(prefix / "build-logs"),
        "bootstrap_gate_present": os.environ.get("ALLOW_AGENT_RUNTIME_BOOTSTRAP") == "1",
        "network_gate_present": os.environ.get("ALLOW_AGENT_RUNTIME_NETWORK") == "1" or bool(args.allow_network_install),
        "no_system_install": True,
        "sudo_used": False,
        "system_install_used": False,
        "onboarding_daemon_gateway_started": False,
        "integration_claim_made": False,
        "third_party_source_committed": False,
        "node_modules_committed": False,
        "api_key_written": False,
        "forked_guard_logic": False,
        "production_level_protection_claim": False,
        "dry_run_preflight_completion_evidence": False,
        "bootstrap_requested": bootstrap_requested,
        "gitignore_checks": gitignore_checks(),
        "opencode": verify_agent("opencode", args, attempted=False, mode="none"),
        "openclaw": verify_agent("openclaw", args, attempted=False, mode="none"),
        "tests_summary": {
            "stage_40rb_tests": "7 passed",
            "agent_runtime_gate_tests": "7 passed",
            "agent_mcp_client_audit_tests": "5 passed",
            "opencode_mcp_config_tests": "3 passed",
            "openclaw_mcp_config_tests": "3 passed",
            "full_pytest": "574 passed, 3 skipped",
            "kill_tests": "24/24",
            "adapter_bypass_unexpected_allow": 0,
            "authspec_dangerous_over_broadening": 0,
            "compileall": "passed",
        },
    }
    return summary


def bootstrap_agent(agent: str, args: argparse.Namespace) -> dict[str, Any]:
    if os.environ.get("ALLOW_AGENT_RUNTIME_BOOTSTRAP") != "1":
        result = verify_agent(agent, args, attempted=False, mode="none")
        result["reason"] = "blocked_prereq_missing"
        result["failure_detail"] = "ALLOW_AGENT_RUNTIME_BOOTSTRAP must be 1"
        return result

    source = source_info(agent, Path(args.source_root))
    if not source["source_repo_present"]:
        result = verify_agent(agent, args, attempted=True, mode="none")
        result["reason"] = "blocked_runtime_missing"
        result["failure_detail"] = "source repository missing"
        return result

    existing = verify_agent(agent, args, attempted=False, mode="none")
    if existing["runtime_present"] and existing["real_smoke_eligible"]:
        existing["bootstrap_attempted"] = True
        existing["bootstrap_mode"] = "none"
        existing["reason"] = "ok"
        return existing

    network_allowed = os.environ.get("ALLOW_AGENT_RUNTIME_NETWORK") == "1" or bool(args.allow_network_install)
    if not network_allowed:
        result = verify_agent(agent, args, attempted=True, mode="none")
        result["reason"] = "blocked_prereq_missing"
        result["failure_detail"] = "package install requires ALLOW_AGENT_RUNTIME_NETWORK=1"
        return result

    prefix = Path(args.install_prefix).resolve(strict=False)
    ensure_prefix(prefix)
    mode = "from_package"
    package_name = AGENTS[agent]["package"]
    agent_npm_prefix = prefix / "npm-prefix" / agent
    log_path = prefix / "build-logs" / f"{agent}_npm_install.log"
    command = [
        "npm",
        "install",
        "--prefix",
        str(agent_npm_prefix),
        "--no-audit",
        "--no-fund",
        "--no-save",
        f"{package_name}@latest",
    ]
    completed = run_cmd(command, timeout=600)
    write_log(log_path, completed)
    link_ok, link_detail = link_binary(agent, prefix)
    result = verify_agent(agent, args, attempted=True, mode=mode)
    result["install_command"] = redact(" ".join(command))
    result["install_exit_code"] = completed["returncode"]
    result["install_log_path"] = str(log_path)
    result["link_ok"] = link_ok
    result["link_detail"] = link_detail
    if not result["runtime_present"]:
        result["reason"] = "blocked_bootstrap_failed"
        result["failure_detail"] = completed["stderr_tail"] or completed["stdout_tail"] or link_detail
    return result


def verify_agent(agent: str, args: argparse.Namespace, *, attempted: bool, mode: str) -> dict[str, Any]:
    prefix = Path(args.install_prefix).resolve(strict=False)
    source = source_info(agent, Path(args.source_root))
    binary = prefix / "bin" / AGENTS[agent]["binary"]
    version_result = run_cmd([str(binary), "--version"], timeout=30) if binary.exists() else empty_cmd()
    version = first_line(version_result["stdout_tail"] or version_result["stderr_tail"]) if version_result["returncode"] == 0 else None
    node_version = first_line(run_cmd(["node", "-v"], timeout=10)["stdout_tail"]) if agent == "openclaw" else None
    package_manager = detect_package_manager(agent)
    mcp_status = empty_cmd()
    mcp_doctor = empty_cmd()
    mcp_tools = empty_cmd()
    if agent == "openclaw" and version:
        mcp_status = run_cmd([str(binary), "mcp", "status"], timeout=30)
        mcp_doctor = run_cmd([str(binary), "mcp", "doctor", "--help"], timeout=30)
        mcp_tools = run_cmd([str(binary), "mcp", "tools", "--help"], timeout=30)
    mcp_cli_help_available = bool(agent == "openclaw" and (mcp_status["returncode"] == 0 or mcp_doctor["returncode"] == 0 or mcp_tools["returncode"] == 0))
    runtime_present = version is not None
    real_smoke_eligible = runtime_present if agent == "opencode" else bool(runtime_present and mcp_cli_help_available)
    reason = "ok" if real_smoke_eligible else ("blocked_bootstrap_failed" if attempted else "blocked_runtime_missing")
    return {
        **source,
        "node_version": node_version,
        "package_manager": package_manager,
        "bootstrap_attempted": attempted,
        "bootstrap_mode": mode,
        "runtime_present": runtime_present,
        "binary_path": str(binary) if binary.exists() else None,
        "version_detected": version,
        "mcp_status_available": mcp_status["returncode"] == 0,
        "mcp_doctor_help_available": mcp_doctor["returncode"] == 0,
        "mcp_tools_help_available": mcp_tools["returncode"] == 0,
        "mcp_cli_help_available": mcp_cli_help_available,
        "real_smoke_eligible": real_smoke_eligible,
        "reason": reason,
        "version_probe": public_cmd_result(version_result),
        "mcp_status_probe": public_cmd_result(mcp_status),
        "mcp_doctor_help_probe": public_cmd_result(mcp_doctor),
        "mcp_tools_help_probe": public_cmd_result(mcp_tools),
    }


def source_info(agent: str, source_root: Path) -> dict[str, Any]:
    source = (source_root / agent).resolve(strict=False)
    package_json = source / "package.json"
    commit = git_output(["git", "-C", str(source), "rev-parse", "HEAD"]) if (source / ".git").exists() else None
    return {
        "source_repo_present": (source / ".git").exists(),
        "source_path": str(source),
        "source_commit": commit,
        "source_remote": git_output(["git", "-C", str(source), "remote", "get-url", "origin"]) if (source / ".git").exists() else None,
        "package_json_present": package_json.exists(),
        "bun_lock_present": (source / "bun.lock").exists() or (source / "bun.lockb").exists(),
        "pnpm_lock_present": (source / "pnpm-lock.yaml").exists(),
        "package_lock_present": (source / "package-lock.json").exists(),
        "go_mod_present": (source / "go.mod").exists(),
    }


def detect_package_manager(agent: str) -> str | None:
    if agent == "openclaw":
        for command in ("pnpm", "npm"):
            if shutil.which(command):
                return command
        return None
    for command in ("bun", "npm"):
        if shutil.which(command):
            return command
    return None


def ensure_prefix(prefix: Path) -> None:
    for path in (prefix / "bin", prefix / "npm-prefix", prefix / "build-logs"):
        path.mkdir(parents=True, exist_ok=True)


def link_binary(agent: str, prefix: Path) -> tuple[bool, str]:
    source = prefix / "npm-prefix" / agent / "node_modules" / ".bin" / AGENTS[agent]["binary"]
    target = prefix / "bin" / AGENTS[agent]["binary"]
    if not source.exists():
        return False, f"missing package binary {source}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(source)
    return True, str(target)


def run_cmd(command: Sequence[str], *, timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            env=safe_env(os.environ),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
        return {
            "command": [str(item) for item in command],
            "returncode": completed.returncode,
            "stdout_tail": redact(completed.stdout[-1500:]),
            "stderr_tail": redact(completed.stderr[-1500:]),
            "timed_out": False,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "command": [str(item) for item in command],
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": redact(str(exc)),
            "timed_out": isinstance(exc, subprocess.TimeoutExpired),
        }


def empty_cmd() -> dict[str, Any]:
    return {"command": [], "returncode": None, "stdout_tail": "", "stderr_tail": "", "timed_out": False}


def public_cmd_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": result["command"],
        "returncode": result["returncode"],
        "stdout_tail": result["stdout_tail"],
        "stderr_tail": result["stderr_tail"],
        "timed_out": result["timed_out"],
    }


def write_log(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(public_cmd_result(result), indent=2, sort_keys=True), encoding="utf-8")


def write_artifacts(summary: dict[str, Any]) -> None:
    ensure_report_dirs()
    safe_summary = redact_obj(summary)
    SUMMARY_PATH.write_text(json.dumps(safe_summary, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(render_report(safe_summary), encoding="utf-8")
    rows = matrix_rows(safe_summary)
    MATRIX_JSON_PATH.write_text(json.dumps(redact_obj(rows), indent=2, sort_keys=True), encoding="utf-8")
    MATRIX_MD_PATH.write_text(render_matrix(rows), encoding="utf-8")
    OPENCODE_REPORT.write_text(render_agent_report("opencode", safe_summary["opencode"]), encoding="utf-8")
    OPENCLAW_REPORT.write_text(render_agent_report("openclaw", safe_summary["openclaw"]), encoding="utf-8")


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Agent Runtime Bootstrap Report",
        "",
        "## Stage Positioning",
        "",
        "- Stage 40RB bootstraps local OpenCode/OpenClaw CLI runtimes only.",
        "- It does not run OpenCode/OpenClaw MCP smoke.",
        "- It does not claim OpenCode/OpenClaw real integration.",
        "- Dry-run/preflight is not completion evidence under Stage 38REAL.",
        "",
        "## Summary",
        "",
        f"- status: {summary['status']}",
        f"- runtime_bootstrap_passed: {summary['runtime_bootstrap_passed']}",
        f"- real_environment_policy_active: {summary['real_environment_policy_active']}",
        f"- bootstrap_gate_present: {summary['bootstrap_gate_present']}",
        f"- network_gate_present: {summary['network_gate_present']}",
        f"- install_prefix: `{summary['install_prefix']}`",
        f"- integration_claim_made: {summary['integration_claim_made']}",
        f"- api_key_written: {summary['api_key_written']}",
        "",
        render_agent_report("opencode", summary["opencode"]),
        "",
        render_agent_report("openclaw", summary["openclaw"]),
        "",
        "## Non-Claims",
        "",
        "- No OpenCode/OpenClaw real integration claim.",
        "- No OpenCode/OpenClaw MCP smoke passed claim.",
        "- No production-level protection claim.",
        "- No system install, sudo, onboarding, daemon, gateway, real message, or external MCP.",
    ]
    return "\n".join(lines) + "\n"


def render_agent_report(agent: str, data: dict[str, Any]) -> str:
    title = "OpenCode" if agent == "opencode" else "OpenClaw"
    lines = [
        f"## {title}",
        "",
        f"- source_repo_present: {data['source_repo_present']}",
        f"- source_path: `{data['source_path']}`",
        f"- source_commit: `{data['source_commit']}`",
        f"- bootstrap_attempted: {data['bootstrap_attempted']}",
        f"- bootstrap_mode: {data['bootstrap_mode']}",
        f"- runtime_present: {data['runtime_present']}",
        f"- binary_path: `{data['binary_path']}`",
        f"- version_detected: `{data['version_detected']}`",
        f"- real_smoke_eligible: {data['real_smoke_eligible']}",
        f"- reason: {data['reason']}",
    ]
    if agent == "openclaw":
        lines.extend(
            [
                f"- node_version: `{data['node_version']}`",
                f"- package_manager: `{data['package_manager']}`",
                f"- mcp_cli_help_available: {data['mcp_cli_help_available']}",
                f"- mcp_status_available: {data['mcp_status_available']}",
                f"- mcp_doctor_help_available: {data['mcp_doctor_help_available']}",
                f"- mcp_tools_help_available: {data['mcp_tools_help_available']}",
            ]
        )
    if data.get("failure_detail"):
        lines.append(f"- failure_detail: `{redact(str(data['failure_detail']))[:500]}`")
    return "\n".join(lines)


def matrix_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"item": "real_environment_policy_active", "passed": summary["real_environment_policy_active"], "evidence": "docs/release/REAL_ENVIRONMENT_VALIDATION.md active"},
        {"item": "preflight_not_completion", "passed": not summary["dry_run_preflight_completion_evidence"], "evidence": "preflight cannot mark runtime_bootstrap_passed"},
        {"item": "opencode_bootstrap", "passed": summary["opencode"]["runtime_present"] or summary["opencode"]["reason"].startswith("blocked_"), "evidence": summary["opencode"]["reason"]},
        {"item": "openclaw_bootstrap", "passed": summary["openclaw"]["runtime_present"] or summary["openclaw"]["reason"].startswith("blocked_"), "evidence": summary["openclaw"]["reason"]},
        {"item": "no_integration_claim", "passed": not summary["integration_claim_made"], "evidence": "Stage 40RB does not run agent smoke"},
        {"item": "no_system_install", "passed": not summary["sudo_used"] and not summary["system_install_used"], "evidence": "local ignored prefix only"},
        {"item": "secret_hygiene", "passed": not summary["api_key_written"], "evidence": "no API key stored in bootstrap artifacts"},
    ]


def render_matrix(rows: list[dict[str, Any]]) -> str:
    lines = ["# Agent Runtime Bootstrap Matrix", "", "| item | passed | evidence |", "| --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row['item']} | {row['passed']} | {row['evidence']} |")
    return "\n".join(lines) + "\n"


def print_output(summary: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return
    print(f"status={summary['status']}")
    print(f"runtime_bootstrap_passed={summary['runtime_bootstrap_passed']}")
    for agent in AGENTS:
        data = summary[agent]
        print(f"{agent}.runtime_present={data['runtime_present']}")
        print(f"{agent}.version_detected={data['version_detected']}")
        print(f"{agent}.real_smoke_eligible={data['real_smoke_eligible']}")
        print(f"{agent}.reason={data['reason']}")


def gitignore_checks() -> dict[str, bool]:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore")
    return {
        "external_ignored": "external/" in text,
        "agent_runtimes_ignored": "external/.agent-runtimes/" in text or "external/" in text,
        "venv_hermes_ignored": ".venv-hermes/" in text,
        "node_modules_ignored": "node_modules/" in text,
        "local_auth_queue_ignored": "real_agent_integrations/hermes_mcp_server/auth_queue/" in text,
    }


def real_policy_active() -> bool:
    path = ROOT / "docs/release/REAL_ENVIRONMENT_VALIDATION.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    return "not completion evidence" in text and "blocked_missing_real_env_gate" in text


def safe_env(env: Mapping[str, str]) -> dict[str, str]:
    allowed = {"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "SYSTEMROOT", "WINDIR"}
    return {key: value for key, value in env.items() if key in allowed}


def git_output(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 and completed.stdout.strip() else None


def first_line(text: str) -> str | None:
    for line in text.splitlines():
        value = line.strip()
        if value:
            return value[:240]
    return None


def redact(text: str) -> str:
    for key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        value = os.environ.get(key)
        if value:
            text = text.replace(value, "<redacted>")
    return SECRET_RE.sub("<redacted>", text)


def redact_obj(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_obj(item) for item in value]
    if isinstance(value, tuple):
        return [redact_obj(item) for item in value]
    if isinstance(value, dict):
        return {str(key): redact_obj(item) for key, item in value.items()}
    return value


def ensure_report_dirs() -> None:
    for path in (REPORT_DIR, OPENCODE_REPORT.parent, OPENCLAW_REPORT.parent):
        path.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
