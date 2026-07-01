"""MCP ASK pending request creation helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

from capproof.mcp.authorization_store import AuthorizationRequest, normalize_approved_scope
from capproof.serialization import JsonObject, stable_hash


DEFAULT_EXPIRY_SECONDS = 3600


def create_authorization_request_payload(
    args: Mapping[str, Any],
    ctx: "CapProofMCPContext",
) -> JsonObject:
    request = build_authorization_request(args, ctx)
    ctx.authorization_store.add_request(request)
    return {
        "verdict": "ASK",
        "reason": "AuthorizationRequested",
        "request_id": request.request_id,
        "canonical_action_hash": request.canonical_action_hash,
        "proof_attempt_id": request.proof_attempt_id,
        "capability_minted": False,
        "executor_called": False,
        "pending_authorization_request": request.to_dict(),
        "request": request.to_dict(),
        "trusted_local_cli_required": True,
        "llm_output_can_approve": False,
        "mcp_metadata_can_approve": False,
    }


def build_authorization_request(
    args: Mapping[str, Any],
    ctx: "CapProofMCPContext",
) -> AuthorizationRequest:
    requested_tool = str(args.get("requested_tool") or "capproof.send_message_mock")
    requested_scope = args.get("requested_scope", {})
    if not isinstance(requested_scope, dict):
        requested_scope = {}
    normalized_scope = normalize_approved_scope(
        requested_tool,
        dict(requested_scope),
        workspace=ctx.workspace,
    )
    requested_action = {
        "tool_name": requested_tool,
        "scope": normalized_scope,
        "reason": str(args.get("reason", "")),
    }
    now = datetime.now(UTC)
    expires_in = _positive_int(args.get("expires_in_seconds"), DEFAULT_EXPIRY_SECONDS)
    expires = now + timedelta(seconds=expires_in)
    user_task = str(args.get("user_task", ""))
    original_arguments = {
        "reason": str(args.get("reason", "")),
        "requested_tool": requested_tool,
        "requested_scope": dict(requested_scope),
        "user_task": user_task,
    }
    canonical_hash = stable_hash(
        {
            "task_id": ctx.task_id,
            "agent_id": ctx.agent_id,
            "requested_action": requested_action,
        }
    )
    request_id = "authreq_" + stable_hash(
        {
            "canonical_action_hash": canonical_hash,
            "created_at": now.isoformat(),
            "reason": str(args.get("reason", "")),
        }
    )[:20]
    trace_id = "ask_trace_" + stable_hash({"request_id": request_id, "canonical_action_hash": canonical_hash})[:16]
    return AuthorizationRequest(
        request_id=request_id,
        requested_action=requested_action,
        requested_scope=normalized_scope,
        user_task=user_task,
        tool_name=requested_tool,
        original_arguments=original_arguments,
        canonical_action_hash=canonical_hash,
        requested_by_agent=ctx.agent_id,
        created_at=now.isoformat().replace("+00:00", "Z"),
        expires_at=expires.isoformat().replace("+00:00", "Z"),
        status="pending",
        trace_id=trace_id,
        proof_attempt_id="proof_attempt_" + canonical_hash[:20],
    )


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return parsed


if False:  # pragma: no cover - import cycle typing hint only.
    from capproof.mcp.context import CapProofMCPContext
