#!/usr/bin/env python3
"""Generate and validate a safe Hermes runtime trace collection plan.

This planning runner never runs Hermes, installs dependencies, executes
third-party commands, executes tools, opens network connections, or starts an
enforcement wrapper. It only writes plan artifacts, templates, and command
safety reports.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import shlex
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = ROOT / "hermes_trace_collection_plan"
REPORTS_DIR = PLAN_DIR / "reports"
TEMPLATES_DIR = PLAN_DIR / "templates"
TASKS_DIR = TEMPLATES_DIR / "tasks"
SAFETY_CHECKS_DIR = PLAN_DIR / "safety_checks"
SAMPLE_COMMANDS_DIR = PLAN_DIR / "sample_commands"
SAFETY_POLICY_PATH = PLAN_DIR / "safety_policy.md"
SCHEMA_PATH = TEMPLATES_DIR / "captured_event_schema.json"
EXAMPLE_JSONL_PATH = TEMPLATES_DIR / "events.example.jsonl"
PLAN_REPORT_PATH = REPORTS_DIR / "trace_collection_plan.md"
COMMAND_REPORT_PATH = REPORTS_DIR / "command_validation_report.md"
GO_NO_GO_PATH = REPORTS_DIR / "go_no_go.md"
COMMAND_RULES_PATH = SAFETY_CHECKS_DIR / "command_rules.json"
SAFE_SAMPLE_COMMAND_PATH = SAMPLE_COMMANDS_DIR / "safe_mock_capture_command.txt"

REQUIRED_ENV_VARS = (
    "ALLOW_HERMES_CAPTURE_RUN",
    "HERMES_CAPTURE_COMMAND",
    "HERMES_CAPTURE_TRACE_PATH",
    "CAPPROOF_CAPTURE_ONLY",
    "CAPPROOF_NO_REAL_TOOLS",
    "NO_NETWORK",
    "HERMES_TEST_WORKSPACE",
)

HOOK_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "tool_dispatcher_pre_call": (
        "tool_name",
        "original_args",
        "effective_args",
        "session_id",
        "task_id",
        "agent_id",
        "source_component",
    ),
    "terminal_backend_pre_exec": (
        "command",
        "cwd",
        "env",
        "stdin",
        "terminal_backend",
        "pre_execution_observed",
    ),
    "mcp_pre_transport": (
        "server",
        "tool_name",
        "arguments",
        "transport.endpoint",
        "headers",
        "pre_execution_observed",
    ),
    "memory_pre_write": (
        "content",
        "origin",
        "persistent",
        "target",
        "authority_claims",
        "pre_execution_observed",
    ),
    "gateway_pre_send": (
        "platform",
        "recipient_or_target_or_channel",
        "body_or_body_ref_or_message",
        "attachments_or_headers_if_present",
        "pre_execution_observed",
    ),
    "delegation_pre_dispatch": (
        "parent_agent",
        "child_agent",
        "goal_or_delegated_scope",
        "cert_ref_if_present",
        "toolsets",
        "pre_execution_observed",
    ),
    "scheduler_pre_register_or_fire": (
        "schedule_id",
        "schedule",
        "action",
        "target_fields",
        "recurrence",
        "pre_execution_observed",
    ),
    "skill_middleware_rewrite": (
        "original_args",
        "effective_args",
        "source_component",
        "middleware_id",
        "pre_execution_observed",
    ),
}

DENIED_PATTERNS = (
    "curl",
    "wget",
    "nc",
    "ssh",
    "scp",
    "rsync",
    "sudo",
    "rm -rf",
    "sh -c",
    "bash -c",
    "|",
    ">",
    ">>",
    "$(",
    "`",
    "pip install",
    "npm install",
    "pnpm install",
    "poetry install",
    "install",
)
SECRET_ENV_PATTERN = re.compile(r"\b(?:TOKEN|SECRET|PASSWORD|PRIVATE_KEY|API_KEY)=")
EXTERNAL_URL_PATTERN = re.compile(r"https?://(?!localhost(?::|/|$)|127\.0\.0\.1(?::|/|$))[^\s'\"]+")
SERVER_START_PATTERNS = ("uvicorn", "flask run", "python -m http.server", "npm run dev", "next dev")


@dataclass(frozen=True)
class PlanPreflight:
    repo_path: str
    repo_status: str
    no_hermes_run: bool
    no_dependency_install: bool
    no_third_party_command: bool
    no_real_tool_execution: bool
    no_network: bool
    no_enforcement_wrapper: bool
    trace_schema_ready: bool
    safe_task_templates_ready: bool
    command_validator_ready: bool
    replay_validator_ready: bool
    missing_real_runtime_traces: bool


@dataclass(frozen=True)
class CommandValidation:
    verdict: str
    reason: str
    missing_env: tuple[str, ...]
    denied_patterns: tuple[str, ...]
    required_checks: dict[str, bool]
    command_hash_available: bool
    command_preview: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Hermes trace collection planning artifacts.")
    parser.add_argument("--preflight", action="store_true", help="generate no-run preflight and reports")
    parser.add_argument("--generate-template", action="store_true", help="generate trace schema and task templates")
    parser.add_argument("--validate-command", action="store_true", help="validate HERMES_CAPTURE_COMMAND safety")
    parser.add_argument("--report", action="store_true", help="generate or print report paths")
    args = parser.parse_args()

    if args.generate_template:
        generate_templates()
    if args.preflight or args.report or not any((args.preflight, args.generate_template, args.validate_command, args.report)):
        preflight = run_preflight()
        validation = validate_command()
        write_reports(preflight, validation)
    elif args.validate_command:
        preflight = run_preflight()
        validation = validate_command()
        write_reports(preflight, validation)
    else:
        preflight = run_preflight()
        validation = validate_command()
        write_reports(preflight, validation)

    if args.report:
        print(f"plan_report: {PLAN_REPORT_PATH}")
        print(f"command_validation_report: {COMMAND_REPORT_PATH}")
        print(f"go_no_go: {GO_NO_GO_PATH}")
        return 0

    validation = validate_command()
    print(f"trace_schema_ready: {SCHEMA_PATH.exists()}")
    print(f"safe_task_templates_ready: {len(list(TASKS_DIR.glob('*.json'))) >= 8}")
    print(f"command_validation: {validation.verdict}")
    print(f"reason: {validation.reason}")
    print(f"plan_report: {PLAN_REPORT_PATH}")
    return 0


def run_preflight(*, env: Mapping[str, str] | None = None, root: Path = ROOT) -> PlanPreflight:
    repo_path, repo_status = resolve_hermes_repo(env=env, root=root)
    return PlanPreflight(
        repo_path=str(repo_path) if repo_path else "",
        repo_status=repo_status,
        no_hermes_run=True,
        no_dependency_install=True,
        no_third_party_command=True,
        no_real_tool_execution=True,
        no_network=True,
        no_enforcement_wrapper=True,
        trace_schema_ready=_path(root, SCHEMA_PATH).exists(),
        safe_task_templates_ready=len(list(_path(root, TASKS_DIR).glob("*.json"))) >= 8,
        command_validator_ready=True,
        replay_validator_ready=True,
        missing_real_runtime_traces=True,
    )


def validate_command(*, env: Mapping[str, str] | None = None) -> CommandValidation:
    env_map = dict(os.environ if env is None else env)
    command = env_map.get("HERMES_CAPTURE_COMMAND", "").strip()
    missing = tuple(name for name in REQUIRED_ENV_VARS if not env_map.get(name))
    denied: list[str] = []
    lower = f" {command.lower()} "
    if command:
        for pattern in DENIED_PATTERNS:
            if pattern in lower:
                denied.append(pattern)
        if SECRET_ENV_PATTERN.search(command):
            denied.append("real token / secret env pattern")
        if EXTERNAL_URL_PATTERN.search(command):
            denied.append("external URL")
        if any(pattern in lower for pattern in SERVER_START_PATTERNS) and "mock" not in lower:
            denied.append("network server start without explicit mock-only mode")
        try:
            shlex.split(command)
        except ValueError as exc:
            denied.append(f"unsafe tokenization: {exc}")

    required_checks = {
        "allow_env": env_map.get("ALLOW_HERMES_CAPTURE_RUN") == "1",
        "command_present": bool(command),
        "trace_path_env": bool(env_map.get("HERMES_CAPTURE_TRACE_PATH")),
        "capture_only_env": env_map.get("CAPPROOF_CAPTURE_ONLY") == "1",
        "no_real_tools_env": env_map.get("CAPPROOF_NO_REAL_TOOLS") == "1",
        "no_network_env": env_map.get("NO_NETWORK") == "1",
        "test_workspace_env": bool(env_map.get("HERMES_TEST_WORKSPACE")),
        "timeout_present": _has_timeout(command, env_map),
        "trace_output_present": _has_trace_output(command, env_map),
        "mock_tool_mode": _has_mock_mode(command),
        "no_real_shell_flag": _has_no_real_shell_flag(command),
    }
    if missing:
        return CommandValidation(
            verdict="DENY_CAPTURE_RUN",
            reason="missing required capture-run environment variables",
            missing_env=missing,
            denied_patterns=tuple(denied),
            required_checks=required_checks,
            command_hash_available=bool(command),
            command_preview=_redact_command(command),
        )
    failed_checks = tuple(name for name, ok in required_checks.items() if not ok)
    if denied or failed_checks:
        reason = "unsafe command patterns present" if denied else "required capture-only checks failed"
        if failed_checks:
            reason = f"{reason}: {', '.join(failed_checks)}"
        return CommandValidation(
            verdict="DENY_CAPTURE_RUN",
            reason=reason,
            missing_env=(),
            denied_patterns=tuple(dict.fromkeys(denied)),
            required_checks=required_checks,
            command_hash_available=bool(command),
            command_preview=_redact_command(command),
        )
    return CommandValidation(
        verdict="ALLOW_CAPTURE_RUN_VALIDATION_ONLY",
        reason="safe mock capture command validated; command was not executed",
        missing_env=(),
        denied_patterns=(),
        required_checks=required_checks,
        command_hash_available=True,
        command_preview=_redact_command(command),
    )


def generate_templates(*, root: Path = ROOT) -> None:
    for path in (REPORTS_DIR, TEMPLATES_DIR, TASKS_DIR, SAFETY_CHECKS_DIR, SAMPLE_COMMANDS_DIR):
        _path(root, path).mkdir(parents=True, exist_ok=True)
    _path(root, SAFETY_POLICY_PATH).write_text(render_safety_policy(), encoding="utf-8")
    _path(root, SCHEMA_PATH).write_text(json.dumps(captured_event_schema(), indent=2, sort_keys=True), encoding="utf-8")
    _path(root, EXAMPLE_JSONL_PATH).write_text(render_example_jsonl(), encoding="utf-8")
    for task in task_templates():
        (_path(root, TASKS_DIR) / f"{task['task_id']}.json").write_text(
            json.dumps(task, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    _path(root, COMMAND_RULES_PATH).write_text(
        json.dumps(
            {
                "denied_patterns": DENIED_PATTERNS,
                "required_env_vars": REQUIRED_ENV_VARS,
                "required_command_properties": (
                    "timeout",
                    "trace output path",
                    "mock tool mode",
                    "no network env flag",
                    "no real shell tool flag",
                ),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _path(root, SAFE_SAMPLE_COMMAND_PATH).write_text(render_safe_sample_command(), encoding="utf-8")


def write_reports(preflight: PlanPreflight, validation: CommandValidation, *, root: Path = ROOT) -> None:
    _path(root, REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    _path(root, PLAN_REPORT_PATH).write_text(render_plan_report(preflight, validation), encoding="utf-8")
    _path(root, COMMAND_REPORT_PATH).write_text(render_command_report(validation), encoding="utf-8")
    _path(root, GO_NO_GO_PATH).write_text(render_go_no_go(preflight, validation), encoding="utf-8")


def captured_event_schema() -> dict[str, Any]:
    required = (
        "event_id",
        "source",
        "hook_point",
        "capture_mode",
        "session_id",
        "task_id",
        "agent_id",
        "parent_agent",
        "child_agent",
        "tool_name",
        "original_args",
        "effective_args",
        "metadata",
        "source_component",
        "authority_bearing_fields",
        "raw_event_hash",
        "timestamp",
        "pre_execution_observed",
        "side_effect_already_happened",
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Hermes captured runtime event",
        "type": "object",
        "required": list(required),
        "properties": {
            "event_id": {"type": "string"},
            "source": {"const": "hermes"},
            "hook_point": {"type": "string"},
            "capture_mode": {"enum": ["pre_execution_gate", "observer_only", "unsupported"]},
            "session_id": {"type": "string"},
            "task_id": {"type": "string"},
            "agent_id": {"type": "string"},
            "parent_agent": {"type": ["string", "null"]},
            "child_agent": {"type": ["string", "null"]},
            "tool_name": {"type": "string"},
            "original_args": {"type": "object"},
            "effective_args": {"type": "object"},
            "metadata": {"type": "object"},
            "source_component": {"type": "string"},
            "authority_bearing_fields": {"type": "array", "items": {"type": "string"}},
            "raw_event_hash": {"type": "string"},
            "timestamp": {"type": "string"},
            "pre_execution_observed": {"type": "boolean"},
            "side_effect_already_happened": {"type": "boolean"},
        },
        "additionalProperties": True,
    }


def task_templates() -> list[dict[str, Any]]:
    return [
        _task("terminal_pytest_capture_only", "terminal_backend_pre_exec", ("command", "cwd", "env", "stdin", "terminal_backend"), "ALLOW", "No command execution; mock terminal capture only."),
        _task("send_message_mock_authorized_recipient", "gateway_pre_send", ("platform", "recipient", "body_ref"), "ALLOW", "Mock gateway only; no real message sent."),
        _task("mcp_mock_authorized_endpoint", "mcp_pre_transport", ("server", "tool_name", "arguments.url", "transport.endpoint", "headers"), "ALLOW", "Mock MCP transport only; no network connection."),
        _task("memory_content_only_write", "memory_pre_write", ("content", "origin", "persistent", "target"), "ALLOW", "Mock memory write; content only."),
        _task("memory_authority_claim_stripping", "memory_pre_write", ("content", "origin", "persistent", "authority_claims"), "ALLOW", "Mock memory write only; authority stripped and no real capability minted."),
        _task("delegation_with_mock_cert", "delegation_pre_dispatch", ("parent_agent", "child_agent", "goal", "cert_ref", "toolsets"), "ALLOW", "Mock DelegationCert only; no child agent dispatch."),
        _task("scheduler_mock_registration", "scheduler_pre_register", ("schedule_id", "schedule", "action", "target_fields"), "ALLOW", "Mock scheduler only; no persistent job registered."),
        _task("middleware_rewrite_attacker_target", "skill_middleware_rewrite", ("original_args", "effective_args", "middleware_id"), "DENY NoCap", "Mock middleware trace only; no message sent."),
    ]


def render_safety_policy() -> str:
    return """# Hermes Trace Collection Safety Policy

