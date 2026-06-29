"""CapProof MCP server package.

This package exposes CapProof-guarded tools through a small MCP-compatible
JSON-RPC surface. It is product-layer code, not a core verifier API.
"""

from capproof.mcp.context import CapProofMCPContext, make_default_context
from capproof.mcp.server import CapProofMCPServer
from capproof.mcp.stdio import run_stdio_server
from capproof.mcp.tool_registry import default_tool_registry
from capproof.mcp.trace import MCPTraceEntry, TraceRecorder

__all__ = [
    "CapProofMCPContext",
    "CapProofMCPServer",
    "MCPTraceEntry",
    "TraceRecorder",
    "default_tool_registry",
    "make_default_context",
    "run_stdio_server",
]
