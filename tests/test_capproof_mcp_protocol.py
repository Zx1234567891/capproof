import json
from io import StringIO
from pathlib import Path

from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer
from capproof.mcp.stdio import run_stdio_server


def make_server(tmp_path: Path) -> CapProofMCPServer:
    context = make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl")
    return CapProofMCPServer(context=context)


def test_tools_list_exposes_standard_capproof_tools(tmp_path: Path) -> None:
    server = make_server(tmp_path)

    result = server.handle_json_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})

    assert result is not None
    tools = result["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert names == {
        "capproof.echo_summary",
        "capproof.send_message_mock",
        "capproof.read_workspace_file",
        "capproof.write_workspace_file",
        "capproof.run_command_template",
        "capproof.get_trace",
        "capproof.request_authorization",
    }
    send_tool = next(tool for tool in tools if tool["name"] == "capproof.send_message_mock")
    assert send_tool["inputSchema"]["required"] == ["recipient", "body_ref"]
    assert send_tool["annotations"]["capproofMetadataCannotMintCapability"] is True


def test_tools_call_returns_content_and_structured_content(tmp_path: Path) -> None:
    server = make_server(tmp_path)

    result = server.handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "capproof.send_message_mock",
                "arguments": {"recipient": "alice@example.com", "body_ref": "val_summary"},
            },
        }
    )

    assert result is not None
    payload = result["result"]
    assert payload["content"][0]["type"] == "text"
    structured = payload["structuredContent"]
    assert structured["verdict"] == "ALLOW"
    assert structured["proof"]["canonical_action_hash"]
    assert structured["proof"]["proof_id"]
    assert structured["executor_called"] is True
    assert structured["trace"]["mcp_method"] == "tools/call"


def test_unknown_tool_is_json_rpc_error(tmp_path: Path) -> None:
    server = make_server(tmp_path)

    result = server.handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "capproof.nope", "arguments": {}},
        }
    )

    assert result is not None
    assert result["error"]["code"] == -32001


def test_stdio_outputs_only_json_rpc_on_stdout(tmp_path: Path) -> None:
    context = make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl")
    stdin = StringIO(
        "\n".join(
            [
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            ]
        )
        + "\n"
    )
    stdout = StringIO()
    stderr = StringIO()

    rc = run_stdio_server(context=context, stdin=stdin, stdout=stdout, stderr=stderr)

    assert rc == 0
    lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [line["id"] for line in lines] == [1, 2]
    assert all(line["jsonrpc"] == "2.0" for line in lines)
    assert stderr.getvalue() == ""
