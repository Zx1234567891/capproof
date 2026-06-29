"""Stdio transport for the CapProof MCP server.

Stdout is reserved for JSON-RPC messages. Diagnostics are written to stderr by
the caller or by this module when malformed input is encountered.
"""

from __future__ import annotations

import json
import sys
from typing import TextIO

from capproof.mcp.context import CapProofMCPContext, make_default_context
from capproof.mcp.errors import MCPError, PARSE_ERROR
from capproof.mcp.server import CapProofMCPServer


def run_stdio_server(
    *,
    context: CapProofMCPContext | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout
    error_stream = stderr or sys.stderr
    server = CapProofMCPServer(context=context or make_default_context())
    for line in input_stream:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": PARSE_ERROR, "message": f"parse error: {exc.msg}"},
            }
        else:
            try:
                response = server.handle_json_rpc(request)
            except MCPError as exc:
                response = {"jsonrpc": "2.0", "id": request.get("id"), "error": exc.to_json()}
            except Exception as exc:  # pragma: no cover - defensive transport guard.
                error_stream.write(f"CapProof MCP internal error: {type(exc).__name__}\n")
                error_stream.flush()
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, dict) else None,
                    "error": {"code": -32603, "message": "internal error"},
                }
        if response is not None:
            output_stream.write(json.dumps(response, sort_keys=True) + "\n")
            output_stream.flush()
    return 0
