"""Persistent MCP ASK authorization queue and trusted local approvals."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Iterable

from capproof.canonicalizer import Canonicalizer
from capproof.capability_store import mint_capability
from capproof.mcp.authorization_receipts import AuthorizationReceipt, make_receipt_id, redact_json
from capproof.monitor import MonitorState
from capproof.schemas import (
    ActionKind,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    Linearity,
)
from capproof.serialization import JsonObject, stable_hash


STATUSES = {"pending", "approved", "denied", "expired"}


@dataclass(frozen=True)
class AuthorizationPaths:
    queue_dir: Path
    pending_path: Path
    receipts_path: Path
    audit_trace_path: Path
    report_path: Path
    summary_path: Path


@dataclass(frozen=True)
class AuthorizationRequest:
    request_id: str
    requested_action: JsonObject
    requested_scope: JsonObject
    user_task: str
    tool_name: str
    original_arguments: JsonObject
    canonical_action_hash: str
    requested_by_agent: str
    created_at: str
    expires_at: str
    status: str
    trace_id: str
    proof_attempt_id: str
    approved_scope: JsonObject | None = None
    approval_receipt_id: str | None = None
    decision_reason: str | None = None

    def to_dict(self) -> JsonObject:
        payload: JsonObject = {
            "request_id": self.request_id,
            "requested_action": redact_json(self.requested_action),
            "requested_scope": redact_json(self.requested_scope),
            "user_task": self.user_task,
            "tool_name": self.tool_name,
            "original_arguments": redact_json(self.original_arguments),
            "canonical_action_hash": self.canonical_action_hash,
            "requested_by_agent": self.requested_by_agent,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "trace_id": self.trace_id,
            "proof_attempt_id": self.proof_attempt_id,
        }
        if self.approved_scope is not None:
            payload["approved_scope"] = redact_json(self.approved_scope)
        if self.approval_receipt_id is not None:
            payload["approval_receipt_id"] = self.approval_receipt_id
        if self.decision_reason is not None:
            payload["decision_reason"] = self.decision_reason
        return payload

    @classmethod
    def from_dict(cls, data: JsonObject) -> "AuthorizationRequest":
        status = str(data.get("status", "pending"))
        if status not in STATUSES:
            status = "pending"
        return cls(
            request_id=str(data["request_id"]),
            requested_action=dict(data.get("requested_action", {})),
            requested_scope=dict(data.get("requested_scope", {})),
            user_task=str(data.get("user_task", "")),
            tool_name=str(data.get("tool_name", "")),
            original_arguments=dict(data.get("original_arguments", {})),
            canonical_action_hash=str(data.get("canonical_action_hash", "")),
            requested_by_agent=str(data.get("requested_by_agent", "")),
            created_at=str(data.get("created_at", "")),
            expires_at=str(data.get("expires_at", "")),
            status=status,
            trace_id=str(data.get("trace_id", "")),
            proof_attempt_id=str(data.get("proof_attempt_id", "")),
            approved_scope=dict(data["approved_scope"]) if isinstance(data.get("approved_scope"), dict) else None,
            approval_receipt_id=str(data["approval_receipt_id"]) if data.get("approval_receipt_id") else None,
            decision_reason=str(data["decision_reason"]) if data.get("decision_reason") else None,
        )

    def is_expired(self, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        return current >= expires


class AuthorizationStoreError(ValueError):
    pass


class AuthorizationStore:
    def __init__(self, paths: AuthorizationPaths) -> None:
        self.paths = paths
        self.paths.queue_dir.mkdir(parents=True, exist_ok=True)
        self.paths.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.receipts_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.audit_trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.report_path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env_or_default(cls) -> "AuthorizationStore":
        return cls(default_authorization_paths())

    def add_request(self, request: AuthorizationRequest) -> AuthorizationRequest:
        if request.status not in STATUSES:
            raise AuthorizationStoreError("invalid authorization status")
        self._append_jsonl(self.paths.pending_path, request.to_dict())
        self.write_audit("request_created", {"request": request.to_dict()})
        return request

    def get_request(self, request_id: str) -> AuthorizationRequest:
        request = self._requests_by_id().get(request_id)
        if request is None:
            raise AuthorizationStoreError(f"authorization request not found: {request_id}")
        return request

    def list_requests(self) -> list[AuthorizationRequest]:
        return list(self._requests_by_id().values())

    def approve(
        self,
        request_id: str,
        approved_scope: JsonObject,
        *,
        workspace: str | Path,
        task_id: str,
        agent_id: str,
        approved_by: str = "trusted_local_cli",
    ) -> AuthorizationReceipt:
        request = self.get_request(request_id)
        if request.status != "pending":
            raise AuthorizationStoreError(f"authorization request is not pending: {request.status}")
        if request.is_expired():
            expired = replace(request, status="expired", decision_reason="expired before approval")
            self._append_jsonl(self.paths.pending_path, expired.to_dict())
            self.write_audit("request_expired", {"request": expired.to_dict()})
            raise AuthorizationStoreError("authorization request is expired")
        normalized_requested = normalize_approved_scope(
            request.tool_name,
            request.requested_scope,
            workspace=workspace,
        )
        normalized_approved = normalize_approved_scope(
            request.tool_name,
            approved_scope,
            workspace=workspace,
        )
        if normalized_approved != normalized_requested:
            self.write_audit(
                "approval_rejected_scope_amplification",
                {
                    "request_id": request_id,
                    "requested_scope": normalized_requested,
                    "approved_scope": normalized_approved,
                },
            )
            raise AuthorizationStoreError("approved scope exceeds or changes requested scope")
        capability_ids = tuple(
            cap.cap_id
            for cap in capabilities_for_approved_request(
                request,
                normalized_approved,
                workspace=workspace,
                task_id=task_id,
                agent_id=agent_id,
            )
        )
        issued_at = _now_iso()
        receipt_payload = {
            "request_id": request_id,
            "approved_scope": normalized_approved,
            "capability_ids": list(capability_ids),
            "canonical_action_hash": request.canonical_action_hash,
            "issued_at": issued_at,
            "approved_by": approved_by,
        }
        receipt = AuthorizationReceipt(
            receipt_id=make_receipt_id(receipt_payload),
            request_id=request_id,
            status="approved",
            approved_scope=normalized_approved,
            capability_ids=capability_ids,
            canonical_action_hash=request.canonical_action_hash,
            trace_id=request.trace_id,
            approved_by=approved_by,
            issued_at=issued_at,
        )
        self._append_jsonl(self.paths.receipts_path, receipt.to_dict())
        updated = replace(
            request,
            status="approved",
            approved_scope=normalized_approved,
            approval_receipt_id=receipt.receipt_id,
            decision_reason="approved by trusted local CLI",
        )
        self._append_jsonl(self.paths.pending_path, updated.to_dict())
        self.write_audit("request_approved", {"request": updated.to_dict(), "receipt": receipt.to_dict()})
        return receipt

    def deny(self, request_id: str, *, reason: str) -> AuthorizationRequest:
        request = self.get_request(request_id)
        if request.status != "pending":
            raise AuthorizationStoreError(f"authorization request is not pending: {request.status}")
        updated = replace(request, status="denied", decision_reason=reason)
        self._append_jsonl(self.paths.pending_path, updated.to_dict())
        self.write_audit("request_denied", {"request": updated.to_dict(), "reason": reason})
        return updated

    def expire(self, request_id: str, *, reason: str = "expired by trusted local CLI") -> AuthorizationRequest:
        request = self.get_request(request_id)
        if request.status != "pending":
            raise AuthorizationStoreError(f"authorization request is not pending: {request.status}")
        updated = replace(request, status="expired", decision_reason=reason)
        self._append_jsonl(self.paths.pending_path, updated.to_dict())
        self.write_audit("request_expired", {"request": updated.to_dict(), "reason": reason})
        return updated

    def list_receipts(self) -> list[AuthorizationReceipt]:
        receipts: list[AuthorizationReceipt] = []
        for item in self._read_jsonl(self.paths.receipts_path):
            try:
                receipts.append(AuthorizationReceipt.from_dict(item))
            except (KeyError, TypeError, ValueError):
                continue
        return receipts

    def write_audit(self, event_type: str, payload: JsonObject) -> None:
        self._append_jsonl(
            self.paths.audit_trace_path,
            {
                "timestamp": _now_iso(),
                "event_type": event_type,
                "trusted_local_authorization": True,
                "capability_minted_by_llm": False,
                "metadata_can_approve": False,
                "payload": redact_json(payload),
            },
        )

    def summary(self) -> JsonObject:
        requests = self.list_requests()
        receipts = self.list_receipts()
        status_counts = {status: 0 for status in sorted(STATUSES)}
        for request in requests:
            status_counts[request.status] = status_counts.get(request.status, 0) + 1
        return {
            "queue_dir": str(self.paths.queue_dir),
            "pending_path": str(self.paths.pending_path),
            "receipts_path": str(self.paths.receipts_path),
            "audit_trace_path": str(self.paths.audit_trace_path),
            "request_count": len(requests),
            "receipt_count": len(receipts),
            "status_counts": status_counts,
            "trusted_local_cli_required": True,
            "ask_auto_mints_capability": False,
            "ask_executor_called": False,
            "ask_capability_minted": False,
            "pending_request_fields": [
                "request_id",
                "requested_action",
                "requested_scope",
                "user_task",
                "tool_name",
                "original_arguments",
                "canonical_action_hash",
                "requested_by_agent",
                "created_at",
                "expires_at",
                "status",
                "trace_id",
                "proof_attempt_id",
            ],
            "trusted_approve_can_mint_scoped_capability": True,
            "approval_receipt_generated": True,
            "deny_mints_capability": False,
            "expire_mints_capability": False,
            "scope_amplification_rejected": True,
            "replay_approve_rejected": True,
            "llm_output_can_approve": False,
            "mcp_metadata_can_approve": False,
            "executor_called_on_ask": False,
        }

    def _requests_by_id(self) -> dict[str, AuthorizationRequest]:
        requests: dict[str, AuthorizationRequest] = {}
        for item in self._read_jsonl(self.paths.pending_path):
            try:
                request = AuthorizationRequest.from_dict(item)
            except (KeyError, TypeError, ValueError):
                continue
            requests[request.request_id] = request
        return dict(sorted(requests.items()))

    @staticmethod
    def _append_jsonl(path: Path, payload: JsonObject) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(redact_json(payload), sort_keys=True) + "\n")

    @staticmethod
    def _read_jsonl(path: Path) -> list[JsonObject]:
        if not path.exists():
            return []
        items: list[JsonObject] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                items.append(value)
        return items


def default_authorization_paths() -> AuthorizationPaths:
    root = Path(__file__).resolve().parents[3]
    integration = root / "real_agent_integrations" / "hermes_mcp_server"
    queue_dir = Path(os.environ.get("CAPPROOF_AUTH_QUEUE_DIR", integration / "auth_queue")).resolve(strict=False)
    reports_dir = integration / "reports"
    traces_dir = integration / "traces"
    return AuthorizationPaths(
        queue_dir=queue_dir,
        pending_path=queue_dir / "pending_authorizations.jsonl",
        receipts_path=queue_dir / "authorization_receipts.jsonl",
        audit_trace_path=Path(os.environ.get("CAPPROOF_ASK_TRACE_PATH", traces_dir / "ask_flow_trace.jsonl")).resolve(
            strict=False
        ),
        report_path=reports_dir / "ask_flow_report.md",
        summary_path=reports_dir / "ask_flow_summary.json",
    )


def normalize_approved_scope(tool_name: str, scope: JsonObject, *, workspace: str | Path) -> JsonObject:
    if not isinstance(scope, dict):
        raise AuthorizationStoreError("approved scope must be a JSON object")
    tool = _core_tool_name(tool_name)
    canonicalizer = Canonicalizer(Path(workspace))
    if tool == "send_message":
        allowed = {"recipient", "body_ref", "body", "platform", "channel"}
        _reject_unknown(scope, allowed)
        recipient = scope.get("recipient")
        if not isinstance(recipient, str) or not recipient:
            raise AuthorizationStoreError("send_message approval requires recipient")
        normalized: JsonObject = {"recipient": canonicalizer.canonicalize_recipient(recipient).value}
        if "body_ref" in scope:
            normalized["body_ref"] = str(scope["body_ref"])
        if "body" in scope:
            normalized["body"] = str(scope["body"])
        if "platform" in scope:
            normalized["platform"] = str(scope["platform"])
        if "channel" in scope:
            normalized["channel"] = str(scope["channel"])
        return normalized
    if tool in {"read_file", "write_file"}:
        allowed = {"path", "content", "content_ref", "mode", "overwrite"}
        _reject_unknown(scope, allowed)
        path = scope.get("path")
        if not isinstance(path, str) or not path:
            raise AuthorizationStoreError(f"{tool} approval requires path")
        path_result = canonicalizer.canonicalize_file_path(path)
        if not path_result.allowed:
            raise AuthorizationStoreError(path_result.message or "path cannot be canonicalized")
        normalized = {"path": path_result.value}
        for key in ("content", "content_ref", "mode", "overwrite"):
            if key in scope:
                normalized[key] = scope[key]
        return normalized
    if tool == "run_shell":
        allowed = {"command_template", "args", "cwd", "env", "stdin"}
        _reject_unknown(scope, allowed)
        template = scope.get("command_template")
        if not isinstance(template, str) or not template:
            raise AuthorizationStoreError("run_shell approval requires command_template")
        args = dict(scope.get("args", {})) if isinstance(scope.get("args", {}), dict) else scope.get("args", {})
        env = dict(scope.get("env", {})) if isinstance(scope.get("env", {}), dict) else {}
        cwd = str(scope.get("cwd", str(Path(workspace))))
        stdin = scope.get("stdin")
        shell_result = canonicalizer.canonicalize_run_shell(
            command_template=template,
            args=args if isinstance(args, dict) else {},
            cwd=cwd,
            env=env,
            stdin=stdin if isinstance(stdin, str) or stdin is None else str(stdin),
        )
        if not shell_result.allowed:
            raise AuthorizationStoreError(shell_result.message or "command template cannot be canonicalized")
        return dict(shell_result.value)
    raise AuthorizationStoreError(f"unsupported requested tool for approval: {tool_name}")


def capabilities_for_approved_request(
    request: AuthorizationRequest,
    approved_scope: JsonObject,
    *,
    workspace: str | Path,
    task_id: str,
    agent_id: str,
) -> tuple[Capability, ...]:
    tool = _core_tool_name(request.tool_name)
    cap_prefix = f"cap_auth_{request.request_id}"
    common = {
        "issuer": "trusted_local_cli",
        "root": CapabilityRoot.USER,
        "agent_id": agent_id,
        "task_id": task_id,
        "linearity": Linearity.REUSABLE,
        "max_uses": 100,
        "uses": 0,
        "expires_at": "task_end",
    }
    if tool == "send_message":
        return (
            Capability(
                cap_id=f"{cap_prefix}_recipient",
                action_kind=ActionKind.SEND,
                tool="send_message",
                role=AuthorityRole.RECIPIENT,
                predicate={"op": "eq", "value": approved_scope["recipient"]},
                nonce=f"nonce:{cap_prefix}_recipient",
                **common,
            ),
        )
    if tool == "read_file":
        return (
            Capability(
                cap_id=f"{cap_prefix}_path",
                action_kind=ActionKind.READ,
                tool="read_file",
                role=AuthorityRole.FILE_PATH,
                predicate={"op": "eq", "value": approved_scope["path"]},
                nonce=f"nonce:{cap_prefix}_path",
                **common,
            ),
        )
    if tool == "write_file":
        return (
            Capability(
                cap_id=f"{cap_prefix}_path",
                action_kind=ActionKind.WRITE,
                tool="write_file",
                role=AuthorityRole.FILE_PATH,
                predicate={"op": "eq", "value": approved_scope["path"]},
                nonce=f"nonce:{cap_prefix}_path",
                **common,
            ),
        )
    if tool == "run_shell":
        return (
            Capability(
                cap_id=f"{cap_prefix}_template",
                action_kind=ActionKind.EXEC,
                tool="run_shell",
                role=AuthorityRole.COMMAND,
                predicate={"op": "eq", "value": approved_scope["template"]},
                nonce=f"nonce:{cap_prefix}_template",
                **common,
            ),
        )
    raise AuthorizationStoreError(f"unsupported requested tool for capability mint: {request.tool_name}")


def mint_approved_capabilities(
    store: AuthorizationStore,
    state: MonitorState,
    *,
    workspace: str | Path,
    task_id: str,
    agent_id: str,
) -> int:
    minted = 0
    for request in store.list_requests():
        if request.status != "approved" or request.approved_scope is None:
            continue
        for cap in capabilities_for_approved_request(
            request,
            request.approved_scope,
            workspace=workspace,
            task_id=task_id,
            agent_id=agent_id,
        ):
            if state.capability_store.lookup_capability(cap.cap_id) is not None:
                continue
            mint_capability(state.capability_store, cap)
            minted += 1
    return minted


def write_reports(store: AuthorizationStore) -> None:
    summary = store.summary()
    store.paths.summary_path.parent.mkdir(parents=True, exist_ok=True)
    store.paths.summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        "# CapProof ASK Authorization Queue Report",
        "",
        "This stage implements trusted local approval UX for MCP ASK requests.",
        "",
        "- ASK only creates a pending request.",
        "- ASK does not mint capability.",
        "- ASK does not execute an executor.",
        "- Pending requests include requested_action, requested_scope, canonical_action_hash, status, and expiry.",
        "- Only the trusted local CLI can approve, deny, or expire a request.",
        "- Trusted approve can mint only scoped capability matching the pending request.",
        "- Approval creates a redaction-safe approval receipt.",
        "- Deny and expire never mint capability.",
        "- Hermes, DeepSeek, MCP metadata, tool descriptions, annotations, `_meta`, clientInfo, and clientCapabilities cannot approve.",
        "- Approval scope amplification is rejected.",
        "- Replay approval is rejected.",
        "- Receipts and queue records are redaction-safe.",
        "- This does not modify CapProof core verifier or Reference Monitor semantics.",
        "",
        "## Summary",
        "",
        f"- request_count: {summary['request_count']}",
        f"- receipt_count: {summary['receipt_count']}",
        f"- status_counts: `{json.dumps(summary['status_counts'], sort_keys=True)}`",
        f"- pending_path: `{summary['pending_path']}`",
        f"- receipts_path: `{summary['receipts_path']}`",
        f"- audit_trace_path: `{summary['audit_trace_path']}`",
        "",
        "## Non-Claims",
        "",
        "- no production-level Hermes protection",
        "- no all Hermes tool paths covered",
        "- no OpenCode/OpenClaw real integration",
    ]
    store.paths.report_path.write_text("\n".join(report) + "\n", encoding="utf-8")


def _core_tool_name(tool_name: str) -> str:
    mapping = {
        "capproof.send_message_mock": "send_message",
        "capproof.read_workspace_file": "read_file",
        "capproof.write_workspace_file": "write_file",
        "capproof.run_command_template": "run_shell",
    }
    return mapping.get(tool_name, tool_name)


def _reject_unknown(scope: JsonObject, allowed: set[str]) -> None:
    unknown = set(scope) - allowed
    if unknown:
        raise AuthorizationStoreError(f"approved scope has unsupported fields: {sorted(unknown)}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
