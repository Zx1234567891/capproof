#!/usr/bin/env python3
"""Stage 43RC clean-room release-candidate reproduction harness."""

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
CLEANROOM_ROOT = ROOT / "artifact_cleanroom"
DEFAULT_WORKDIR = CLEANROOM_ROOT / "worktrees" / "capproof-rc"
REPORT_DIR = ROOT / "artifact_reports"
SUMMARY_PATH = REPORT_DIR / "cleanroom_release_candidate_summary.json"
REPORT_PATH = REPORT_DIR / "cleanroom_release_candidate_report.md"
MATRIX_JSON_PATH = REPORT_DIR / "cleanroom_release_candidate_matrix.json"
MATRIX_MD_PATH = REPORT_DIR / "cleanroom_release_candidate_matrix.md"

REQUIRED_GATES = (
    "ALLOW_CAPROOF_CLEANROOM_RC",
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage 43RC clean-room release candidate reproduction.")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--fresh-run", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-real", action="store_true")
    parser.add_argument("--fail-if-gate-missing", action="store_true")
    parser.add_argument("--clean-before-run", action="store_true")
    parser.add_argument("--clean-after-run", action="store_true")
    parser.add_argument("--source-ref", default="HEAD")
    parser.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    args = parser.parse_args(argv)

    workdir = Path(args.workdir).resolve(strict=False)
    preflight = build_preflight(args, workdir, os.environ)

    if args.require_real and (preflight["missing_gates"] or not args.fresh_run):
        reason = "blocked_missing_real_env_gate" if preflight["missing_gates"] else "blocked_fresh_run_not_requested"
        summary = build_base_summary(args, workdir, preflight, cleanroom_mode="blocked", reason=reason)
        write_artifacts(summary)
        print_output(summary, args.json)
        return 2 if args.fail_if_gate_missing else 1

    if args.fresh_run:
        if preflight["missing_gates"]:
            summary = build_base_summary(
                args,
                workdir,
                preflight,
                cleanroom_mode="blocked_missing_real_env_gate",
                reason="blocked_missing_real_env_gate",
            )
            write_artifacts(summary)
            print_output(summary, args.json)
            return 1
        summary = run_fresh_cleanroom(args, workdir, preflight)
        write_artifacts(summary)
        print_output(summary, args.json)
        return 0 if summary["cleanroom_passed"] else 1

    if args.prepare:
        summary = prepare_only(args, workdir, preflight)
        write_artifacts(summary)
        print_output(summary, args.json)
        return 0

    if args.preflight or args.report or args.json:
        summary = build_base_summary(args, workdir, preflight, cleanroom_mode="preflight", reason="readiness_only_not_completion_evidence")
        write_artifacts(summary)
        print_output(summary, args.json)
        return 0

    parser.print_help()
    return 0


def build_preflight(args: argparse.Namespace, workdir: Path, env: Mapping[str, str]) -> dict[str, Any]:
    missing = [
        name
        for name in REQUIRED_GATES
        if not env.get(name) or (name != "DEEPSEEK_API_KEY" and env.get(name) != "1")
    ]
    return {
        "stage": "43RC",
        "real_environment_policy_active": True,
        "dry_run_preflight_counts_as_completion": False,
        "reuse_existing_reports_counts_as_completion": False,
        "required_gates": list(REQUIRED_GATES),
        "missing_gates": missing,
        "gate_ready": not missing,
        "deepseek_key_present": bool(env.get("DEEPSEEK_API_KEY")),
        "deepseek_key_printed": False,
        "source_ref": args.source_ref,
        "workdir": str(workdir),
        "artifact_cleanroom_ignored": gitignore_contains("artifact_cleanroom/"),
        "root_git_status_clean": git_status(ROOT) == "",
        "default_does_not_run_real_agents": True,
    }


def prepare_only(args: argparse.Namespace, workdir: Path, preflight: Mapping[str, Any]) -> dict[str, Any]:
    summary = build_base_summary(args, workdir, preflight, cleanroom_mode="prepare", reason="prepare_only_not_completion_evidence")
    if args.clean_before_run:
        remove_worktree(workdir)
    prepared = create_worktree(args.source_ref, workdir)
    summary["prepare"] = prepared
    summary["source_commit"] = prepared.get("source_commit")
    summary["cleanroom_git_status_before"] = "clean" if git_status(workdir) == "" else "dirty"
    return summary


def run_fresh_cleanroom(args: argparse.Namespace, workdir: Path, preflight: Mapping[str, Any]) -> dict[str, Any]:
    if args.clean_before_run:
        remove_worktree(workdir)
    prepared = create_worktree(args.source_ref, workdir)
    status_before = git_status(workdir)
    runtime = prepare_runtime(workdir, os.environ)
    evaluator = run_evaluator(workdir, os.environ)
    evaluator_summary = load_json(workdir / "artifact_reports" / "real_agent_parity_evaluator_summary.json")
    cleanroom_key_scan = secret_scan(workdir, os.environ)
    forbidden = forbidden_tracked_paths(workdir)
    matrix_rows = evaluator_summary.get("all_agents", [])
    clean_status_after_run = git_status(workdir)
    copied = copy_redaction_safe_outputs(workdir, evaluator_summary, cleanroom_key_scan)
    # Keep the linked worktree usable, but remove tracked dirt after evidence was copied.
    cleanup_result = cleanup_cleanroom_worktree(workdir)
    final_status = git_status(workdir)
    if args.clean_after_run:
        remove_worktree(workdir)
        final_status = "removed"

    summary = build_base_summary(args, workdir, preflight, cleanroom_mode="fresh-run", reason="ok")
    summary.update(
        {
            "source_commit": prepared.get("source_commit"),
            "cleanroom_git_status_before": "clean" if status_before == "" else status_before,
            "cleanroom_git_status_after": "clean" if final_status == "" else final_status,
            "runtime_bootstrap": runtime,
            "evaluator_command": evaluator,
            "evaluator_passed": bool(evaluator_summary.get("evaluator_passed")) and evaluator.get("returncode") == 0,
            "aggregate_agent_parity_passed": bool(evaluator_summary.get("aggregate_agent_parity_passed")),
            "hermes_parity": agent_passed(evaluator_summary, "hermes"),
            "opencode_parity": agent_passed(evaluator_summary, "opencode"),
            "openclaw_parity": agent_passed(evaluator_summary, "openclaw"),
            "all_agents_deepseek": all(bool(row.get("deepseek_real_call")) for row in matrix_rows),
            "all_key_source_env": all(row.get("deepseek_key_source") == "DEEPSEEK_API_KEY" for row in matrix_rows),
            "key_written": any(bool(row.get("deepseek_key_written")) for row in matrix_rows),
            "real_key_scan": cleanroom_key_scan["real_key_scan"],
            "tools_list_all_agents": all(bool(row.get("tools_list_observed")) for row in matrix_rows),
            "tools_call_all_agents": all(bool(row.get("tools_call_observed")) for row in matrix_rows),
            "allow_deny_ask_all_agents": all(
                bool(row.get("allow_read_write_command_observed"))
                and bool(row.get("deny_outside_path_raw_shell_attacker_observed"))
                and bool(row.get("ask_pending_request_created"))
                and bool(row.get("trusted_approval_executed"))
                and bool(row.get("rerun_allow_observed"))
                for row in matrix_rows
            ),
            "forbidden_tracked_paths": forbidden,
            "forbidden_tracked_paths_count": len(forbidden),
            "production_level_overclaim": bool(evaluator_summary.get("production_level_overclaim")),
            "raw_logs_copied": False,
            "redaction_safe": copied["redaction_safe"] and cleanroom_key_scan["real_key_scan"] == "REAL_KEY_NOT_FOUND",
            "copied_outputs": copied,
            "cleanroom_git_status_after_run_before_cleanup": "clean" if clean_status_after_run == "" else clean_status_after_run,
            "cleanup_result": cleanup_result,
        }
    )
    summary["cleanroom_passed"] = cleanroom_passed(summary)
    summary["status"] = "passed" if summary["cleanroom_passed"] else summary.get("reason", "failed_cleanroom_reproduction")
    if not summary["cleanroom_passed"]:
        summary["reason"] = first_failure(summary)
        summary["status"] = summary["reason"]
    return summary


def build_base_summary(
    args: argparse.Namespace,
    workdir: Path,
    preflight: Mapping[str, Any],
    *,
    cleanroom_mode: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "stage": "43RC",
        "cleanroom_passed": False,
        "cleanroom_mode": cleanroom_mode,
        "status": reason,
        "reason": reason,
        "source_ref": args.source_ref,
        "source_commit": None,
        "workdir": str(workdir),
        "cleanroom_git_status_before": "not_created",
        "cleanroom_git_status_after": "not_created",
        "evaluator_passed": False,
        "aggregate_agent_parity_passed": False,
        "hermes_parity": False,
        "opencode_parity": False,
        "openclaw_parity": False,
        "all_agents_deepseek": False,
        "all_key_source_env": False,
        "key_written": False,
        "real_key_scan": "not_run",
        "tools_list_all_agents": False,
        "tools_call_all_agents": False,
        "allow_deny_ask_all_agents": False,
        "forbidden_tracked_paths_count": 0,
        "production_level_overclaim": False,
        "raw_logs_copied": False,
        "redaction_safe": False,
        "preflight": dict(preflight),
        "runtime_bootstrap": {},
        "evaluator_command": {},
    }


def cleanroom_passed(summary: Mapping[str, Any]) -> bool:
    return bool(
        summary.get("cleanroom_mode") == "fresh-run"
        and summary.get("evaluator_passed")
        and summary.get("aggregate_agent_parity_passed")
        and summary.get("hermes_parity")
        and summary.get("opencode_parity")
        and summary.get("openclaw_parity")
        and summary.get("all_agents_deepseek")
        and summary.get("all_key_source_env")
        and not summary.get("key_written")
        and summary.get("real_key_scan") == "REAL_KEY_NOT_FOUND"
        and summary.get("tools_list_all_agents")
        and summary.get("tools_call_all_agents")
        and summary.get("allow_deny_ask_all_agents")
        and int(summary.get("forbidden_tracked_paths_count", 1)) == 0
        and not summary.get("production_level_overclaim")
        and not summary.get("raw_logs_copied")
        and summary.get("redaction_safe")
    )


def first_failure(summary: Mapping[str, Any]) -> str:
    checks = (
        ("evaluator_passed", "failed_evaluator"),
        ("aggregate_agent_parity_passed", "failed_aggregate_agent_parity"),
        ("hermes_parity", "failed_hermes_parity"),
        ("opencode_parity", "failed_opencode_parity"),
        ("openclaw_parity", "failed_openclaw_parity"),
        ("all_agents_deepseek", "failed_deepseek"),
        ("all_key_source_env", "failed_key_source"),
        ("tools_list_all_agents", "failed_tools_list"),
        ("tools_call_all_agents", "failed_tools_call"),
        ("allow_deny_ask_all_agents", "failed_allow_deny_ask"),
        ("redaction_safe", "failed_redaction"),
    )
    for key, reason in checks:
        if not summary.get(key):
            return reason
    if summary.get("key_written"):
        return "failed_key_written"
    if summary.get("real_key_scan") != "REAL_KEY_NOT_FOUND":
        return "failed_real_key_scan"
    if int(summary.get("forbidden_tracked_paths_count", 1)) != 0:
        return "failed_forbidden_tracked_paths"
    if summary.get("production_level_overclaim"):
        return "failed_production_level_overclaim"
    if summary.get("raw_logs_copied"):
        return "failed_raw_logs_copied"
    return "failed_unknown"


def create_worktree(source_ref: str, workdir: Path) -> dict[str, Any]:
    workdir.parent.mkdir(parents=True, exist_ok=True)
    if not workdir.exists():
        run_cmd(["git", "worktree", "add", "--detach", str(workdir), source_ref], cwd=ROOT, timeout=300)
    source_commit = git_output(["git", "-C", str(workdir), "rev-parse", "HEAD"])
    return {
        "workdir": str(workdir),
        "source_ref": source_ref,
        "source_commit": source_commit,
        "git_status": git_status(workdir),
    }


def remove_worktree(workdir: Path) -> None:
    if not is_under(workdir, CLEANROOM_ROOT):
        raise RuntimeError(f"refusing to remove non-cleanroom path: {workdir}")
    if workdir.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(workdir)], cwd=ROOT, text=True, capture_output=True)
        if workdir.exists():
            shutil.rmtree(workdir)


