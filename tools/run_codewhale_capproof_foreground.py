#!/usr/bin/env python3
"""One-command foreground CodeWhale + DeepSeek + CapProof MCP entrypoint."""

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
from typing import Mapping, Sequence

from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer

import run_capproof_trace_viewer


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "real_agent_integrations" / "codewhale_mcp_server"
CONFIG_DIR = INTEGRATION_DIR / "configs"
REPORT_DIR = INTEGRATION_DIR / "reports"
TRACE_DIR = INTEGRATION_DIR / "traces"
WORKSPACE_DIR = INTEGRATION_DIR / "sandbox_workspace"
RUNTIME_DIR = INTEGRATION_DIR / "runtime"
RUNTIME_HOME = RUNTIME_DIR / "home"
AUTH_QUEUE_DIR = RUNTIME_DIR / "auth_queue"
CONFIG_PATH = CONFIG_DIR / "codewhale.capproof.deepseek.real.toml"
MCP_CONFIG_PATH = CONFIG_DIR / "codewhale.capproof.mcp.json"
TRACE_PATH = TRACE_DIR / "real_codewhale_deepseek_parity_trace.jsonl"
LIVE_LOG_PATH = REPORT_DIR / "real_codewhale_deepseek_parity_live.log"
SUMMARY_PATH = REPORT_DIR / "real_codewhale_deepseek_parity_summary.json"
REPORT_PATH = REPORT_DIR / "real_codewhale_deepseek_parity_report.md"
CODEWHALE_BINARY = ROOT / "external" / ".agent-runtimes" / "bin" / "codewhale"
CODEWHALE_TUI_BINARY = ROOT / "external" / ".agent-runtimes" / "bin" / "codewhale-tui"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"


REQUIRED_GATES = {
    "ALLOW_AGENT_RUNTIME_REAL_SMOKE": "1",
    "ALLOW_CAPROOF_REAL_CODEWHALE_SMOKE": "1",
    "ALLOW_CAPROOF_AGENT_PARITY": "1",
    "ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION": "1",
    "ALLOW_CAPROOF_ASK_APPROVAL_DEMO": "1",
    "ALLOW_CAPROOF_REAL_ENV_VALIDATION": "1",
}


