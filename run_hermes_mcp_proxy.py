#!/usr/bin/env python3
"""Standalone local CapProof MCP proxy runner.

This script does not run Hermes and does not call model APIs. It exposes the
same mock-only local tools used by Stage 30 and routes every call through
CapProofMiddleware before MockExecutor can run.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from run_real_hermes_mcp_test import (
    CapProofMCPProxy,
    LocalMCPHTTPServer,
    TRACE_PATH,
    ensure_dirs,
    workspace_from_env_or_temp,
    write_local_mcp_config,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a localhost CapProof MCP mock/proxy.")
    parser.add_argument("--list-tools", action="store_true", help="print exposed mock tool names")
    parser.add_argument("--call-tool", help="call one mock tool once without starting a long-running server")
    parser.add_argument("--arguments-json", default="{}", help="JSON object arguments for --call-tool")
    parser.add_argument("--serve", action="store_true", help="serve localhost proxy until interrupted")
    parser.add_argument("--workspace", help="mock workspace; defaults to HERMES_TEST_WORKSPACE or temp")
    args = parser.parse_args()

    ensure_dirs()
    workspace = Path(args.workspace) if args.workspace else workspace_from_env_or_temp()
    proxy = CapProofMCPProxy(workspace=workspace, trace_path=TRACE_PATH)
    if args.list_tools:
        print(json.dumps({"tools": list(proxy.tools)}, sort_keys=True))
        return 0
    if args.call_tool:
        try:
            arguments = json.loads(args.arguments_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid --arguments-json: {exc}") from exc
        if not isinstance(arguments, dict):
            raise SystemExit("--arguments-json must decode to an object")
        result = proxy.handle_tool_call(args.call_tool, arguments)
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.serve:
        server = LocalMCPHTTPServer(proxy)
        server.start()
        port = int(server.server_address[1])
        write_local_mcp_config(port)
        print(json.dumps({"host": "127.0.0.1", "port": port, "trace": str(TRACE_PATH)}, sort_keys=True))
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
        return 0
    print(json.dumps({"tools": list(proxy.tools), "trace": str(TRACE_PATH), "workspace": str(workspace)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