def prepare_runtime(workdir: Path, env: Mapping[str, str]) -> dict[str, Any]:
    hermes = prepare_hermes_runtime(workdir)
    command = [
        sys.executable,
        "tools/run_agent_runtime_bootstrap.py",
        "--bootstrap",
        "all",
        "--verify",
        "--report",
        "--install-prefix",
        str(workdir / "external" / ".agent-runtimes"),
        "--source-root",
        str(ROOT / "external"),
    ]
    run_env = dict(env)
    run_env["ALLOW_AGENT_RUNTIME_BOOTSTRAP"] = "1"
    run_env["ALLOW_AGENT_RUNTIME_NETWORK"] = "1"
    result = run_cmd(command, cwd=workdir, env=run_env, timeout=1200)
    summary = load_json(workdir / "agent_coverage_audit" / "agent_runtime_bootstrap_summary.json")
    return {"hermes": hermes, "command": result, "summary": summary}


def prepare_hermes_runtime(workdir: Path) -> dict[str, Any]:
    source = ROOT / "external" / "external" / "hermes-agent"
    target = workdir / "external" / "external" / "hermes-agent"
    venv_source = ROOT / ".venv-hermes"
    venv_target = workdir / ".venv-hermes"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink() and target.resolve(strict=False) == source.resolve(strict=False):
            source_result = {"source_present": source.exists(), "target": str(target), "prepared": True, "mode": "existing_symlink"}
        elif target.is_dir() and not target.is_symlink():
            source_result = {"source_present": source.exists(), "target": str(target), "prepared": True, "mode": "existing_directory"}
        else:
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
            source_result = {"source_present": source.exists(), "target": str(target), "prepared": False, "mode": "replaced_stale_target"}
    else:
        source_result = {"source_present": source.exists(), "target": str(target), "prepared": False, "mode": "missing_source"}
    if not source_result["prepared"] and source.exists():
        target.symlink_to(source, target_is_directory=True)
        source_result = {"source_present": True, "target": str(target), "prepared": True, "mode": "symlink_ignored_runtime_source"}

    if venv_target.exists() or venv_target.is_symlink():
        if not (venv_target.is_symlink() and venv_target.resolve(strict=False) == venv_source.resolve(strict=False)):
            if venv_target.is_dir() and not venv_target.is_symlink():
                shutil.rmtree(venv_target)
            else:
                venv_target.unlink()
    if not venv_target.exists() and not venv_target.is_symlink() and venv_source.exists():
        venv_target.symlink_to(venv_source, target_is_directory=True)
    venv_result = {
        "venv_source_present": venv_source.exists(),
        "venv_target": str(venv_target),
        "venv_prepared": (venv_target / "bin" / "hermes").exists(),
        "venv_mode": "symlink_ignored_runtime_venv" if venv_target.is_symlink() else "missing_venv",
    }
    return {**source_result, **venv_result}


