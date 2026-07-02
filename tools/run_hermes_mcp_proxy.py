#!/usr/bin/env python3
"""Standalone CapProof MCP proxy runner.

The default list/call path uses the productized CapProof MCP server package.
It does not run Hermes, call model APIs, send email, execute shell commands, or
connect to external services. Legacy Stage 30 tool names are accepted as aliases
for local compatibility.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import time
from typing import Any
import tempfile
import threading

from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "real_agent_integrations" / "hermes_mcp_server"
TRACE_PATH = INTEGRATION_DIR / "traces" / "capproof_mcp_trace.jsonl"
CONFIG_PATH = INTEGRATION_DIR / "configs" / "local_mcp_proxy_config.json"


LEGACY_TOOL_ALIASES = {
    "safe_echo_summary": "capproof.send_message_mock",
    "attempt_exfiltrate": "capproof.send_message_mock",
    "run_shell": "capproof.run_command_template",
}


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
    server = CapProofMCPServer(context=make_default_context(workspace=workspace, trace_path=TRACE_PATH))
    if args.list_tools:
        print(json.dumps(server.list_tools(), sort_keys=True))
        return 0
    if args.call_tool:
        try:
            arguments = json.loads(args.arguments_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid --arguments-json: {exc}") from exc
        if not isinstance(arguments, dict):
            raise SystemExit("--arguments-json must decode to an object")
        tool_name, mapped_arguments = _map_legacy_tool(args.call_tool, arguments, workspace)
        result = server.call_tool(tool_name, mapped_arguments)
        print(json.dumps(result["structuredContent"], sort_keys=True))
        return 0
    if args.serve:
        http = LocalProductMCPHTTPServer(server)
        http.start()
        port = int(http.server_address[1])
        write_local_mcp_config(port)
        print(json.dumps({"host": "127.0.0.1", "port": port, "trace": str(TRACE_PATH)}, sort_keys=True))
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            http.stop()
        return 0
    print(json.dumps({"tools": [tool["name"] for tool in server.list_tools()["tools"]], "trace": str(TRACE_PATH), "workspace": str(workspace)}, sort_keys=True))
    return 0


class _Handler(BaseHTTPRequestHandler):
    server: "LocalProductMCPHTTPServer"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/tools":
            self._write_json(self.server.mcp_server.list_tools())
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/tool", "/call"}:
            self.send_error(404)
            return
        length = int(self.headers.get("content-length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400)
            return
        tool_name = str(payload.get("tool") or payload.get("name") or "")
        args = payload.get("arguments") or payload.get("input") or {}
        if not isinstance(args, dict):
            self.send_error(400)
            return
        mapped_tool, mapped_args = _map_legacy_tool(tool_name, args, self.server.mcp_server.context.workspace)
        self._write_json(self.server.mcp_server.call_tool(mapped_tool, mapped_args)["structuredContent"])

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _write_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class LocalProductMCPHTTPServer(ThreadingHTTPServer):
    def __init__(self, mcp_server: CapProofMCPServer) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.mcp_server = mcp_server
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.shutdown()
        self.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)


def _map_legacy_tool(tool_name: str, arguments: dict[str, Any], workspace: Path) -> tuple[str, dict[str, Any]]:
    if tool_name not in LEGACY_TOOL_ALIASES:
        return tool_name, dict(arguments)
    if tool_name in {"safe_echo_summary", "attempt_exfiltrate"}:
        return (
            LEGACY_TOOL_ALIASES[tool_name],
            {
                "recipient": str(arguments.get("recipient", "")),
                "body_ref": str(arguments.get("body_ref", "val_summary")),
            },
        )
    if tool_name == "run_shell":
        return (
            "capproof.run_command_template",
            {
                "command_template": str(arguments.get("command", "")),
                "args": {},
                "cwd": str(workspace),
                "env": {},
                "stdin": None,
            },
        )
    return tool_name, dict(arguments)


def ensure_dirs() -> None:
    (INTEGRATION_DIR / "traces").mkdir(parents=True, exist_ok=True)
    (INTEGRATION_DIR / "configs").mkdir(parents=True, exist_ok=True)


def workspace_from_env_or_temp() -> Path:
    import os

    workspace = os.environ.get("HERMES_TEST_WORKSPACE") or os.environ.get("CAPPROOF_MCP_WORKSPACE")
    if workspace:
        path = Path(workspace)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return Path(tempfile.mkdtemp(prefix="capproof_mcp_proxy_"))


def write_local_mcp_config(port: int) -> None:
    CONFIG_PATH.write_text(
        json.dumps(
            {
                "host": "127.0.0.1",
                "port": port,
                "url": f"http://127.0.0.1:{port}",
                "tools_method": "tools/list",
                "call_method": "tools/call",
                "external_mcp": False,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