def main(argv: Sequence[str] | None = None, *, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CodeWhale with DeepSeek and the standard CapProof MCP server.")
    parser.add_argument("--preflight", action="store_true", help="check wrapper readiness without running CodeWhale")
    parser.add_argument("--doctor", action="store_true", help="run local readiness checks without calling DeepSeek")
    parser.add_argument("--where-trace", action="store_true", help="print trace, live log, workspace, config, and auth queue paths")
    parser.add_argument("--trace-follow", action="store_true", help="follow the CodeWhale CapProof trace")
    parser.add_argument("--capproof-status", action="store_true", help="print concise CapProof MCP status and latest verdict")
    parser.add_argument("--mcp-tools", action="store_true", help="ask CodeWhale to list CapProof MCP tools")
    parser.add_argument("--json", action="store_true", help="print JSON for status-style commands")
    args, passthrough = parser.parse_known_args(list(argv) if argv is not None else None)

    run_env = build_env(os.environ if env is None else env)
    if args.where_trace:
        print_where_trace(json_output=args.json)
        return 0
    if args.trace_follow:
        return run_capproof_trace_viewer.main(["--file", str(TRACE_PATH), "--follow"])
    if args.capproof_status:
        print_capproof_status(json_output=args.json)
        return 0
    if args.doctor:
        print_doctor(run_env, json_output=args.json)
        return 0
    if args.preflight:
        print_preflight(run_env, json_output=args.json)
        return 0
    if args.mcp_tools:
        return run_mcp_tools(run_env)
    if not run_env.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is missing. Set it in the shell; do not write it to a file.")
        return 2
    return run_foreground(run_env, passthrough=passthrough)


def build_env(base_env: Mapping[str, str]) -> dict[str, str]:
    run_env = dict(base_env)
    run_env.update(REQUIRED_GATES)
    run_env.setdefault("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    run_env.setdefault("DEEPSEEK_MODEL", DEFAULT_MODEL)
    run_env.setdefault("CODEWHALE_PROVIDER", "deepseek")
    run_env.setdefault("CODEWHALE_BASE_URL", run_env.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    run_env.setdefault("CODEWHALE_MODEL", run_env.get("DEEPSEEK_MODEL", DEFAULT_MODEL))
    return run_env


def run_foreground(env: Mapping[str, str], *, passthrough: Sequence[str]) -> int:
    with patched_environ(env):
        runtime_env = prepare_runtime(env)
        command = build_codewhale_command(env, passthrough)
        print_startup_banner(file=sys.stderr)
        try:
            completed = subprocess.run(command, cwd=str(WORKSPACE_DIR), env=runtime_env, shell=False, check=False)
        except KeyboardInterrupt:
            print("\nCodeWhale foreground session interrupted.", file=sys.stderr)
            return 130
        return int(completed.returncode)


def run_mcp_tools(env: Mapping[str, str]) -> int:
    with patched_environ(env):
        runtime_env = prepare_runtime(env)
        command = [
            str(CODEWHALE_TUI_BINARY),
            "--config",
            str(CONFIG_PATH),
            "--workspace",
            str(WORKSPACE_DIR),
            "--skip-onboarding",
            "mcp",
            "tools",
            "capproof",
        ]
        completed = subprocess.run(command, cwd=str(WORKSPACE_DIR), env=runtime_env, shell=False, check=False)
        return int(completed.returncode)


def prepare_runtime(env: Mapping[str, str]) -> dict[str, str]:
    ensure_dirs()
    prepare_workspace()
    write_codewhale_config(env)
    write_mcp_config()
    runtime_env = dict(env)
    runtime_env.update(
        {
            "CODEWHALE_HOME": str(RUNTIME_HOME),
            "CODEWHALE_CONFIG_PATH": str(CONFIG_PATH),
            "DEEPSEEK_CONFIG_PATH": str(CONFIG_PATH),
            "DEEPSEEK_MCP_CONFIG": str(MCP_CONFIG_PATH),
            "CAPPROOF_AUTH_QUEUE_DIR": str(AUTH_QUEUE_DIR),
            "CAPPROOF_ASK_TRACE_PATH": str(TRACE_PATH),
            "CAPPROOF_MCP_TRACE_PATH": str(TRACE_PATH),
            "CAPPROOF_MCP_LIVE_LOG": str(LIVE_LOG_PATH),
            "CAPPROOF_MCP_WORKSPACE": str(WORKSPACE_DIR),
            "CAPPROOF_SANDBOX_REAL_EXECUTION": "1",
        }
    )
    return runtime_env


def ensure_dirs() -> None:
    for directory in (CONFIG_DIR, REPORT_DIR, TRACE_DIR, WORKSPACE_DIR, RUNTIME_HOME, AUTH_QUEUE_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def prepare_workspace() -> None:
    (WORKSPACE_DIR / "docs").mkdir(parents=True, exist_ok=True)
    (WORKSPACE_DIR / "reports").mkdir(parents=True, exist_ok=True)
    (WORKSPACE_DIR / "tests").mkdir(parents=True, exist_ok=True)
    (WORKSPACE_DIR / "docs" / "input.txt").write_text(
        "CodeWhale CapProof MCP input. The summary value is val_summary.\n",
        encoding="utf-8",
    )
    (WORKSPACE_DIR / "tests" / "test_codewhale_capproof.py").write_text(
        "def test_codewhale_capproof_template():\n    assert 'val_summary'.startswith('val_')\n",
        encoding="utf-8",
    )
    (WORKSPACE_DIR / "AGENTS.md").write_text(
        "\n".join(
            [
                "# CapProof MCP workspace instructions",
                "",
                "Use CapProof MCP tools when the user explicitly asks for CapProof.",
                "Do not use built-in shell/file/messaging tools for CapProof validation prompts.",
                "After every CapProof MCP tool call, show the user these returned fields when present:",
                "tool_name, verdict, reason, proof_id, request_id, executor_called, capability_minted.",
                "Never claim a user approved authorization unless the trusted local CLI approval path produced a receipt.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_codewhale_config(env: Mapping[str, str]) -> None:
    model = env.get("DEEPSEEK_MODEL", DEFAULT_MODEL)
    base_url = env.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    text = "\n".join(
        [
            'provider = "deepseek"',
            f'model = "{toml_escape(model)}"',
            f'base_url = "{toml_escape(base_url)}"',
            f'mcp_config_path = "{toml_escape(str(MCP_CONFIG_PATH))}"',
            'approval_policy = "on-request"',
            'sandbox_mode = "workspace-write"',
            "allow_shell = false",
            "telemetry = false",
            "",
            "[providers.deepseek]",
            f'model = "{toml_escape(model)}"',
            f'base_url = "{toml_escape(base_url)}"',
            "",
        ]
    )
    CONFIG_PATH.write_text(text, encoding="utf-8")


def write_mcp_config() -> None:
    config = {
        "timeouts": {"connect_timeout": 10, "execute_timeout": 60, "read_timeout": 120},
        "servers": {
            "capproof": {
                "command": sys.executable,
                "args": [
                    str(ROOT / "tools" / "run_capproof_mcp_server.py"),
                    "--stdio",
                    "--sandboxed-real-execution",
                    "--workspace",
                    str(WORKSPACE_DIR),
                    "--trace-path",
                    str(TRACE_PATH),
                ],
                "cwd": str(ROOT),
                "env": {
                    "CAPPROOF_MCP_WORKSPACE": str(WORKSPACE_DIR),
                    "CAPPROOF_MCP_TRACE_PATH": str(TRACE_PATH),
                    "CAPPROOF_AUTH_QUEUE_DIR": str(AUTH_QUEUE_DIR),
                    "CAPPROOF_ASK_TRACE_PATH": str(TRACE_PATH),
                    "CAPPROOF_SANDBOX_REAL_EXECUTION": "1",
                },
                "enabled": True,
                "required": True,
                "connect_timeout": 10,
                "execute_timeout": 60,
                "read_timeout": 120,
            }
        },
    }
    MCP_CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def build_codewhale_command(env: Mapping[str, str], passthrough: Sequence[str]) -> list[str]:
    if passthrough:
        return [str(CODEWHALE_BINARY), "--config", str(CONFIG_PATH), "--workspace", str(WORKSPACE_DIR), *passthrough]
    return [
        str(CODEWHALE_TUI_BINARY),
        "--config",
        str(CONFIG_PATH),
        "--workspace",
        str(WORKSPACE_DIR),
        "--skip-onboarding",
        "--no-project-config",
    ]


def print_startup_banner(*, file) -> None:
    payload = wrapper_status_payload()
    lines = [
        "CodeWhale CapProof foreground",
        "CapProof MCP attached: yes",
        "agent: CodeWhale",
        f"agent binary: {payload['agent_binary']}",
        f"model provider: {payload['model_provider']}",
        f"model: {payload['model_name']}",
        "MCP mode: stdio",
        "sandboxed-real-execution: enabled",
        f"exposed tools: {payload['tools_count']}",
        f"trace file: {payload['trace_path']}",
        f"live log: {payload['live_log_path']}",
        f"auth queue: {payload['auth_queue_dir']}",
        "inside CodeWhale: /mcp validate, then /mcp to view servers/tools",
        "safety boundary: DeepSeek not safety TCB; CapProof guard gates tools",
    ]
    print("\n".join(lines), file=file)


def print_where_trace(*, json_output: bool) -> None:
    payload = {
        "trace_jsonl_path": str(TRACE_PATH),
        "live_log_path": str(LIVE_LOG_PATH),
        "sandbox_workspace_path": str(WORKSPACE_DIR),
        "config_path": str(CONFIG_PATH),
        "mcp_config_path": str(MCP_CONFIG_PATH),
        "summary_path": str(SUMMARY_PATH),
        "report_path": str(REPORT_PATH),
        "auth_queue_dir": str(AUTH_QUEUE_DIR),
    }
    print_payload(payload, json_output=json_output)


def print_capproof_status(*, json_output: bool) -> None:
    entries, skipped = run_capproof_trace_viewer.read_trace(TRACE_PATH)
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
    ensure_dirs()
    payload = wrapper_status_payload()
    payload.update(
        {
            "deepseek_api_key_present": bool(env.get("DEEPSEEK_API_KEY")),
            "deepseek_key_value": "redacted" if env.get("DEEPSEEK_API_KEY") else "",
            "runtime_present": CODEWHALE_BINARY.exists() and CODEWHALE_TUI_BINARY.exists(),
            "version": probe_version(CODEWHALE_BINARY),
            "tui_version": probe_version(CODEWHALE_TUI_BINARY),
            "config_exists": CONFIG_PATH.exists(),
            "mcp_config_exists": MCP_CONFIG_PATH.exists(),
            "trace_dir_writable": ensure_writable(TRACE_DIR),
            "live_log_dir_writable": ensure_writable(REPORT_DIR),
            "sandbox_workspace_exists": WORKSPACE_DIR.exists(),
            "key_written": False,
        }
    )
    print_payload(payload, json_output=json_output)


def print_preflight(env: Mapping[str, str], *, json_output: bool) -> None:
    payload = {
        "agent": "codewhale",
        "source_repo_present": (ROOT / "external" / "codewhale").exists(),
        "source_commit": source_commit(),
        "deepseek_api_key_present": bool(env.get("DEEPSEEK_API_KEY")),
        "deepseek_key_source": "DEEPSEEK_API_KEY",
        "key_written": False,
        "runtime_present": CODEWHALE_BINARY.exists() and CODEWHALE_TUI_BINARY.exists(),
        "version": probe_version(CODEWHALE_BINARY),
        "tui_version": probe_version(CODEWHALE_TUI_BINARY),
        "standard_capproof_mcp_server": "tools/run_capproof_mcp_server.py --stdio --sandboxed-real-execution",
        "dry_run_preflight_counts_as_completion": False,
    }
    print_payload(payload, json_output=json_output)


def wrapper_status_payload() -> dict[str, object]:
    return {
        "capproof_mcp_attached": True,
        "agent": "codewhale",
        "agent_binary": str(CODEWHALE_BINARY),
        "agent_tui_binary": str(CODEWHALE_TUI_BINARY),
        "model_provider": "deepseek",
        "model_name": os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
        "mcp_mode": "stdio",
        "sandboxed_real_execution": True,
        "tools_count": len(tool_names()),
        "trace_path": str(TRACE_PATH),
        "live_log_path": str(LIVE_LOG_PATH),
        "workspace": str(WORKSPACE_DIR),
        "auth_queue_dir": str(AUTH_QUEUE_DIR),
        "deepseek_not_safety_tcb": True,
        "capproof_guard_gates_tools": True,
    }


def tool_names() -> list[str]:
    context = make_default_context(workspace=WORKSPACE_DIR, trace_path=TRACE_PATH, executor_mode="sandbox")
    server = CapProofMCPServer(context=context)
    return [str(tool.get("name", "")) for tool in server.list_tools()["tools"]]


def probe_version(binary: Path) -> str:
    if not binary.exists():
        return ""
    completed = subprocess.run([str(binary), "--version"], text=True, capture_output=True, timeout=20, check=False)
    return (completed.stdout or completed.stderr).strip().splitlines()[0] if (completed.stdout or completed.stderr).strip() else ""


def source_commit() -> str:
    repo = ROOT / "external" / "codewhale"
    if not repo.exists():
        return ""
    completed = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, capture_output=True, timeout=20, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def ensure_writable(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".capproof_write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def print_payload(payload: Mapping[str, object], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}={value}")


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