def run_evaluator(workdir: Path, env: Mapping[str, str]) -> dict[str, Any]:
    command = [
        sys.executable,
        "tools/run_real_agent_parity_evaluator.py",
        "--all",
        "--fresh-run",
        "--require-real",
        "--fail-if-gate-missing",
        "--report",
    ]
    run_env = dict(env)
    run_env.setdefault("ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO", "1")
    run_env["HERMES_REPO"] = str(workdir / "external" / "external" / "hermes-agent")
    return run_cmd(command, cwd=workdir, env=run_env, timeout=COMMAND_TIMEOUT_SECONDS)


def copy_redaction_safe_outputs(workdir: Path, evaluator_summary: Mapping[str, Any], scan: Mapping[str, Any]) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if scan["real_key_scan"] != "REAL_KEY_NOT_FOUND":
        return {"redaction_safe": False, "copied": []}
    source_summary = workdir / "artifact_reports" / "real_agent_parity_evaluator_summary.json"
    source_report = workdir / "artifact_reports" / "real_agent_parity_evaluator_report.md"
    source_matrix_json = workdir / "artifact_reports" / "real_agent_parity_evaluator_matrix.json"
    source_matrix_md = workdir / "artifact_reports" / "real_agent_parity_evaluator_matrix.md"
    copied: list[str] = []
    for src, dst in (
        (source_report, REPORT_PATH),
        (source_matrix_json, MATRIX_JSON_PATH),
        (source_matrix_md, MATRIX_MD_PATH),
    ):
        if src.exists():
            shutil.copyfile(src, dst)
            copied.append(str(dst))
    # The root summary is rendered from Stage 43 fields, not copied raw.
    return {
        "redaction_safe": bool(evaluator_summary.get("evaluator_passed")) and scan["real_key_scan"] == "REAL_KEY_NOT_FOUND",
        "copied": copied,
    }


