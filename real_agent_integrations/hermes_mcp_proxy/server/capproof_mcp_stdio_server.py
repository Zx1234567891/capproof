#!/usr/bin/env python3
"""Compatibility entrypoint for the productized CapProof MCP stdio server."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def _load_context():
    repo = os.environ.get("CAPPROOF_REPO")
    if repo:
        sys.path.insert(0, repo)
        sys.path.insert(0, str(Path(repo) / "src"))
    from capproof.mcp.context import make_default_context

    workspace = Path(os.environ.get("CAPPROOF_PROXY_WORKSPACE", os.getcwd()))
    trace_path = Path(os.environ.get("CAPPROOF_PROXY_TRACE_PATH", "hermes_mcp_trace.jsonl"))
    return make_default_context(workspace=workspace, trace_path=trace_path)


def main() -> int:
    from capproof.mcp.stdio import run_stdio_server

    return run_stdio_server(context=_load_context())


if __name__ == "__main__":
    raise SystemExit(main())
