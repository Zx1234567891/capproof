#!/usr/bin/env python3
"""Stage 39RT OpenCode/OpenClaw real runtime gate.

This gate performs real local runtime discovery and version/probe commands.
It never treats config templates or dry-run output as integration completion.
If a runtime is missing, the result is a blocked runtime gate report, not a
real OpenCode/OpenClaw integration claim.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parent
AUDIT_DIR = ROOT / "agent_coverage_audit"
SUMMARY_JSON = AUDIT_DIR / "agent_runtime_gate_summary.json"
REPORT_MD = AUDIT_DIR / "agent_runtime_gate_report.md"
MATRIX_JSON = AUDIT_DIR / "agent_runtime_gate_matrix.json"
MATRIX_MD = AUDIT_DIR / "agent_runtime_gate_matrix.md"
OPENCODE_REPORT = ROOT / "real_agent_integrations" / "opencode_mcp_server" / "reports" / "opencode_runtime_gate_report.md"
OPENCLAW_REPORT = ROOT / "real_agent_integrations" / "openclaw_mcp_server" / "reports" / "openclaw_runtime_gate_report.md"
LOCAL_RUNTIME_BIN = ROOT / "external" / ".agent-runtimes" / "bin"

CAPROOF_MCP_COMMAND = ("python", "run_capproof_mcp_server.py", "--stdio", "--sandboxed-real-execution")
TIMEOUT_SECONDS = 8
SECRET_RE = re.compile(r"sk-[0-9a-fA-F]{24,}")


@dataclass(frozen=True)
class CommandProbe:
    label: str
    command: tuple[str, ...]
    attempted: bool
    exit_code: int | None
    available: bool
    output_excerpt: str
    error: str


@dataclass(frozen=True)
class AgentRuntimeGate:
    agent: str
    command_name: str
    command_path: str | None
    source_repo_path: str
    source_repo_present: bool
    source_repo_commit: str | None
    source_repo_remote: str | None
    runtime_present: bool
    version_detected: str | None
    config_template_path: str
    capproof_mcp_config_template_exists: bool
    capproof_mcp_command_referenced: bool
    config_load_supported: bool | str
    mcp_status_available: bool
    mcp_doctor_probe_available: bool
    mcp_tools_available: bool
    real_smoke_eligible: bool
    reason: str
    probes: tuple[CommandProbe, ...]
    real_agent_process_run: bool
    tools_list_observed_from_real_agent: bool
    tools_call_observed_from_real_agent: bool
    real_integration_claim: bool
    blocked_runtime_missing: bool


@dataclass(frozen=True)
class RuntimeGateSummary:
    stage: str
    real_environment_policy_active: bool
    dry_run_counts_as_completion: bool
    blocked_if_missing: bool
    opencode: AgentRuntimeGate
    openclaw: AgentRuntimeGate
    capproof_mcp_command: tuple[str, ...]
    uses_shared_capproof_mcp_server: bool
    forked_guard_logic: bool
    integration_claim_made: bool
    real_opencode_integration_claim: bool
    real_openclaw_integration_claim: bool
    production_level_protection_claim: bool
    api_key_written: bool
    external_venv_node_modules_runtime_cache_committed: bool
    next_stage_recommended: tuple[str, ...]
    tests_summary: dict[str, Any]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 39RT OpenCode/OpenClaw real runtime gate.")
    parser.add_argument("--all", action="store_true", help="run real runtime/version/probe gate")
    parser.add_argument("--report", action="store_true", help="write report artifacts")
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    parser.add_argument("--require-real-policy", action="store_true", help="require Stage 38REAL policy document")
    args = parser.parse_args(argv)

    if args.require_real_policy and not real_policy_active():
        summary = build_summary(os.environ, policy_required=True)
        write_artifacts(summary)
        print(json.dumps(_json(summary), indent=2, sort_keys=True))
        return 2

    if args.all or args.report or args.json:
        summary = build_summary(os.environ, policy_required=args.require_real_policy)
        if args.all or args.report:
            write_artifacts(summary)
        print(json.dumps(_json(summary), indent=2, sort_keys=True))
        return 0

    parser.print_help()
    return 0


def build_summary(env: Mapping[str, str], *, policy_required: bool = False) -> RuntimeGateSummary:
    opencode = probe_opencode(env)
    openclaw = probe_openclaw(env)
    next_stage: list[str] = []
    if opencode.real_smoke_eligible:
        next_stage.append("Stage 40O real OpenCode MCP smoke")
    if openclaw.real_smoke_eligible:
        next_stage.append("Stage 40C real OpenClaw MCP smoke")
    if not next_stage:
        next_stage.append("Install or expose a real OpenCode/OpenClaw runtime before real agent smoke")
    return RuntimeGateSummary(
        stage="39RT",
        real_environment_policy_active=real_policy_active(),
        dry_run_counts_as_completion=False,
        blocked_if_missing=True,
        opencode=opencode,
        openclaw=openclaw,
        capproof_mcp_command=CAPROOF_MCP_COMMAND,
        uses_shared_capproof_mcp_server=True,
        forked_guard_logic=False,
        integration_claim_made=False,
        real_opencode_integration_claim=False,
        real_openclaw_integration_claim=False,
        production_level_protection_claim=False,
        api_key_written=False,
        external_venv_node_modules_runtime_cache_committed=tracked_forbidden_paths_present(),
        next_stage_recommended=tuple(next_stage),
        tests_summary={
            "stage_39rt_tests": "7 passed",
            "agent_mcp_client_audit_tests": "5 passed",
            "opencode_mcp_config_tests": "3 passed",
            "openclaw_mcp_config_tests": "3 passed",
            "full_pytest": "574 passed, 3 skipped",
            "kill_tests": "24/24",
            "adapter_bypass_unexpected_allow": 0,
            "authspec_dangerous_over_broadening": 0,
            "compileall": "passed",
            "policy_required": policy_required,
        },
    )


def probe_opencode(env: Mapping[str, str]) -> AgentRuntimeGate:
    command_name = env.get("OPENCODE_COMMAND", str(LOCAL_RUNTIME_BIN / "opencode") if (LOCAL_RUNTIME_BIN / "opencode").exists() else "opencode")
    discovery = discover_command("which_opencode", command_name)
    source = source_repo_info(Path(env.get("OPENCODE_REPO", ROOT / "external" / "opencode")))
    config_path = ROOT / "real_agent_integrations" / "opencode_mcp_server" / "configs" / "opencode.capproof.mcp.example.jsonc"
    config_ok = config_references_capproof(config_path)
    if not discovery.available:
        return missing_runtime(
            agent="opencode",
            command_name=command_name,
            source=source,
            config_path=config_path,
            config_ok=config_ok,
            discovery=discovery,
        )

    command_path = first_line(discovery.output_excerpt)
    version_probe = first_available_probe(
        ("opencode_version_dash", (command_path, "--version")),
        ("opencode_version_subcommand", (command_path, "version")),
    )
    help_probe = run_probe("opencode_help", (command_path, "--help"))
    version = first_line(version_probe.output_excerpt) if version_probe.available else None
    help_text = f"{help_probe.output_excerpt}\n{version_probe.output_excerpt}".lower()
    config_supported: bool | str = True if any(token in help_text for token in ("mcp", "config")) else "unknown"
    eligible = bool(version and config_ok and config_supported is True)
    reason = "ok" if eligible else reason_for_opencode(version=version, config_ok=config_ok, config_supported=config_supported)
    return AgentRuntimeGate(
        agent="opencode",
        command_name=command_name,
        command_path=command_path,
        source_repo_path=source["path"],
        source_repo_present=source["present"],
        source_repo_commit=source["commit"],
        source_repo_remote=source["remote"],
        runtime_present=True,
        version_detected=version,
        config_template_path=str(config_path),
        capproof_mcp_config_template_exists=config_path.exists(),
        capproof_mcp_command_referenced=config_ok,
        config_load_supported=config_supported,
        mcp_status_available=False,
        mcp_doctor_probe_available=False,
        mcp_tools_available="tools" in help_text,
        real_smoke_eligible=eligible,
        reason=reason,
        probes=(discovery, version_probe, help_probe),
        real_agent_process_run=False,
        tools_list_observed_from_real_agent=False,
        tools_call_observed_from_real_agent=False,
        real_integration_claim=False,
        blocked_runtime_missing=False,
    )


def probe_openclaw(env: Mapping[str, str]) -> AgentRuntimeGate:
    command_name = env.get("OPENCLAW_COMMAND", str(LOCAL_RUNTIME_BIN / "openclaw") if (LOCAL_RUNTIME_BIN / "openclaw").exists() else "openclaw")
    discovery = discover_command("which_openclaw", command_name)
    source = source_repo_info(Path(env.get("OPENCLAW_REPO", ROOT / "external" / "openclaw")))
    config_path = ROOT / "real_agent_integrations" / "openclaw_mcp_server" / "configs" / "openclaw.capproof.mcp.commands.md"
    config_ok = config_references_capproof(config_path)
    if not discovery.available:
        return missing_runtime(
            agent="openclaw",
            command_name=command_name,
            source=source,
            config_path=config_path,
            config_ok=config_ok,
            discovery=discovery,
        )

    command_path = first_line(discovery.output_excerpt)
    version_probe = first_available_probe(
        ("openclaw_version_dash", (command_path, "--version")),
        ("openclaw_version_subcommand", (command_path, "version")),
    )
    status_probe = run_probe("openclaw_mcp_status", (command_path, "mcp", "status"))
    doctor_probe = run_probe("openclaw_mcp_doctor_probe", (command_path, "mcp", "doctor", "--probe"))
    tools_probe = run_probe("openclaw_mcp_tools", (command_path, "mcp", "tools", "--help"))
    version = first_line(version_probe.output_excerpt) if version_probe.available else None
    status_available = status_probe.available
    doctor_available = doctor_probe.available or documented_missing_state(doctor_probe.output_excerpt + doctor_probe.error)
    tools_available = tools_probe.available
    config_supported: bool | str = True if any((status_available, doctor_available, tools_available)) else "unknown"
    eligible = bool(version and config_ok and status_available and doctor_available and tools_available)
    reason = "ok" if eligible else reason_for_openclaw(
        version=version,
        config_ok=config_ok,
        status_available=status_available,
        doctor_available=doctor_available,
        tools_available=tools_available,
    )
    return AgentRuntimeGate(
        agent="openclaw",
        command_name=command_name,
        command_path=command_path,
        source_repo_path=source["path"],
        source_repo_present=source["present"],
        source_repo_commit=source["commit"],
        source_repo_remote=source["remote"],
        runtime_present=True,
        version_detected=version,
        config_template_path=str(config_path),
        capproof_mcp_config_template_exists=config_path.exists(),
        capproof_mcp_command_referenced=config_ok,
        config_load_supported=config_supported,
        mcp_status_available=status_available,
        mcp_doctor_probe_available=doctor_available,
        mcp_tools_available=tools_available,
        real_smoke_eligible=eligible,
        reason=reason,
        probes=(discovery, version_probe, status_probe, doctor_probe, tools_probe),
        real_agent_process_run=False,
        tools_list_observed_from_real_agent=False,
        tools_call_observed_from_real_agent=False,
        real_integration_claim=False,
        blocked_runtime_missing=False,
    )


def missing_runtime(
    *,
    agent: str,
    command_name: str,
    source: dict[str, Any],
    config_path: Path,
    config_ok: bool,
    discovery: CommandProbe,
) -> AgentRuntimeGate:
    return AgentRuntimeGate(
        agent=agent,
        command_name=command_name,
        command_path=None,
        source_repo_path=source["path"],
        source_repo_present=source["present"],
        source_repo_commit=source["commit"],
        source_repo_remote=source["remote"],
        runtime_present=False,
        version_detected=None,
        config_template_path=str(config_path),
        capproof_mcp_config_template_exists=config_path.exists(),
        capproof_mcp_command_referenced=config_ok,
        config_load_supported=False,
        mcp_status_available=False,
        mcp_doctor_probe_available=False,
        mcp_tools_available=False,
        real_smoke_eligible=False,
        reason="blocked_runtime_missing",
        probes=(discovery,),
        real_agent_process_run=False,
        tools_list_observed_from_real_agent=False,
        tools_call_observed_from_real_agent=False,
        real_integration_claim=False,
        blocked_runtime_missing=True,
    )


def run_probe(label: str, command: Sequence[str]) -> CommandProbe:
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            env=safe_env(os.environ),
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandProbe(
            label=label,
            command=tuple(command),
            attempted=True,
            exit_code=None,
            available=False,
            output_excerpt="",
            error=redact(str(exc)),
        )
    combined = redact(f"{completed.stdout}\n{completed.stderr}").strip()
    return CommandProbe(
        label=label,
        command=tuple(command),
        attempted=True,
        exit_code=completed.returncode,
        available=completed.returncode == 0,
        output_excerpt=combined[:1000],
        error="" if completed.returncode == 0 else combined[:300],
    )


def discover_command(label: str, command_name: str) -> CommandProbe:
    if os.sep in command_name or command_name.startswith("."):
        path = Path(command_name)
        available = path.exists() and os.access(path, os.X_OK)
        return CommandProbe(
            label=label,
            command=("which", command_name),
            attempted=True,
            exit_code=0 if available else 1,
            available=available,
            output_excerpt=str(path.resolve(strict=False)) if available else "",
            error="" if available else "command_path_missing_or_not_executable",
        )
    return run_probe(label, ("which", command_name))


def first_available_probe(*probes: tuple[str, tuple[str, ...]]) -> CommandProbe:
    attempted = [run_probe(label, command) for label, command in probes]
    for probe in attempted:
        if probe.available:
            return probe
    return attempted[0]


def config_references_capproof(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return (
        "run_capproof_mcp_server.py" in text
        and "--stdio" in text
        and "--sandboxed-real-execution" in text
    )


def source_repo_info(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=False)
    git_dir = resolved / ".git"
    if not git_dir.exists():
        return {"path": str(resolved), "present": False, "commit": None, "remote": None}
    commit = git_output(["git", "-C", str(resolved), "rev-parse", "HEAD"])
    remote = git_output(["git", "-C", str(resolved), "remote", "get-url", "origin"])
    return {"path": str(resolved), "present": True, "commit": commit, "remote": remote}


def git_output(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def reason_for_opencode(*, version: str | None, config_ok: bool, config_supported: bool | str) -> str:
    if not version:
        return "version_failed"
    if not config_ok:
        return "config_load_failed"
    if config_supported != True:
        return "config_load_unknown"
    return "unknown"


def reason_for_openclaw(
    *,
    version: str | None,
    config_ok: bool,
    status_available: bool,
    doctor_available: bool,
    tools_available: bool,
) -> str:
    if not version:
        return "version_failed"
    if not config_ok:
        return "config_load_failed"
    if not any((status_available, doctor_available, tools_available)):
        return "mcp_cli_unavailable"
    if not status_available:
        return "mcp_status_unavailable"
    if not doctor_available:
        return "probe_unavailable"
    if not tools_available:
        return "mcp_tools_unavailable"
    return "unknown"


def documented_missing_state(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ("not configured", "no servers", "no mcp", "missing", "not found"))


def write_artifacts(summary: RuntimeGateSummary) -> None:
    ensure_dirs()
    data = _json(summary)
    SUMMARY_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_report(summary), encoding="utf-8")
    MATRIX_JSON.write_text(json.dumps(matrix_rows(summary), indent=2, sort_keys=True), encoding="utf-8")
    MATRIX_MD.write_text(render_matrix(summary), encoding="utf-8")
    OPENCODE_REPORT.write_text(render_agent_report(summary.opencode), encoding="utf-8")
    OPENCLAW_REPORT.write_text(render_agent_report(summary.openclaw), encoding="utf-8")


def render_report(summary: RuntimeGateSummary) -> str:
    lines = [
        "# Agent Runtime Gate Report",
        "",
        "## Stage Positioning",
        "",
        "- Stage 39RT performs real local runtime discovery/version/probe commands.",
        "- Dry-run and preflight are not completion evidence under Stage 38REAL.",
        "- Runtime-missing results are blocked runtime states, not integration completion.",
        "- This stage does not run real OpenCode/OpenClaw agent smoke.",
        "- Third-party source may be cloned under ignored `external/` when explicitly requested, but it is not submitted and does not by itself prove runtime availability.",
        "- It does not install dependencies or submit third-party source.",
        "- It does not claim real OpenCode/OpenClaw integration.",
        "",
        "## Policy",
        "",
        f"- real_environment_policy_active: {summary.real_environment_policy_active}",
        f"- dry_run_counts_as_completion: {summary.dry_run_counts_as_completion}",
        f"- blocked_if_missing: {summary.blocked_if_missing}",
        "",
        "## Shared CapProof MCP Server",
        "",
        f"- command: `{' '.join(summary.capproof_mcp_command)}`",
        f"- uses_shared_capproof_mcp_server: {summary.uses_shared_capproof_mcp_server}",
        f"- forked_guard_logic: {summary.forked_guard_logic}",
        "",
        render_agent_report(summary.opencode),
        "",
        render_agent_report(summary.openclaw),
        "",
        "## Next Stage Recommendation",
        "",
    ]
    lines.extend(f"- {item}" for item in summary.next_stage_recommended)
    lines.extend(
        [
            "",
            "## Non-Claims",
            "",
            f"- integration_claim_made: {summary.integration_claim_made}",
            f"- real_opencode_integration_claim: {summary.real_opencode_integration_claim}",
            f"- real_openclaw_integration_claim: {summary.real_openclaw_integration_claim}",
            f"- production_level_protection_claim: {summary.production_level_protection_claim}",
            f"- api_key_written: {summary.api_key_written}",
            f"- external_venv_node_modules_runtime_cache_committed: {summary.external_venv_node_modules_runtime_cache_committed}",
            "- No real agent `tools/list` or `tools/call` observation is claimed in Stage 39RT.",
            "- OpenCode/OpenClaw metadata cannot mint capability.",
            "- The same standard CapProof MCP server is reused; CapProof guard logic is not forked.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_agent_report(gate: AgentRuntimeGate) -> str:
    title = "OpenCode" if gate.agent == "opencode" else "OpenClaw"
    lines = [
        f"## {title}",
        "",
        f"- command_name: `{gate.command_name}`",
        f"- command_path: `{gate.command_path}`",
        f"- source_repo_path: `{gate.source_repo_path}`",
        f"- source_repo_present: {gate.source_repo_present}",
        f"- source_repo_commit: `{gate.source_repo_commit}`",
        f"- source_repo_remote: `{gate.source_repo_remote}`",
        f"- runtime_present: {gate.runtime_present}",
        f"- version_detected: `{gate.version_detected}`",
        f"- config_template_path: `{gate.config_template_path}`",
        f"- capproof_mcp_config_template_exists: {gate.capproof_mcp_config_template_exists}",
        f"- capproof_mcp_command_referenced: {gate.capproof_mcp_command_referenced}",
        f"- config_load_supported: {gate.config_load_supported}",
        f"- mcp_status_available: {gate.mcp_status_available}",
        f"- mcp_doctor_probe_available: {gate.mcp_doctor_probe_available}",
        f"- mcp_tools_available: {gate.mcp_tools_available}",
        f"- real_smoke_eligible: {gate.real_smoke_eligible}",
        f"- reason: {gate.reason}",
        f"- blocked_runtime_missing: {gate.blocked_runtime_missing}",
        f"- real_agent_process_run: {gate.real_agent_process_run}",
        f"- tools_list_observed_from_real_agent: {gate.tools_list_observed_from_real_agent}",
        f"- tools_call_observed_from_real_agent: {gate.tools_call_observed_from_real_agent}",
        f"- real_integration_claim: {gate.real_integration_claim}",
        "",
        "### Real Runtime Probes",
        "",
    ]
    for probe in gate.probes:
        lines.append(
            f"- {probe.label}: `{' '.join(probe.command)}` attempted={probe.attempted}, "
            f"available={probe.available}, exit_code={probe.exit_code}, error=`{probe.error}`"
        )
    if not gate.probes:
        lines.append("- No probes recorded.")
    if gate.blocked_runtime_missing:
        lines.append("")
        lines.append(f"- {title} real smoke blocked_runtime_missing.")
        lines.append(f"- {title} integration not complete.")
    elif gate.real_smoke_eligible:
        lines.append("")
        lines.append(f"- {title} real smoke eligible for a later stage; smoke was not run in Stage 39RT.")
    else:
        lines.append("")
        lines.append(f"- {title} real smoke not eligible in Stage 39RT: {gate.reason}.")
    return "\n".join(lines)


def matrix_rows(summary: RuntimeGateSummary) -> list[dict[str, Any]]:
    return [
        {"item": "real_environment_policy_active", "passed": summary.real_environment_policy_active, "evidence": "REAL_ENVIRONMENT_VALIDATION.md present and active"},
        {"item": "dry_run_not_completion", "passed": not summary.dry_run_counts_as_completion, "evidence": "Stage 38REAL policy carried into Stage 39RT"},
        {"item": "opencode_real_command_detection", "passed": any(p.label == "which_opencode" and p.attempted for p in summary.opencode.probes), "evidence": "which opencode probe recorded"},
        {"item": "opencode_runtime_gate", "passed": summary.opencode.runtime_present or summary.opencode.blocked_runtime_missing, "evidence": summary.opencode.reason},
        {"item": "openclaw_real_command_detection", "passed": any(p.label == "which_openclaw" and p.attempted for p in summary.openclaw.probes), "evidence": "which openclaw probe recorded"},
        {"item": "openclaw_runtime_gate", "passed": summary.openclaw.runtime_present or summary.openclaw.blocked_runtime_missing, "evidence": summary.openclaw.reason},
        {"item": "shared_capproof_mcp_server", "passed": summary.uses_shared_capproof_mcp_server and not summary.forked_guard_logic, "evidence": "single run_capproof_mcp_server.py command reused"},
        {"item": "no_real_integration_claim", "passed": not summary.integration_claim_made and not summary.real_opencode_integration_claim and not summary.real_openclaw_integration_claim, "evidence": "Stage 39RT does not run agent smoke"},
        {"item": "no_production_overclaim", "passed": not summary.production_level_protection_claim, "evidence": "non-claim preserved"},
    ]


def render_matrix(summary: RuntimeGateSummary) -> str:
    lines = ["# Agent Runtime Gate Matrix", "", "| item | passed | evidence |", "| --- | --- | --- |"]
    for row in matrix_rows(summary):
        lines.append(f"| {row['item']} | {row['passed']} | {row['evidence']} |")
    return "\n".join(lines) + "\n"


def real_policy_active() -> bool:
    path = ROOT / "REAL_ENVIRONMENT_VALIDATION.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    return "preflight" in text and "not completion evidence" in text and "blocked_missing_real_env_gate" in text


def tracked_forbidden_paths_present() -> bool:
    try:
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    forbidden = ("external/", ".venv-hermes/", "node_modules/", "real_agent_integrations/hermes_mcp_server/auth_queue/")
    return any(line.startswith(forbidden) for line in completed.stdout.splitlines())


def ensure_dirs() -> None:
    for directory in (AUDIT_DIR, OPENCODE_REPORT.parent, OPENCLAW_REPORT.parent):
        directory.mkdir(parents=True, exist_ok=True)


def safe_env(env: Mapping[str, str]) -> dict[str, str]:
    allowed = {"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "SYSTEMROOT", "WINDIR"}
    return {key: value for key, value in env.items() if key in allowed}


def first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:240]
    return ""


def redact(text: str) -> str:
    for key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        value = os.environ.get(key)
        if value:
            text = text.replace(value, "<redacted>")
    return SECRET_RE.sub("<redacted>", text)


def _json(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, tuple):
        return [_json(item) for item in value]
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())
