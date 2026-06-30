from pathlib import Path

import pytest

from capproof.mcp.sandbox import WorkspaceSandbox
from capproof.mcp.sandbox_policy import SandboxPolicy, SandboxPolicyError


def test_workspace_file_read_returns_content(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "docs").mkdir(parents=True)
    (workspace / "docs" / "input.txt").write_text("hello", encoding="utf-8")
    sandbox = WorkspaceSandbox(SandboxPolicy(workspace))

    result = sandbox.read_text("docs/input.txt")

    assert result["content"] == "hello"
    assert result["side_effect"] == "workspace_file_read"
    assert result["path"].endswith("docs/input.txt")


def test_file_read_size_cap(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "large.txt").write_text("123456", encoding="utf-8")
    sandbox = WorkspaceSandbox(SandboxPolicy(workspace, max_file_bytes=5))

    with pytest.raises(SandboxPolicyError, match="file_too_large"):
        sandbox.read_text("large.txt")


def test_file_read_secret_path_denied(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".env").write_text("SECRET=1", encoding="utf-8")
    sandbox = WorkspaceSandbox(SandboxPolicy(workspace))

    with pytest.raises(SandboxPolicyError, match="secret_path_denied"):
        sandbox.read_text(".env")
