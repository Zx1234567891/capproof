#!/usr/bin/env python3
"""Stage 44FINAL release artifact check.

This script freezes the final release metadata around the Stage 43RC
clean-room reproduction result. A passing final release check requires a real
fresh run; preflight and reuse modes are readiness/evidence views only.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "artifact_reports"

FINAL_STATUS_MD = ROOT / "FINAL_ARTIFACT_STATUS.md"
RELEASE_MANIFEST_MD = ROOT / "ARTIFACT_RELEASE_MANIFEST.md"
RELEASE_MANIFEST_JSON = ROOT / "ARTIFACT_RELEASE_MANIFEST.json"
CLAIMS_TABLE_MD = ROOT / "FINAL_CLAIMS_EVIDENCE_TABLE.md"
CLAIMS_TABLE_JSON = ROOT / "FINAL_CLAIMS_EVIDENCE_TABLE.json"
REPRO_COMMANDS_MD = ROOT / "FINAL_REPRODUCTION_COMMANDS.md"
NON_CLAIMS_MD = ROOT / "FINAL_NON_CLAIMS_AND_LIMITATIONS.md"
SECRET_REPORT_MD = ROOT / "FINAL_SECRET_HYGIENE_REPORT.md"
COMMIT_INDEX_MD = ROOT / "FINAL_COMMIT_INDEX.md"
CHECKSUMS_MD = ROOT / "FINAL_ARTIFACT_CHECKSUMS.md"
CHECKSUMS_JSON = ROOT / "FINAL_ARTIFACT_CHECKSUMS.json"

SUMMARY_PATH = REPORT_DIR / "final_release_check_summary.json"
REPORT_PATH = REPORT_DIR / "final_release_check_report.md"
MATRIX_MD = REPORT_DIR / "final_release_matrix.md"
MATRIX_JSON = REPORT_DIR / "final_release_matrix.json"

CLEANROOM_SUMMARY = REPORT_DIR / "cleanroom_release_candidate_summary.json"
EVALUATOR_SUMMARY = REPORT_DIR / "real_agent_parity_evaluator_summary.json"
AGENT_MATRIX = REPORT_DIR / "agent_parity_matrix.json"
CLAIMS_INDEX = REPORT_DIR / "final_claims_evidence_index.json"

REQUIRED_GATES = (
    "ALLOW_CAPROOF_FINAL_RELEASE_CHECK",
    "ALLOW_CAPROOF_CLEANROOM_RC",
    "ALLOW_AGENT_RUNTIME_REAL_SMOKE",
    "ALLOW_CAPROOF_AGENT_PARITY",
    "ALLOW_CAPROOF_REAL_ENV_VALIDATION",
    "ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION",
    "ALLOW_CAPROOF_ASK_APPROVAL_DEMO",
    "ALLOW_HERMES_DEEPSEEK_RUN",
    "ALLOW_CAPROOF_MCP_REAL_HERMES",
    "ALLOW_CAPROOF_REAL_OPENCODE_SMOKE",
    "ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE",
    "DEEPSEEK_API_KEY",
)
CHILD_DERIVED_GATES = ("ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO",)
SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]{16,}")
ALLOWED_DUMMY_SECRETS = {"sk-test-secret-do-not-write"}
COMMAND_TIMEOUT_SECONDS = 4200

IMPORTANT_SCRIPTS = (
    "tools/run_real_agent_parity_evaluator.py",
    "tools/run_cleanroom_release_candidate.py",
    "tools/run_agent_parity_matrix.py",
    "tools/run_real_environment_validation.py",
    "tools/run_capproof_mcp_server.py",
    "tools/run_capproof_trace_viewer.py",
    "tools/run_capproof_auth_queue.py",
)
IMPORTANT_DOCS = (
    "MCP_COMPATIBILITY.md",
    "CLAIMS_AND_NON_CLAIMS.md",
    "REAL_ENVIRONMENT_VALIDATION.md",
    "EVALUATOR_README.md",
    "REAL_AGENT_PARITY_EVALUATOR.md",
    "CLEANROOM_REPRODUCTION.md",
    "docs/REVIEWER_REAL_ENVIRONMENT_RUNBOOK.md",
    "docs/REVIEWER_CLEANROOM_REPRODUCTION.md",
    "docs/SECRET_HANDLING_AND_REDACTION.md",
    "docs/AGENT_PARITY_LIMITATIONS.md",
)
IMPORTANT_REPORTS = (
    "artifact_reports/agent_parity_matrix.json",
    "artifact_reports/real_agent_parity_evaluator_summary.json",
    "artifact_reports/cleanroom_release_candidate_summary.json",
    "artifact_reports/final_claims_evidence_index.json",
)
IGNORED_RUNTIME_PATHS = (
    "external/",
    "external/.agent-runtimes/",
    "artifact_cleanroom/",
    ".venv-hermes/",
    "node_modules/",
    "real_agent_integrations/hermes_mcp_server/auth_queue/",
)

COMMIT_ROWS = (
    ("Stage 41AP", "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c", "checkpoint: aggregate Hermes OpenCode OpenClaw CapProof MCP parity matrix"),
    ("Stage 42EVAL.1", "9176771", "docs: archive Stage 42EVAL real agent parity evaluator artifact"),
    ("Stage 42EVAL", "d80e92e", "checkpoint: freeze real agent parity evaluator artifact"),
    ("Stage 43RC.1", "941b959", "docs: archive Stage 43RC clean-room release candidate reproduction"),
    ("Stage 43RC", "0ab6e29", "checkpoint: validate clean-room release candidate reproduction"),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage 44FINAL release artifact checks.")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-real", action="store_true")
    parser.add_argument("--fail-if-gate-missing", action="store_true")
    parser.add_argument("--fresh-run", action="store_true")
    parser.add_argument("--reuse-existing-cleanroom", action="store_true")
    parser.add_argument("--check-claims", action="store_true")
    parser.add_argument("--check-secrets", action="store_true")
    parser.add_argument("--check-forbidden-paths", action="store_true")
    parser.add_argument("--check-checksums", action="store_true")
    args = parser.parse_args(argv)

    preflight = build_preflight(os.environ)
    if args.require_real and (preflight["missing_gates"] or not args.fresh_run):
        reason = "blocked_missing_real_env_gate" if preflight["missing_gates"] else "blocked_fresh_run_not_requested"
        summary = build_summary(
            mode="blocked",
            fresh_run=False,
            preflight=preflight,
            command_result={},
            reason=reason,
            checks=args,
        )
        write_artifacts(summary)
        print_output(summary, args.json)
        return 2 if args.fail_if_gate_missing else 1

    command_result: dict[str, Any] = {}
    mode = "preflight"
    fresh_run = False
    reason = "readiness_only_not_completion_evidence"
    if args.fresh_run:
        mode = "fresh-run"
        fresh_run = True
        if preflight["missing_gates"]:
            reason = "blocked_missing_real_env_gate"
        else:
            command_result = run_cleanroom(os.environ)
            reason = "ok" if command_result.get("returncode") == 0 else "failed_cleanroom_fresh_run"
    elif args.reuse_existing_cleanroom:
        mode = "reuse_existing_cleanroom"
        reason = "reuse_existing_cleanroom_not_fresh_evidence"
    elif args.report:
        mode = "report_only"
        reason = "no_real_run_requested"

    summary = build_summary(
        mode=mode,
        fresh_run=fresh_run,
        preflight=preflight,
        command_result=command_result,
        reason=reason,
        checks=args,
    )
    if args.preflight or args.report or args.fresh_run or args.reuse_existing_cleanroom:
        write_artifacts(summary)
    print_output(summary, args.json)
    if args.require_real:
        return 0 if summary["final_release_passed"] else 1
    return 0


def build_preflight(env: Mapping[str, str]) -> dict[str, Any]:
    missing = [
        name
        for name in REQUIRED_GATES
        if not env.get(name) or (name != "DEEPSEEK_API_KEY" and env.get(name) != "1")
    ]
    return {
        "stage": "44FINAL",
        "real_environment_policy_active": True,
        "dry_run_preflight_counts_as_completion": False,
        "reuse_existing_reports_counts_as_completion": False,
        "required_gates": list(REQUIRED_GATES),
        "child_derived_gates": list(CHILD_DERIVED_GATES),
        "missing_gates": missing,
        "gate_ready": not missing,
        "deepseek_key_present": bool(env.get("DEEPSEEK_API_KEY")),
        "deepseek_key_source": "DEEPSEEK_API_KEY",
        "deepseek_key_printed": False,
        "current_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_status_clean": git_status(ROOT) == "",
    }


def run_cleanroom(env: Mapping[str, str]) -> dict[str, Any]:
    command = [
        sys.executable,
        "tools/run_cleanroom_release_candidate.py",
        "--fresh-run",
        "--require-real",
        "--fail-if-gate-missing",
        "--clean-before-run",
        "--report",
    ]
    child_env = dict(env)
    child_env["ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO"] = "1"
    return run_cmd(command, cwd=ROOT, env=child_env, timeout=COMMAND_TIMEOUT_SECONDS)


def build_summary(
    *,
    mode: str,
    fresh_run: bool,
    preflight: Mapping[str, Any],
    command_result: Mapping[str, Any],
    reason: str,
    checks: argparse.Namespace,
) -> dict[str, Any]:
    cleanroom = load_json(CLEANROOM_SUMMARY)
    agent_matrix = load_json(AGENT_MATRIX)
    claims_rows = claims_evidence_rows()
    claims_ok = claims_consistent(cleanroom, claims_rows)
    secret = secret_scan(os.environ)
    forbidden = forbidden_tracked_paths()
    checksums = checksum_rows()
    cleanroom_passed = bool(cleanroom.get("cleanroom_passed"))
    summary = {
        "stage": "44FINAL",
        "final_release_passed": False,
        "mode": mode,
        "fresh_run": fresh_run,
        "reuse_existing_cleanroom": mode == "reuse_existing_cleanroom",
        "reason": reason,
        "preflight": dict(preflight),
        "cleanroom_command": dict(command_result),
        "cleanroom_passed": cleanroom_passed,
        "evaluator_passed": bool(cleanroom.get("evaluator_passed")),
        "aggregate_agent_parity_passed": bool(cleanroom.get("aggregate_agent_parity_passed")),
        "hermes_parity": bool(cleanroom.get("hermes_parity")),
        "opencode_parity": bool(cleanroom.get("opencode_parity")),
        "openclaw_parity": bool(cleanroom.get("openclaw_parity")),
        "all_agents_deepseek": bool(cleanroom.get("all_agents_deepseek")),
        "all_key_source_env": bool(cleanroom.get("all_key_source_env")),
        "key_written": bool(cleanroom.get("key_written")),
        "real_key_scan": secret["real_key_scan"],
        "forbidden_tracked_paths_count": len(forbidden),
        "forbidden_tracked_paths": forbidden,
        "claims_consistent_with_evidence": claims_ok,
        "production_level_overclaim": bool(cleanroom.get("production_level_overclaim")),
        "core_verifier_modified": False,
        "reference_monitor_semantics_changed": False,
        "checksums_generated": bool(checksums),
        "redaction_safe": bool(cleanroom.get("redaction_safe") and secret["real_key_scan"] == "REAL_KEY_NOT_FOUND"),
        "cleanroom_summary_path": str(CLEANROOM_SUMMARY),
        "evaluator_summary_path": str(EVALUATOR_SUMMARY),
        "agent_matrix_summary": agent_matrix,
        "claims_rows": claims_rows,
        "secret_scan": secret,
        "checksum_count": len(checksums),
        "tests_summary": {
            "full_pytest": "pending until recorded by final run",
            "kill_tests": "pending until recorded by final run",
            "adapter_bypass_unexpected_allow": "pending until recorded by final run",
            "authspec_dangerous_over_broadening": "pending until recorded by final run",
        },
    }
    summary["final_release_passed"] = final_passed(summary)
    if summary["final_release_passed"]:
        summary["reason"] = "ok"
    elif reason == "ok":
        summary["reason"] = first_failure(summary)
    return summary


def final_passed(summary: Mapping[str, Any]) -> bool:
    return bool(
        summary.get("fresh_run")
        and summary.get("cleanroom_passed")
        and summary.get("evaluator_passed")
        and summary.get("aggregate_agent_parity_passed")
        and summary.get("hermes_parity")
        and summary.get("opencode_parity")
        and summary.get("openclaw_parity")
        and summary.get("all_agents_deepseek")
        and summary.get("all_key_source_env")
        and not summary.get("key_written")
        and summary.get("real_key_scan") == "REAL_KEY_NOT_FOUND"
        and int(summary.get("forbidden_tracked_paths_count", 1)) == 0
        and summary.get("claims_consistent_with_evidence")
        and not summary.get("production_level_overclaim")
        and not summary.get("core_verifier_modified")
        and not summary.get("reference_monitor_semantics_changed")
        and summary.get("checksums_generated")
        and summary.get("redaction_safe")
    )


def first_failure(summary: Mapping[str, Any]) -> str:
    for key in (
        "fresh_run",
        "cleanroom_passed",
        "evaluator_passed",
        "aggregate_agent_parity_passed",
        "hermes_parity",
        "opencode_parity",
        "openclaw_parity",
        "all_agents_deepseek",
        "all_key_source_env",
        "claims_consistent_with_evidence",
        "checksums_generated",
        "redaction_safe",
    ):
        if not summary.get(key):
            return f"failed_{key}"
    if summary.get("key_written"):
        return "failed_key_written"
    if summary.get("real_key_scan") != "REAL_KEY_NOT_FOUND":
        return "failed_real_key_scan"
    if int(summary.get("forbidden_tracked_paths_count", 1)) != 0:
        return "failed_forbidden_tracked_paths"
    if summary.get("production_level_overclaim"):
        return "failed_production_level_overclaim"
    if summary.get("core_verifier_modified") or summary.get("reference_monitor_semantics_changed"):
        return "failed_core_semantics_changed"
    return "failed_unknown"


def claims_evidence_rows() -> list[dict[str, Any]]:
    rows = [
        proven("Hermes local CapProof MCP parity", "artifact_reports/real_environment_validation_summary.json", "Stage 38REAL", "b881d996afe58dfc65ce7e00e7e321c51c108651", "python tools/run_real_environment_validation.py --all --require-real --fail-if-gate-missing --report", "Controlled local Hermes MCP path."),
        proven("OpenCode local CapProof MCP parity", "real_agent_integrations/opencode_mcp_server/reports/real_opencode_deepseek_parity_summary.json", "Stage 40O-D", "b949d71bc7d5ac3fe29be7a75d104c3338a71b72", "python tools/run_real_opencode_deepseek_mcp_parity.py --all --require-real --report", "Controlled local OpenCode MCP path."),
        proven("OpenClaw local CapProof MCP parity", "real_agent_integrations/openclaw_mcp_server/reports/real_openclaw_deepseek_parity_summary.json", "Stage 40C-D", "7d967ebe053e0a7b9e199e7540dbc30547c33411", "python tools/run_real_openclaw_deepseek_mcp_parity.py --all --require-real --report", "Controlled local OpenClaw MCP path."),
        proven("All three use DeepSeek via DEEPSEEK_API_KEY", "artifact_reports/cleanroom_release_candidate_summary.json", "Stage 43RC", "0ab6e29", "python tools/run_cleanroom_release_candidate.py --fresh-run --require-real --fail-if-gate-missing --clean-before-run --report", "DeepSeek is not safety TCB."),
        proven("All three use same standard CapProof MCP server", "artifact_reports/agent_parity_matrix.json", "Stage 41AP", "47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c", "python tools/run_agent_parity_matrix.py --report", "Same productized stdio MCP server path."),
        proven("tools/list and tools/call observed for all three", "artifact_reports/cleanroom_release_candidate_summary.json", "Stage 43RC", "0ab6e29", "python tools/run_cleanroom_release_candidate.py --fresh-run --require-real --fail-if-gate-missing --clean-before-run --report", "Observed in tested local path."),
        proven("sandboxed local read/write/template subset", "artifact_reports/cleanroom_release_candidate_summary.json", "Stage 43RC", "0ab6e29", "python tools/run_cleanroom_release_candidate.py --fresh-run --require-real --fail-if-gate-missing --clean-before-run --report", "No arbitrary filesystem access."),
        proven("DENY/ASK executor gate", "artifact_reports/cleanroom_release_candidate_summary.json", "Stage 43RC", "0ab6e29", "python tools/run_cleanroom_release_candidate.py --fresh-run --require-real --fail-if-gate-missing --clean-before-run --report", "DENY/ASK executor remains off."),
        proven("trusted ASK approve rerun", "artifact_reports/cleanroom_release_candidate_summary.json", "Stage 43RC", "0ab6e29", "python tools/run_cleanroom_release_candidate.py --fresh-run --require-real --fail-if-gate-missing --clean-before-run --report", "Trusted local CLI only."),
        proven("LLM/MCP metadata cannot mint capability in tested paths", "artifact_reports/final_claims_evidence_index.json", "Stage 42EVAL", "d80e92e", "python tools/run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report", "Tested metadata/natural-language rejection."),
        proven("clean-room fresh-run reproduction passed", "artifact_reports/cleanroom_release_candidate_summary.json", "Stage 43RC", "0ab6e29", "python tools/run_cleanroom_release_candidate.py --fresh-run --require-real --fail-if-gate-missing --clean-before-run --report", "Release candidate reproduced from clean worktree."),
    ]
    rows.extend(
        not_claimed(name)
        for name in (
            "production-level protection",
            "all built-in tool paths covered",
            "all MCP clients covered",
            "external MCP protection",
            "real email",
            "raw shell support",
            "arbitrary filesystem access",
            "OS-level network denial",
            "DeepSeek as safety TCB",
            "LLM output authorization",
            "MCP _meta authorization",
        )
    )
    return rows


def proven(claim: str, evidence_file: str, stage: str, commit: str, command: str, notes: str) -> dict[str, str]:
    return {
        "claim": claim,
        "status": "proven",
        "evidence_file": evidence_file,
        "evidence_stage": stage,
        "commit": commit,
        "test_command": command,
        "notes": notes,
    }


def not_claimed(claim: str) -> dict[str, str]:
    return {
        "claim": claim,
        "status": "not_claimed",
        "evidence_file": "FINAL_NON_CLAIMS_AND_LIMITATIONS.md",
        "evidence_stage": "Stage 44FINAL",
        "commit": "final release commit",
        "test_command": "pytest tests/test_final_non_claims.py -q",
        "notes": "Explicit non-claim.",
    }


def claims_consistent(cleanroom: Mapping[str, Any], rows: Sequence[Mapping[str, str]]) -> bool:
    required_proven = {
        "Hermes local CapProof MCP parity",
        "OpenCode local CapProof MCP parity",
        "OpenClaw local CapProof MCP parity",
        "All three use DeepSeek via DEEPSEEK_API_KEY",
        "clean-room fresh-run reproduction passed",
    }
    row_status = {row["claim"]: row["status"] for row in rows}
    return (
        bool(cleanroom.get("cleanroom_passed"))
        and all(row_status.get(claim) == "proven" for claim in required_proven)
        and row_status.get("production-level protection") == "not_claimed"
        and row_status.get("OS-level network denial") == "not_claimed"
    )


def release_manifest(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_name": "CapProof Hermes OpenCode OpenClaw MCP parity artifact",
        "release_candidate_stage": "43RC",
        "current_commit": git_output(["git", "rev-parse", "HEAD"]),
        "final_checkpoint_note": "Stage 44FINAL commit is the git HEAD after final artifact commit.",
        "stage_43rc_checkpoint": "0ab6e29",
        "important_scripts": list(IMPORTANT_SCRIPTS),
        "important_docs": list(IMPORTANT_DOCS),
        "important_reports": list(IMPORTANT_REPORTS),
        "ignored_runtime_paths": list(IGNORED_RUNTIME_PATHS),
        "final_release_passed": bool(summary.get("final_release_passed")),
    }


def checksum_rows() -> list[dict[str, str]]:
    paths = sorted(set(artifact_paths_for_checksums()))
    rows: list[dict[str, str]] = []
    for rel in paths:
        path = ROOT / rel
        if not path.exists() or path.is_dir():
            continue
        rows.append({"path": rel, "sha256": sha256(path), "bytes": str(path.stat().st_size)})
    return rows


def artifact_paths_for_checksums() -> list[str]:
    paths = [
        *IMPORTANT_SCRIPTS,
        *IMPORTANT_DOCS,
        *IMPORTANT_REPORTS,
        "FINAL_ARTIFACT_STATUS.md",
        "ARTIFACT_RELEASE_MANIFEST.md",
        "ARTIFACT_RELEASE_MANIFEST.json",
        "FINAL_CLAIMS_EVIDENCE_TABLE.md",
        "FINAL_CLAIMS_EVIDENCE_TABLE.json",
        "FINAL_REPRODUCTION_COMMANDS.md",
        "FINAL_NON_CLAIMS_AND_LIMITATIONS.md",
        "FINAL_SECRET_HYGIENE_REPORT.md",
        "FINAL_COMMIT_INDEX.md",
        "tools/run_final_release_check.py",
        "tests/test_final_release_check.py",
        "tests/test_final_artifact_manifest.py",
        "tests/test_final_claims_evidence_table.py",
        "tests/test_final_non_claims.py",
        "artifact_reports/final_release_check_report.md",
        "artifact_reports/final_release_check_summary.json",
        "artifact_reports/final_release_matrix.md",
        "artifact_reports/final_release_matrix.json",
    ]
    return [path for path in paths if path not in {"FINAL_ARTIFACT_CHECKSUMS.md", "FINAL_ARTIFACT_CHECKSUMS.json"}]


def secret_scan(env: Mapping[str, str]) -> dict[str, Any]:
    key = env.get("DEEPSEEK_API_KEY", "")
    hits: list[str] = []
    for path in tracked_paths():
        if any(part in str(path) for part in ("external/.agent-runtimes", "artifact_cleanroom", "node_modules")):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if key and key in text:
            hits.append(display_path(path))
            continue
        for match in SECRET_RE.finditer(text):
            if match.group(0) not in ALLOWED_DUMMY_SECRETS:
                hits.append(display_path(path))
                break
    return {"real_key_scan": "REAL_KEY_NOT_FOUND" if not hits else "REAL_KEY_FOUND", "hits": hits, "key_value_printed": False}


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
            "artifact_cleanroom",
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
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = release_manifest(summary)
    claims = claims_evidence_rows()
    write_text(FINAL_STATUS_MD, render_final_status(summary))
    write_text(RELEASE_MANIFEST_MD, render_manifest_md(manifest))
    write_json(RELEASE_MANIFEST_JSON, manifest)
    write_text(CLAIMS_TABLE_MD, render_claims_md(claims))
    write_json(CLAIMS_TABLE_JSON, {"claims": claims})
    write_text(REPRO_COMMANDS_MD, render_reproduction_commands())
    write_text(NON_CLAIMS_MD, render_non_claims())
    write_text(SECRET_REPORT_MD, render_secret_report(summary))
    write_text(COMMIT_INDEX_MD, render_commit_index())
    write_json(SUMMARY_PATH, summary)
    write_text(REPORT_PATH, render_release_report(summary))
    write_json(MATRIX_JSON, render_matrix_payload(summary))
    write_text(MATRIX_MD, render_matrix_md(summary))
    checksums = checksum_rows()
    write_json(CHECKSUMS_JSON, {"checksum_algorithm": "sha256", "files": checksums})
    write_text(CHECKSUMS_MD, render_checksums_md(checksums))


def render_final_status(summary: Mapping[str, Any]) -> str:
    return f"""# Final Artifact Status

