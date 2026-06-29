"""No-side-effect executor helpers for the MCP product layer."""

from __future__ import annotations

from pathlib import Path

from capproof.agent_adapter import MockExecutor


class MCPMockExecutor(MockExecutor):
    """MockExecutor marker used by the MCP server.

    The implementation inherits the existing no-real-network/no-real-email
    behavior. DENY/ASK calls are still blocked by GuardedExecutor before this
    executor can run.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        super().__init__(workspace_root)
