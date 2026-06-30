"""Workspace-only file operations for the Stage 33S MCP sandbox."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

from capproof.mcp.sandbox_policy import SandboxPolicy
from capproof.serialization import JsonObject


@dataclass
class WorkspaceSandbox:
    policy: SandboxPolicy

    def read_text(self, path: str) -> JsonObject:
        resolved = self.policy.resolve_workspace_path(path)
        self.policy.ensure_readable_file(resolved)
        content = resolved.read_text(encoding="utf-8")
        return {
            "sandbox_tool": "read_workspace_file",
            "side_effect": "workspace_file_read",
            "path": str(resolved),
            "bytes": len(content.encode("utf-8")),
            "content": content,
            "workspace_root": str(self.policy.workspace_root),
        }

    def write_text(self, path: str, content: str, *, overwrite: bool) -> JsonObject:
        resolved = self.policy.resolve_workspace_path(path, for_write=True)
        self.policy.ensure_write_allowed(resolved, content=content, overwrite=overwrite)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{resolved.name}.", suffix=".tmp", dir=str(resolved.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, resolved)
        except Exception:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            finally:
                raise
        return {
            "sandbox_tool": "write_workspace_file",
            "side_effect": "workspace_file_write",
            "path": str(resolved),
            "bytes": len(content.encode("utf-8")),
            "atomic_write": True,
            "workspace_root": str(self.policy.workspace_root),
        }
