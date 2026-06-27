"""Controlled one-shot endorsement for CapProof."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from capproof.capability_store import CapabilityCheck, CapabilityStore, consume_capability, reserve_capability
from capproof.canonicalizer import Canonicalizer
from capproof.contracts import ToolContractRegistry
from capproof.provenance import ProvenanceRuntime
from capproof.schemas import (
    Action,
    ActionKind,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    DenyReason,
    JsonObject,
    JsonValue,
    Linearity,
    Receipt,
    ReceiptType,
    ToolContract,
    VerificationDecision,
)
from capproof.serialization import CanonicalModel, stable_hash


class EndorsementError(ValueError):
    """Raised when an endorsement challenge/response cannot mint authority."""


@dataclass(frozen=True)
class EndorsementCheck:
    decision: VerificationDecision
    deny_reason: DenyReason | None = None
    message: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == VerificationDecision.ALLOW


@dataclass(frozen=True)
class EndorsementChallenge(CanonicalModel):
    challenge_id: str
    task_id: str
    agent_id: str
    action_hash: str
    action_kind: ActionKind
    tool: str
    field: str
    role: AuthorityRole
    canonical_value: JsonValue
    data_class: str
    canonical_action: JsonObject
    one_shot: bool = True
    transferable: bool = False
    persistent: bool = False

    def challenge_text(self) -> str:
        scope_label = _scope_label(self.role)
        return "\n".join(
            (
                "CapProof needs approval for one high-impact action.",
                f"Task: {self.task_id}",
                f"Action: {self.action_kind.value} via {self.tool}",
                f"{scope_label}: {self.canonical_value}",
                f"Data: {self.data_class}",
                "One-time: exactly one use for this task; non-transferable; non-persistent.",
                "Approve once or deny.",
            )
        )

    @classmethod
    def from_dict(cls, data: JsonObject) -> "EndorsementChallenge":
        return cls(
            challenge_id=str(data["challenge_id"]),
            task_id=str(data["task_id"]),
            agent_id=str(data["agent_id"]),
            action_hash=str(data["action_hash"]),
            action_kind=ActionKind(data["action_kind"]),
            tool=str(data["tool"]),
            field=str(data["field"]),
            role=AuthorityRole(data["role"]),
            canonical_value=data["canonical_value"],
            data_class=str(data["data_class"]),
            canonical_action=dict(data["canonical_action"]),
            one_shot=bool(data.get("one_shot", True)),
            transferable=bool(data.get("transferable", False)),
            persistent=bool(data.get("persistent", False)),
        )


@dataclass(frozen=True)
class EndorsementResponse(CanonicalModel):
    challenge_id: str
    task_id: str
    agent_id: str
    action_hash: str
    approved_by: str
    approved: bool

    @classmethod
    def approve(cls, challenge: EndorsementChallenge, *, approved_by: str) -> "EndorsementResponse":
        return cls(
            challenge_id=challenge.challenge_id,
            task_id=challenge.task_id,
            agent_id=challenge.agent_id,
            action_hash=challenge.action_hash,
            approved_by=approved_by,
            approved=True,
        )

    @classmethod
    def deny(cls, challenge: EndorsementChallenge, *, approved_by: str) -> "EndorsementResponse":
        return cls(
            challenge_id=challenge.challenge_id,
            task_id=challenge.task_id,
            agent_id=challenge.agent_id,
            action_hash=challenge.action_hash,
            approved_by=approved_by,
            approved=False,
        )

    @classmethod
    def from_dict(cls, data: JsonObject) -> "EndorsementResponse":
        return cls(
            challenge_id=str(data["challenge_id"]),
            task_id=str(data["task_id"]),
            agent_id=str(data["agent_id"]),
            action_hash=str(data["action_hash"]),
            approved_by=str(data["approved_by"]),
            approved=bool(data["approved"]),
        )


@dataclass(frozen=True)
class EndorsementGrant(CanonicalModel):
    capability: Capability
    receipt: Receipt

    @classmethod
    def from_dict(cls, data: JsonObject) -> "EndorsementGrant":
        return cls(
            capability=Capability.from_dict(dict(data["capability"])),
            receipt=Receipt.from_dict(dict(data["receipt"])),
        )


class EndorsementManager:
    """Mint scoped, one-shot endorsement capabilities from explicit responses."""

    def __init__(
        self,
        *,
        capability_store: CapabilityStore,
        provenance_runtime: ProvenanceRuntime,
        tool_contracts: ToolContractRegistry,
        canonicalizer: Canonicalizer,
        issuer: str = "endorsement_manager",
    ) -> None:
        self.capability_store = capability_store
        self.provenance_runtime = provenance_runtime
        self.tool_contracts = tool_contracts
        self.canonicalizer = canonicalizer
        self.issuer = issuer
        self._counter = 0
        self._challenges: dict[str, EndorsementChallenge] = {}

    def create_challenge(
        self,
        action: Action,
        *,
        field: str,
        role: AuthorityRole | None = None,
        data_class: str | None = None,
        action_kind: ActionKind | None = None,
    ) -> EndorsementChallenge:
        contract = self.tool_contracts.require(action.tool)
        authority_field = _require_authority_field(contract, field)
        expected_role = role or authority_field.role
        if authority_field.role != expected_role:
            raise EndorsementError("challenge role does not match tool contract field")
        canonical_args = _canonicalize_action_args(action, contract, self.canonicalizer)
        if field not in canonical_args:
            raise EndorsementError("challenge field is absent from action")
        canonical_value = canonical_args[field]
        if canonical_value in (None, "", [], {}):
            raise EndorsementError("challenge field has no authority-bearing value")
        resolved_data_class = data_class or _single_action_data_class(action)
        self._counter += 1
        action_hash = stable_hash(
            {
                "task_id": action.task_id,
                "agent_id": action.agent_id,
                "tool": action.tool,
                "args": canonical_args,
                "value_refs": [value_ref.to_dict() for value_ref in action.value_refs],
            }
        )
        challenge = EndorsementChallenge(
            challenge_id=f"endorsement_challenge_{self._counter:06d}",
            task_id=action.task_id,
            agent_id=action.agent_id,
            action_hash=action_hash,
            action_kind=action_kind or _infer_action_kind(action.tool),
            tool=action.tool,
            field=field,
            role=expected_role,
            canonical_value=canonical_value,
            data_class=resolved_data_class,
            canonical_action={
                "task_id": action.task_id,
                "agent_id": action.agent_id,
                "tool": action.tool,
                "args": canonical_args,
                "value_refs": [value_ref.to_dict() for value_ref in action.value_refs],
            },
        )
        self._challenges[challenge.challenge_id] = challenge
        return challenge

    def mint_endorsement_capability(
        self,
        response: EndorsementResponse,
        *,
        cap_id: str | None = None,
        expires_at: str = "task_end",
    ) -> EndorsementGrant:
        challenge = self._challenges.get(response.challenge_id)
        if challenge is None:
            raise EndorsementError("unknown endorsement challenge")
        return mint_endorsement_capability(
            challenge=challenge,
            response=response,
            capability_store=self.capability_store,
            provenance_runtime=self.provenance_runtime,
            issuer=self.issuer,
            cap_id=cap_id,
            expires_at=expires_at,
        )

    def consume_endorsement_capability(
        self,
        capability: Capability,
        *,
        action_hash: str,
        reservation_nonce: str | None = None,
    ) -> CapabilityCheck:
        nonce = reservation_nonce or f"endorsement-use:{action_hash}"
        reserved = reserve_capability(
            self.capability_store,
            capability.cap_id,
            task_id=capability.task_id,
            agent_id=capability.agent_id,
            reservation_nonce=nonce,
        )
        if not reserved.allowed:
            return reserved
        consumed = consume_capability(
            self.capability_store,
            capability.cap_id,
            task_id=capability.task_id,
            agent_id=capability.agent_id,
            reservation_nonce=nonce,
        )
        if consumed.allowed and consumed.capability is not None:
            self.provenance_runtime.record_cap_consume(
                capability=consumed.capability,
                action_hash=action_hash,
            )
        return consumed


def mint_endorsement_capability(
    *,
    challenge: EndorsementChallenge,
    response: EndorsementResponse,
    capability_store: CapabilityStore,
    provenance_runtime: ProvenanceRuntime,
    issuer: str = "endorsement_manager",
    cap_id: str | None = None,
    expires_at: str = "task_end",
) -> EndorsementGrant:
    _validate_response(challenge, response)
    capability = Capability(
        cap_id=cap_id or _cap_id(challenge, response),
        issuer=issuer,
        root=CapabilityRoot.ENDORSEMENT,
        agent_id=challenge.agent_id,
        task_id=challenge.task_id,
        action_kind=challenge.action_kind,
        tool=challenge.tool,
        role=challenge.role,
        predicate={
            "op": "eq",
            "value": challenge.canonical_value,
            "data_class": challenge.data_class,
            "action_hash": challenge.action_hash,
        },
        linearity=Linearity.LINEAR,
        max_uses=1,
        uses=0,
        expires_at=expires_at,
        nonce=f"endorsement:{challenge.challenge_id}",
        delegable=False,
        transferable=False,
        persistent=False,
    )
    capability = capability_store.mint_capability(capability)
    receipt = record_endorsement_receipt(
        provenance_runtime,
        challenge=challenge,
        response=response,
        capability=capability,
    )
    provenance_runtime.record_cap_mint(capability=capability)
    return EndorsementGrant(capability=capability, receipt=receipt)


def record_endorsement_receipt(
    runtime: ProvenanceRuntime,
    *,
    challenge: EndorsementChallenge,
    response: EndorsementResponse,
    capability: Capability,
) -> Receipt:
    _validate_response(challenge, response)
    return runtime.record_endorsement(
        challenge_id=challenge.challenge_id,
        action_hash=challenge.action_hash,
        approved_by=response.approved_by,
        canonical_action=challenge.canonical_action,
        cap_id=capability.cap_id,
        scope=_scope_payload(challenge),
    )


def check_endorsement_scope(
    *,
    capability: Capability,
    receipt: Receipt,
    action: Action,
    action_hash: str,
    claim_field: str,
    claim_role: AuthorityRole,
    claim_value: JsonValue,
) -> EndorsementCheck:
    if capability.root != CapabilityRoot.ENDORSEMENT:
        return _deny("capability is not endorsement-rooted")
    if capability.linearity != Linearity.LINEAR or capability.max_uses != 1:
        return _deny("endorsement capability must be one-shot linear")
    if capability.transferable or capability.persistent or capability.delegable:
        return _deny("endorsement capability must be non-transferable, non-persistent, non-delegable")
    expected_data_class = capability.predicate.get("data_class")
    if expected_data_class is not None:
        data_classes = action_data_classes(action)
        if not data_classes or any(data_class != expected_data_class for data_class in data_classes):
            return EndorsementCheck(
                decision=VerificationDecision.DENY,
                deny_reason=DenyReason.DATA_CLASS_MISMATCH,
                message="endorsement data_class mismatch",
            )
    expected_action_hash = capability.predicate.get("action_hash")
    if expected_action_hash is not None and expected_action_hash != action_hash:
        return _deny("endorsement action_hash mismatch")
    if receipt.receipt_type != ReceiptType.ENDORSEMENT:
        return _deny("receipt is not an endorsement")
    if receipt.task_id != capability.task_id or receipt.task_id != action.task_id:
        return EndorsementCheck(
            decision=VerificationDecision.DENY,
            deny_reason=DenyReason.TASK_MISMATCH,
            message="endorsement receipt task_id mismatch",
        )
    if receipt.agent_id != capability.agent_id or receipt.agent_id != action.agent_id:
        return EndorsementCheck(
            decision=VerificationDecision.DENY,
            deny_reason=DenyReason.AGENT_MISMATCH,
            message="endorsement receipt agent_id mismatch",
        )
    if receipt.payload.get("cap_id") != capability.cap_id:
        return _deny("endorsement receipt cap_id mismatch")
    if receipt.payload.get("action_hash") != action_hash:
        return _deny("endorsement receipt action_hash mismatch")
    scope = receipt.payload.get("scope")
    if not isinstance(scope, dict):
        return _deny("endorsement receipt lacks structured scope")
    if scope.get("task_id") != action.task_id or scope.get("agent_id") != action.agent_id:
        return _deny("endorsement scope task/agent mismatch")
    if scope.get("field") != claim_field or scope.get("role") != claim_role.value:
        return _deny("endorsement authority field mismatch")
    if scope.get("canonical_value") != claim_value:
        return _deny("endorsement canonical value mismatch")
    if expected_data_class is not None and scope.get("data_class") != expected_data_class:
        return EndorsementCheck(
            decision=VerificationDecision.DENY,
            deny_reason=DenyReason.DATA_CLASS_MISMATCH,
            message="endorsement receipt data_class mismatch",
        )
    if scope.get("one_shot") is not True or scope.get("transferable") is not False:
        return _deny("endorsement scope is not one-shot non-transferable")
    if scope.get("persistent") is not False:
        return _deny("endorsement scope is persistent")
    return EndorsementCheck(decision=VerificationDecision.ALLOW)


def action_data_classes(action: Action) -> tuple[str, ...]:
    value_by_id = {value.value_id: value for value in action.value_refs}
    content_bindings = action.metadata.get("content_bindings", {})
    ids: list[str] = []
    if isinstance(content_bindings, dict):
        for value_id in content_bindings.values():
            if isinstance(value_id, str) and value_id not in ids:
                ids.append(value_id)
    if not ids:
        ids = [value.value_id for value in action.value_refs]
    classes: list[str] = []
    for value_id in ids:
        value = value_by_id.get(value_id)
        if value is not None and value.data_class not in classes:
            classes.append(value.data_class)
    return tuple(classes)


def _validate_response(challenge: EndorsementChallenge, response: EndorsementResponse) -> None:
    if not response.approved:
        raise EndorsementError("endorsement response was denied")
    if response.challenge_id != challenge.challenge_id:
        raise EndorsementError("endorsement response challenge_id mismatch")
    if response.task_id != challenge.task_id:
        raise EndorsementError("endorsement response task_id mismatch")
    if response.agent_id != challenge.agent_id:
        raise EndorsementError("endorsement response agent_id mismatch")
    if response.action_hash != challenge.action_hash:
        raise EndorsementError("endorsement response action_hash mismatch")
    if not response.approved_by:
        raise EndorsementError("endorsement response approved_by must be non-empty")


def _cap_id(challenge: EndorsementChallenge, response: EndorsementResponse) -> str:
    digest = stable_hash(
        {
            "challenge_id": challenge.challenge_id,
            "action_hash": challenge.action_hash,
            "approved_by": response.approved_by,
        }
    )
    return f"cap_endorse_{digest[:24]}"


def _scope_payload(challenge: EndorsementChallenge) -> JsonObject:
    return {
        "task_id": challenge.task_id,
        "agent_id": challenge.agent_id,
        "action_hash": challenge.action_hash,
        "action_kind": challenge.action_kind.value,
        "tool": challenge.tool,
        "field": challenge.field,
        "role": challenge.role.value,
        "canonical_value": challenge.canonical_value,
        "data_class": challenge.data_class,
        "one_shot": challenge.one_shot,
        "transferable": challenge.transferable,
        "persistent": challenge.persistent,
    }


def _single_action_data_class(action: Action) -> str:
    data_classes = action_data_classes(action)
    if len(data_classes) != 1:
        raise EndorsementError("endorsement challenge requires an exact data_class")
    return data_classes[0]


def _require_authority_field(contract: ToolContract, field: str) -> Any:
    for authority_field in contract.authority:
        if authority_field.name == field:
            return authority_field
    raise EndorsementError("challenge field is not authority-bearing in the tool contract")


def _canonicalize_action_args(
    action: Action,
    contract: ToolContract,
    canonicalizer: Canonicalizer,
) -> JsonObject:
    allowed_fields = set(contract.args_schema.get("properties", {}))
    extra = set(action.args) - allowed_fields
    if extra:
        raise EndorsementError("action contains undeclared fields")
    canonical_args: JsonObject = dict(action.args)
    for field in contract.authority:
        if field.name not in action.args or action.args[field.name] in (None, [], {}):
            continue
        value = action.args[field.name]
        if field.role == AuthorityRole.RECIPIENT:
            canonical_args[field.name] = _canonicalize_recipient_value(value, canonicalizer)
        elif field.role == AuthorityRole.FILE_PATH:
            canonical_args[field.name] = _canonicalize_path_value(value, canonicalizer)
        elif field.role == AuthorityRole.EXTERNAL_ENDPOINT:
            canonical_args[field.name] = _canonicalize_endpoint_value(value, canonicalizer)
    return canonical_args


def _canonicalize_recipient_value(value: Any, canonicalizer: Canonicalizer) -> JsonValue:
    if isinstance(value, list):
        return [_require_canonical(canonicalizer.canonicalize_recipient(item)) for item in value]
    return _require_canonical(canonicalizer.canonicalize_recipient(value))


def _canonicalize_path_value(value: Any, canonicalizer: Canonicalizer) -> JsonValue:
    if isinstance(value, list):
        return [_require_canonical(canonicalizer.canonicalize_file_path(item)) for item in value]
    return _require_canonical(canonicalizer.canonicalize_file_path(value))


def _canonicalize_endpoint_value(value: Any, canonicalizer: Canonicalizer) -> JsonValue:
    return _require_canonical(canonicalizer.canonicalize_endpoint(value))


def _require_canonical(result: Any) -> JsonValue:
    if not result.allowed or result.value is None:
        raise EndorsementError(result.message)
    return result.value


def _infer_action_kind(tool: str) -> ActionKind:
    if tool == "send_email":
        return ActionKind.SEND
    if tool == "write_file":
        return ActionKind.WRITE
    if tool == "read_file":
        return ActionKind.READ
    if tool == "run_shell":
        return ActionKind.EXEC
    return ActionKind.NET


def _scope_label(role: AuthorityRole) -> str:
    if role == AuthorityRole.RECIPIENT:
        return "Recipient"
    if role == AuthorityRole.EXTERNAL_ENDPOINT:
        return "Endpoint"
    if role == AuthorityRole.COMMAND:
        return "Command"
    if role == AuthorityRole.FILE_PATH:
        return "File path"
    return role.value


def _deny(message: str) -> EndorsementCheck:
    return EndorsementCheck(
        decision=VerificationDecision.DENY,
        deny_reason=DenyReason.ENDORSEMENT_SCOPE_ERROR,
        message=message,
    )