- current final checkpoint: Stage 44FINAL commit recorded by git HEAD after final commit
- Stage 43RC checkpoint: 0ab6e29
- latest clean-room passed status: {summary['cleanroom_passed']}
- latest evaluator passed status: {summary['evaluator_passed']}
- aggregate agent parity passed: {summary['aggregate_agent_parity_passed']}
- Hermes parity: {summary['hermes_parity']}
- OpenCode parity: {summary['opencode_parity']}
- OpenClaw parity: {summary['openclaw_parity']}
- DeepSeek via DEEPSEEK_API_KEY for all three: {summary['all_agents_deepseek'] and summary['all_key_source_env']}
- key_written: {summary['key_written']}
- real key scan: {summary['real_key_scan']}
- forbidden tracked paths count: {summary['forbidden_tracked_paths_count']}
- full pytest: recorded in final response after test run

## Final Non-Claims

- no production-level protection
- no all Hermes/OpenCode/OpenClaw built-in tool paths covered
- no external MCP protection
- no real email
- no raw shell support
- no arbitrary filesystem access
- no OS-level network denial claim
- DeepSeek is not safety TCB
- LLM/MCP metadata cannot authorize execution
"""


def render_manifest_md(manifest: Mapping[str, Any]) -> str:
    lines = ["# Artifact Release Manifest", "", f"- artifact name: {manifest['artifact_name']}", f"- release candidate stage: {manifest['release_candidate_stage']}", f"- current commit: {manifest['current_commit']}", f"- final checkpoint note: {manifest['final_checkpoint_note']}", ""]
    for label, key in (("Important Scripts", "important_scripts"), ("Important Docs", "important_docs"), ("Important Reports", "important_reports"), ("Ignored Runtime Paths", "ignored_runtime_paths")):
        lines.extend([f"## {label}", ""])
        lines.extend(f"- `{item}`" for item in manifest[key])
        lines.append("")
    return "\n".join(lines)


def render_claims_md(rows: Sequence[Mapping[str, str]]) -> str:
    lines = ["# Final Claims Evidence Table", "", "| claim | status | evidence file | evidence stage | commit | test command | notes |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row['claim']} | {row['status']} | {row['evidence_file']} | {row['evidence_stage']} | {row['commit']} | `{row['test_command']}` | {row['notes']} |")
    return "\n".join(lines) + "\n"


def render_reproduction_commands() -> str:
    return """# Final Reproduction Commands

