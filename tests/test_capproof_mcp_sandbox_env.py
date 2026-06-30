from pathlib import Path

import pytest

from capproof.mcp.command_templates import build_command_plan
from capproof.mcp.context import make_default_context
from capproof.mcp.sandbox_policy import SandboxPolicy, SandboxPolicyError
from capproof.mcp.server import CapProofMCPServer


def test_env_allowlist_only(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = SandboxPolicy(workspace)

    assert policy.sanitize_env({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}) == {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    with pytest.raises(SandboxPolicyError, match="env_key_not_allowed"):
        policy.sanitize_env({"PATH": "/usr/bin"})


def test_secret_env_key_is_not_allowed_in_template_plan(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = SandboxPolicy(workspace)

    with pytest.raises(SandboxPolicyError, match="env_key_not_allowed"):
        build_command_plan(
            {
                "command_template": "pytest",
                "args": {"target": "tests/"},
                "cwd": str(workspace),
                "env": {"DEEPSEEK_API_KEY": "redacted"},
                "stdin": None,
            },
            policy,
        )


def test_command_does_not_inherit_parent_secret_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STAGE33_SECRET_TOKEN", "do-not-inherit")
    workspace = tmp_path / "workspace"
    (workspace / "tests").mkdir(parents=True)
    (workspace / "tests" / "test_env.py").write_text(
        "import os\n\ndef test_secret_absent():\n    assert 'STAGE33_SECRET_TOKEN' not in os.environ\n",
        encoding="utf-8",
    )
    context = make_default_context(workspace=workspace, trace_path=tmp_path / "trace.jsonl", executor_mode="sandbox")
    server = CapProofMCPServer(context=context)

    result = server.call_tool(
        "capproof.run_command_template",
        {"command_template": "pytest", "args": {"target": "tests/"}, "cwd": str(workspace), "env": {}, "stdin": None},
    )

    event = result["structuredContent"]["trace"]["mock_event"]
    assert result["structuredContent"]["verdict"] == "ALLOW"
    assert event["returncode"] == 0
    assert "do-not-inherit" not in event["stdout"]
    assert "do-not-inherit" not in event["stderr"]


def test_disallowed_env_is_denied_before_executor(tmp_path: Path) -> None:
    context = make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl", executor_mode="sandbox")
    server = CapProofMCPServer(context=context)

    result = server.call_tool(
        "capproof.run_command_template",
        {
            "command_template": "pytest",
            "args": {"target": "tests/"},
            "cwd": str(context.workspace),
            "env": {"PATH": "/usr/bin"},
            "stdin": None,
        },
    )

    structured = result["structuredContent"]
    assert structured["verdict"] == "DENY"
    assert structured["executor_called"] is False