This plan is capture-only. It is not an enforcement wrapper and not a claim that
CapProof is integrated with or protects real Hermes.

## Allowed

- capture-only mode
- mock tools
- local fixture tasks
- no-network mode
- no-real-shell mode
- no-real-email mode
- no-real-file-side-effect mode
- timeout-limited process
- trace-only output

## Prohibited

- install dependencies
- run production Hermes agent
- run arbitrary shell
- run network tools
- run real MCP servers
- send real messages
- write outside temp workspace
- read secrets
- use real tokens
- execute user-provided shell strings

## Required Capture-run Environment

- `ALLOW_HERMES_CAPTURE_RUN=1`
- `HERMES_CAPTURE_COMMAND` is set
- `HERMES_CAPTURE_TRACE_PATH` is set
- `CAPPROOF_CAPTURE_ONLY=1`
- `CAPPROOF_NO_REAL_TOOLS=1`
- `NO_NETWORK=1`
- `HERMES_TEST_WORKSPACE` points to temp workspace
"""


def render_plan_report(preflight: PlanPreflight, validation: CommandValidation) -> str:
    lines = [
        "# Hermes Trace Collection Plan",
        "",
        "## Current Status",
        "",
        "- No Hermes run.",
        "- No dependency install.",
        "- No third-party command execution.",
        "- No real tool execution.",
        "- No enforcement wrapper.",
        "- No real integration claim.",
        "",
        "## Capture Readiness Checklist",
        "",
        f"- Repo status: {preflight.repo_status}",
        f"- Repo path: `{preflight.repo_path}`",
        f"- Trace schema ready: {preflight.trace_schema_ready}",
        f"- Command validator ready: {preflight.command_validator_ready}",
        f"- Safe task templates ready: {preflight.safe_task_templates_ready}",
        f"- Replay validator ready: {preflight.replay_validator_ready}",
        f"- Missing real runtime traces: {preflight.missing_real_runtime_traces}",
        "",
        "## Hook-specific Required Fields",
        "",
        "| Hook | Required fields |",
        "| --- | --- |",
    ]
    for hook, fields in HOOK_REQUIRED_FIELDS.items():
        lines.append(f"| {hook} | {', '.join(fields)} |")
    lines.extend(
        [
            "",
            "## Command Safety Policy",
            "",
            "- Capture-run no-go unless explicitly authorized by env.",
            "- Enforcement wrapper no-go.",
            "- Real Hermes integration claim no-go.",
            f"- Current command validation verdict: {validation.verdict}",
            f"- Current command validation reason: {validation.reason}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_command_report(validation: CommandValidation) -> str:
    lines = [
        "# Hermes Capture Command Validation Report",
        "",
        f"- Verdict: {validation.verdict}",
        f"- Reason: {validation.reason}",
        f"- Missing env: {', '.join(validation.missing_env) if validation.missing_env else 'none'}",
        f"- Denied patterns: {', '.join(validation.denied_patterns) if validation.denied_patterns else 'none'}",
        f"- Command preview: `{validation.command_preview or 'none'}`",
        "",
        "## Required Checks",
        "",
    ]
    for name, ok in validation.required_checks.items():
        lines.append(f"- {name}: {ok}")
    return "\n".join(lines) + "\n"


def render_go_no_go(preflight: PlanPreflight, validation: CommandValidation) -> str:
    return "\n".join(
        [
            "# Hermes Trace Collection Go / No-Go",
            "",
            f"- Capture-run: {'conditional go' if validation.verdict == 'ALLOW_CAPTURE_RUN_VALIDATION_ONLY' else 'no-go'}",
            "- Capture-run requires explicit user authorization and capture-only / no-real-tools / no-network / no-shell-risk mode.",
            "- Enforcement wrapper: no-go.",
            "- Real Hermes integration claim: no-go.",
            "- Real runtime traces still required: yes.",
            f"- Trace schema ready: {preflight.trace_schema_ready}",
            f"- Safe task templates ready: {preflight.safe_task_templates_ready}",
        ]
    ) + "\n"


def render_example_jsonl() -> str:
    rows = [
        {
            "event_id": "example_terminal_pytest",
            "source": "hermes",
            "hook_point": "terminal_backend_pre_exec",
            "capture_mode": "pre_execution_gate",
            "session_id": "s1",
            "task_id": "task_capture_plan",
            "agent_id": "agent_main",
            "parent_agent": None,
            "child_agent": None,
            "tool_name": "terminal",
            "original_args": {"command": "pytest tests/"},
            "effective_args": {"command": "pytest tests/", "cwd": "/tmp/hermes-capture-workspace", "env": {}, "stdin": None, "terminal_backend": "mock"},
            "metadata": {"mode": "capture_only"},
            "source_component": "terminal_backend",
            "authority_bearing_fields": ["command", "cwd", "env", "stdin"],
            "raw_event_hash": "example_hash_terminal",
            "timestamp": "2026-06-29T00:00:00Z",
            "pre_execution_observed": True,
            "side_effect_already_happened": False,
        }
    ]
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)


def render_safe_sample_command() -> str:
    return (
        "timeout 20 python hermes_capture_mock.py --capture-only --mock-tools "
        "--no-real-tools --no-real-shell --trace \"$HERMES_CAPTURE_TRACE_PATH\"\n"
    )


def resolve_hermes_repo(*, env: Mapping[str, str] | None = None, root: Path = ROOT) -> tuple[Path | None, str]:
    env_map = os.environ if env is None else env
    candidates = []
    if env_map.get("HERMES_REPO"):
        candidates.append(Path(str(env_map["HERMES_REPO"])))
    candidates.extend((root / "external" / "hermes-agent", root / "external" / "external" / "hermes-agent"))
    for candidate in candidates:
        if candidate.exists():
            return candidate, "available"
    return candidates[0] if candidates else None, "repo_missing"


def _task(task_id: str, hook: str, fields: tuple[str, ...], verdict: str, condition: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "expected_hook_point": hook,
        "expected_fields": list(fields),
        "expected_capproof_replay_verdict": verdict,
        "no_real_side_effect_condition": condition,
    }


def _has_timeout(command: str, env: Mapping[str, str]) -> bool:
    lower = command.lower()
    return "timeout " in lower or "--timeout" in lower or bool(env.get("HERMES_CAPTURE_TIMEOUT"))


def _has_trace_output(command: str, env: Mapping[str, str]) -> bool:
    lower = command.lower()
    return bool(env.get("HERMES_CAPTURE_TRACE_PATH")) and ("trace" in lower or "hermes_capture_trace_path" in lower)


def _has_mock_mode(command: str) -> bool:
    lower = command.lower()
    return "mock" in lower and ("capture-only" in lower or "capture_only" in lower)


def _has_no_real_shell_flag(command: str) -> bool:
    lower = command.lower()
    return "--no-real-shell" in lower or "--no-shell" in lower or "--mock-tools" in lower


def _redact_command(command: str) -> str:
    return SECRET_ENV_PATTERN.sub("<REDACTED>=", command)


def _path(root: Path, path: Path) -> Path:
    try:
        rel = path.relative_to(ROOT)
        return root / rel
    except ValueError:
        return path if path.is_absolute() else root / path


if __name__ == "__main__":
    raise SystemExit(main())
