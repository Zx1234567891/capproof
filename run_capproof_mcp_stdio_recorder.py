#!/usr/bin/env python3
"""Record CapProof MCP stdio traffic without polluting stdout.

Stdout is reserved for MCP JSON-RPC responses. Human-readable diagnostics are
written to stderr and the optional live log. The recorder runs the standard
CapProof MCP server implementation in-process so Hermes can use it as a normal
stdio MCP server while Stage 34H captures observable workflow artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from capproof.mcp.context import make_default_context
from capproof.mcp.stdio import run_stdio_server


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT / "real_agent_integrations" / "hermes_mcp_server"
TRACE_DIR = BASE_DIR / "traces"
REPORT_DIR = BASE_DIR / "reports"
DEFAULT_TRACE_PATH = TRACE_DIR / "foreground_hermes_mcp_trace.jsonl"
DEFAULT_LIVE_LOG = REPORT_DIR / "foreground_hermes_mcp_live.log"


def main() -> int:
    parser = argparse.ArgumentParser(description="CapProof MCP stdio recorder for Stage 34H foreground demos.")
    parser.add_argument("--stdio", action="store_true", help="serve MCP JSON-RPC over stdio")
    parser.add_argument("--workspace", help="workspace root for sandboxed local execution")
    parser.add_argument("--trace-path", help="CapProof MCP trace JSONL path")
    parser.add_argument("--live-log", help="human-readable live log path")
    parser.add_argument("--sandboxed-real-execution", action="store_true", help="use Stage 33S sandbox executor")
    args = parser.parse_args()

    ensure_dirs()
    workspace = Path(args.workspace or os.environ.get("CAPPROOF_MCP_WORKSPACE") or tempfile.mkdtemp(prefix="capproof_foreground_mcp_"))
    trace_path = Path(args.trace_path or os.environ.get("CAPPROOF_MCP_TRACE_PATH") or DEFAULT_TRACE_PATH)
    live_log = Path(args.live_log or os.environ.get("CAPPROOF_MCP_LIVE_LOG") or DEFAULT_LIVE_LOG)
    live_log.parent.mkdir(parents=True, exist_ok=True)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    context = make_default_context(
        workspace=workspace,
        trace_path=trace_path,
        executor_mode="sandbox" if args.sandboxed_real_execution else "mock",
    )
    _log(live_log, f"CapProof MCP stdio recorder starting workspace={workspace} trace_path={trace_path}")
    if not args.stdio:
        print(
            json.dumps(
                {
                    "server": "capproof-mcp-stdio-recorder",
                    "stdio": False,
                    "workspace": str(workspace),
                    "trace_path": str(trace_path),
                    "live_log": str(live_log),
                    "stdout_reserved_for_mcp": True,
                },
                sort_keys=True,
            )
        )
        return 0
    try:
        return run_stdio_server(context=context, stderr=sys.stderr)
    finally:
        _log(live_log, "CapProof MCP stdio recorder stopped")


def _log(path: Path, message: str) -> None:
    import time

    line = json.dumps({"timestamp": time.time(), "component": "capproof_mcp_stdio_recorder", "message": message}, sort_keys=True)
    path.open("a", encoding="utf-8").write(line + "\n")
    print(message, file=sys.stderr)


def ensure_dirs() -> None:
    for directory in (TRACE_DIR, REPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
