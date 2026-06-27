"""Memory authority stripping for CapProof.

Memory stores facts and content. It does not become an authorization root by
default, and ordinary memory entries cannot mint capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Protocol

from capproof.capability_store import CapabilityStore
from capproof.provenance import ProvenanceRuntime
from capproof.schemas import (
    ActionKind,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    JsonObject,
    JsonValue,
    Linearity,
    ValueRef,
)
from capproof.serialization import CanonicalModel


class MemoryAuthorityError(ValueError):
    """Raised when memory content is incorrectly used as authority."""


@dataclass(frozen=True)
class MemoryEntry(CanonicalModel):
    key: str
    content: JsonValue
    provenance: ValueRef
    content_kind: str = "fact"
    authority_claims: JsonObject = field(default_factory=dict)
    stripped_authority: bool = False
    persistent_authority: bool = False
    metadata: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonObject) -> "MemoryEntry":
        return cls(
            key=str(data["key"]),
            content=data.get("content"),
            provenance=ValueRef.from_dict(data["provenance"]),
            content_kind=str(data.get("content_kind", "fact")),
            authority_claims=dict(data.get("authority_claims", {})),
            stripped_authority=bool(data.get("stripped_authority", False)),
            persistent_authority=bool(data.get("persistent_authority", False)),
            metadata=dict(data.get("metadata", {})),
        )


class MemoryStore(Protocol):
    def write(self, entry: MemoryEntry) -> MemoryEntry:
        """Write a memory entry after stripping authority."""

    def read(self, key: str) -> MemoryEntry | None:
        """Read a memory entry without trust upgrade."""


class InMemoryMemoryStore:
    """In-memory fact/content store with authority stripping."""

    def __init__(self, provenance_runtime: ProvenanceRuntime | None = None) -> None:
        self._entries: dict[str, MemoryEntry] = {}
        self._lock = RLock()
        self._provenance_runtime = provenance_runtime

    def write(self, entry: MemoryEntry) -> MemoryEntry:
        stripped = strip_authority(entry)
        if self._provenance_runtime is not None:
            receipt = self._provenance_runtime.record_memory_write(
                value=stripped.provenance,
                memory_key=stripped.key,
            )
            stripped = _with_provenance_receipt(stripped, receipt.receipt_id)
        with self._lock:
            self._entries[stripped.key] = stripped
            return stripped

    def read(self, key: str) -> MemoryEntry | None:
        with self._lock:
            entry = self._entries.get(key)
        if entry is None:
            return None
        if self._provenance_runtime is None:
            return entry
        value, _ = self._provenance_runtime.record_memory_read(
            stored_value=entry.provenance,
            memory_key=entry.key,
        )
        return MemoryEntry(
            key=entry.key,
            content=entry.content,
            provenance=value,
            content_kind=entry.content_kind,
            authority_claims=entry.authority_claims,
            stripped_authority=entry.stripped_authority,
            persistent_authority=entry.persistent_authority,
            metadata=entry.metadata,
        )


def strip_authority(memory_entry: MemoryEntry) -> MemoryEntry:
    if _is_explicit_persistent_authority(memory_entry):
        return MemoryEntry(
            key=memory_entry.key,
            content=memory_entry.content,
            provenance=memory_entry.provenance,
            content_kind=memory_entry.content_kind,
            authority_claims=dict(memory_entry.authority_claims),
            stripped_authority=False,
            persistent_authority=True,
            metadata=memory_entry.metadata,
        )
    provenance = _demote_memory_provenance(memory_entry.provenance)
    return MemoryEntry(
        key=memory_entry.key,
        content=memory_entry.content,
        provenance=provenance,
        content_kind=memory_entry.content_kind,
        authority_claims={},
        stripped_authority=bool(memory_entry.authority_claims),
        persistent_authority=False,
        metadata={
            **memory_entry.metadata,
            "stripped_authority_claims": dict(memory_entry.authority_claims),
        },
    )


def memory_write(store: MemoryStore, entry: MemoryEntry) -> MemoryEntry:
    return store.write(entry)


def memory_read(store: MemoryStore, key: str) -> MemoryEntry | None:
    return store.read(key)


def mint_persistent_authority_capability(
    *,
    memory_entry: MemoryEntry,
    capability_store: CapabilityStore,
    cap_id: str,
    issuer: str,
    agent_id: str,
    task_id: str,
    action_kind: ActionKind,
    tool: str,
    role: AuthorityRole,
    predicate: JsonObject,
    expires_at: str = "task_end",
    max_uses: int = 1,
) -> Capability:
    if not _is_explicit_persistent_authority(memory_entry):
        raise MemoryAuthorityError("memory entry is not explicit persistent endorsed authority")
    if memory_entry.stripped_authority:
        raise MemoryAuthorityError("stripped memory entry cannot mint authority")
    _validate_scope(memory_entry, role, predicate)
    capability = Capability(
        cap_id=cap_id,
        issuer=issuer,
        root=CapabilityRoot.ENDORSEMENT,
        agent_id=agent_id,
        task_id=task_id,
        action_kind=action_kind,
        tool=tool,
        role=role,
        predicate=predicate,
        linearity=Linearity.LINEAR,
        max_uses=max_uses,
        uses=0,
        expires_at=expires_at,
        nonce=f"memory:{memory_entry.key}",
        persistent=True,
        transferable=False,
        delegable=False,
    )
    return capability_store.mint_capability(capability)


def _is_explicit_persistent_authority(memory_entry: MemoryEntry) -> bool:
    return (
        memory_entry.persistent_authority
        and memory_entry.provenance.provenance_root == CapabilityRoot.ENDORSEMENT.value
        and bool(memory_entry.authority_claims)
    )


def _demote_memory_provenance(value: ValueRef) -> ValueRef:
    return ValueRef(
        value_id=value.value_id,
        data_class=value.data_class,
        provenance_root="UNENDORSED_MEMORY",
        content_hash=value.content_hash,
        origins=value.origins or (value.value_id,),
        receipt_ids=value.receipt_ids,
        metadata={
            **value.metadata,
            "original_provenance_root": value.provenance_root,
        },
    )


def _with_provenance_receipt(entry: MemoryEntry, receipt_id: str) -> MemoryEntry:
    if receipt_id in entry.provenance.receipt_ids:
        return entry
    provenance = ValueRef(
        value_id=entry.provenance.value_id,
        data_class=entry.provenance.data_class,
        provenance_root=entry.provenance.provenance_root,
        content_hash=entry.provenance.content_hash,
        origins=entry.provenance.origins,
        receipt_ids=(*entry.provenance.receipt_ids, receipt_id),
        metadata=entry.provenance.metadata,
    )
    return MemoryEntry(
        key=entry.key,
        content=entry.content,
        provenance=provenance,
        content_kind=entry.content_kind,
        authority_claims=entry.authority_claims,
        stripped_authority=entry.stripped_authority,
        persistent_authority=entry.persistent_authority,
        metadata=entry.metadata,
    )


def _validate_scope(memory_entry: MemoryEntry, role: AuthorityRole, predicate: JsonObject) -> None:
    claim = memory_entry.authority_claims.get(role.value)
    if claim is None:
        raise MemoryAuthorityError(f"memory endorsement lacks authority claim for role {role.value}")
    if predicate.get("op") != "eq":
        raise MemoryAuthorityError("persistent memory authority only supports scoped eq predicate")
    if predicate.get("value") != claim:
        raise MemoryAuthorityError("persistent memory authority predicate exceeds endorsed scope")
