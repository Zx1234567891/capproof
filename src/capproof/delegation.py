"""Delegation certificates and attenuation checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from capproof.capability_store import CapabilityStore
from capproof.provenance import ProvenanceRuntime
from capproof.schemas import (
    ActionKind,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    DenyReason,
    JsonObject,
    Linearity,
    Receipt,
    VerificationDecision,
)
from capproof.serialization import CanonicalModel


class DelegationError(ValueError):
    """Raised when a delegation certificate fails attenuation checks."""


@dataclass(frozen=True)
class DelegationCheck:
    decision: VerificationDecision
    deny_reason: DenyReason | None = None
    message: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == VerificationDecision.ALLOW


@dataclass(frozen=True)
class DelegationCert(CanonicalModel):
    cert_id: str
    parent_agent: str
    child_agent: str
    parent_caps: tuple[str, ...]
    child_caps: tuple[str, ...]
    child_capability_specs: tuple[JsonObject, ...]
    delegated_scope: JsonObject
    expires_at: str
    non_redelegable: bool = True
    redelegation_allowed: bool = False
    signature: str | None = None

    @classmethod
    def from_dict(cls, data: JsonObject) -> "DelegationCert":
        return cls(
            cert_id=str(data["cert_id"]),
            parent_agent=str(data["parent_agent"]),
            child_agent=str(data["child_agent"]),
            parent_caps=tuple(str(item) for item in data.get("parent_caps", ())),
            child_caps=tuple(str(item) for item in data.get("child_caps", ())),
            child_capability_specs=tuple(dict(item) for item in data.get("child_capability_specs", ())),
            delegated_scope=dict(data.get("delegated_scope", {})),
            expires_at=str(data["expires_at"]),
            non_redelegable=bool(data.get("non_redelegable", True)),
            redelegation_allowed=bool(data.get("redelegation_allowed", False)),
            signature=data.get("signature"),
        )


def verify_delegation_attenuation(
    parent_capabilities: tuple[Capability, ...],
    cert: DelegationCert,
) -> DelegationCheck:
    parent_by_id = {cap.cap_id: cap for cap in parent_capabilities}
    if cert.redelegation_allowed and cert.non_redelegable:
        return _deny("non_redelegable certificate cannot allow redelegation")
    if tuple(spec.get("cap_id") for spec in cert.child_capability_specs) != cert.child_caps:
        return _deny("child_caps must match child capability specs")
    if not cert.child_capability_specs:
        return _deny("delegation certificate contains no child capabilities")
    for spec in cert.child_capability_specs:
        parent_cap_id = str(spec.get("parent_cap", ""))
        parent = parent_by_id.get(parent_cap_id)
        if parent is None:
            return _deny("child capability references missing parent cap")
        if parent.cap_id not in cert.parent_caps:
            return _deny("parent cap is not listed in certificate")
        if parent.agent_id != cert.parent_agent:
            return _deny("parent cap is not held by the delegating agent")
        if not parent.delegable:
            return _deny("parent cap is not delegable")
        result = _verify_child_spec(parent, cert, spec)
        if not result.allowed:
            return result
    return DelegationCheck(decision=VerificationDecision.ALLOW)


def mint_child_capabilities(
    *,
    parent_capabilities: tuple[Capability, ...],
    cert: DelegationCert,
    capability_store: CapabilityStore | None = None,
    issuer: str = "delegation_manager",
) -> tuple[Capability, ...]:
    check = verify_delegation_attenuation(parent_capabilities, cert)
    if not check.allowed:
        raise DelegationError(check.message)
    parent_by_id = {cap.cap_id: cap for cap in parent_capabilities}
    child_caps: list[Capability] = []
    for spec in cert.child_capability_specs:
        parent = parent_by_id[str(spec["parent_cap"])]
        child = Capability(
            cap_id=str(spec["cap_id"]),
            issuer=issuer,
            root=CapabilityRoot.DELEGATION,
            agent_id=cert.child_agent,
            task_id=parent.task_id,
            action_kind=ActionKind(spec.get("action_kind", parent.action_kind.value)),
            tool=str(spec.get("tool", parent.tool)),
            role=AuthorityRole(spec.get("role", parent.role.value)),
            predicate=dict(spec.get("predicate", parent.predicate)),
            linearity=Linearity(spec.get("linearity", parent.linearity.value)),
            max_uses=int(spec.get("max_uses", parent.max_uses)),
            uses=0,
            expires_at=str(spec.get("expires_at", cert.expires_at)),
            nonce=f"delegation:{cert.cert_id}:{spec['cap_id']}",
            delegable=bool(cert.redelegation_allowed and not cert.non_redelegable),
            transferable=False,
            persistent=False,
            parent_cap=parent.cap_id,
        )
        if capability_store is not None:
            child = capability_store.mint_capability(child)
        child_caps.append(child)
    return tuple(child_caps)


def record_delegation_receipt(
    runtime: ProvenanceRuntime,
    *,
    cert: DelegationCert,
    check: DelegationCheck | None = None,
) -> Receipt:
    result = check or DelegationCheck(decision=VerificationDecision.ALLOW)
    return runtime.record_delegation(
        parent_agent=cert.parent_agent,
        child_agent=cert.child_agent,
        parent_caps=cert.parent_caps,
        child_caps=cert.child_caps,
        delegated_scope={
            **cert.delegated_scope,
            "delegation_cert": cert.to_dict(),
            "attenuation_valid": result.allowed,
            "attenuation_deny_reason": result.deny_reason.value if result.deny_reason else None,
        },
    )


def delegation_from_message(message: str) -> None:
    """Natural-language delegation messages are not authority."""

    return None


def _verify_child_spec(
    parent: Capability,
    cert: DelegationCert,
    spec: JsonObject,
) -> DelegationCheck:
    child_role = AuthorityRole(spec.get("role", parent.role.value))
    if child_role != parent.role:
        return _deny("child cannot change authority role")
    child_tool = str(spec.get("tool", parent.tool))
    if parent.tool != "*" and child_tool != parent.tool:
        return _deny("child cannot add a new tool")
    child_action_kind = ActionKind(spec.get("action_kind", parent.action_kind.value))
    if child_action_kind != parent.action_kind:
        return _deny("child cannot change action kind")
    child_predicate = dict(spec.get("predicate", parent.predicate))
    if not _predicate_subset(parent.predicate, child_predicate):
        return _deny("child scope is not a subset of parent scope")
    if not _scope_fields_subset(parent, cert, child_predicate):
        return _deny("child adds authority outside delegated scope")
    child_expires_at = str(spec.get("expires_at", cert.expires_at))
    if not _ttl_lte(child_expires_at, parent.expires_at):
        return _deny("child TTL exceeds parent TTL")
    if not _ttl_lte(child_expires_at, cert.expires_at):
        return _deny("child TTL exceeds certificate TTL")
    if int(spec.get("max_uses", parent.max_uses)) > parent.max_uses:
        return _deny("child max_uses exceeds parent max_uses")
    if bool(spec.get("delegable", False)) and cert.non_redelegable:
        return _deny("child cannot redelegate under non_redelegable cert")
    return DelegationCheck(decision=VerificationDecision.ALLOW)


def _predicate_subset(parent: JsonObject, child: JsonObject) -> bool:
    if parent.get("data_class") is not None and child.get("data_class") != parent.get("data_class"):
        return False
    parent_op = parent.get("op")
    child_op = child.get("op")
    if parent_op == "eq":
        return child_op == "eq" and child.get("value") == parent.get("value")
    if parent_op == "in":
        parent_values = set(parent.get("values", ()))
        if child_op == "eq":
            return child.get("value") in parent_values
        if child_op == "in":
            return set(child.get("values", ())).issubset(parent_values)
    if parent_op == "subtree":
        parent_root = parent.get("root")
        child_root = child.get("root")
        if child_op != "subtree" or not isinstance(parent_root, str) or not isinstance(child_root, str):
            return False
        return child_root.startswith(parent_root.rstrip("/") + "/") or child_root == parent_root
    return False


def _scope_fields_subset(parent: Capability, cert: DelegationCert, child_predicate: JsonObject) -> bool:
    scope_value = cert.delegated_scope.get(parent.role.value)
    if scope_value is None:
        return True
    if parent.role in {
        AuthorityRole.RECIPIENT,
        AuthorityRole.EXTERNAL_ENDPOINT,
        AuthorityRole.COMMAND,
    }:
        return child_predicate.get("value") == scope_value
    if parent.role == AuthorityRole.FILE_PATH:
        root = child_predicate.get("root") or child_predicate.get("value")
        return isinstance(root, str) and (root == scope_value or root.startswith(str(scope_value).rstrip("/") + "/"))
    return True


def _ttl_lte(child_expires_at: str, parent_expires_at: str) -> bool:
    if child_expires_at == parent_expires_at:
        return True
    if parent_expires_at == "task_end":
        return child_expires_at != "task_end"
    if child_expires_at == "task_end":
        return False
    child_dt = _parse_time(child_expires_at)
    parent_dt = _parse_time(parent_expires_at)
    if child_dt is None or parent_dt is None:
        return False
    return child_dt <= parent_dt


def _parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _deny(message: str) -> DelegationCheck:
    return DelegationCheck(
        decision=VerificationDecision.DENY,
        deny_reason=DenyReason.DELEGATION_AMPLIFICATION,
        message=message,
    )
