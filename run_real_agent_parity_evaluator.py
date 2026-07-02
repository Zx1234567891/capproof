#!/usr/bin/env python3
"""Stage 42EVAL real-agent parity evaluator.

The evaluator freezes the controlled local real-environment parity artifact
for Hermes, OpenCode, and OpenClaw. Preflight and reused reports are useful
readiness/evidence views, but only --fresh-run with the explicit gates can be
completion evidence.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parent
ARTIFACT_DIR = ROOT / "artifact_reports"
SUMMARY_PATH = ARTIFACT_DIR / "real_agent_parity_evaluator_summary.json"
REPORT_PATH = ARTIFACT_DIR / "real_agent_parity_evaluator_report.md"
MATRIX_MD_PATH = ARTIFACT_DIR / "real_agent_parity_evaluator_matrix.md"
MATRIX_JSON_PATH = ARTIFACT_DIR / "real_agent_parity_evaluator_matrix.json"
CLAIMS_MD_PATH = ARTIFACT_DIR / "final_claims_evidence_index.md"
CLAIMS_JSON_PATH = ARTIFACT_DIR / "final_claims_evidence_index.json"

HERMES_SUMMARY = ROOT / "artifact_reports" / "real_environment_validation_summary.json"
OPENCODE_SUMMARY = (
    ROOT / "real_agent_integrations" / "opencode_mcp_server" / "reports" / "real_opencode_deepseek_parity_summary.json"
)
OPENCLAW_SUMMARY = (
    ROOT / "real_agent_integrations" / "openclaw_mcp_server" / "reports" / "real_openclaw_deepseek_parity_summary.json"
)
AGENT_PARITY_MATRIX = ROOT / "artifact_reports" / "agent_parity_matrix.json"

AGENTS = ("hermes", "opencode", "openclaw")
REQUIRED_GATES = (
    "ALLOW_AGENT_RUNTIME_REAL_SMOKE",
    "ALLOW_CAPROOF_AGENT_PARITY",
    "ALLOW_CAPROOF_REAL_ENV_VALIDATION",
    "ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION",
    "ALLOW_CAPROOF_ASK_APPROVAL_DEMO",
    "ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO",
    "ALLOW_HERMES_DEEPSEEK_RUN",
    "ALLOW_CAPROOF_MCP_REAL_HERMES",
    "ALLOW_CAPROOF_REAL_OPENCODE_SMOKE",
    "ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE",
    "DEEPSEEK_API_KEY",
)
SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]{16,}")
ALLOWED_DUMMY_SECRETS = {"sk-test-secret-do-not-write"}
COMMAND_TIMEOUT_SECONDS = 3600

REAL_COMMANDS = {
    "hermes": [
        sys.executable,
        "run_real_environment_validation.py",
        "--all",
        "--require-real",
        "--fail-if-gate-missing",
        "--report",
    ],
    "opencode": [
        sys.executable,
        "run_real_opencode_deepseek_mcp_parity.py",
        "--all",
        "--require-real",
        "--report",
    ],
    "openclaw": [
        sys.executable,
        "run_real_openclaw_deepseek_mcp_parity.py",
        "--all",
        "--require-real",
        "--report",
    ],
}

CLAIM_ROWS = (
    (
        "Hermes local foreground CapProof MCP parity",
        "proven",
        "artifact_reports/real_environment_validation_summary.json",
        "python run_real_environment_validation.py --all --require-real --fail-if-gate-missing --report",
        "b881d996afe58dfc65ce7e00e7e321c51c108651",
        "Controlled local Hermes path only.",
    ),
    (
        "OpenCode local CapProof MCP parity",
        "proven",
        "real_agent_integrations/opencode_mcp_server/reports/real_opencode_deepseek_parity_summary.json",
        "python run_real_opencode_deepseek_mcp_parity.py --all --require-real --report",
        "b949d71bc7d5ac3fe29be7a75d104c3338a71b72",
        "Controlled local OpenCode path only.",
    ),
    (
        "OpenClaw local CapProof MCP parity",
        "proven",
        "real_agent_integrations/openclaw_mcp_server/reports/real_openclaw_deepseek_parity_summary.json",
        "python run_real_openclaw_deepseek_mcp_parity.py --all --require-real --report",
        "7d967ebe053e0a7b9e199e7540dbc30547c33411",
        "Controlled local OpenClaw path only.",
    ),
    (
        "DeepSeek backend used by all three via DEEPSEEK_API_KEY",
        "proven",
        "artifact_reports/real_agent_parity_evaluator_matrix.json",
        "python run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report",
        "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c",
        "DeepSeek is not part of the safety TCB.",
    ),
    (
        "standard MCP tools/list/tools/call observed for all three",
        "proven",
        "artifact_reports/agent_parity_matrix.json",
        "python run_agent_parity_matrix.py --report",
        "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c",
        "Only the tested local stdio MCP path is covered.",
    ),
    (
        "sandboxed local read/write/template subset",
        "proven",
        "artifact_reports/real_agent_parity_evaluator_matrix.json",
        "python run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report",
        "3d5f3c2c20451b14c9303398c03a2145e5c3f775",
        "No arbitrary filesystem or raw shell support.",
    ),
    (
        "DENY/ASK executor gate",
        "proven",
        "artifact_reports/real_agent_parity_evaluator_matrix.json",
        "python run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report",
        "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c",
        "executor_called_on_deny_ask remains zero.",
    ),
    (
        "ASK trusted approve rerun",
        "proven",
        "artifact_reports/real_agent_parity_evaluator_matrix.json",
        "python run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report",
        "a132be58d4b40d1b469ad1cc1f609375854c9aa8",
        "Only trusted local CLI approval can mint scoped capability.",
    ),
    (
        "LLM/MCP metadata cannot mint capability",
        "proven",
        "artifact_reports/real_agent_parity_evaluator_matrix.json",
        "python run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report",
        "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c",
        "Natural-language and metadata approval are rejected.",
    ),
    ("production-level protection", "not_claimed", "CLAIMS_AND_NON_CLAIMS.md", "pytest tests/test_claims_and_non_claims.py -q", "d06928b8c1f26d2db78d88b2b4d30e6905162492", "Not claimed."),
    ("all built-in tool paths covered", "not_claimed", "docs/AGENT_PARITY_LIMITATIONS.md", "pytest tests/test_real_agent_parity_evaluator.py -q", "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c", "Not claimed."),
    ("external MCP protection", "not_claimed", "docs/AGENT_PARITY_LIMITATIONS.md", "pytest tests/test_real_agent_parity_evaluator.py -q", "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c", "Not claimed."),
    ("real email", "not_claimed", "CLAIMS_AND_NON_CLAIMS.md", "pytest tests/test_claims_and_non_claims.py -q", "d06928b8c1f26d2db78d88b2b4d30e6905162492", "Not claimed."),
    ("raw shell support", "not_claimed", "CLAIMS_AND_NON_CLAIMS.md", "pytest tests/test_claims_and_non_claims.py -q", "d06928b8c1f26d2db78d88b2b4d30e6905162492", "Not claimed."),
    ("arbitrary filesystem access", "not_claimed", "CLAIMS_AND_NON_CLAIMS.md", "pytest tests/test_claims_and_non_claims.py -q", "d06928b8c1f26d2db78d88b2b4d30e6905162492", "Not claimed."),
    ("OS-level network denial", "not_claimed", "docs/AGENT_PARITY_LIMITATIONS.md", "pytest tests/test_real_agent_parity_evaluator.py -q", "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c", "Not claimed."),
    ("DeepSeek as safety TCB", "not_claimed", "docs/AGENT_PARITY_LIMITATIONS.md", "pytest tests/test_real_agent_parity_evaluator.py -q", "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c", "Not claimed."),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or summarize the real agent parity evaluator.")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--list-agents", action="store_true")
    parser.add_argument("--agent", action="append", choices=AGENTS)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--require-real", action="store_true")
    parser.add_argument("--fail-if-gate-missing", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--reuse-existing-reports", action="store_true")
    parser.add_argument("--fresh-run", action="store_true")
    args = parser.parse_args(argv)

    if args.list_agents:
        print(json.dumps({"agents": list(AGENTS)}, indent=2, sort_keys=True))
        return 0

    selected = selected_agents(args)
    preflight = build_preflight(os.environ)

    if args.require_real and (preflight["missing_gates"] or not args.fresh_run):
        reason = "blocked_missing_real_env_gate" if preflight["missing_gates"] else "blocked_real_run_not_requested"
        summary = build_summary(
            evaluator_mode="blocked",
            selected_agents=selected,
            preflight=preflight,
            command_results=[],
            fresh_run=False,
            reason=reason,
        )
        write_artifacts(summary)
        print_output(summary, args.json)
        return 2 if args.fail_if_gate_missing else 1

    command_results: list[dict[str, Any]] = []
    evaluator_mode = "preflight"
    reason = "readiness_only_not_completion_evidence"
    fresh_run = False

    if args.fresh_run:
        evaluator_mode = "fresh_run"
        fresh_run = True
        if preflight["missing_gates"]:
            reason = "blocked_missing_real_env_gate"
        else:
            command_results = run_fresh(selected, os.environ)
            reason = "ok" if all(result["returncode"] == 0 for result in command_results) else "failed_real_command"
    elif args.reuse_existing_reports:
        evaluator_mode = "reuse_existing"
        reason = "reuse_existing_reports_not_fresh_evidence"
    elif args.report:
        evaluator_mode = "report_only"
        reason = "no_real_run_requested"

    summary = build_summary(
        evaluator_mode=evaluator_mode,
        selected_agents=selected,
        preflight=preflight,
        command_results=command_results,
        fresh_run=fresh_run,
        reason=reason,
    )
    if args.preflight or args.report or args.reuse_existing_reports or args.fresh_run:
        write_artifacts(summary)
    print_output(summary, args.json)
    if args.require_real:
        return 0 if summary["evaluator_passed"] else 1
    return 0


def selected_agents(args: argparse.Namespace) -> list[str]:
    if args.all or not args.agent:
        return list(AGENTS)
    return list(dict.fromkeys(args.agent))


def build_preflight(env: Mapping[str, str]) -> dict[str, Any]:
    missing = [
        name
        for name in REQUIRED_GATES
        if not env.get(name) or (name != "DEEPSEEK_API_KEY" and env.get(name) != "1")
    ]
    return {
        "stage": "42EVAL",
        "real_environment_policy_active": True,
        "dry_run_preflight_counts_as_completion": False,
        "required_gates": list(REQUIRED_GATES),
        "missing_gates": missing,
        "gate_ready": not missing,
        "deepseek_key_present": bool(env.get("DEEPSEEK_API_KEY")),
        "deepseek_key_source": "DEEPSEEK_API_KEY",
        "deepseek_key_printed": False,
        "existing_reports": {
            "hermes": HERMES_SUMMARY.exists(),
            "opencode": OPENCODE_SUMMARY.exists(),
            "openclaw": OPENCLAW_SUMMARY.exists(),
            "agent_parity_matrix": AGENT_PARITY_MATRIX.exists(),
        },
    }


def run_fresh(selected: Sequence[str], env: Mapping[str, str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for agent in selected:
        result = run_command(agent, REAL_COMMANDS[agent], env=env)
        results.append(result)
        if result["returncode"] != 0:
            break
    if all(result["returncode"] == 0 for result in results):
        results.append(run_command("agent_parity_matrix", [sys.executable, "run_agent_parity_matrix.py", "--report"], env=env))
    return results


def run_command(label: str, command: list[str], *, env: Mapping[str, str]) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=dict(env),
            text=True,
            capture_output=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "label": label,
            "command": display_command(command),
            "returncode": 124,
            "duration_seconds": round(time.time() - started, 3),
            "timed_out": True,
            "stdout_tail": redact(exc.stdout if isinstance(exc.stdout, str) else "", env),
            "stderr_tail": redact(f"timeout after {COMMAND_TIMEOUT_SECONDS} seconds", env),
        }
    return {
        "label": label,
        "command": display_command(command),
        "returncode": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "timed_out": False,
        "stdout_tail": redact(completed.stdout[-4000:], env),
        "stderr_tail": redact(completed.stderr[-4000:], env),
    }


def build_summary(
    *,
    evaluator_mode: str,
    selected_agents: Sequence[str],
    preflight: Mapping[str, Any],
    command_results: Sequence[Mapping[str, Any]],
    fresh_run: bool,
    reason: str,
) -> dict[str, Any]:
    agent_rows = build_agent_rows()
    selected_rows = [row for row in agent_rows if row["agent"] in selected_agents]
    secret_scan = secret_scan_result(os.environ)
    forbidden = forbidden_tracked_paths()
    command_ok = bool(command_results) and all(result["returncode"] == 0 for result in command_results)
    selected_ok = bool(selected_rows) and all(row["parity_passed"] for row in selected_rows)
    evaluator_passed = (
        evaluator_mode == "fresh_run"
        and fresh_run
        and command_ok
        and selected_ok
        and secret_scan["real_key_scan"] == "REAL_KEY_NOT_FOUND"
        and not forbidden
    )
    summary = {
        "stage": "42EVAL",
        "status": "passed" if evaluator_passed else reason,
        "reason": "ok" if evaluator_passed else reason,
        "evaluator_passed": evaluator_passed,
        "evaluator_mode": evaluator_mode,
        "fresh_run": fresh_run,
        "reuse_existing_reports_not_fresh_evidence": evaluator_mode == "reuse_existing",
        "real_environment_policy_active": True,
        "dry_run_preflight_counts_as_completion": False,
        "selected_agents": list(selected_agents),
        "preflight": dict(preflight),
        "commands": list(command_results),
        "agents": selected_rows,
        "aggregate_agent_parity_passed": all(row["parity_passed"] for row in agent_rows),
        "all_agents": agent_rows,
        "secret_scan": secret_scan,
        "forbidden_tracked_paths": forbidden,
        "forbidden_tracked_paths_count": len(forbidden),
        "api_key_written": secret_scan["real_key_scan"] != "REAL_KEY_NOT_FOUND",
        "production_level_overclaim": False,
        "claims_index_path": str(CLAIMS_MD_PATH),
        "matrix_path": str(MATRIX_MD_PATH),
        "summary_path": str(SUMMARY_PATH),
        "report_path": str(REPORT_PATH),
    }
    return summary


def build_agent_rows() -> list[dict[str, Any]]:
    return [
        hermes_row(load_json(HERMES_SUMMARY)),
        parity_agent_row("opencode", load_json(OPENCODE_SUMMARY)),
        parity_agent_row("openclaw", load_json(OPENCLAW_SUMMARY)),
    ]


def hermes_row(summary: Mapping[str, Any]) -> dict[str, Any]:
    denied_paths = scenario_passed(summary, "denied_paths_and_shell")
    attacker = scenario_passed(summary, "attacker_recipient_denied")
    row = {
        "agent": "hermes",
        "real_agent_process_ran": bool(summary.get("real_hermes_foreground_run")),
        "agent_binary": "bin/hermes",
        "agent_version": "foreground-wrapper",
        "deepseek_real_call": bool(summary.get("real_deepseek_call")),
        "deepseek_key_source": "DEEPSEEK_API_KEY",
        "deepseek_key_written": bool(summary.get("key_leak_detected")),
        "standard_capproof_mcp_server_used": bool(summary.get("standard_mcp_server_used")),
        "tools_list_observed": bool(summary.get("tools_list_observed")),
        "tools_call_observed": bool(summary.get("tools_call_observed")),
        "allow_read_write_command_observed": bool(
            summary.get("sandbox_read_executed")
            and summary.get("sandbox_write_executed")
            and summary.get("command_template_executed")
        ),
        "deny_outside_path_raw_shell_attacker_observed": bool(denied_paths and attacker),
        "ask_pending_request_created": bool(summary.get("ask_pending_request_created")),
        "trusted_approval_executed": bool(summary.get("trusted_approval_executed")),
        "approval_receipt_generated": bool(summary.get("approval_receipt_generated")),
        "rerun_allow_observed": bool(summary.get("rerun_allow_observed")),
        "llm_metadata_approval_rejected": bool(
            summary.get("llm_claimed_approval_rejected")
            and summary.get("mcp_meta_approval_rejected")
            and summary.get("scope_amplification_rejected")
        ),
        "executor_called_on_deny_ask": 0 if denied_paths and attacker else 1,
        "trace_live_log_report_generated": all(
            Path(str(summary.get(key, ""))).exists() for key in ("trace_path", "live_log_path", "report_path")
        ),
        "production_level_overclaim": bool(summary.get("production_level_overclaim")),
    }
    row["parity_passed"] = row_passed(row)
    row["reason"] = "ok" if row["parity_passed"] else first_missing(row)
    return row


def parity_agent_row(agent: str, summary: Mapping[str, Any]) -> dict[str, Any]:
    row = {
        "agent": agent,
        "real_agent_process_ran": bool(summary.get("real_agent_process_ran")),
        "agent_binary": str(summary.get("agent_binary", "")),
        "agent_version": str(summary.get("agent_version", "")),
        "deepseek_real_call": bool(summary.get("deepseek_real_call")),
        "deepseek_key_source": str(summary.get("deepseek_key_source", "")),
        "deepseek_key_written": bool(summary.get("deepseek_key_written") or summary.get("api_key_written")),
        "standard_capproof_mcp_server_used": bool(summary.get("standard_capproof_mcp_server_used")),
        "tools_list_observed": bool(summary.get("tools_list_observed")),
        "tools_call_observed": bool(summary.get("tools_call_observed")),
        "allow_read_write_command_observed": bool(summary.get("allow_read_write_command_observed")),
        "deny_outside_path_raw_shell_attacker_observed": bool(
            summary.get("deny_outside_path_raw_shell_attacker_observed")
        ),
        "ask_pending_request_created": bool(summary.get("ask_pending_request_created")),
        "trusted_approval_executed": bool(summary.get("trusted_approval_executed")),
        "approval_receipt_generated": bool(summary.get("approval_receipt_generated")),
        "rerun_allow_observed": bool(summary.get("rerun_allow_observed")),
        "llm_metadata_approval_rejected": bool(summary.get("llm_metadata_approval_rejected")),
        "executor_called_on_deny_ask": int(summary.get("executor_called_on_deny_ask", 1)),
        "trace_live_log_report_generated": bool(summary.get("trace_live_log_report_generated")),
        "production_level_overclaim": bool(summary.get("production_level_overclaim")),
    }
    row["parity_passed"] = row_passed(row)
    row["reason"] = "ok" if row["parity_passed"] else first_missing(row)
    return row


def row_passed(row: Mapping[str, Any]) -> bool:
    required_true = (
        "real_agent_process_ran",
        "deepseek_real_call",
        "standard_capproof_mcp_server_used",
        "tools_list_observed",
        "tools_call_observed",
        "allow_read_write_command_observed",
        "deny_outside_path_raw_shell_attacker_observed",
        "ask_pending_request_created",
        "trusted_approval_executed",
        "approval_receipt_generated",
        "rerun_allow_observed",
        "llm_metadata_approval_rejected",
        "trace_live_log_report_generated",
    )
    return (
        all(bool(row.get(key)) for key in required_true)
        and bool(row.get("agent_binary"))
        and bool(row.get("agent_version"))
        and row.get("deepseek_key_source") == "DEEPSEEK_API_KEY"
        and not bool(row.get("deepseek_key_written"))
        and int(row.get("executor_called_on_deny_ask", 1)) == 0
        and not bool(row.get("production_level_overclaim"))
    )


def first_missing(row: Mapping[str, Any]) -> str:
    for key in (
        "agent_binary",
        "agent_version",
        "real_agent_process_ran",
        "deepseek_real_call",
        "standard_capproof_mcp_server_used",
        "tools_list_observed",
        "tools_call_observed",
        "allow_read_write_command_observed",
        "deny_outside_path_raw_shell_attacker_observed",
        "ask_pending_request_created",
        "trusted_approval_executed",
        "approval_receipt_generated",
        "rerun_allow_observed",
        "llm_metadata_approval_rejected",
        "trace_live_log_report_generated",
    ):
        if not row.get(key):
            return f"blocked_{key}"
    if row.get("deepseek_key_source") != "DEEPSEEK_API_KEY":
        return "blocked_deepseek_key_source"
    if row.get("deepseek_key_written"):
        return "failed_deepseek_key_written"
    if int(row.get("executor_called_on_deny_ask", 1)) != 0:
        return "failed_executor_called_on_deny_ask"
    if row.get("production_level_overclaim"):
        return "failed_production_level_overclaim"
    return "blocked_unknown"


def scenario_passed(summary: Mapping[str, Any], scenario_id: str) -> bool:
    for row in summary.get("scenario_matrix", []):
        if isinstance(row, dict) and row.get("scenario_id") == scenario_id:
            return bool(row.get("passed"))
    return False


def secret_scan_result(env: Mapping[str, str]) -> dict[str, Any]:
    current_key = env.get("DEEPSEEK_API_KEY", "")
    paths = tracked_paths()
    for directory in (
        ARTIFACT_DIR,
        ROOT / "real_agent_integrations" / "hermes_mcp_server" / "reports",
        ROOT / "real_agent_integrations" / "hermes_mcp_server" / "traces",
        ROOT / "real_agent_integrations" / "opencode_mcp_server" / "reports",
        ROOT / "real_agent_integrations" / "opencode_mcp_server" / "traces",
        ROOT / "real_agent_integrations" / "openclaw_mcp_server" / "reports",
        ROOT / "real_agent_integrations" / "openclaw_mcp_server" / "traces",
    ):
        if directory.exists():
            paths.extend(path for path in directory.rglob("*") if path.is_file())
    hits: list[str] = []
    for path in sorted(set(paths)):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if current_key and current_key in text:
            hits.append(display_path(path))
            continue
        for match in SECRET_RE.finditer(text):
            if match.group(0) not in ALLOWED_DUMMY_SECRETS:
                hits.append(display_path(path))
                break
    return {
        "real_key_scan": "REAL_KEY_NOT_FOUND" if not hits else "REAL_KEY_FOUND",
        "hits": hits,
        "key_value_printed": False,
        "dummy_fixture_allowlist": sorted(ALLOWED_DUMMY_SECRETS),
    }


def tracked_paths() -> list[Path]:
    completed = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return []
    return [ROOT / line for line in completed.stdout.splitlines() if line.strip()]


def forbidden_tracked_paths() -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "ls-files",
            "external",
            "external/.agent-runtimes",
            ".venv-hermes",
            "node_modules",
            "real_agent_integrations/hermes_mcp_server/auth_queue",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ["git_ls_files_failed"]
    return [line for line in completed.stdout.splitlines() if line.strip()]


def write_artifacts(summary: Mapping[str, Any]) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(summary), encoding="utf-8")
    matrix = {"stage": "42EVAL", "agents": summary["all_agents"], "evaluator_passed": summary["evaluator_passed"]}
    MATRIX_JSON_PATH.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MATRIX_MD_PATH.write_text(render_matrix(summary["all_agents"], summary["evaluator_passed"]), encoding="utf-8")
    claims = claims_index()
    CLAIMS_JSON_PATH.write_text(json.dumps({"claims": claims}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CLAIMS_MD_PATH.write_text(render_claims(claims), encoding="utf-8")


def render_report(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Real Agent Parity Evaluator Report",
        "",
        "## Positioning",
        "",
        "- Stage 42EVAL freezes the controlled local real-environment agent parity artifact.",
        "- Preflight and dry-run are readiness only, not completion evidence.",
        "- Reusing existing reports is labeled as reuse and is not a fresh run.",
        "- This report does not claim production-level protection.",
        "",
        "## Summary",
        "",
        f"- evaluator_mode: {summary['evaluator_mode']}",
        f"- fresh_run: {summary['fresh_run']}",
        f"- evaluator_passed: {summary['evaluator_passed']}",
        f"- aggregate_agent_parity_passed: {summary['aggregate_agent_parity_passed']}",
        f"- real_environment_policy_active: {summary['real_environment_policy_active']}",
        f"- dry_run_preflight_counts_as_completion: {summary['dry_run_preflight_counts_as_completion']}",
        f"- api_key_written: {summary['api_key_written']}",
        f"- production_level_overclaim: {summary['production_level_overclaim']}",
        f"- forbidden_tracked_paths_count: {summary['forbidden_tracked_paths_count']}",
        f"- secret_scan: {summary['secret_scan']['real_key_scan']}",
        "",
        "## Agent Matrix",
        "",
    ]
    lines.append(render_matrix_table(summary["all_agents"]))
    lines.extend(
        [
            "",
            "## Commands",
            "",
        ]
    )
    if summary["commands"]:
        for item in summary["commands"]:
            lines.append(f"- {item['label']}: rc={item['returncode']} command=`{item['command']}`")
    else:
        lines.append("- no real commands executed")
    lines.extend(
        [
            "",
            "## Non-Claims",
            "",
            "- no production-level protection",
            "- no all built-in tool paths covered",
            "- no external MCP protection",
            "- no real email",
            "- no raw shell support",
            "- no arbitrary filesystem access",
            "- no OS-level network denial",
            "- DeepSeek is not safety TCB",
            "- LLM/MCP metadata cannot authorize execution",
        ]
    )
    return "\n".join(lines) + "\n"


def render_matrix(rows: Sequence[Mapping[str, Any]], evaluator_passed: bool) -> str:
    return (
        "# Real Agent Parity Evaluator Matrix\n\n"
        f"- evaluator_passed: {evaluator_passed}\n\n"
        + render_matrix_table(rows)
        + "\n"
    )


def render_matrix_table(rows: Sequence[Mapping[str, Any]]) -> str:
    fields = (
        "agent",
        "real_agent_process_ran",
        "agent_binary",
        "agent_version",
        "deepseek_real_call",
        "deepseek_key_source",
        "deepseek_key_written",
        "standard_capproof_mcp_server_used",
        "tools_list_observed",
        "tools_call_observed",
        "allow_read_write_command_observed",
        "deny_outside_path_raw_shell_attacker_observed",
        "ask_pending_request_created",
        "trusted_approval_executed",
        "approval_receipt_generated",
        "rerun_allow_observed",
        "llm_metadata_approval_rejected",
        "executor_called_on_deny_ask",
        "trace_live_log_report_generated",
        "parity_passed",
        "reason",
    )
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def claims_index() -> list[dict[str, Any]]:
    return [
        {
            "claim": claim,
            "status": status,
            "evidence_file": evidence_file,
            "test_command": test_command,
            "stage_commit": stage_commit,
            "notes": notes,
        }
        for claim, status, evidence_file, test_command, stage_commit, notes in CLAIM_ROWS
    ]


def render_claims(claims: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Final Claims Evidence Index",
        "",
        "| claim | status | evidence file | test command | stage commit | notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in claims:
        lines.append(
            f"| {row['claim']} | {row['status']} | {row['evidence_file']} | `{row['test_command']}` | {row['stage_commit']} | {row['notes']} |"
        )
    return "\n".join(lines) + "\n"


def print_output(summary: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return
    print(f"evaluator_mode={summary['evaluator_mode']}")
    print(f"fresh_run={summary['fresh_run']}")
    print(f"evaluator_passed={summary['evaluator_passed']}")
    print(f"aggregate_agent_parity_passed={summary['aggregate_agent_parity_passed']}")
    print(f"summary={SUMMARY_PATH}")
    print(f"report={REPORT_PATH}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def display_command(command: Sequence[str]) -> str:
    return " ".join(command)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def redact(text: str, env: Mapping[str, str] | None = None) -> str:
    redacted = SECRET_RE.sub("[REDACTED_SECRET]", text)
    key = env.get("DEEPSEEK_API_KEY") if env else None
    if key:
        redacted = redacted.replace(key, "[REDACTED_DEEPSEEK_API_KEY]")
    return redacted


if __name__ == "__main__":
    raise SystemExit(main())
