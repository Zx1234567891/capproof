from pathlib import Path

import pytest

from capproof.mcp.sandbox_policy import SandboxPolicy, SandboxPolicyError


def test_path_traversal_is_denied(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = SandboxPolicy(workspace)

    with pytest.raises(SandboxPolicyError, match="path_outside_workspace"):
        policy.resolve_workspace_path("../outside.txt")


def test_absolute_outside_path_is_denied(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    policy = SandboxPolicy(workspace)

    with pytest.raises(SandboxPolicyError, match="path_outside_workspace"):
        policy.resolve_workspace_path(outside)


def test_symlink_escape_is_denied(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    target = outside / "secret.txt"
    target.write_text("secret", encoding="utf-8")
    (workspace / "link.txt").symlink_to(target)
    policy = SandboxPolicy(workspace)

    with pytest.raises(SandboxPolicyError, match="path_outside_workspace"):
        policy.resolve_workspace_path("link.txt")


def test_inside_path_resolves(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = SandboxPolicy(workspace)

    assert policy.resolve_workspace_path("docs/report.md", for_write=True) == workspace / "docs" / "report.md"
