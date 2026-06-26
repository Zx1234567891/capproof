"""Typed CapProof MVP schema objects.

These models are passive data structures. They do not implement verification,
capability minting, proof synthesis, or tool execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Self

from capproof.serialization import CanonicalModel, JsonObject, JsonValue, stable_hash


def _tuple_of_dicts(value: Any) -> tuple[JsonObject, ...]:
    return tuple(dict(item) for item in value)


def _tuple_of_strings(value: Any) -> tuple[str, ...]:
    return tuple(str(item) for item in value)


class CapabilityRoot(str, Enum):
    USER = "USER"
    POLICY = "POLICY"
    ENDORSEMENT = "ENDORSEMENT"
    DELEGATION = "DELEGATION"


class ActionKind(str, Enum):
    READ = "read"
    TRANSFORM = "transform"
    SEND = "send"
    WRITE = "write"
    EXEC = "exec"
    NET = "net"
    ENDORSE = "endorse"


class AuthorityRole(str, Enum):
    RECIPIENT = "recipient"
    FILE_PATH = "file_path"
    COMMAND = "command"
    EXTERNAL_ENDPOINT = "external_endpoint"
    DATA = "data"
    CONTROL = "control"
    NONE = "none"


class Linearity(str, Enum):
    REUSABLE = "reusable"
    AFFINE = "affine"
    LINEAR = "linear"


class CapabilityStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    CONSUMED = "consumed"
    REVOKED = "revoked"
    EXPIRED = "expired"


class BindingStatus(str, Enum):
    EXPLICIT = "explicit"
    USER_CONFIRMED = "user_confirmed"
    INFERRED = "inferred"


class ReceiptType(str, Enum):
    DERIVATION = "derivation"
    ENDORSEMENT = "endorsement"
    OUTCOME = "outcome"
    DELEGATION = "delegation"


class VerificationDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ASK = "ASK"


class DenyReason(str, Enum):
    UNKNOWN_TOOL = "UnknownTool"
    PROOF_NOT_CANONICAL = "ProofNotCanonical"
    CANONICALIZATION_MISMATCH = "CanonicalizationMismatch"
    ADAPTER_COVERAGE_GAP = "AdapterCoverageGap"
    NO_CAP = "NoCap"
    CAP_INVALID = "CapInvalid"
    EXPIRED_CAP = "ExpiredCap"
    REVOKED_CAP = "RevokedCap"
    CONSUMED_CAP = "ConsumedCap"
    RESERVED_CAP = "ReservedCap"
    CAP_PREDICATE_MISMATCH = "CapPredicateMismatch"
    TASK_MISMATCH = "TaskMismatch"
    AGENT_MISMATCH = "AgentMismatch"
    MEMORY_AUTHORITY_USE = "MemoryAuthorityUse"
    BAD_DERIVATION = "BadDerivation"
    UNAUTHORIZED_DATA_FLOW = "UnauthorizedDataFlow"
    DELEGATION_AMPLIFICATION = "DelegationAmplification"
    DATA_CLASS_MISMATCH = "DataClassMismatch"
    COMMAND_TEMPLATE_VIOLATION = "CommandTemplateViolation"
    TEMPLATE_ARG_REJECTED = "TemplateArgRejected"


@dataclass(frozen=True)
class AuthSpec(CanonicalModel):
    auth_id: str
    task_id: str
    principal: str
    intent: str
    resources: tuple[JsonObject, ...] = ()
    transforms: tuple[JsonObject, ...] = ()
    actions: tuple[JsonObject, ...] = ()
    forbidden: tuple[str, ...] = ()
    expires_at: str = "task_end"
    metadata: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            auth_id=str(data["auth_id"]),
            task_id=str(data["task_id"]),
            principal=str(data["principal"]),
            intent=str(data["intent"]),
            resources=_tuple_of_dicts(data.get("resources", ())),
            transforms=_tuple_of_dicts(data.get("transforms", ())),
            actions=_tuple_of_dicts(data.get("actions", ())),
            forbidden=_tuple_of_strings(data.get("forbidden", ())),
            expires_at=str(data.get("expires_at", "task_end")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class Capability(CanonicalModel):
    cap_id: str
    issuer: str
    root: CapabilityRoot
    agent_id: str
    task_id: str
    action_kind: ActionKind
    tool: str
    role: AuthorityRole
    predicate: JsonObject
    linearity: Linearity
    max_uses: int
    uses: int
    expires_at: str
    nonce: str
    delegable: bool = False
    transferable: bool = False
    persistent: bool = False
    parent_cap: str | None = None
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    key_id: str | None = None
    mac: str | None = None

    def __post_init__(self) -> None:
        if self.max_uses < 0:
            raise ValueError("max_uses must be non-negative")
        if self.uses < 0:
            raise ValueError("uses must be non-negative")
        if self.uses > self.max_uses:
            raise ValueError("uses cannot exceed max_uses")

    @property
    def subject_agent(self) -> str:
        return self.agent_id

    def handle(self) -> str:
        """Return the opaque runtime handle exposed outside the trusted store."""

        return self.cap_id

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            cap_id=str(data["cap_id"]),
            issuer=str(data["issuer"]),
            root=CapabilityRoot(data["root"]),
            agent_id=str(data["agent_id"]),
            task_id=str(data["task_id"]),
            action_kind=ActionKind(data["action_kind"]),
            tool=str(data["tool"]),
            role=AuthorityRole(data["role"]),
            predicate=dict(data["predicate"]),
            linearity=Linearity(data["linearity"]),
            max_uses=int(data["max_uses"]),
            uses=int(data["uses"]),
            expires_at=str(data["expires_at"]),
            nonce=str(data["nonce"]),
            delegable=bool(data.get("delegable", False)),
            transferable=bool(data.get("transferable", False)),
            persistent=bool(data.get("persistent", False)),
            parent_cap=data.get("parent_cap"),
            status=CapabilityStatus(data.get("status", CapabilityStatus.AVAILABLE.value)),
            key_id=data.get("key_id"),
            mac=data.get("mac"),
        )


@dataclass(frozen=True)
class ValueRef(CanonicalModel):
    value_id: str
    data_class: str
    provenance_root: str
    content_hash: str
    metadata: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            value_id=str(data["value_id"]),
            data_class=str(data["data_class"]),
            provenance_root=str(data["provenance_root"]),
            content_hash=str(data["content_hash"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class AuthorityField(CanonicalModel):
    name: str
    role: AuthorityRole
    required: bool = True
    high_impact: bool = True
    data_class: str | None = None
    access: str | None = None

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            name=str(data["name"]),
            role=AuthorityRole(data["role"]),
            required=bool(data.get("required", True)),
            high_impact=bool(data.get("high_impact", True)),
            data_class=data.get("data_class"),
            access=data.get("access"),
        )


@dataclass(frozen=True)
class ToolContract(CanonicalModel):
    tool: str
    args_schema: JsonObject
    authority: tuple[AuthorityField, ...]
    side_effects: tuple[str, ...] = ()
    coverage_fields: tuple[str, ...] = ()
    high_impact_fields: tuple[str, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            tool=str(data["tool"]),
            args_schema=dict(data.get("args_schema", {})),
            authority=tuple(AuthorityField.from_dict(item) for item in data.get("authority", ())),
            side_effects=_tuple_of_strings(data.get("side_effects", ())),
            coverage_fields=_tuple_of_strings(data.get("coverage_fields", ())),
            high_impact_fields=_tuple_of_strings(data.get("high_impact_fields", ())),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class Action(CanonicalModel):
    action_id: str
    task_id: str
    agent_id: str
    tool: str
    args: JsonObject
    value_refs: tuple[ValueRef, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def canonical_action(self) -> JsonObject:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "tool": self.tool,
            "args": self.args,
            "value_refs": [value_ref.to_dict() for value_ref in self.value_refs],
        }

    def action_hash(self) -> str:
        return stable_hash(self.canonical_action())

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            action_id=str(data["action_id"]),
            task_id=str(data["task_id"]),
            agent_id=str(data["agent_id"]),
            tool=str(data["tool"]),
            args=dict(data.get("args", {})),
            value_refs=tuple(ValueRef.from_dict(item) for item in data.get("value_refs", ())),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class Receipt(CanonicalModel):
    receipt_id: str
    receipt_type: ReceiptType
    task_id: str
    agent_id: str
    subject_hash: str
    payload: JsonObject
    issued_at: str
    key_id: str | None = None
    signature: str | None = None

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            receipt_id=str(data["receipt_id"]),
            receipt_type=ReceiptType(data["receipt_type"]),
            task_id=str(data["task_id"]),
            agent_id=str(data["agent_id"]),
            subject_hash=str(data["subject_hash"]),
            payload=dict(data.get("payload", {})),
            issued_at=str(data["issued_at"]),
            key_id=data.get("key_id"),
            signature=data.get("signature"),
        )


@dataclass(frozen=True)
class CapabilityUse(CanonicalModel):
    cap_id: str
    role: AuthorityRole
    reserved_nonce: str | None = None

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            cap_id=str(data["cap_id"]),
            role=AuthorityRole(data["role"]),
            reserved_nonce=data.get("reserved_nonce"),
        )


@dataclass(frozen=True)
class ArgBinding(CanonicalModel):
    arg: str
    canonical_value: JsonValue
    cap_id: str

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            arg=str(data["arg"]),
            canonical_value=data["canonical_value"],
            cap_id=str(data["cap_id"]),
        )


@dataclass(frozen=True)
class DerivationStep(CanonicalModel):
    output_class: str
    op: str
    inputs: tuple[str, ...]
    receipt_id: str

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            output_class=str(data["output_class"]),
            op=str(data["op"]),
            inputs=_tuple_of_strings(data.get("inputs", ())),
            receipt_id=str(data["receipt_id"]),
        )


@dataclass(frozen=True)
class Proof(CanonicalModel):
    proof_id: str
    action_hash: str
    authspec_ref: str
    capability_uses: tuple[CapabilityUse, ...] = ()
    arg_bindings: tuple[ArgBinding, ...] = ()
    derivation_steps: tuple[DerivationStep, ...] = ()
    receipts: tuple[str, ...] = ()
    delegation_chain: tuple[str, ...] = ()
    endorsement_chain: tuple[str, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def manifest(self) -> JsonObject:
        return {
            "action_hash": self.action_hash,
            "authspec_ref": self.authspec_ref,
            "capability_uses": [item.to_dict() for item in self.capability_uses],
            "arg_bindings": [item.to_dict() for item in self.arg_bindings],
            "derivation_steps": [item.to_dict() for item in self.derivation_steps],
            "receipts": list(self.receipts),
            "delegation_chain": list(self.delegation_chain),
            "endorsement_chain": list(self.endorsement_chain),
        }

    def proof_hash(self) -> str:
        return stable_hash(self.manifest())

    @classmethod
    def from_dict(cls, data: JsonObject) -> Self:
        return cls(
            proof_id=str(data["proof_id"]),
            action_hash=str(data["action_hash"]),
            authspec_ref=str(data["authspec_ref"]),
            capability_uses=tuple(
                CapabilityUse.from_dict(item) for item in data.get("capability_uses", ())
            ),
            arg_bindings=tuple(ArgBinding.from_dict(item) for item in data.get("arg_bindings", ())),
            derivation_steps=tuple(
                DerivationStep.from_dict(item) for item in data.get("derivation_steps", ())
            ),
            receipts=_tuple_of_strings(data.get("receipts", ())),
            delegation_chain=_tuple_of_strings(data.get("delegation_chain", ())),
            endorsement_chain=_tuple_of_strings(data.get("endorsement_chain", ())),
            metadata=dict(data.get("metadata", {})),
        )