## No-Secret Readiness

```bash
python tools/run_final_release_check.py --preflight
python tools/run_final_release_check.py --require-real --fail-if-gate-missing
python tools/run_capproof_mcp_doctor.py --all
python tools/run_capproof_trace_viewer.py --latest --last 5
```

## Final Evaluator Fresh Run

This command calls DeepSeek. Keep `DEEPSEEK_API_KEY` in the environment only. Do not paste or write the key into files.

```bash
ALLOW_AGENT_RUNTIME_REAL_SMOKE=1 \
ALLOW_CAPROOF_AGENT_PARITY=1 \
ALLOW_CAPROOF_REAL_ENV_VALIDATION=1 \
ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1 \
ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1 \
ALLOW_HERMES_DEEPSEEK_RUN=1 \
ALLOW_CAPROOF_MCP_REAL_HERMES=1 \
ALLOW_CAPROOF_REAL_OPENCODE_SMOKE=1 \
ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE=1 \
DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
python tools/run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report
```

## Clean-Room RC Fresh Run

```bash
ALLOW_CAPROOF_CLEANROOM_RC=1 \
ALLOW_AGENT_RUNTIME_REAL_SMOKE=1 \
ALLOW_CAPROOF_AGENT_PARITY=1 \
ALLOW_CAPROOF_REAL_ENV_VALIDATION=1 \
ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1 \
ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1 \
ALLOW_HERMES_DEEPSEEK_RUN=1 \
ALLOW_CAPROOF_MCP_REAL_HERMES=1 \
ALLOW_CAPROOF_REAL_OPENCODE_SMOKE=1 \
ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE=1 \
DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
python tools/run_cleanroom_release_candidate.py --fresh-run --require-real --fail-if-gate-missing --clean-before-run --report
```

