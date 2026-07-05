#!/usr/bin/env python3
"""One-command foreground OpenClaw + DeepSeek + CapProof MCP entrypoint."""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from typing import Mapping, Sequence

from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer

import run_capproof_trace_viewer
import run_real_openclaw_deepseek_mcp_parity as parity


REQUIRED_GATES = {
    "ALLOW_AGENT_RUNTIME_REAL_SMOKE": "1",
    "ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE": "1",
    "ALLOW_CAPROOF_AGENT_PARITY": "1",
    "ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION": "1",
    "ALLOW_CAPROOF_ASK_APPROVAL_DEMO": "1",
    "ALLOW_CAPROOF_REAL_ENV_VALIDATION": "1",
}
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
WEB_HOST = "127.0.0.1"
WEB_PORT = "18789"
WEB_TOKEN = "capproof-test"


def runtime_dir_for_env() -> Path:
    run_id = os.environ.get("CAPPROOF_RECORDING_RUN_ID", "").strip()
    if not run_id:
        return parity.INTEGRATION_DIR / "runtime"
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in run_id)[:80]
    return parity.INTEGRATION_DIR / "runtime" / safe


def session_id_for_env() -> str:
    run_id = os.environ.get("CAPPROOF_AGENT_SESSION_ID", "").strip()
    if not run_id:
        return "main"
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in run_id)[:80]


RUNTIME_DIR = runtime_dir_for_env()
RUNTIME_HOME = RUNTIME_DIR / "home"
AUTH_QUEUE_DIR = RUNTIME_DIR / "auth_queue"
RUNTIME_CONFIG = RUNTIME_HOME / ".openclaw-capproof" / "openclaw.json"