def cleanup_cleanroom_worktree(workdir: Path) -> dict[str, Any]:
    restore = run_cmd(["git", "restore", "."], cwd=workdir, timeout=120)
    clean = run_cmd(["git", "clean", "-fd"], cwd=workdir, timeout=120)
    return {"restore": restore["returncode"], "clean": clean["returncode"]}


def agent_passed(summary: Mapping[str, Any], agent: str) -> bool:
    for row in summary.get("all_agents", []):
        if isinstance(row, dict) and row.get("agent") == agent:
            return bool(row.get("parity_passed"))
    return False


def secret_scan(workdir: Path, env: Mapping[str, str]) -> dict[str, Any]:
    current_key = env.get("DEEPSEEK_API_KEY", "")
    paths = tracked_paths(workdir)
    for directory in (
        workdir / "artifact_reports",
        workdir / "real_agent_integrations" / "hermes_mcp_server" / "reports",
        workdir / "real_agent_integrations" / "hermes_mcp_server" / "traces",
        workdir / "real_agent_integrations" / "opencode_mcp_server" / "reports",
        workdir / "real_agent_integrations" / "opencode_mcp_server" / "traces",
        workdir / "real_agent_integrations" / "openclaw_mcp_server" / "reports",
        workdir / "real_agent_integrations" / "openclaw_mcp_server" / "traces",
    ):
        if directory.exists():
            paths.extend(path for path in directory.rglob("*") if path.is_file())
    hits: list[str] = []
    for path in sorted(set(paths)):
        if "external/.agent-runtimes" in str(path) or "node_modules" in str(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if current_key and current_key in text:
            hits.append(display_path(path, workdir))
            continue
        for match in SECRET_RE.finditer(text):
            if match.group(0) not in ALLOWED_DUMMY_SECRETS:
                hits.append(display_path(path, workdir))
                break
    return {
        "real_key_scan": "REAL_KEY_NOT_FOUND" if not hits else "REAL_KEY_FOUND",
        "hits": hits,
        "key_value_printed": False,
    }


def tracked_paths(workdir: Path) -> list[Path]:
    completed = subprocess.run(["git", "ls-files"], cwd=workdir, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return []
    return [workdir / line for line in completed.stdout.splitlines() if line.strip()]


def forbidden_tracked_paths(workdir: Path) -> list[str]:
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
        cwd=workdir,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ["git_ls_files_failed"]
    return [line for line in completed.stdout.splitlines() if line.strip()]


def write_artifacts(summary: Mapping[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(summary), encoding="utf-8")
    MATRIX_JSON_PATH.write_text(json.dumps(render_matrix_payload(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MATRIX_MD_PATH.write_text(render_matrix(summary), encoding="utf-8")


def render_matrix_payload(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": "43RC",
        "cleanroom_passed": summary.get("cleanroom_passed"),
        "cleanroom_mode": summary.get("cleanroom_mode"),
        "source_commit": summary.get("source_commit"),
        "evaluator_passed": summary.get("evaluator_passed"),
        "aggregate_agent_parity_passed": summary.get("aggregate_agent_parity_passed"),
        "agents": {
            "hermes": summary.get("hermes_parity"),
            "opencode": summary.get("opencode_parity"),
            "openclaw": summary.get("openclaw_parity"),
        },
        "all_agents_deepseek": summary.get("all_agents_deepseek"),
        "all_key_source_env": summary.get("all_key_source_env"),
        "tools_list_all_agents": summary.get("tools_list_all_agents"),
        "tools_call_all_agents": summary.get("tools_call_all_agents"),
        "allow_deny_ask_all_agents": summary.get("allow_deny_ask_all_agents"),
        "real_key_scan": summary.get("real_key_scan"),
        "forbidden_tracked_paths_count": summary.get("forbidden_tracked_paths_count"),
        "production_level_overclaim": summary.get("production_level_overclaim"),
    }


def render_report(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Clean-Room Release Candidate Report",
        "",
        "## Positioning",
        "",
        "- Stage 43RC validates the release candidate from a clean-room worktree.",
        "- Preflight is readiness only, not completion evidence.",
        "- Reuse-existing reports cannot pass clean-room reproduction.",
        "- This report does not claim production-level protection.",
        "",
        "## Summary",
        "",
        f"- cleanroom_mode: {summary['cleanroom_mode']}",
        f"- cleanroom_passed: {summary['cleanroom_passed']}",
        f"- source_commit: {summary.get('source_commit')}",
        f"- cleanroom_git_status_before: {summary.get('cleanroom_git_status_before')}",
        f"- cleanroom_git_status_after: {summary.get('cleanroom_git_status_after')}",
        f"- evaluator_passed: {summary['evaluator_passed']}",
        f"- aggregate_agent_parity_passed: {summary['aggregate_agent_parity_passed']}",
        f"- hermes_parity: {summary['hermes_parity']}",
        f"- opencode_parity: {summary['opencode_parity']}",
        f"- openclaw_parity: {summary['openclaw_parity']}",
        f"- all_agents_deepseek: {summary['all_agents_deepseek']}",
        f"- all_key_source_env: {summary['all_key_source_env']}",
        f"- key_written: {summary['key_written']}",
        f"- real_key_scan: {summary['real_key_scan']}",
        f"- tools_list_all_agents: {summary['tools_list_all_agents']}",
        f"- tools_call_all_agents: {summary['tools_call_all_agents']}",
        f"- allow_deny_ask_all_agents: {summary['allow_deny_ask_all_agents']}",
        f"- forbidden_tracked_paths_count: {summary['forbidden_tracked_paths_count']}",
        f"- production_level_overclaim: {summary['production_level_overclaim']}",
        f"- raw_logs_copied: {summary['raw_logs_copied']}",
        f"- redaction_safe: {summary['redaction_safe']}",
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
    ]
    return "\n".join(lines) + "\n"


def render_matrix(summary: Mapping[str, Any]) -> str:
    rows = render_matrix_payload(summary)
    lines = [
        "# Clean-Room Release Candidate Matrix",
        "",
        f"- cleanroom_passed: {rows['cleanroom_passed']}",
        f"- evaluator_passed: {rows['evaluator_passed']}",
        f"- aggregate_agent_parity_passed: {rows['aggregate_agent_parity_passed']}",
        "",
        "| check | value |",
        "| --- | --- |",
    ]
    for key, value in rows.items():
        if key != "agents":
            lines.append(f"| {key} | {value} |")
    for agent, value in rows["agents"].items():
        lines.append(f"| {agent}_parity | {value} |")
    return "\n".join(lines) + "\n"


def print_output(summary: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return
    print(f"cleanroom_mode={summary['cleanroom_mode']}")
    print(f"cleanroom_passed={summary['cleanroom_passed']}")
    print(f"evaluator_passed={summary['evaluator_passed']}")
    print(f"aggregate_agent_parity_passed={summary['aggregate_agent_parity_passed']}")
    print(f"report={REPORT_PATH}")
    print(f"summary={SUMMARY_PATH}")


def run_cmd(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    timeout: int,
) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=dict(env or os.environ),
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
            "stdout_tail": redact(exc.stdout if isinstance(exc.stdout, str) else "", env or os.environ),
            "stderr_tail": redact(f"timeout after {timeout} seconds", env or os.environ),
        }
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "timed_out": False,
        "stdout_tail": redact(completed.stdout[-4000:], env or os.environ),
        "stderr_tail": redact(completed.stderr[-4000:], env or os.environ),
    }


def git_status(path: Path) -> str:
    completed = subprocess.run(["git", "status", "--short"], cwd=path, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else "git_status_failed"


def git_output(command: Sequence[str]) -> str | None:
    completed = subprocess.run(list(command), cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def gitignore_contains(pattern: str) -> bool:
    try:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    except OSError:
        return False
    return pattern in text


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
    except ValueError:
        return False
    return True


def display_path(path: Path, base: Path) -> str:
    try:
        return str(path.resolve(strict=False).relative_to(base.resolve(strict=False)))
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