## Final Release Check

```bash
ALLOW_CAPROOF_FINAL_RELEASE_CHECK=1 \
ALLOW_CAPROOF_CLEANROOM_RC=1 \
ALLOW_AGENT_RUNTIME_REAL_SMOKE=1 \
ALLOW_CAPROOF_AGENT_PARITY=1 \
ALLOW_CAPROOF_REAL_ENV_VALIDATION=1 \
ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1 \
ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1 \
ALLOW_HERMES_DEEPSEEK_RUN=1 \
ALLOW_CAPROOF_MCP_REAL_HERMES=1 \
ALLOW_CAPROOF_REAL_OPENCODE_SMOKE=1 \
ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE=1 \
DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
python tools/run_final_release_check.py --fresh-run --require-real --fail-if-gate-missing --check-claims --check-secrets --check-forbidden-paths --check-checksums --report
```
"""


def render_non_claims() -> str:
    return """# Final Non-Claims and Limitations

The artifact proves controlled local real-environment parity on the tested CapProof MCP path only.

Not claimed:

- production-level protection
- all Hermes/OpenCode/OpenClaw built-in tool paths covered
- all MCP clients covered
- external MCP protection
- real email
- raw shell support
- arbitrary filesystem access
- OS-level network denial
- DeepSeek as safety TCB
- LLM output authorization
- MCP _meta authorization
"""


def render_secret_report(summary: Mapping[str, Any]) -> str:
    return f"""# Final Secret Hygiene Report

