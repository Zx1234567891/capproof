"""Trusted local authorization receipts for MCP ASK approvals.

These receipts are product-layer audit artifacts. They do not change the
Reference Monitor, proof model, or capability store semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from capproof.serialization import JsonObject, stable_hash


SECRET_KEYS = ("api_key", "apikey", "token", "secret", "password", "credential")


@dataclass(frozen=True)
class AuthorizationReceipt:
    receipt_id: str
    request_id: str
    status: str
    approved_scope: JsonObject
    capability_ids: tuple[str, ...]
    canonical_action_hash: str
    trace_id: str
    approved_by: str
    issued_at: str

    def to_dict(self) -> JsonObject:
        return {
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "status": self.status,
            "approved_scope": redact_json(self.approved_scope),
            "capability_ids": list(self.capability_ids),
            "canonical_action_hash": self.canonical_action_hash,
            "trace_id": self.trace_id,
            "approved_by": self.approved_by,
            "issued_at": self.issued_at,
        }

    @classmethod
    def from_dict(cls, data: JsonObject) -> "AuthorizationReceipt":
        return cls(
            receipt_id=str(data["receipt_id"]),
            request_id=str(data["request_id"]),
            status=str(data.get("status", "approved")),
            approved_scope=dict(data.get("approved_scope", {})),
            capability_ids=tuple(str(item) for item in data.get("capability_ids", ())),
            canonical_action_hash=str(data.get("canonical_action_hash", "")),
            trace_id=str(data.get("trace_id", "")),
            approved_by=str(data.get("approved_by", "trusted_local_cli")),
            issued_at=str(data.get("issued_at", "")),
        )


def make_receipt_id(payload: JsonObject) -> str:
    return f"authreceipt_{stable_hash(payload)[:20]}"


def redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: JsonObject = {}
        for key, item in value.items():
            lowered = key.lower()
            if any(marker in lowered for marker in SECRET_KEYS):
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = redact_json(item)
        return redacted
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, tuple):
        return [redact_json(item) for item in value]
    return value
