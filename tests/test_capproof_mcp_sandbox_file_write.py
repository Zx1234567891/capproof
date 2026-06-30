from pathlib import Path

from capproof.mcp.context import make_default_context
from capproof.mcp.sandbox import WorkspaceSandbox
from capproof.mcp.sandbox_policy import SandboxPolicy
from capproof.mcp.server import CapProofMCPServer


def test_workspace_file_write_is_atomic(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    sandbox = WorkspaceSandbox(SandboxPolicy(workspace))

    result = sandbox.write_text("reports/out.txt", "hello", overwrite=False)

    written = workspace / "reports" / "out.txt"
    assert written.read_text(encoding="utf-8") == "hello"
    assert result["atomic_write"] is True
    assert list((workspace / "reports").glob(".*.tmp")) == []


def test_secret_write_is_refused_after_guard_allow(tmp_path: Path) -> None:
    context = make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl", executor_mode="sandbox")
    server = CapProofMCPServer(context=context)

    result = server.call_tool(
        "capproof.write_workspace_file",
        {"path": ".env", "content": "val_summary", "mode": "create", "overwrite": False},
    )

    structured = result["structuredContent"]
    event = structured["trace"]["mock_event"]
    assert structured["verdict"] == "ALLOW"
    assert structured["executor_called"] is True
    assert event["sandbox_refused"] is True
    assert event["reason"] == "secret_path_denied"
    assert not (context.workspace / ".env").exists()


def test_deny_does_not_call_sandbox_executor(tmp_path: Path) -> None:
    context = make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl", executor_mode="sandbox")
    server = CapProofMCPServer(context=context)

    result = server.call_tool("capproof.read_workspace_file", {"path": "../outside.txt"})

    structured = result["structuredContent"]
    assert structured["verdict"] == "DENY"
    assert structured["executor_called"] is False
    assert context.executor.executions == []
