import json
from pathlib import Path
import importlib.util

from capproof.mcp.authorization_store import AuthorizationStore, default_authorization_paths
from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer


_CLI_PATH = Path(__file__).resolve().parents[1] / "run_capproof_auth_queue.py"
_SPEC = importlib.util.spec_from_file_location("run_capproof_auth_queue", _CLI_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_CLI = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CLI)
auth_queue_main = _CLI.main


def _store(tmp_path: Path, monkeypatch) -> AuthorizationStore:
    queue_dir = tmp_path / "auth_queue"
    monkeypatch.setenv("CAPPROOF_AUTH_QUEUE_DIR", str(queue_dir))
    monkeypatch.setenv("CAPPROOF_ASK_TRACE_PATH", str(tmp_path / "ask_trace.jsonl"))
    return AuthorizationStore(default_authorization_paths())


def _create_request(tmp_path: Path, monkeypatch) -> tuple[AuthorizationStore, str]:
    store = _store(tmp_path, monkeypatch)
    context = make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl")
    server = CapProofMCPServer(context=context)
    result = server.call_tool(
        "capproof.request_authorization",
        {
            "reason": "Need user approval for bob@example.com",
            "requested_tool": "capproof.send_message_mock",
            "requested_scope": {"recipient": "bob@example.com", "body_ref": "val_summary"},
            "user_task": "Ask before sending to Bob",
        },
    )
    request_id = result["structuredContent"]["request_id"]
    return store, request_id


def test_auth_queue_doctor_and_list_do_not_require_real_hermes(tmp_path: Path, monkeypatch, capsys) -> None:
    _store(tmp_path, monkeypatch)

    assert auth_queue_main(["doctor"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["doctor_ok"] is True
    assert doctor["ask_auto_mints_capability"] is False
    assert doctor["llm_output_can_approve"] is False

    assert auth_queue_main(["list"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["requests"] == []


def test_pending_request_has_required_fields_and_ask_invariants(tmp_path: Path, monkeypatch) -> None:
    store, request_id = _create_request(tmp_path, monkeypatch)

    request = store.get_request(request_id)
    assert request.status == "pending"
    assert request.requested_action["tool_name"] == "capproof.send_message_mock"
    assert request.requested_scope["recipient"] == "bob@example.com"
    assert request.canonical_action_hash
    assert request.expires_at
    assert request.trace_id
    assert request.proof_attempt_id


def test_trusted_cli_approval_creates_redaction_safe_receipt(tmp_path: Path, monkeypatch, capsys) -> None:
    store, request_id = _create_request(tmp_path, monkeypatch)
    scope_file = tmp_path / "approved_scope.json"
    scope_file.write_text(
        json.dumps({"recipient": "bob@example.com", "body_ref": "val_summary"}),
        encoding="utf-8",
    )

    assert auth_queue_main(["approve", request_id, "--scope-file", str(scope_file), "--workspace", str(tmp_path / "workspace")]) == 0
    approved = json.loads(capsys.readouterr().out)
    assert approved["approved"] is True
    assert approved["capability_minted"] is True
    assert approved["receipt"]["approved_by"] == "trusted_local_cli"
    assert "api_key" not in json.dumps(approved).lower()

    request = store.get_request(request_id)
    assert request.status == "approved"
    assert request.approval_receipt_id == approved["receipt"]["receipt_id"]
    assert len(store.list_receipts()) == 1
