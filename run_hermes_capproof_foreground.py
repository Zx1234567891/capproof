#!/usr/bin/env python3
"""One-command foreground Hermes + CapProof MCP entrypoint.

This is a thin convenience wrapper over ``run_real_hermes_foreground_mcp_demo``.
It sets the fixed Stage 34H safety gates in the child environment, reads the
DeepSeek key only from ``DEEPSEEK_API_KEY``, and never writes or prints the key.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from typing import Mapping, Sequence

from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer

import run_capproof_mcp_doctor
import run_capproof_trace_viewer
import run_real_hermes_foreground_mcp_demo as foreground


REQUIRED_GATES = {
    "ALLOW_HERMES_DEEPSEEK_RUN": "1",
    "ALLOW_CAPROOF_MCP_REAL_HERMES": "1",
    "ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION": "1",
    "ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO": "1",
}


def main(argv: Sequence[str] | None = None, *, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run foreground Hermes with the standard CapProof MCP server.")
    parser.add_argument("--preflight", action="store_true", help="check the one-command environment without running Hermes")
    parser.add_argument("--dry-run", action="store_true", help="exercise the local CapProof MCP workflow without Hermes/DeepSeek")
    parser.add_argument("--workflow-demo", action="store_true", help="run the report-oriented multi-task foreground validation harness")
    parser.add_argument("--list-tasks", action="store_true", help="list foreground validation tasks")
    parser.add_argument("--doctor", action="store_true", help="run local CapProof MCP readiness checks without Hermes/DeepSeek")
    parser.add_argument("--where-trace", action="store_true", help="print foreground trace, live log, workspace, and UX summary paths")
    parser.add_argument("--trace-follow", action="store_true", help="follow the foreground CapProof MCP trace")
    parser.add_argument("--capproof-status", action="store_true", help="print concise CapProof MCP status and latest verdict")
    parser.add_argument("--json", action="store_true", help="print full JSON summary")
    interface = parser.add_mutually_exclusive_group()
    interface.add_argument("--classic", action="store_true", help="use Hermes classic CLI")
    interface.add_argument("--tui", action="store_true", help="use Hermes TUI; this is the default")
    args = parser.parse_args(list(argv) if argv is not None else None)

    run_env = build_env(os.environ if env is None else env)
    if args.list_tasks:
        print(json.dumps({"tasks": [task["task_id"] for task in foreground.TASKS]}, indent=2, sort_keys=True))
        return 0
    if args.where_trace:
        print_where_trace(json_output=args.json)
        return 0
    if args.doctor:
        return run_capproof_mcp_doctor.main(["--all", "--json"] if args.json else ["--all"])
    if args.trace_follow:
        return run_capproof_trace_viewer.main(["--latest", "--follow"])
    if args.capproof_status:
        print_capproof_status(json_output=args.json)
        return 0
    if args.dry_run:
        return _run_dry(run_env, json_output=args.json)
    if not run_env.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is missing. Set it in the shell; do not write it to a file.")
        return 2
    if args.preflight:
        preflight = foreground.run_preflight(run_env)
        foreground.write_reports(
            foreground.build_summary(
                preflight=preflight,
                dry_run=True,
                foreground=False,
                hermes_run=foreground.default_run_result(preflight),
                run_local=True,
            )
        )
        return _print_preflight(preflight, json_output=args.json)
    if args.workflow_demo:
        return _run_workflow_demo(run_env, json_output=args.json)
    return _run_interactive(run_env, classic=args.classic)


def build_env(base_env: Mapping[str, str]) -> dict[str, str]:
    run_env = dict(base_env)
    run_env.update(REQUIRED_GATES)
    run_env.setdefault("DEEPSEEK_BASE_URL", foreground.DEFAULT_BASE_URL)
    run_env.setdefault("DEEPSEEK_MODEL", foreground.DEFAULT_MODEL)
    return run_env


def _run_dry(env: Mapping[str, str], *, json_output: bool) -> int:
    preflight = foreground.run_preflight(env)
    summary = foreground.build_summary(
        preflight=preflight,
        dry_run=True,
        foreground=False,
        hermes_run=foreground.default_run_result(preflight),
        run_local=True,
    )
    foreground.write_reports(summary)
    passed = foreground.dry_run_passed(summary)
    _print_summary(summary, passed=passed, json_output=json_output, mode="dry-run")
    return 0 if passed else 1


def _run_workflow_demo(env: Mapping[str, str], *, json_output: bool) -> int:
    with patched_environ(env):
        preflight = foreground.run_preflight(env)
        if not preflight.run_allowed:
            summary = foreground.build_summary(
                preflight=preflight,
                dry_run=False,
                foreground=True,
                hermes_run=foreground.default_run_result(preflight),
                run_local=False,
            )
            foreground.write_reports(summary)
            _print_summary(summary, passed=False, json_output=json_output, mode="foreground")
            return 1
        run = foreground.run_hermes_foreground(env, preflight.command_validation)
        summary = foreground.build_summary(preflight=preflight, dry_run=False, foreground=True, hermes_run=run, run_local=False)
        foreground.write_reports(summary)
    passed = foreground.real_foreground_passed(summary)
    _print_summary(summary, passed=passed, json_output=json_output, mode="foreground")
    return 0 if passed else 1


def _run_interactive(env: Mapping[str, str], *, classic: bool) -> int:
    with patched_environ(env):
        preflight = foreground.run_preflight(env)
        if not preflight.run_allowed:
            print("Hermes foreground launch denied by safety preflight.")
            print(f"missing_env={','.join(preflight.command_validation.missing_env) or 'none'}")
            print(f"denial_reasons={','.join(preflight.denial_reasons) or 'none'}")
            return 1
        foreground.prepare_workspace(foreground.SANDBOX_WORKSPACE)
        hermes_home = Path(tempfile.mkdtemp(prefix="hermes_interactive_capproof_home_"))
        workspace = foreground.SANDBOX_WORKSPACE.resolve(strict=False)
        foreground.write_hermes_runtime_config(hermes_home=hermes_home, workspace=workspace, env=env)
        run_env = dict(os.environ)
        run_env.update(
            {
                "DEEPSEEK_BASE_URL": env.get("DEEPSEEK_BASE_URL", foreground.DEFAULT_BASE_URL),
                "DEEPSEEK_MODEL": env.get("DEEPSEEK_MODEL", foreground.DEFAULT_MODEL),
                "HERMES_HOME": str(hermes_home),
                "HOME": str(hermes_home / "home"),
                "CAPPROOF_NO_REAL_TOOLS": "1",
                "NO_NETWORK_EXCEPT_DEEPSEEK": "1",
                "CAPPROOF_MCP_TRACE_PATH": str(foreground.TRACE_PATH),
                "CAPPROOF_MCP_LIVE_LOG": str(foreground.LIVE_LOG_PATH),
                "CAPPROOF_MCP_WORKSPACE": str(foreground.SANDBOX_WORKSPACE),
                "CAPPROOF_SANDBOX_REAL_EXECUTION": "1",
                "HERMES_YOLO_MODE": "1",
                "HERMES_ACCEPT_HOOKS": "1",
            }
        )
        (hermes_home / "home").mkdir(parents=True, exist_ok=True)
        command = resolve_interactive_command(env, classic=classic)
        command_text = " ".join(shlex.quote(part) for part in command)
        denied = foreground.denied_command_patterns(command_text)
        if denied or foreground.SECRET_LITERAL_RE.search(command_text) or foreground.EXTERNAL_URL_RE.search(command_text):
            print("Hermes foreground launch denied by interactive command safety check.")
            print(f"denied_patterns={','.join(denied) or 'none'}")
            return 1
        print_startup_banner(file=sys.stderr)
        try:
            completed = subprocess.run(
                command,
                cwd=str(workspace),
                env=run_env,
                check=False,
                shell=False,
            )
        except KeyboardInterrupt:
            print("\nHermes foreground session interrupted.")
            return 130
        return int(completed.returncode)


def resolve_interactive_command(env: Mapping[str, str], *, classic: bool) -> list[str]:
    configured = env.get("HERMES_INTERACTIVE_COMMAND", "").strip()
    if configured:
        return shlex.split(configured)
    hermes = foreground.ROOT / ".venv-hermes" / "bin" / "hermes"
    if not hermes.exists():
        fallback, _source = foreground.resolve_hermes_command(env)
        if fallback:
            parts = [part for part in shlex.split(fallback) if part not in {"-z", "--oneshot", foreground.PROMPT_TOKEN}]
            return parts
        return ["hermes"]
    interface_flag = "--cli" if classic else "--tui"
    return [
        str(hermes),
        "--provider",
        "deepseek",
        "-m",
        env.get("DEEPSEEK_MODEL", foreground.DEFAULT_MODEL),
        "-t",
        foreground.MCP_SERVER_NAME,
        "--ignore-rules",
        interface_flag,
    ]


def print_startup_banner(*, file) -> None:
    tools = tool_names()
    lines = [
        "CapProof MCP attached: yes",
        "MCP mode: stdio",
        "sandboxed-real-execution: enabled",
        f"exposed tools: {len(tools)}",
        f"trace file: {foreground.TRACE_PATH}",
        f"live log: {foreground.LIVE_LOG_PATH}",
        "safety boundary: DeepSeek not safety TCB; CapProof guard gates tools",
        "Exit Hermes normally when finished.",
    ]
    print("\n".join(lines), file=file)


def print_where_trace(*, json_output: bool) -> None:
    payload = {
        "foreground_trace_jsonl_path": str(foreground.TRACE_PATH),
        "foreground_live_log_path": str(foreground.LIVE_LOG_PATH),
        "sandbox_workspace_path": str(foreground.SANDBOX_WORKSPACE),
        "latest_summary_path": str(run_capproof_mcp_doctor.UX_SUMMARY),
        "foreground_demo_summary_path": str(foreground.SUMMARY_PATH),
    }
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}={value}")


def print_capproof_status(*, json_output: bool) -> None:
    doctor = run_capproof_mcp_doctor.run_checks()
    entries, skipped = run_capproof_trace_viewer.read_trace(foreground.TRACE_PATH)
    latest = entries[-1] if entries else {}
    payload = {
        "capproof_mcp_attached": True,
        "mcp_mode": "stdio",
        "sandboxed_real_execution": True,
        "tools_count": doctor["checks"]["tools_count"],
        "trace_path": str(foreground.TRACE_PATH),
        "live_log_path": str(foreground.LIVE_LOG_PATH),
        "latest_verdict": run_capproof_trace_viewer.entry_verdict(latest) if latest else "",
        "latest_tool_name": latest.get("tool_name", "") if latest else "",
        "latest_reason": latest.get("reason", "") if latest else "",
        "latest_executor_called": bool(latest.get("executor_called")) if latest else False,
        "skipped_malformed_count": skipped,
        "deepseek_not_safety_tcb": True,
        "capproof_guard_gates_tools": True,
    }
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}={value}")


def tool_names() -> list[str]:
    context = make_default_context(workspace=foreground.SANDBOX_WORKSPACE, trace_path=foreground.TRACE_PATH, executor_mode="sandbox")
    server = CapProofMCPServer(context=context)
    return [str(tool.get("name", "")) for tool in server.list_tools()["tools"]]


def _print_preflight(preflight: foreground.PreflightResult, *, json_output: bool) -> int:
    if json_output:
        print(json.dumps(foreground._json(preflight), indent=2, sort_keys=True))
    else:
        print(f"preflight_run_allowed={preflight.run_allowed}")
        print(f"hermes_repo_exists={preflight.hermes_repo_exists}")
        print(f"command_source={preflight.command_validation.command_source}")
        print(f"missing_env={','.join(preflight.command_validation.missing_env) or 'none'}")
        print(f"report={foreground.REPORT_PATH}")
    return 0 if preflight.command_validation.command_present else 1


def _print_summary(summary: foreground.ForegroundSummary, *, passed: bool, json_output: bool, mode: str) -> None:
    if json_output:
        print(json.dumps(foreground._json(summary), indent=2, sort_keys=True))
        return
    print(f"mode={mode}")
    print(f"passed={passed}")
    print(f"hermes_started={summary.hermes_started}")
    print(f"deepseek_called={summary.deepseek_called}")
    print(f"tools_list_observed={summary.tools_list_observed}")
    print(f"tools_call_observed={summary.tools_call_observed}")
    print(f"executor_called_on_deny_ask={summary.executor_called_on_deny_ask}")
    print(f"key_leak_detected={summary.key_leak_detected}")
    print(f"report={foreground.REPORT_PATH}")
    print(f"live_log={foreground.LIVE_LOG_PATH}")
    print(f"trace={foreground.TRACE_PATH}")


class patched_environ:
    def __init__(self, env: Mapping[str, str]) -> None:
        self._env = dict(env)
        self._original: dict[str, str] | None = None

    def __enter__(self) -> None:
        self._original = dict(os.environ)
        os.environ.clear()
        os.environ.update(self._env)

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self._original is not None
        os.environ.clear()
        os.environ.update(self._original)


if __name__ == "__main__":
    raise SystemExit(main())
