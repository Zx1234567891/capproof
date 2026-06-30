from pathlib import Path

import pytest

from capproof.mcp.sandbox_policy import SandboxPolicy, SandboxPolicyError


def test_policy_canonicalizes_workspace_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    policy = SandboxPolicy(workspace)

    assert policy.workspace_root == workspace.resolve()


def test_policy_denies_secret_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = SandboxPolicy(workspace)

    with pytest.raises(SandboxPolicyError, match="secret_path_denied"):
        policy.resolve_workspace_path(".env", for_write=True)

    with pytest.raises(SandboxPolicyError, match="secret_path_denied"):
        policy.resolve_workspace_path("keys/service.pem", for_write=True)


def test_policy_sanitizes_env_allowlist_only(tmp_path: Path) -> None:
    policy = SandboxPolicy(tmp_path / "workspace")

    assert policy.sanitize_env({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}) == {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}

    with pytest.raises(SandboxPolicyError, match="env_key_not_allowed"):
        policy.sanitize_env({"DEEPSEEK_API_KEY": "redacted"})
