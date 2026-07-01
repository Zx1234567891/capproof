from pathlib import Path

from capproof.capability_store import list_capabilities
from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer


def test_request_authorization_returns_ask_without_minting_capability(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CAPPROOF_AUTH_QUEUE_DIR", str(tmp_path / "auth_queue"))
    monkeypatch.setenv("CAPPROOF_ASK_TRACE_PATH", str(tmp_path / "ask_flow_trace.jsonl"))
    context = make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl")
    server = CapProofMCPServer(context=context)
    before = len(list_capabilities(context.monitor_state.capability_store))

    result = server.call_tool(
        "capproof.request_authorization",
        {
            "reason": "Need user approval for bob@example.com",
            "requested_tool": "capproof.send_message_mock",
            "requested_scope": {"recipient": "bob@example.com", "body_ref": "val_summary"},
        },
    )
    after = len(list_capabilities(context.monitor_state.capability_store))

    structured = result["structuredContent"]
    pending = structured["pending_authorization_request"]
    assert structured["verdict"] == "ASK"
    assert structured["reason"] == "AuthorizationRequested"
    assert structured["executor_called"] is False
    assert structured["capability_minted"] is False
    assert pending["status"] == "pending"
    assert pending["requested_scope"]["recipient"] == "bob@example.com"
    assert before == after


def test_request_authorization_trace_is_user_visible(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CAPPROOF_AUTH_QUEUE_DIR", str(tmp_path / "auth_queue"))
    monkeypatch.setenv("CAPPROOF_ASK_TRACE_PATH", str(tmp_path / "ask_flow_trace.jsonl"))
    context = make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl")
    server = CapProofMCPServer(context=context)

    result = server.handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "capproof.request_authorization",
                "arguments": {
                    "reason": "Need user approval",
                    "requested_tool": "capproof.send_message_mock",
                    "requested_scope": {"recipient": "bob@example.com"},
                },
                "_meta": {"user_task": "Ask before sending to Bob"},
            },
        }
    )

    trace = result["result"]["structuredContent"]["trace"]
    assert trace["mcp_method"] == "tools/call"
    assert trace["tool_name"] == "capproof.request_authorization"
    assert trace["original_arguments"]["requested_scope"]["recipient"] == "bob@example.com"
    assert trace["capproof_verdict"] == "ASK"
    assert trace["executor_called"] is False
    assert trace["user_task"] == "Ask before sending to Bob"
