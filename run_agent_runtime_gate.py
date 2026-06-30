#!/usr/bin/env python3
"""Stage 34R-G OpenCode/OpenClaw runtime gate.

This gate only checks whether local OpenCode/OpenClaw runtimes appear present
and whether their CLI metadata suggests a future CapProof MCP smoke could be
attempted. It does not run a real agent session and does not exercise agent
tools/list or tools/call.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parent
AUDIT_DIR = ROOT / "agent_coverage_audit"
SUMMARY_JSON = AUDIT_DIR / "agent_runtime_gate_summary.json"
REPORT_MD = AUDIT_DIR / "agent_runtime_gate_report.md"

CAPROOF_MCP_COMMAND = ("python", "run_capproof_mcp_server.py", "--stdio", "--sandboxed-real-execution")
TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class CommandProbe:
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
    command_path: str
    runtime_present: bool
    version_detected: bool
    version: str
    config_path_detected: bool
    config_path: str
    mcp_status_available: bool
    mcp_doctor_probe_available: bool
    mcp_tools_available: bool
    can_load_capproof_mcp_config: bool
    real_smoke_eligible: bool
    reason: str
    probes: tuple[CommandProbe, ...]
    real_agent_process_run: bool
    tools_list_observed_from_real_agent: bool
    tools_call_observed_from_real_agent: bool
    real_integration_claim: bool


@dataclass(frozen=True)
class RuntimeGateSummary:
    stage: str
    opencode: AgentRuntimeGate
    openclaw: AgentRuntimeGate
    capproof_mcp_command: tuple[str, ...]
    uses_shared_capproof_mcp_server: bool
    forked_guard_logic: bool
    real_opencode_integration_claim: bool
    real_openclaw_integration_claim: bool
    production_level_protection_claim: bool
    api_key_written: bool
    external_or_venv_committed: bool


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 34R-G OpenCode/OpenClaw runtime gate.")
    parser.add_argument("--all", action="store_true", help="run runtime gate and write report artifacts")
    parser.add_argument("--report", action="store_true", help="write report artifacts using the current gate state")
    args = parser.parse_args()
    ensure_dirs()
    if args.all or args.report:
        summary = build_summary(os.environ)
        write_artifacts(summary)
        print(json.dumps(_json(summary), indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 0


def build_summary(env: Mapping[str, str]) -> RuntimeGateSummary:
    opencode = probe_opencode(env)
    openclaw = probe_openclaw(env)
    return RuntimeGateSummary(
        stage="34R-G",
        opencode=opencode,
        openclaw=openclaw,
        capproof_mcp_command=CAPROOF_MCP_COMMAND,
        uses_shared_capproof_mcp_server=True,
        forked_guard_logic=False,
        real_opencode_integration_claim=False,
        real_openclaw_integration_claim=False,
        production_level_protection_claim=False,
        api_key_written=False,
        external_or_venv_committed=False,
    )


def probe_opencode(env: Mapping[str, str]) -> AgentRuntimeGate:
    command_name = env.get("OPENCODE_COMMAND", "opencode")
    command_path = _which(command_name)
    if not command_path:
        return _missing_runtime(agent="opencode", command_name=command_name, reason="runtime_missing: opencode command is not on PATH")

    version_probe = _run_probe((command_path, "--version"))
    help_probe = _run_probe((command_path, "--help"))
    output = f"{version_probe.output_excerpt}\n{help_probe.output_excerpt}".lower()
    version = _first_line(version_probe.output_excerpt)
    config_path = _detect_config_path(
        env,
        env_var="OPENCODE_CONFIG",
        candidates=(
            ROOT / "real_agent_integrations" / "opencode_mcp_server" / "configs" / "opencode.capproof.mcp.example.jsonc",
            Path.home() / ".config" / "opencode",
        ),
    )
    can_load_config = bool(config_path) and any(token in output for token in ("mcp", "config", "server"))
    eligible = bool(version_probe.available and help_probe.available and can_load_config)
    reason = "eligible_metadata_only" if eligible else _join_reasons(
        "runtime_present_but_not_smoke_eligible",
        None if version_probe.available else "version_probe_failed",
        None if "mcp" in output else "mcp_help_not_confirmed",
        None if config_path else "config_path_missing",
        None if can_load_config else "capproof_mcp_config_load_unverified",
    )
    return AgentRuntimeGate(
        agent="opencode",
        command_name=command_name,
        command_path=command_path,
        runtime_present=True,
        version_detected=bool(version),
        version=version,
        config_path_detected=bool(config_path),
        config_path=config_path,
        mcp_status_available="mcp" in output,
        mcp_doctor_probe_available=False,
        mcp_tools_available="tools" in output,
        can_load_capproof_mcp_config=can_load_config,
        real_smoke_eligible=eligible,
        reason=reason,
        probes=(version_probe, help_probe),
        real_agent_process_run=False,
        tools_list_observed_from_real_agent=False,
        tools_call_observed_from_real_agent=False,
        real_integration_claim=False,
    )


def probe_openclaw(env: Mapping[str, str]) -> AgentRuntimeGate:
    command_name = env.get("OPENCLAW_COMMAND", "openclaw")
    command_path = _which(command_name)
    if not command_path:
        return _missing_runtime(agent="openclaw", command_name=command_name, reason="runtime_missing: openclaw command is not on PATH")

    version_probe = _run_probe((command_path, "--version"))
    mcp_help_probe = _run_probe((command_path, "mcp", "--help"))
    output = f"{version_probe.output_excerpt}\n{mcp_help_probe.output_excerpt}".lower()
    version = _first_line(version_probe.output_excerpt)
    config_path = _detect_config_path(
        env,
        env_var="OPENCLAW_CONFIG",
        candidates=(
            ROOT / "real_agent_integrations" / "openclaw_mcp_server" / "configs" / "openclaw.capproof.mcp.commands.md",
            Path.home() / ".config" / "openclaw",
        ),
    )
    status_available = "status" in output
    doctor_available = "doctor" in output or "probe" in output
    tools_available = "tools" in output
    can_load_config = bool(config_path) and "mcp" in output
    eligible = bool(version_probe.available and mcp_help_probe.available and status_available and doctor_available and tools_available and can_load_config)
    reason = "eligible_metadata_only" if eligible else _join_reasons(
        "runtime_present_but_not_smoke_eligible",
        None if version_probe.available else "version_probe_failed",
        None if mcp_help_probe.available else "mcp_help_probe_failed",
        None if status_available else "mcp_status_unconfirmed",
        None if doctor_available else "mcp_doctor_probe_unconfirmed",
        None if tools_available else "mcp_tools_unconfirmed",
        None if can_load_config else "capproof_mcp_config_load_unverified",
    )
    return AgentRuntimeGate(
        agent="openclaw",
        command_name=command_name,
        command_path=command_path,
        runtime_present=True,
        version_detected=bool(version),
        version=version,
        config_path_detected=bool(config_path),
        config_path=config_path,
        mcp_status_available=status_available,
        mcp_doctor_probe_available=doctor_available,
        mcp_tools_available=tools_available,
        can_load_capproof_mcp_config=can_load_config,
        real_smoke_eligible=eligible,
        reason=reason,
        probes=(version_probe, mcp_help_probe),
        real_agent_process_run=False,
        tools_list_observed_from_real_agent=False,
        tools_call_observed_from_real_agent=False,
        real_integration_claim=False,
    )


def write_artifacts(summary: RuntimeGateSummary) -> None:
    ensure_dirs()
    SUMMARY_JSON.write_text(json.dumps(_json(summary), indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_report(summary), encoding="utf-8")


def render_report(summary: RuntimeGateSummary) -> str:
    return "\n".join(
        [
            "# Agent Runtime Gate Report",
            "",
            "## Stage Positioning",
            "",
            "- Stage 34R-G only detects local OpenCode/OpenClaw runtime readiness.",
            "- It does not run a real OpenCode/OpenClaw agent smoke.",
            "- It does not install dependencies or third-party source.",
            "- It does not claim real OpenCode/OpenClaw integration.",
            "- It reuses the same standard CapProof MCP server command.",
            "",
            "## Shared CapProof MCP Server",
            "",
            f"- command: `{' '.join(summary.capproof_mcp_command)}`",
            f"- uses_shared_capproof_mcp_server: {summary.uses_shared_capproof_mcp_server}",
            f"- forked_guard_logic: {summary.forked_guard_logic}",
            "",
            _render_agent(summary.opencode, title="OpenCode"),
            "",
            _render_agent(summary.openclaw, title="OpenClaw"),
            "",
            "## Non-Claims",
            "",
            f"- real_opencode_integration_claim: {summary.real_opencode_integration_claim}",
            f"- real_openclaw_integration_claim: {summary.real_openclaw_integration_claim}",
            f"- production_level_protection_claim: {summary.production_level_protection_claim}",
            f"- api_key_written: {summary.api_key_written}",
            f"- external_or_venv_committed: {summary.external_or_venv_committed}",
            "- No real agent `tools/list` or `tools/call` observation is claimed.",
            "- OpenCode/OpenClaw metadata cannot mint capability.",
        ]
    ) + "\n"


def _render_agent(gate: AgentRuntimeGate, *, title: str) -> str:
    lines = [
        f"## {title}",
        "",
        f"- command_name: `{gate.command_name}`",
        f"- command_path: `{gate.command_path}`",
        f"- runtime_present: {gate.runtime_present}",
        f"- version_detected: {gate.version_detected}",
        f"- version: `{gate.version}`",
        f"- config_path_detected: {gate.config_path_detected}",
        f"- config_path: `{gate.config_path}`",
        f"- mcp_status_available: {gate.mcp_status_available}",
        f"- mcp_doctor_probe_available: {gate.mcp_doctor_probe_available}",
        f"- mcp_tools_available: {gate.mcp_tools_available}",
        f"- can_load_capproof_mcp_config: {gate.can_load_capproof_mcp_config}",
        f"- real_smoke_eligible: {gate.real_smoke_eligible}",
        f"- reason: {gate.reason}",
        f"- real_agent_process_run: {gate.real_agent_process_run}",
        f"- tools_list_observed_from_real_agent: {gate.tools_list_observed_from_real_agent}",
        f"- tools_call_observed_from_real_agent: {gate.tools_call_observed_from_real_agent}",
        "",
        "### Probes",
        "",
    ]
    if not gate.probes:
        lines.append("- No metadata commands were run because the runtime command was missing.")
    for probe in gate.probes:
        lines.append(
            f"- `{' '.join(probe.command)}`: attempted={probe.attempted}, available={probe.available}, exit_code={probe.exit_code}, error=`{probe.error}`"
        )
    return "\n".join(lines)


def _missing_runtime(*, agent: str, command_name: str, reason: str) -> AgentRuntimeGate:
    return AgentRuntimeGate(
        agent=agent,
        command_name=command_name,
        command_path="",
        runtime_present=False,
        version_detected=False,
        version="",
        config_path_detected=False,
        config_path="",
        mcp_status_available=False,
        mcp_doctor_probe_available=False,
        mcp_tools_available=False,
        can_load_capproof_mcp_config=False,
        real_smoke_eligible=False,
        reason=reason,
        probes=(),
        real_agent_process_run=False,
        tools_list_observed_from_real_agent=False,
        tools_call_observed_from_real_agent=False,
        real_integration_claim=False,
    )


def _which(command: str) -> str:
    return shutil.which(command) or ""


def _run_probe(command: Sequence[str]) -> CommandProbe:
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            env=_safe_env(os.environ),
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandProbe(
            command=tuple(command),
            attempted=True,
            exit_code=None,
            available=False,
            output_excerpt="",
            error=_redact(str(exc)),
        )
    combined = _redact(f"{completed.stdout}\n{completed.stderr}").strip()
    return CommandProbe(
        command=tuple(command),
        attempted=True,
        exit_code=completed.returncode,
        available=completed.returncode == 0,
        output_excerpt=combined[:1000],
        error="" if completed.returncode == 0 else combined[:300],
    )


def _safe_env(env: Mapping[str, str]) -> dict[str, str]:
    allowed = {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "SYSTEMROOT",
        "WINDIR",
    }
    return {key: value for key, value in env.items() if key in allowed}


def _detect_config_path(env: Mapping[str, str], *, env_var: str, candidates: Sequence[Path]) -> str:
    configured = env.get(env_var)
    if configured:
        return configured if Path(configured).exists() else ""
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return ""


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return ""


def _join_reasons(*parts: str | None) -> str:
    return "; ".join(part for part in parts if part)


def _redact(text: str) -> str:
    for key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        value = os.environ.get(key)
        if value:
            text = text.replace(value, "<redacted>")
    return text


def ensure_dirs() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


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
