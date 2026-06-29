from pathlib import Path

from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer
from capproof.mcp.trace import TraceRecorder


def make_server(tmp_path: Path) -> CapProofMCPServer:
    context = make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl")
    return CapProofMCPServer(context=context)


def test_trace_contains_user_visible_workflow_fields(tmp_path: Path) -> None:
    server = make_server(tmp_path)

    server.call_tool(
        "capproof.send_message_mock",
        {"recipient": "alice@example.com", "body_ref": "val_summary"},
    )

    entries = TraceRecorder(tmp_path / "trace.jsonl").read_entries()
    assert len(entries) == 1
    entry = entries[0]
    for field in (
        "mcp_method",
        "tool_name",
        "arguments",
        "canonical_action_hash",
        "capproof_verdict",
        "proof_id",
        "reason",
        "executor_called",
    ):
        assert field in entry
    assert entry["tool_name"] == "capproof.send_message_mock"
    assert entry["capproof_verdict"] == "ALLOW"
    assert entry["executor_called"] is True


def test_get_trace_returns_recent_entries(tmp_path: Path) -> None:
    server = make_server(tmp_path)
    server.call_tool("capproof.echo_summary", {"body_ref": "val_summary"})
    server.call_tool(
        "capproof.send_message_mock",
        {"recipient": "attacker@example.com", "body_ref": "val_summary"},
    )

    result = server.call_tool("capproof.get_trace", {"limit": 2})

    structured = result["structuredContent"]
    assert structured["verdict"] == "ALLOW"
    entries = structured["payload"]["entries"]
    assert len(entries) == 2
    assert entries[-1]["capproof_verdict"] == "DENY"
    assert entries[-1]["tool_name"] == "capproof.send_message_mock"


def test_deny_trace_records_executor_not_called(tmp_path: Path) -> None:
    server = make_server(tmp_path)

    result = server.call_tool(
        "capproof.send_message_mock",
        {"recipient": "attacker@example.com", "body_ref": "val_summary"},
    )

    trace = result["structuredContent"]["trace"]
    assert trace["capproof_verdict"] == "DENY"
    assert trace["reason"] == "NoCap"
    assert trace["executor_called"] is False
    assert trace["proof_id"] is None