def main(argv: Sequence[str] | None = None, *, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run OpenClaw with DeepSeek and the standard CapProof MCP server.")
    parser.add_argument("--preflight", action="store_true", help="check wrapper readiness without running OpenClaw")
    parser.add_argument("--doctor", action="store_true", help="run local readiness checks without calling DeepSeek")
    parser.add_argument("--where-trace", action="store_true", help="print trace, live log, workspace, config, and auth queue paths")
    parser.add_argument("--trace-follow", action="store_true", help="follow the OpenClaw CapProof trace")
    parser.add_argument("--capproof-status", action="store_true", help="print concise CapProof MCP status and latest verdict")
    parser.add_argument("--list-scenarios", action="store_true", help="list parity validation scenarios")
    parser.add_argument("--parity-demo", action="store_true", help="run the full real OpenClaw parity harness")
    parser.add_argument("--web", action="store_true", help="run the local OpenClaw browser UI gateway in the foreground")
    parser.add_argument("--web-url", action="store_true", help="print the local OpenClaw browser UI URL")
    parser.add_argument("--json", action="store_true", help="print JSON for status-style commands")
    args, passthrough = parser.parse_known_args(list(argv) if argv is not None else None)

    run_env = build_env(os.environ if env is None else env)
    if args.web_url:
        print_web_url(json_output=args.json)
        return 0
    if args.where_trace:
        print_where_trace(json_output=args.json)
        return 0
    if args.trace_follow:
        return run_capproof_trace_viewer.main(["--file", str(parity.TRACE_PATH), "--follow"])
    if args.capproof_status:
        print_capproof_status(json_output=args.json)
        return 0
    if args.doctor:
        print_doctor(run_env, json_output=args.json)
        return 0
    if args.list_scenarios:
        return parity.main(["--list-scenarios"])
    if args.parity_demo:
        return run_parity_demo(run_env, json_output=args.json)
    if args.preflight:
        print_preflight(run_env, json_output=args.json)
        return 0
    if args.web or is_dashboard_passthrough(passthrough):
        if not run_env.get("DEEPSEEK_API_KEY"):
            print("DEEPSEEK_API_KEY is missing. Set it in the shell; do not write it to a file.")
            return 2
        return run_web_gateway(run_env)
    if not run_env.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is missing. Set it in the shell; do not write it to a file.")
        return 2
    return run_foreground(run_env, passthrough=passthrough)


def build_env(base_env: Mapping[str, str]) -> dict[str, str]:
    run_env = dict(base_env)
    run_env.update(REQUIRED_GATES)
    run_env.setdefault("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    run_env.setdefault("DEEPSEEK_MODEL", DEFAULT_MODEL)
    return run_env


def run_foreground(env: Mapping[str, str], *, passthrough: Sequence[str]) -> int:
    with patched_environ(env):
        runtime_env = prepare_runtime()
        command = build_openclaw_command(passthrough)
        print_startup_banner(file=sys.stderr)
        try:
            completed = subprocess.run(command, cwd=str(parity.WORKSPACE_DIR), env=runtime_env, shell=False, check=False)
        except KeyboardInterrupt:
            print("\nOpenClaw foreground session interrupted.")
            return 130
        return int(completed.returncode)


def run_web_gateway(env: Mapping[str, str]) -> int:
    with patched_environ(env):
        runtime_env = prepare_runtime()
        command = [
            str(parity.smoke.OPENCLAW_BINARY),
            "--profile",
            "capproof",
            "gateway",
            "run",
            "--force",
            "--bind",
            "loopback",
            "--port",
            WEB_PORT,
            "--auth",
            "token",
            "--token",
            WEB_TOKEN,
        ]
        print_web_banner(file=sys.stderr)
        try:
            completed = subprocess.run(command, cwd=str(parity.WORKSPACE_DIR), env=runtime_env, shell=False, check=False)
        except KeyboardInterrupt:
            print("\nOpenClaw browser UI gateway stopped.", file=sys.stderr)
            return 130
        return int(completed.returncode)


def run_parity_demo(env: Mapping[str, str], *, json_output: bool) -> int:
    argv = ["--all", "--require-real", "--report"]
    if json_output:
        argv.append("--json")
    with patched_environ(env):
        if json_output:
            return parity.main(argv)
        print("Starting real OpenClaw parity demo. This runs multiple real agent turns; Ctrl-C stops it.", file=sys.stderr)
        print(f"Trace: {parity.TRACE_PATH}", file=sys.stderr)
        print(f"Live log: {parity.LIVE_LOG_PATH}", file=sys.stderr)
        with foreground_trace_monitor(parity.TRACE_PATH, label="openclaw"):
            return parity.main(argv)


def prepare_runtime() -> dict[str, str]:
    prepare_runtime_config()
    runtime_env = parity.smoke.make_openclaw_env(str(RUNTIME_HOME))
    runtime_env["CAPPROOF_AUTH_QUEUE_DIR"] = str(AUTH_QUEUE_DIR)
    runtime_env["CAPPROOF_ASK_TRACE_PATH"] = str(parity.TRACE_PATH)
    add_result = subprocess.run(
        parity.smoke.mcp_add_command(parity.WORKSPACE_DIR, parity.TRACE_PATH),
        cwd=str(parity.ROOT),
        env=runtime_env,
        text=True,
        capture_output=True,
        shell=False,
        check=False,
        timeout=60,
    )
    if add_result.returncode != 0 and not mcp_already_registered(add_result):
        print("OpenClaw CapProof MCP registration failed.", file=sys.stderr)
        print((add_result.stderr or add_result.stdout).strip(), file=sys.stderr)
        raise SystemExit(int(add_result.returncode or 1))
    return runtime_env


def prepare_runtime_config() -> None:
    parity.configure_smoke_paths()
    parity.ensure_dirs()
    parity.prepare_examples()
    parity.smoke.prepare_workspace(parity.WORKSPACE_DIR)
    for directory in (RUNTIME_DIR, RUNTIME_HOME, AUTH_QUEUE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    parity.smoke.write_openclaw_config(RUNTIME_CONFIG, parity.WORKSPACE_DIR)
    parity.smoke.write_openclaw_config(parity.CONFIG_PATH, parity.WORKSPACE_DIR)


def build_openclaw_command(passthrough: Sequence[str]) -> list[str]:
    if passthrough:
        if "--profile" in passthrough:
            return [str(parity.smoke.OPENCLAW_BINARY), *passthrough]
        return [str(parity.smoke.OPENCLAW_BINARY), "--profile", "capproof", *passthrough]
    return [str(parity.smoke.OPENCLAW_BINARY), "--profile", "capproof", "tui", "--local", "--session", session_id_for_env()]


def is_dashboard_passthrough(passthrough: Sequence[str]) -> bool:
    return bool(passthrough) and passthrough[0] == "dashboard"


def mcp_already_registered(result: subprocess.CompletedProcess[str]) -> bool:
    text = f"{result.stdout or ''}\n{result.stderr or ''}".lower()
    return "already" in text or "exist" in text


def print_startup_banner(*, file) -> None:
    payload = wrapper_status_payload()
    lines = [
        "OpenClaw CapProof foreground",
        "CapProof MCP attached: yes",
        "agent: OpenClaw",
        f"agent binary: {payload['agent_binary']}",
        f"model provider: {payload['model_provider']}",
        f"model: {payload['model_name']}",
        "MCP mode: stdio",
        "sandboxed-real-execution: enabled",
        f"exposed tools: {payload['tools_count']}",
        f"trace file: {payload['trace_path']}",
        f"live log: {payload['live_log_path']}",
        f"auth queue: {payload['auth_queue_dir']}",
        "safety boundary: DeepSeek not safety TCB; CapProof guard gates tools",
    ]
    print("\n".join(lines), file=file)


def print_web_banner(*, file) -> None:
    payload = wrapper_status_payload()
    lines = [
        "OpenClaw CapProof browser UI",
        "CapProof MCP attached: yes",
        f"URL: http://{WEB_HOST}:{WEB_PORT}/",
        f"auth token: {WEB_TOKEN}",
        f"model: {payload['model_name']}",
        "MCP mode: stdio",
        "sandboxed-real-execution: enabled",
        f"exposed tools: {payload['tools_count']}",
        "mode: foreground loopback gateway; no systemd install",
        "Stop with Ctrl-C.",
    ]
    print("\n".join(lines), file=file)


def print_web_url(*, json_output: bool) -> None:
    payload = {
        "url": f"http://{WEB_HOST}:{WEB_PORT}/",
        "auth_token": WEB_TOKEN,
        "start_command": "openclaw --web",
        "system_service_install": False,
    }
    print_payload(payload, json_output=json_output)


def print_where_trace(*, json_output: bool) -> None:
    payload = {
        "trace_jsonl_path": str(parity.TRACE_PATH),
        "live_log_path": str(parity.LIVE_LOG_PATH),
        "sandbox_workspace_path": str(parity.WORKSPACE_DIR),
        "config_path": str(RUNTIME_CONFIG),
        "summary_path": str(parity.SUMMARY_PATH),
        "report_path": str(parity.REPORT_PATH),
        "auth_queue_dir": str(AUTH_QUEUE_DIR),
    }
    print_payload(payload, json_output=json_output)


def print_capproof_status(*, json_output: bool) -> None:
    entries, skipped = run_capproof_trace_viewer.read_trace(parity.TRACE_PATH)
    latest = entries[-1] if entries else {}
    payload = wrapper_status_payload()
    payload.update(
        {
            "latest_verdict": run_capproof_trace_viewer.entry_verdict(latest) if latest else "",
            "latest_tool_name": latest.get("tool_name", "") if latest else "",
            "latest_reason": latest.get("reason", "") if latest else "",
            "latest_executor_called": bool(latest.get("executor_called")) if latest else False,
            "skipped_malformed_count": skipped,
        }
    )
    print_payload(payload, json_output=json_output)


def print_doctor(env: Mapping[str, str], *, json_output: bool) -> None:
    payload = wrapper_status_payload()
    payload.update(
        {
            "deepseek_api_key_present": bool(env.get("DEEPSEEK_API_KEY")),
            "deepseek_key_value": "redacted" if env.get("DEEPSEEK_API_KEY") else "",
            "runtime_present": parity.smoke.OPENCLAW_BINARY.exists(),
            "version": probe_version(),
            "config_exists": RUNTIME_CONFIG.exists() or parity.CONFIG_PATH.exists(),
            "trace_dir_writable": ensure_writable(parity.TRACE_DIR),
            "live_log_dir_writable": ensure_writable(parity.REPORT_DIR),
            "sandbox_workspace_exists": parity.WORKSPACE_DIR.exists(),
            "key_written": False,
        }
    )
    print_payload(payload, json_output=json_output)


def print_preflight(env: Mapping[str, str], *, json_output: bool) -> None:
    payload = {
        "agent": "openclaw",
        "deepseek_api_key_present": bool(env.get("DEEPSEEK_API_KEY")),
        "deepseek_key_source": "DEEPSEEK_API_KEY",
        "key_written": False,
        "runtime_present": parity.smoke.OPENCLAW_BINARY.exists(),
        "version": probe_version(),
        "standard_capproof_mcp_server": "tools/run_capproof_mcp_server.py --stdio --sandboxed-real-execution",
        "dry_run_preflight_counts_as_completion": False,
    }
    print_payload(payload, json_output=json_output)


def wrapper_status_payload() -> dict[str, object]:
    return {
        "capproof_mcp_attached": True,
        "agent": "openclaw",
        "agent_binary": str(parity.smoke.OPENCLAW_BINARY),
        "model_provider": "deepseek",
        "model_name": os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
        "mcp_mode": "stdio",
        "sandboxed_real_execution": True,
        "tools_count": len(tool_names()),
        "trace_path": str(parity.TRACE_PATH),
        "live_log_path": str(parity.LIVE_LOG_PATH),
        "workspace": str(parity.WORKSPACE_DIR),
        "auth_queue_dir": str(AUTH_QUEUE_DIR),
        "deepseek_not_safety_tcb": True,
        "capproof_guard_gates_tools": True,
    }


def tool_names() -> list[str]:
    context = make_default_context(workspace=parity.WORKSPACE_DIR, trace_path=parity.TRACE_PATH, executor_mode="sandbox")
    server = CapProofMCPServer(context=context)
    return [str(tool.get("name", "")) for tool in server.list_tools()["tools"]]


def probe_version() -> str:
    if not parity.smoke.OPENCLAW_BINARY.exists():
        return ""
    completed = subprocess.run([str(parity.smoke.OPENCLAW_BINARY), "--version"], text=True, capture_output=True, timeout=20, check=False)
    return (completed.stdout or completed.stderr).strip().splitlines()[0] if (completed.stdout or completed.stderr).strip() else ""


def ensure_writable(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".capproof_write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def print_payload(payload: Mapping[str, object], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}={value}")


@contextmanager
def foreground_trace_monitor(trace_path: Path, *, label: str):
    stop = threading.Event()
    thread = threading.Thread(target=_tail_trace, args=(trace_path, stop, label), daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1.0)


def _tail_trace(trace_path: Path, stop: threading.Event, label: str) -> None:
    offset = trace_path.stat().st_size if trace_path.exists() else 0
    while not stop.is_set():
        if trace_path.exists():
            with trace_path.open("r", encoding="utf-8") as handle:
                handle.seek(offset)
                while True:
                    line = handle.readline()
                    if not line:
                        break
                    offset = handle.tell()
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    tool = entry.get("tool_name") or entry.get("tool") or ""
                    verdict = run_capproof_trace_viewer.entry_verdict(entry)
                    reason = entry.get("reason") or entry.get("deny_reason") or ""
                    executor_called = bool(entry.get("executor_called"))
                    proof_id = entry.get("proof_id") or entry.get("proof_attempt_id") or ""
                    print(
                        f"[{label} trace] tool={tool} verdict={verdict} reason={reason} "
                        f"executor_called={executor_called} proof_id={proof_id}",
                        file=sys.stderr,
                        flush=True,
                    )
        stop.wait(0.5)


@contextmanager
def patched_environ(env: Mapping[str, str]):
    old = os.environ.copy()
    os.environ.clear()
    os.environ.update(env)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)


if __name__ == "__main__":
    raise SystemExit(main())
