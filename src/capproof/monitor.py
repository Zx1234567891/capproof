"""Deterministic Reference Monitor for CapProof.

The monitor is the final allow/deny boundary. It does not call model APIs,
execute tools, or trust prose explanations in a proof object.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from capproof.canonicalizer import Canonicalizer
from capproof.capability_store import CapabilityStore
from capproof.contracts import ToolContractRegistry
from capproof.endorsement import check_endorsement_scope
from capproof.receipts import ReceiptStore
from capproof.schemas import (
    Action,
    ArgBinding,
    AuthorityField,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    DenyReason,
    JsonObject,
    JsonValue,
    Linearity,
    Proof,
    ReceiptType,
    ToolContract,
    VerificationDecision,
)
from capproof.serialization import stable_hash

UNTRUSTED_AUTHORITY_ROOTS = frozenset(
    {
        "UNENDORSED_MEMORY",
        "UNENDORSED_MEMORY_DERIVED",
        "MEMORY",
        "MEMORY_DERIVED",
        "WEBPAGE",
        "WEBPAGE_DERIVED",
        "EXTERNAL",
        "EXTERNAL_DERIVED",
    }
)


@dataclass(frozen=True)
class MonitorState:
    capability_store: CapabilityStore
    receipt_store: ReceiptStore
    tool_contracts: ToolContractRegistry
    canonicalizer: Canonicalizer


@dataclass(frozen=True)
class VerificationResult:
    decision: VerificationDecision
    deny_reason: DenyReason | None = None
    message: str = ""
    canonical_action_hash: str | None = None

    @property
    def allowed(self) -> bool:
        return self.decision == VerificationDecision.ALLOW


@dataclass(frozen=True)
class AuthorityClaim:
    field: str
    role: AuthorityRole
    value: JsonValue
    high_impact: bool


@dataclass(frozen=True)
class _CanonicalActionResult:
    allowed: bool
    args: JsonObject | None = None
    deny_reason: DenyReason | None = None
    message: str = ""


@dataclass(frozen=True)
class _CanonicalValueResult:
    allowed: bool
    value: JsonValue | None = None
    deny_reason: DenyReason | None = None
    message: str = ""


class ReferenceMonitor:
    """Deterministic verifier over action, proof, stores, and contracts."""

    def verify(self, action: Action, proof: Proof, state: MonitorState) -> VerificationResult:
        contract = state.tool_contracts.get(action.tool)
        if contract is None:
            return _deny(DenyReason.UNKNOWN_TOOL, "unknown tool")
        canonical = _canonicalize_action(action, contract, state.canonicalizer)
        if not canonical.allowed or canonical.args is None:
            return _deny(
                canonical.deny_reason or DenyReason.CANONICALIZATION_MISMATCH,
                canonical.message,
            )
        canonical_args = canonical.args
        action_hash = canonical_action_hash(action, canonical_args)
        if proof.action_hash != action_hash:
            return _deny(
                DenyReason.CANONICALIZATION_MISMATCH,
                "proof action_hash does not match canonical action",
                action_hash,
            )
        if _has_memory_authority(action):
            return _deny(DenyReason.MEMORY_AUTHORITY_USE, "memory value used as authority", action_hash)
        claims = _authority_claims(contract, canonical_args)
        bindings = _bindings_by_field(proof.arg_bindings)
        for claim in claims:
            result = self._verify_authority_claim(action, proof, state, claim, bindings, action_hash)
            if not result.allowed:
                return result
        content_result = _verify_content_receipts(action, proof, contract, canonical_args, state, action_hash)
        if not content_result.allowed:
            return content_result
        return VerificationResult(
            decision=VerificationDecision.ALLOW,
            canonical_action_hash=action_hash,
        )

    def _verify_authority_claim(
        self,
        action: Action,
        proof: Proof,
        state: MonitorState,
        claim: AuthorityClaim,
        bindings: dict[str, list[ArgBinding]],
        action_hash: str,
    ) -> VerificationResult:
        binding = _find_binding(bindings, claim)
        if binding is None:
            return _deny(
                DenyReason.MISSING_ARG_BINDING,
                f"missing proof binding for {claim.field}",
                action_hash,
            )
        check = state.capability_store.validate_capability(
            binding.cap_id,
            task_id=action.task_id,
            agent_id=action.agent_id,
            require_available=True,
        )
        if not check.allowed or check.capability is None:
            return _deny(check.deny_reason or DenyReason.NO_CAP, check.message, action_hash)
        cap = check.capability
        if cap.role != claim.role:
            return _deny(DenyReason.SOURCE_MISMATCH, "capability role does not match arg role", action_hash)
        if cap.tool not in {action.tool, "*"}:
            return _deny(DenyReason.SOURCE_MISMATCH, "capability tool does not match action", action_hash)
        if not _predicate_matches(cap, claim.value):
            return _deny(DenyReason.CAP_PREDICATE_MISMATCH, "capability predicate mismatch", action_hash)
        if cap.root == CapabilityRoot.DELEGATION:
            result = _verify_delegation(cap, proof, state, action_hash)
            if not result.allowed:
                return result
        if cap.root == CapabilityRoot.ENDORSEMENT:
            result = _verify_endorsement(cap, proof, state, action, claim, action_hash)
            if not result.allowed:
                return result
        if claim.high_impact and cap.linearity in {Linearity.AFFINE, Linearity.LINEAR}:
            if cap.uses >= cap.max_uses:
                return _deny(DenyReason.CONSUMED_CAP, "capability is consumed", action_hash)
        return VerificationResult(VerificationDecision.ALLOW, canonical_action_hash=action_hash)


def verify(action: Action, proof: Proof, state: MonitorState) -> VerificationResult:
    return ReferenceMonitor().verify(action, proof, state)


def canonical_action_hash(action: Action, canonical_args: JsonObject) -> str:
    return stable_hash(
        {
            "task_id": action.task_id,
            "agent_id": action.agent_id,
            "tool": action.tool,
            "args": canonical_args,
            "value_refs": [value_ref.to_dict() for value_ref in action.value_refs],
        }
    )


def _canonicalize_action(
    action: Action,
    contract: ToolContract,
    canonicalizer: Canonicalizer,
) -> _CanonicalActionResult:
    allowed_fields = set(contract.args_schema.get("properties", {}))
    extra = set(action.args) - allowed_fields
    if extra:
        return _canonical_deny(DenyReason.ADAPTER_COVERAGE_GAP, "action contains undeclared fields")
    canonical_args: JsonObject = dict(action.args)
    if action.tool == "run_shell":
        shell_result = canonicalizer.canonicalize_run_shell(
            command_template=str(action.args.get("command_template", "")),
            args=action.args.get("args", {}),
            cwd=str(action.args.get("cwd", "")),
            env=action.args.get("env", {}),
            stdin=action.args.get("stdin"),
        )
        if not shell_result.allowed:
            return _canonical_deny(
                shell_result.deny_reason or DenyReason.COMMAND_TEMPLATE_VIOLATION,
                shell_result.message,
            )
    for field in contract.authority:
        if field.name not in action.args or action.args[field.name] in (None, [], {}):
            continue
        value = action.args[field.name]
        if field.role == AuthorityRole.RECIPIENT:
            converted = _canonicalize_recipient_value(value, canonicalizer)
        elif field.role == AuthorityRole.FILE_PATH:
            converted = _canonicalize_path_value(value, canonicalizer)
        elif field.role == AuthorityRole.EXTERNAL_ENDPOINT:
            converted = _canonicalize_endpoint_value(value, canonicalizer)
        else:
            converted = _canonical_value_allow(value)
        if field.role in {
            AuthorityRole.RECIPIENT,
            AuthorityRole.FILE_PATH,
            AuthorityRole.EXTERNAL_ENDPOINT,
        }:
            if not converted.allowed:
                return _canonical_deny(
                    converted.deny_reason or DenyReason.CANONICALIZATION_MISMATCH,
                    converted.message,
                )
            canonical_args[field.name] = converted.value
    return _canonical_action_allow(canonical_args)


def _canonicalize_recipient_value(value: Any, canonicalizer: Canonicalizer) -> _CanonicalValueResult:
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            result = canonicalizer.canonicalize_recipient(item)
            if not result.allowed or result.value is None:
                return _canonical_value_deny(DenyReason.CANONICALIZATION_MISMATCH, result.message)
            items.append(str(result.value))
        return _canonical_value_allow(items)
    result = canonicalizer.canonicalize_recipient(value)
    if not result.allowed or result.value is None:
        return _canonical_value_deny(DenyReason.CANONICALIZATION_MISMATCH, result.message)
    return _canonical_value_allow(str(result.value))


def _canonicalize_path_value(value: Any, canonicalizer: Canonicalizer) -> _CanonicalValueResult:
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            result = canonicalizer.canonicalize_file_path(item)
            if not result.allowed or result.value is None:
                return _canonical_value_deny(
                    result.deny_reason or DenyReason.CANONICALIZATION_MISMATCH,
                    result.message,
                )
            items.append(str(result.value))
        return _canonical_value_allow(items)
    result = canonicalizer.canonicalize_file_path(value)
    if not result.allowed or result.value is None:
        return _canonical_value_deny(
            result.deny_reason or DenyReason.CANONICALIZATION_MISMATCH,
            result.message,
        )
    return _canonical_value_allow(str(result.value))


def _canonicalize_endpoint_value(value: Any, canonicalizer: Canonicalizer) -> _CanonicalValueResult:
    result = canonicalizer.canonicalize_endpoint(value)
    if not result.allowed or result.value is None:
        return _canonical_value_deny(
            result.deny_reason or DenyReason.CANONICALIZATION_MISMATCH,
            result.message,
        )
    return _canonical_value_allow(str(result.value))


def _authority_claims(contract: ToolContract, canonical_args: JsonObject) -> tuple[AuthorityClaim, ...]:
    claims: list[AuthorityClaim] = []
    for field in contract.authority:
        if field.role == AuthorityRole.CONTENT or not field.high_impact:
            continue
        if field.name not in canonical_args or canonical_args[field.name] in (None, [], {}):
            continue
        value = canonical_args[field.name]
        if isinstance(value, list):
            claims.extend(
                AuthorityClaim(field=field.name, role=field.role, value=item, high_impact=field.high_impact)
                for item in value
            )
        else:
            claims.append(
                AuthorityClaim(
                    field=field.name,
                    role=field.role,
                    value=value,
                    high_impact=field.high_impact,
                )
            )
    return tuple(claims)


def _bindings_by_field(bindings: tuple[ArgBinding, ...]) -> dict[str, list[ArgBinding]]:
    result: dict[str, list[ArgBinding]] = {}
    for binding in bindings:
        result.setdefault(binding.arg, []).append(binding)
    return result


def _find_binding(bindings: dict[str, list[ArgBinding]], claim: AuthorityClaim) -> ArgBinding | None:
    for binding in bindings.get(claim.field, ()):
        if binding.canonical_value == claim.value:
            return binding
    return None


def _predicate_matches(cap: Capability, value: JsonValue) -> bool:
    predicate = cap.predicate
    op = predicate.get("op")
    if op == "eq":
        return predicate.get("value") == value
    if op == "in":
        values = predicate.get("values", ())
        return value in values
    if op == "subtree":
        root = predicate.get("root")
        if not isinstance(root, str) or not isinstance(value, str):
            return False
        try:
            Path(value).resolve(strict=False).relative_to(Path(root).resolve(strict=False))
            return True
        except ValueError:
            return False
    return False


def _verify_content_receipts(
    action: Action,
    proof: Proof,
    contract: ToolContract,
    canonical_args: JsonObject,
    state: MonitorState,
    action_hash: str,
) -> VerificationResult:
    content_bindings = action.metadata.get("content_bindings", {})
    if not isinstance(content_bindings, dict):
        return _deny(DenyReason.MISSING_RECEIPT, "content_bindings must be a map", action_hash)
    required_content_fields = tuple(
        field.name
        for field in contract.authority
        if field.role == AuthorityRole.CONTENT
        and field.name in canonical_args
        and canonical_args[field.name] not in (None, "", [], {})
    )
    refs = {value_ref.value_id: value_ref for value_ref in action.value_refs}
    for field_name in required_content_fields:
        value_id = content_bindings.get(field_name)
        if not isinstance(value_id, str) or value_id not in refs:
            return _deny(DenyReason.MISSING_RECEIPT, f"missing content value for {field_name}", action_hash)
        value_ref = refs[value_id]
        if not value_ref.receipt_ids:
            return _deny(DenyReason.MISSING_RECEIPT, f"missing receipts for {field_name}", action_hash)
        for receipt_id in value_ref.receipt_ids:
            if receipt_id not in proof.receipts:
                return _deny(DenyReason.MISSING_RECEIPT, f"proof does not reference {receipt_id}", action_hash)
            if state.receipt_store.lookup(receipt_id) is None:
                return _deny(DenyReason.MISSING_RECEIPT, f"unknown receipt {receipt_id}", action_hash)
    return VerificationResult(VerificationDecision.ALLOW, canonical_action_hash=action_hash)


def _verify_delegation(
    cap: Capability,
    proof: Proof,
    state: MonitorState,
    action_hash: str,
) -> VerificationResult:
    if not proof.delegation_chain:
        return _deny(DenyReason.DELEGATION_MISSING, "delegated cap lacks delegation receipt", action_hash)
    for receipt_id in proof.delegation_chain:
        receipt = state.receipt_store.lookup(receipt_id)
        if receipt is None:
            return _deny(DenyReason.MISSING_RECEIPT, "missing delegation receipt", action_hash)
        if receipt.receipt_type != ReceiptType.DELEGATION:
            continue
        scope = receipt.payload.get("delegated_scope", {})
        if not isinstance(scope, dict):
            return _deny(DenyReason.DELEGATION_AMPLIFICATION, "delegated scope malformed", action_hash)
        if scope.get("attenuation_valid") is False:
            return _deny(DenyReason.DELEGATION_AMPLIFICATION, "delegation attenuation invalid", action_hash)
        child_caps = receipt.payload.get("child_caps", ())
        if cap.cap_id not in child_caps:
            continue
        allowed_value = scope.get(cap.role.value)
        predicate_value = cap.predicate.get("value")
        if allowed_value is not None and predicate_value != allowed_value:
            return _deny(DenyReason.DELEGATION_AMPLIFICATION, "delegated scope exceeded", action_hash)
        return VerificationResult(VerificationDecision.ALLOW, canonical_action_hash=action_hash)
    return _deny(DenyReason.DELEGATION_MISSING, "cap not covered by delegation chain", action_hash)


def _verify_endorsement(
    cap: Capability,
    proof: Proof,
    state: MonitorState,
    action: Action,
    claim: AuthorityClaim,
    action_hash: str,
) -> VerificationResult:
    if not proof.endorsement_chain:
        return _deny(DenyReason.ENDORSEMENT_SCOPE_ERROR, "endorsement receipt missing", action_hash)
    last_result: VerificationResult | None = None
    for receipt_id in proof.endorsement_chain:
        receipt = state.receipt_store.lookup(receipt_id)
        if receipt is None:
            return _deny(DenyReason.MISSING_RECEIPT, "missing endorsement receipt", action_hash)
        if receipt.receipt_type != ReceiptType.ENDORSEMENT:
            continue
        check = check_endorsement_scope(
            capability=cap,
            receipt=receipt,
            action=action,
            action_hash=action_hash,
            claim_field=claim.field,
            claim_role=claim.role,
            claim_value=claim.value,
        )
        if check.allowed:
            return VerificationResult(VerificationDecision.ALLOW, canonical_action_hash=action_hash)
        last_result = _deny(
            check.deny_reason or DenyReason.ENDORSEMENT_SCOPE_ERROR,
            check.message,
            action_hash,
        )
        if check.deny_reason == DenyReason.DATA_CLASS_MISMATCH:
            return last_result
    return last_result or _deny(
        DenyReason.ENDORSEMENT_SCOPE_ERROR,
        "cap not covered by endorsement chain",
        action_hash,
    )


def _has_memory_authority(action: Action) -> bool:
    arg_provenance = action.metadata.get("arg_provenance", {})
    if not isinstance(arg_provenance, dict):
        return False
    return any(str(root).upper() in UNTRUSTED_AUTHORITY_ROOTS for root in arg_provenance.values())


def _canonical_action_allow(args: JsonObject) -> _CanonicalActionResult:
    return _CanonicalActionResult(allowed=True, args=args)


def _canonical_deny(reason: DenyReason, message: str) -> _CanonicalActionResult:
    return _CanonicalActionResult(allowed=False, deny_reason=reason, message=message)


def _canonical_value_allow(value: JsonValue) -> _CanonicalValueResult:
    return _CanonicalValueResult(allowed=True, value=value)


def _canonical_value_deny(reason: DenyReason, message: str) -> _CanonicalValueResult:
    return _CanonicalValueResult(allowed=False, deny_reason=reason, message=message)


def _deny(
    reason: DenyReason,
    message: str,
    action_hash: str | None = None,
) -> VerificationResult:
    return VerificationResult(
        decision=VerificationDecision.DENY,
        deny_reason=reason,
        message=message,
        canonical_action_hash=action_hash,
    )
