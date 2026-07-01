from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from capproof.mcp.authorization_store import (
    AuthorizationStore,
    AuthorizationStoreError,
    default_authorization_paths,
)
from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer


def _request_id(tmp_path: Path, monkeypatch) -> tuple[AuthorizationStore, CapProofMCPServer, str]:
    monkeypatch.setenv("CAPPROOF_AUTH_QUEUE_DIR", str(tmp_path / "auth_queue"))
    monkeypatch.setenv("CAPPROOF_ASK_TRACE_PATH", str(tmp_path / "ask_flow_trace.jsonl"))
    server = CapProofMCPServer(
        context=make_default_context(workspace=tmp_path / "workspace", trace_path=tmp_path / "trace.jsonl")
    )
    result = server.call_tool(
        "capproof.request_authorization",
        {
            "reason": "Need user approval for Bob",
            "requested_tool": "capproof.send_message_mock",
            "requested_scope": {"recipient": "bob@example.com", "body_ref": "val_summary"},
        },
    )
    return AuthorizationStore(default_authorization_paths()), server, result["structuredContent"]["request_id"]


def test_replay_approval_is_rejected_without_duplicate_capability(tmp_path: Path, monkeypatch) -> None:
    store, server, request_id = _request_id(tmp_path, monkeypatch)
    scope = {"recipient": "bob@example.com", "body_ref": "val_summary"}

    first = store.approve(
        request_id,
        scope,
        workspace=server.context.workspace,
        task_id=server.context.task_id,
        agent_id=server.context.agent_id,
    )
    with pytest.raises(AuthorizationStoreError, match="not pending"):
        store.approve(
            request_id,
            scope,
            workspace=server.context.workspace,
            task_id=server.context.task_id,
            agent_id=server.context.agent_id,
        )

    assert store.get_request(request_id).status == "approved"
    assert len(store.list_receipts()) == 1
    assert store.list_receipts()[0].receipt_id == first.receipt_id


def test_replay_deny_after_approval_is_rejected_and_mints_no_capability(tmp_path: Path, monkeypatch) -> None:
    store, server, request_id = _request_id(tmp_path, monkeypatch)
    store.approve(
        request_id,
        {"recipient": "bob@example.com", "body_ref": "val_summary"},
        workspace=server.context.workspace,
        task_id=server.context.task_id,
        agent_id=server.context.agent_id,
    )

    with pytest.raises(AuthorizationStoreError, match="not pending"):
        store.deny(request_id, reason="late deny")
    assert len(store.list_receipts()) == 1


def test_expired_request_cannot_be_approved(tmp_path: Path, monkeypatch) -> None:
    store, server, request_id = _request_id(tmp_path, monkeypatch)
    request = store.get_request(request_id)
    expired = type(request)(
        **{
            **request.to_dict(),
            "expires_at": (datetime.now(UTC) - timedelta(seconds=5)).isoformat().replace("+00:00", "Z"),
        }
    )
    store._append_jsonl(store.paths.pending_path, expired.to_dict())

    with pytest.raises(AuthorizationStoreError, match="expired"):
        store.approve(
            request_id,
            {"recipient": "bob@example.com", "body_ref": "val_summary"},
            workspace=server.context.workspace,
            task_id=server.context.task_id,
            agent_id=server.context.agent_id,
        )

    assert store.get_request(request_id).status == "expired"
    assert store.list_receipts() == []