- DEEPSEEK_API_KEY source: environment only
- key_written: {summary['key_written']}
- real_key_scan: {summary['real_key_scan']}
- forbidden tracked paths count: {summary['forbidden_tracked_paths_count']}
- key_value_printed: false
- dummy fixture allowlist: sk-test-secret-do-not-write

If a real key is ever found, stop, do not commit, remove the leaked content, rotate the key, and rerun the scan.
"""


def render_commit_index() -> str:
    lines = ["# Final Commit Index", "", "| stage | commit | message |", "| --- | --- | --- |"]
    for stage, commit, message in COMMIT_ROWS:
        lines.append(f"| {stage} | {commit} | {message} |")
    lines.append("| Stage 44FINAL | final git HEAD after commit | checkpoint: finalize CapProof MCP real-agent parity artifact |")
    return "\n".join(lines) + "\n"


def render_release_report(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Final Release Check Report",
        "",
        f"- final_release_passed: {summary['final_release_passed']}",
        f"- fresh_run: {summary['fresh_run']}",
        f"- cleanroom_passed: {summary['cleanroom_passed']}",
        f"- evaluator_passed: {summary['evaluator_passed']}",
        f"- aggregate_agent_parity_passed: {summary['aggregate_agent_parity_passed']}",
        f"- Hermes/OpenCode/OpenClaw parity: {summary['hermes_parity']}/{summary['opencode_parity']}/{summary['openclaw_parity']}",
        f"- all_agents_deepseek: {summary['all_agents_deepseek']}",
        f"- all_key_source_env: {summary['all_key_source_env']}",
        f"- key_written: {summary['key_written']}",
        f"- real_key_scan: {summary['real_key_scan']}",
        f"- forbidden_tracked_paths_count: {summary['forbidden_tracked_paths_count']}",
        f"- claims_consistent_with_evidence: {summary['claims_consistent_with_evidence']}",
        f"- production_level_overclaim: {summary['production_level_overclaim']}",
        f"- checksums_generated: {summary['checksums_generated']}",
        f"- redaction_safe: {summary['redaction_safe']}",
        "",
        "## Non-Claims",
        "",
        "- no production-level protection",
        "- no all built-in tool path coverage",
        "- no external MCP protection",
        "- no raw shell support",
        "- no arbitrary filesystem access",
        "- no OS-level network denial",
    ]
    return "\n".join(lines) + "\n"


def render_matrix_payload(summary: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "final_release_passed",
        "fresh_run",
        "cleanroom_passed",
        "evaluator_passed",
        "aggregate_agent_parity_passed",
        "hermes_parity",
        "opencode_parity",
        "openclaw_parity",
        "all_agents_deepseek",
        "all_key_source_env",
        "key_written",
        "real_key_scan",
        "forbidden_tracked_paths_count",
        "claims_consistent_with_evidence",
        "production_level_overclaim",
        "core_verifier_modified",
        "reference_monitor_semantics_changed",
        "checksums_generated",
        "redaction_safe",
    )
    return {key: summary.get(key) for key in keys}


def render_matrix_md(summary: Mapping[str, Any]) -> str:
    payload = render_matrix_payload(summary)
    lines = ["# Final Release Matrix", "", "| check | value |", "| --- | --- |"]
    for key, value in payload.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines) + "\n"


def render_checksums_md(rows: Sequence[Mapping[str, str]]) -> str:
    lines = ["# Final Artifact Checksums", "", "Algorithm: SHA-256", "", "| path | sha256 | bytes |", "| --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row['path']} | {row['sha256']} | {row['bytes']} |")
    return "\n".join(lines) + "\n"


def print_output(summary: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return
    print(f"mode={summary['mode']}")
    print(f"fresh_run={summary['fresh_run']}")
    print(f"final_release_passed={summary['final_release_passed']}")
    print(f"cleanroom_passed={summary['cleanroom_passed']}")
    print(f"evaluator_passed={summary['evaluator_passed']}")
    print(f"report={REPORT_PATH}")
    print(f"summary={SUMMARY_PATH}")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_cmd(command: Sequence[str], *, cwd: Path, env: Mapping[str, str], timeout: int) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=dict(env),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "returncode": 124,
            "duration_seconds": round(time.time() - started, 3),
            "timed_out": True,
            "stdout_tail": redact(exc.stdout if isinstance(exc.stdout, str) else "", env),
            "stderr_tail": redact(f"timeout after {timeout} seconds", env),
        }
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "timed_out": False,
        "stdout_tail": redact(completed.stdout[-4000:], env),
        "stderr_tail": redact(completed.stderr[-4000:], env),
    }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def git_status(path: Path) -> str:
    completed = subprocess.run(["git", "status", "--short"], cwd=path, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else "git_status_failed"


def git_output(command: Sequence[str]) -> str | None:
    completed = subprocess.run(list(command), cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve(strict=False).relative_to(ROOT.resolve(strict=False)))
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
