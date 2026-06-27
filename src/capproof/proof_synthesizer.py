"""Proof synthesis for CapProof.

The synthesizer searches for a witness DAG. It is not a security boundary:
every synthesized proof is re-checked by the deterministic Reference Monitor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import capproof.monitor as monitor_module
from capproof.endorsement import check_endorsement_scope
from capproof.monitor import MonitorState, ReferenceMonitor, VerificationResult, canonical_action_hash
from capproof.schemas import (
    Action,
    ArgBinding,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    CapabilityStatus,
    CapabilityUse,
    DenyReason,
    DerivationStep,
    JsonObject,
    JsonValue,
    Linearity,
    Proof,
    Receipt,
    ReceiptType,
    VerificationDecision,
)
from capproof.serialization import CanonicalModel, stable_hash


class ProofFailureReason(str, Enum):
    UNKNOWN_TOOL = "UnknownTool"
    CANONICALIZATION_MISMATCH = "CanonicalizationMismatch"
    ADAPTER_COVERAGE_GAP = "AdapterCoverageGap"
    NO_CAP = "NoCap"
    ENDORSEMENT_REQUIRED = "EndorsementRequired"
    EXPIRED_CAP = "ExpiredCap"
    REVOKED_CAP = "RevokedCap"
    CONSUMED_CAP = "ConsumedCap"
    RESERVED_CAP = "ReservedCap"
    CAP_INVALID = "CapInvalid"
    TASK_MISMATCH = "TaskMismatch"
    AGENT_MISMATCH = "AgentMismatch"
    MEMORY_AUTHORITY_USE = "MemoryAuthorityUse"
    MISSING_RECEIPT = "MissingReceipt"
    DELEGATION_MISSING = "DelegationMissing"
    DELEGATION_AMPLIFICATION = "DelegationAmplification"
    ENDORSEMENT_SCOPE_ERROR = "EndorsementScopeError"
    DATA_CLASS_MISMATCH = "DataClassMismatch"
    VERIFIER_REJECTED = "VerifierRejected"


@dataclass(frozen=True)
class CapUse(CanonicalModel):
    cap_id: str
    role: AuthorityRole
    root: CapabilityRoot
    task_id: str
    agent_id: str
    predicate_hash: str
    linearity: Linearity
    max_uses: int
    uses: int
    status: CapabilityStatus
    reserved_nonce: str | None = None

    @classmethod
    def from_capability(cls, capability: Capability) -> "CapUse":
        return cls(
            cap_id=capability.cap_id,
            role=capability.role,
            root=capability.root,
            task_id=capability.task_id,
            agent_id=capability.agent_id,
            predicate_hash=stable_hash(capability.predicate),
            linearity=capability.linearity,
            max_uses=capability.max_uses,
            uses=capability.uses,
            status=capability.status,
        )

    @classmethod
    def from_dict(cls, data: JsonObject) -> "CapUse":
        return cls(
            cap_id=str(data["cap_id"]),
            role=AuthorityRole(data["role"]),
            root=CapabilityRoot(data["root"]),
            task_id=str(data["task_id"]),
            agent_id=str(data["agent_id"]),
            predicate_hash=str(data["predicate_hash"]),
            linearity=Linearity(data["linearity"]),
            max_uses=int(data["max_uses"]),
            uses=int(data["uses"]),
            status=CapabilityStatus(data["status"]),
            reserved_nonce=data.get("reserved_nonce"),
        )

    def to_capability_use(self) -> CapabilityUse:
        return CapabilityUse(
            cap_id=self.cap_id,
            role=self.role,
            reserved_nonce=self.reserved_nonce,
        )


@dataclass(frozen=True)
class ArgBindingProof(CanonicalModel):
    arg: str
    role: AuthorityRole
    canonical_value: JsonValue
    cap_id: str

    @classmethod
    def from_dict(cls, data: JsonObject) -> "ArgBindingProof":
        return cls(
            arg=str(data["arg"]),
            role=AuthorityRole(data["role"]),
            canonical_value=data["canonical_value"],
            cap_id=str(data["cap_id"]),
        )

    def to_arg_binding(self) -> ArgBinding:
        return ArgBinding(
            arg=self.arg,
            canonical_value=self.canonical_value,
            cap_id=self.cap_id,
        )


@dataclass(frozen=True)
class ProofDAG(CanonicalModel):
    proof_id: str
    action_hash: str
    authspec_ref: str
    arg_bindings: tuple[ArgBindingProof, ...] = ()
    cap_uses: tuple[CapUse, ...] = ()
    derivation_steps: tuple[DerivationStep, ...] = ()
    receipts: tuple[str, ...] = ()
    delegation_chain: tuple[str, ...] = ()
    endorsement_chain: tuple[str, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonObject) -> "ProofDAG":
        return cls(
            proof_id=str(data["proof_id"]),
            action_hash=str(data["action_hash"]),
            authspec_ref=str(data["authspec_ref"]),
            arg_bindings=tuple(
                ArgBindingProof.from_dict(dict(item)) for item in data.get("arg_bindings", ())
            ),
            cap_uses=tuple(CapUse.from_dict(dict(item)) for item in data.get("cap_uses", ())),
            derivation_steps=tuple(
                DerivationStep.from_dict(dict(item)) for item in data.get("derivation_steps", ())
            ),
            receipts=tuple(str(item) for item in data.get("receipts", ())),
            delegation_chain=tuple(str(item) for item in data.get("delegation_chain", ())),
            endorsement_chain=tuple(str(item) for item in data.get("endorsement_chain", ())),
            metadata=dict(data.get("metadata", {})),
        )

    def to_proof(self) -> Proof:
        return Proof(
            proof_id=self.proof_id,
            action_hash=self.action_hash,
            authspec_ref=self.authspec_ref,
            capability_uses=tuple(cap_use.to_capability_use() for cap_use in self.cap_uses),
            arg_bindings=tuple(binding.to_arg_binding() for binding in self.arg_bindings),
            derivation_steps=self.derivation_steps,
            receipts=self.receipts,
            delegation_chain=self.delegation_chain,
            endorsement_chain=self.endorsement_chain,
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class ProofSynthesisResult(CanonicalModel):
    decision: VerificationDecision
    proof_dag: ProofDAG | None = None
    proof: Proof | None = None
    failure_reason: ProofFailureReason | None = None
    verifier_result: VerificationResult | None = None
    message: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == VerificationDecision.ALLOW

    @classmethod
    def from_dict(cls, data: JsonObject) -> "ProofSynthesisResult":
        verifier_data = data.get("verifier_result")
        return cls(
            decision=VerificationDecision(data["decision"]),
            proof_dag=ProofDAG.from_dict(dict(data["proof_dag"])) if data.get("proof_dag") else None,
            proof=Proof.from_dict(dict(data["proof"])) if data.get("proof") else None,
            failure_reason=(
                ProofFailureReason(data["failure_reason"]) if data.get("failure_reason") else None
            ),
            verifier_result=_verification_result_from_dict(dict(verifier_data))
            if isinstance(verifier_data, dict)
            else None,
            message=str(data.get("message", "")),
        )


def synthesize_proof(
    action: Action,
    state: MonitorState,
    *,
    authspec_ref: str = "synthesized",
) -> ProofSynthesisResult:
    contract = state.tool_contracts.get(action.tool)
    if contract is None:
        return _failure(ProofFailureReason.UNKNOWN_TOOL, "unknown tool")
    canonical = monitor_module._canonicalize_action(action, contract, state.canonicalizer)
    if not canonical.allowed or canonical.args is None:
        return _failure(
            _failure_from_deny(canonical.deny_reason or DenyReason.CANONICALIZATION_MISMATCH),
            canonical.message,
        )
    if monitor_module._has_memory_authority(action):
        return _failure(ProofFailureReason.MEMORY_AUTHORITY_USE, "memory value used as authority")

    action_hash = canonical_action_hash(action, canonical.args)
    claims = monitor_module._authority_claims(contract, canonical.args)
    arg_bindings: list[ArgBindingProof] = []
    cap_uses: list[CapUse] = []
    delegation_chain: list[str] = []
    endorsement_chain: list[str] = []

    for claim in claims:
        selected = _select_capability_for_claim(
            action=action,
            state=state,
            claim=claim,
            action_hash=action_hash,
        )
        if not selected.allowed or selected.capability is None:
            return _failure(selected.failure_reason or ProofFailureReason.NO_CAP, selected.message)
        cap = selected.capability
        arg_bindings.append(
            ArgBindingProof(
                arg=claim.field,
                role=claim.role,
                canonical_value=claim.value,
                cap_id=cap.cap_id,
            )
        )
        cap_uses.append(CapUse.from_capability(cap))
        _extend_unique(delegation_chain, selected.delegation_chain)
        _extend_unique(endorsement_chain, selected.endorsement_chain)

    content = _collect_content_evidence(action, contract, canonical.args, state)
    if not content.allowed:
        return _failure(content.failure_reason or ProofFailureReason.MISSING_RECEIPT, content.message)

    proof_dag = ProofDAG(
        proof_id=f"proof_synth_{stable_hash({'action_hash': action_hash, 'bindings': [b.to_dict() for b in arg_bindings]})[:16]}",
        action_hash=action_hash,
        authspec_ref=authspec_ref,
        arg_bindings=tuple(arg_bindings),
        cap_uses=tuple(cap_uses),
        derivation_steps=content.derivation_steps,
        receipts=content.receipts,
        delegation_chain=tuple(delegation_chain),
        endorsement_chain=tuple(endorsement_chain),
        metadata={"synthesizer": "capproof.proof_synthesizer.v1"},
    )
    proof = proof_dag.to_proof()
    verifier_result = ReferenceMonitor().verify(action, proof, state)
    if not verifier_result.allowed:
        return ProofSynthesisResult(
            decision=VerificationDecision.DENY,
            proof_dag=proof_dag,
            proof=proof,
            failure_reason=_failure_from_deny(
                verifier_result.deny_reason,
                default=ProofFailureReason.VERIFIER_REJECTED,
            ),
            verifier_result=verifier_result,
            message="synthesized proof rejected by verifier",
        )
    return ProofSynthesisResult(
        decision=VerificationDecision.ALLOW,
        proof_dag=proof_dag,
        proof=proof,
        verifier_result=verifier_result,
    )


@dataclass(frozen=True)
class _CapSelection:
    allowed: bool
    capability: Capability | None = None
    failure_reason: ProofFailureReason | None = None
    message: str = ""
    delegation_chain: tuple[str, ...] = ()
    endorsement_chain: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ContentEvidence:
    allowed: bool
    receipts: tuple[str, ...] = ()
    derivation_steps: tuple[DerivationStep, ...] = ()
    failure_reason: ProofFailureReason | None = None
    message: str = ""


def _select_capability_for_claim(
    *,
    action: Action,
    state: MonitorState,
    claim: monitor_module.AuthorityClaim,
    action_hash: str,
) -> _CapSelection:
    candidates = tuple(
        cap
        for cap in _list_capabilities(state)
        if _cap_shape_matches_action(cap, action, claim) and monitor_module._predicate_matches(cap, claim.value)
    )
    if not candidates:
        if _endorsement_is_requested(action, claim.field):
            return _cap_failure(ProofFailureReason.ENDORSEMENT_REQUIRED, "endorsement required")
        return _cap_failure(ProofFailureReason.NO_CAP, "no matching capability")

    failures: list[ProofFailureReason] = []
    for cap in sorted(candidates, key=_cap_sort_key):
        validation = state.capability_store.validate_capability(
            cap.cap_id,
            task_id=action.task_id,
            agent_id=action.agent_id,
            require_available=True,
        )
        if not validation.allowed or validation.capability is None:
            failures.append(_failure_from_deny(validation.deny_reason))
            continue
        checked_cap = validation.capability
        if checked_cap.root == CapabilityRoot.DELEGATION:
            delegation = _delegation_chain_for_cap(checked_cap, state)
            if not delegation.allowed:
                failures.append(delegation.failure_reason or ProofFailureReason.DELEGATION_MISSING)
                continue
            return _CapSelection(
                allowed=True,
                capability=checked_cap,
                delegation_chain=delegation.delegation_chain,
            )
        if checked_cap.root == CapabilityRoot.ENDORSEMENT:
            endorsement = _endorsement_chain_for_cap(
                cap=checked_cap,
                action=action,
                state=state,
                claim=claim,
                action_hash=action_hash,
            )
            if not endorsement.allowed:
                failures.append(endorsement.failure_reason or ProofFailureReason.ENDORSEMENT_SCOPE_ERROR)
                continue
            return _CapSelection(
                allowed=True,
                capability=checked_cap,
                endorsement_chain=endorsement.endorsement_chain,
            )
        return _CapSelection(allowed=True, capability=checked_cap)
    return _cap_failure(_prioritize_failures(failures), "no usable capability")


def _list_capabilities(state: MonitorState) -> tuple[Capability, ...]:
    if hasattr(state.capability_store, "list_capabilities"):
        return state.capability_store.list_capabilities()
    return tuple(getattr(state.capability_store, "_caps", {}).values())


def _list_receipts(state: MonitorState) -> tuple[Receipt, ...]:
    if hasattr(state.receipt_store, "list_receipts"):
        return state.receipt_store.list_receipts()
    return tuple(getattr(state.receipt_store, "_receipts", {}).values())


def _cap_shape_matches_action(
    cap: Capability,
    action: Action,
    claim: monitor_module.AuthorityClaim,
) -> bool:
    return (
        cap.role == claim.role
        and cap.task_id == action.task_id
        and cap.agent_id == action.agent_id
        and cap.tool in {action.tool, "*"}
    )


def _cap_sort_key(cap: Capability) -> tuple[int, str]:
    root_priority = {
        CapabilityRoot.USER: 0,
        CapabilityRoot.POLICY: 1,
        CapabilityRoot.ENDORSEMENT: 2,
        CapabilityRoot.DELEGATION: 3,
    }
    status_priority = 0 if cap.status == CapabilityStatus.AVAILABLE else 1
    use_priority = 0 if cap.uses < cap.max_uses else 1
    return (status_priority, use_priority, root_priority.get(cap.root, 9), cap.cap_id)


@dataclass(frozen=True)
class _DelegationEvidence:
    allowed: bool
    delegation_chain: tuple[str, ...] = ()
    failure_reason: ProofFailureReason | None = None


def _delegation_chain_for_cap(cap: Capability, state: MonitorState) -> _DelegationEvidence:
    for receipt in _list_receipts(state):
        if receipt.receipt_type != ReceiptType.DELEGATION:
            continue
        scope = receipt.payload.get("delegated_scope", {})
        if not isinstance(scope, dict):
            return _DelegationEvidence(False, failure_reason=ProofFailureReason.DELEGATION_AMPLIFICATION)
        if scope.get("attenuation_valid") is False:
            return _DelegationEvidence(False, failure_reason=ProofFailureReason.DELEGATION_AMPLIFICATION)
        child_caps = receipt.payload.get("child_caps", ())
        if cap.cap_id not in child_caps:
            continue
        allowed_value = scope.get(cap.role.value)
        predicate_value = cap.predicate.get("value")
        if allowed_value is not None and predicate_value != allowed_value:
            return _DelegationEvidence(False, failure_reason=ProofFailureReason.DELEGATION_AMPLIFICATION)
        return _DelegationEvidence(True, delegation_chain=(receipt.receipt_id,))
    return _DelegationEvidence(False, failure_reason=ProofFailureReason.DELEGATION_MISSING)


@dataclass(frozen=True)
class _EndorsementEvidence:
    allowed: bool
    endorsement_chain: tuple[str, ...] = ()
    failure_reason: ProofFailureReason | None = None


def _endorsement_chain_for_cap(
    *,
    cap: Capability,
    action: Action,
    state: MonitorState,
    claim: monitor_module.AuthorityClaim,
    action_hash: str,
) -> _EndorsementEvidence:
    failures: list[ProofFailureReason] = []
    for receipt in _list_receipts(state):
        if receipt.receipt_type != ReceiptType.ENDORSEMENT:
            continue
        if receipt.payload.get("cap_id") != cap.cap_id:
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
            return _EndorsementEvidence(True, endorsement_chain=(receipt.receipt_id,))
        failures.append(_failure_from_deny(check.deny_reason))
    return _EndorsementEvidence(
        False,
        failure_reason=_prioritize_failures(failures, default=ProofFailureReason.ENDORSEMENT_SCOPE_ERROR),
    )


def _collect_content_evidence(
    action: Action,
    contract: object,
    canonical_args: JsonObject,
    state: MonitorState,
) -> _ContentEvidence:
    content_bindings = action.metadata.get("content_bindings", {})
    if not isinstance(content_bindings, dict):
        return _content_failure(ProofFailureReason.MISSING_RECEIPT, "content_bindings must be a map")
    refs = {value_ref.value_id: value_ref for value_ref in action.value_refs}
    receipt_ids: list[str] = []
    derivation_steps: list[DerivationStep] = []
    required_content_fields = tuple(
        field.name
        for field in contract.authority
        if field.role == AuthorityRole.CONTENT
        and field.name in canonical_args
        and canonical_args[field.name] not in (None, "", [], {})
    )
    for field_name in required_content_fields:
        value_id = content_bindings.get(field_name)
        if not isinstance(value_id, str) or value_id not in refs:
            return _content_failure(ProofFailureReason.MISSING_RECEIPT, "missing content value")
        value_ref = refs[value_id]
        if not value_ref.receipt_ids:
            return _content_failure(ProofFailureReason.MISSING_RECEIPT, "missing content receipts")
        for receipt_id in value_ref.receipt_ids:
            receipt = state.receipt_store.lookup(receipt_id)
            if receipt is None:
                return _content_failure(ProofFailureReason.MISSING_RECEIPT, "unknown content receipt")
            _append_unique(receipt_ids, receipt_id)
            step = _derivation_step_from_receipt(receipt)
            if step is not None:
                derivation_steps.append(step)
    return _ContentEvidence(
        allowed=True,
        receipts=tuple(receipt_ids),
        derivation_steps=tuple(derivation_steps),
    )


def _derivation_step_from_receipt(receipt: Receipt) -> DerivationStep | None:
    if receipt.receipt_type != ReceiptType.DERIVATION:
        return None
    output_value = receipt.payload.get("output_value", {})
    if not isinstance(output_value, dict):
        return None
    return DerivationStep(
        output_class=str(output_value.get("data_class", "")),
        op=str(receipt.payload.get("op", "")),
        inputs=tuple(str(item) for item in receipt.payload.get("input_value_ids", ())),
        receipt_id=receipt.receipt_id,
    )


def _endorsement_is_requested(action: Action, field: str) -> bool:
    fields = action.metadata.get("endorsement_required_fields")
    if isinstance(fields, list | tuple | set):
        return field in fields
    if action.metadata.get("endorsement_required") is True:
        return True
    return False


def _prioritize_failures(
    failures: list[ProofFailureReason],
    *,
    default: ProofFailureReason = ProofFailureReason.NO_CAP,
) -> ProofFailureReason:
    if not failures:
        return default
    priority = (
        ProofFailureReason.CONSUMED_CAP,
        ProofFailureReason.RESERVED_CAP,
        ProofFailureReason.REVOKED_CAP,
        ProofFailureReason.EXPIRED_CAP,
        ProofFailureReason.DELEGATION_AMPLIFICATION,
        ProofFailureReason.DELEGATION_MISSING,
        ProofFailureReason.DATA_CLASS_MISMATCH,
        ProofFailureReason.ENDORSEMENT_SCOPE_ERROR,
        ProofFailureReason.TASK_MISMATCH,
        ProofFailureReason.AGENT_MISMATCH,
        ProofFailureReason.CAP_INVALID,
    )
    for reason in priority:
        if reason in failures:
            return reason
    return failures[0]


def _failure_from_deny(
    reason: DenyReason | None,
    *,
    default: ProofFailureReason = ProofFailureReason.VERIFIER_REJECTED,
) -> ProofFailureReason:
    if reason is None:
        return default
    try:
        return ProofFailureReason(reason.value)
    except ValueError:
        return default


def _failure(reason: ProofFailureReason, message: str) -> ProofSynthesisResult:
    return ProofSynthesisResult(
        decision=VerificationDecision.DENY,
        failure_reason=reason,
        message=message,
    )


def _cap_failure(reason: ProofFailureReason, message: str) -> _CapSelection:
    return _CapSelection(allowed=False, failure_reason=reason, message=message)


def _content_failure(reason: ProofFailureReason, message: str) -> _ContentEvidence:
    return _ContentEvidence(allowed=False, failure_reason=reason, message=message)


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _extend_unique(items: list[str], values: tuple[str, ...]) -> None:
    for value in values:
        _append_unique(items, value)


def _verification_result_from_dict(data: JsonObject) -> VerificationResult:
    deny_reason = data.get("deny_reason")
    return VerificationResult(
        decision=VerificationDecision(data["decision"]),
        deny_reason=DenyReason(deny_reason) if deny_reason else None,
        message=str(data.get("message", "")),
        canonical_action_hash=data.get("canonical_action_hash"),
    )
