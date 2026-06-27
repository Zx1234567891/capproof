"""Provenance runtime for values and receipts.

This module records provenance metadata only. It does not perform tool
execution, authorization, endorsement validation, or delegation validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from typing import Any

from capproof.receipts import InMemoryReceiptStore, ReceiptStore
from capproof.schemas import Capability, JsonObject, Receipt, ReceiptType, ValueRef
from capproof.serialization import canonical_json, stable_hash

TRUSTED_PROVENANCE_ROOTS = frozenset({"USER", "POLICY", "ENDORSEMENT", "DELEGATION"})


@dataclass
class ProvenanceRuntime:
    task_id: str
    agent_id: str
    receipt_store: ReceiptStore

    def __init__(
        self,
        *,
        task_id: str,
        agent_id: str,
        receipt_store: ReceiptStore | None = None,
    ) -> None:
        self.task_id = task_id
        self.agent_id = agent_id
        self.receipt_store = receipt_store or InMemoryReceiptStore()
        self._counter = 0

    def record_tool_in(
        self,
        *,
        tool: str,
        inputs: tuple[ValueRef, ...],
        args: JsonObject | None = None,
    ) -> Receipt:
        return self._append_receipt(
            ReceiptType.TOOL_IN,
            payload={
                "tool": tool,
                "args": args or {},
                "input_value_ids": [value.value_id for value in inputs],
                "input_receipts": _unique_receipt_ids(inputs),
            },
            parent_receipt_ids=_unique_receipt_ids(inputs),
        )

    def record_tool_out(
        self,
        *,
        tool: str,
        output_id: str,
        data_class: str,
        content: Any,
        inputs: tuple[ValueRef, ...] = (),
        provenance_root: str | None = None,
    ) -> tuple[ValueRef, Receipt]:
        parent_receipts = _unique_receipt_ids(inputs)
        root = provenance_root or _derive_root(inputs)
        value_without_receipt = ValueRef(
            value_id=output_id,
            data_class=data_class,
            provenance_root=root,
            content_hash=_content_hash(content),
            origins=_derive_origins(inputs, output_id),
            receipt_ids=parent_receipts,
            metadata={"tool": tool},
        )
        receipt = self._append_receipt(
            ReceiptType.TOOL_OUT,
            payload={
                "tool": tool,
                "output_value": value_without_receipt.to_dict(),
                "input_value_ids": [value.value_id for value in inputs],
            },
            parent_receipt_ids=parent_receipts,
        )
        value = _with_receipt(value_without_receipt, receipt.receipt_id)
        return value, receipt

    def record_memory_write(self, *, value: ValueRef, memory_key: str) -> Receipt:
        return self._append_receipt(
            ReceiptType.MEMORY_WRITE,
            payload={
                "memory_key": memory_key,
                "value": value.to_dict(),
                "trust_root_preserved": value.provenance_root,
            },
            parent_receipt_ids=value.receipt_ids,
        )

    def record_memory_read(self, *, stored_value: ValueRef, memory_key: str) -> tuple[ValueRef, Receipt]:
        receipt = self._append_receipt(
            ReceiptType.MEMORY_READ,
            payload={
                "memory_key": memory_key,
                "stored_value_id": stored_value.value_id,
                "provenance_root": stored_value.provenance_root,
            },
            parent_receipt_ids=stored_value.receipt_ids,
        )
        value = _with_receipt(stored_value, receipt.receipt_id)
        return value, receipt

    def record_cap_mint(self, *, capability: Capability) -> Receipt:
        return self._append_receipt(
            ReceiptType.CAP_MINT,
            payload={
                "cap_id": capability.cap_id,
                "root": capability.root.value,
                "role": capability.role.value,
                "tool": capability.tool,
            },
            parent_receipt_ids=(),
        )

    def record_cap_consume(
        self,
        *,
        capability: Capability,
        action_hash: str,
    ) -> Receipt:
        return self._append_receipt(
            ReceiptType.CAP_CONSUME,
            payload={
                "cap_id": capability.cap_id,
                "uses": capability.uses,
                "max_uses": capability.max_uses,
                "action_hash": action_hash,
            },
            parent_receipt_ids=(),
        )

    def record_endorsement(
        self,
        *,
        challenge_id: str,
        action_hash: str,
        approved_by: str,
        canonical_action: JsonObject,
        cap_id: str | None = None,
        scope: JsonObject | None = None,
    ) -> Receipt:
        payload: JsonObject = {
            "challenge_id": challenge_id,
            "action_hash": action_hash,
            "approved_by": approved_by,
            "canonical_action": canonical_action,
        }
        if cap_id is not None:
            payload["cap_id"] = cap_id
        if scope is not None:
            payload["scope"] = scope
        return self._append_receipt(
            ReceiptType.ENDORSEMENT,
            payload=payload,
            parent_receipt_ids=(),
        )

    def record_delegation(
        self,
        *,
        parent_agent: str,
        child_agent: str,
        parent_caps: tuple[str, ...],
        child_caps: tuple[str, ...],
        delegated_scope: JsonObject,
    ) -> Receipt:
        return self._append_receipt(
            ReceiptType.DELEGATION,
            payload={
                "parent_agent": parent_agent,
                "child_agent": child_agent,
                "parent_caps": list(parent_caps),
                "child_caps": list(child_caps),
                "delegated_scope": delegated_scope,
            },
            parent_receipt_ids=(),
        )

    def derive_value(
        self,
        *,
        op: str,
        inputs: tuple[ValueRef, ...],
        output_id: str,
        data_class: str,
        content: Any,
    ) -> tuple[ValueRef, Receipt]:
        parent_receipts = _unique_receipt_ids(inputs)
        value_without_receipt = ValueRef(
            value_id=output_id,
            data_class=data_class,
            provenance_root=_derive_root(inputs),
            content_hash=_content_hash(content),
            origins=_derive_origins(inputs, output_id),
            receipt_ids=parent_receipts,
            metadata={
                "derived_by": op,
                "input_value_ids": [value.value_id for value in inputs],
            },
        )
        receipt = self._append_receipt(
            ReceiptType.DERIVATION,
            payload={
                "op": op,
                "output_value": value_without_receipt.to_dict(),
                "input_value_ids": [value.value_id for value in inputs],
            },
            parent_receipt_ids=parent_receipts,
        )
        value = _with_receipt(value_without_receipt, receipt.receipt_id)
        return value, receipt

    def _append_receipt(
        self,
        receipt_type: ReceiptType,
        *,
        payload: JsonObject,
        parent_receipt_ids: tuple[str, ...],
    ) -> Receipt:
        self._counter += 1
        issued_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        subject_hash = stable_hash(
            {
                "receipt_type": receipt_type.value,
                "task_id": self.task_id,
                "agent_id": self.agent_id,
                "payload": payload,
                "parents": list(parent_receipt_ids),
            }
        )
        receipt = Receipt(
            receipt_id=f"receipt_{self._counter:06d}",
            receipt_type=receipt_type,
            task_id=self.task_id,
            agent_id=self.agent_id,
            subject_hash=subject_hash,
            payload=payload,
            issued_at=issued_at,
            parent_receipt_ids=parent_receipt_ids,
        )
        return self.receipt_store.append(receipt)


def record_tool_in(
    runtime: ProvenanceRuntime,
    *,
    tool: str,
    inputs: tuple[ValueRef, ...],
    args: JsonObject | None = None,
) -> Receipt:
    return runtime.record_tool_in(tool=tool, inputs=inputs, args=args)


def record_tool_out(
    runtime: ProvenanceRuntime,
    *,
    tool: str,
    output_id: str,
    data_class: str,
    content: Any,
    inputs: tuple[ValueRef, ...] = (),
    provenance_root: str | None = None,
) -> tuple[ValueRef, Receipt]:
    return runtime.record_tool_out(
        tool=tool,
        output_id=output_id,
        data_class=data_class,
        content=content,
        inputs=inputs,
        provenance_root=provenance_root,
    )


def record_memory_write(runtime: ProvenanceRuntime, *, value: ValueRef, memory_key: str) -> Receipt:
    return runtime.record_memory_write(value=value, memory_key=memory_key)


def record_memory_read(
    runtime: ProvenanceRuntime,
    *,
    stored_value: ValueRef,
    memory_key: str,
) -> tuple[ValueRef, Receipt]:
    return runtime.record_memory_read(stored_value=stored_value, memory_key=memory_key)


def record_cap_mint(runtime: ProvenanceRuntime, *, capability: Capability) -> Receipt:
    return runtime.record_cap_mint(capability=capability)


def record_cap_consume(
    runtime: ProvenanceRuntime,
    *,
    capability: Capability,
    action_hash: str,
) -> Receipt:
    return runtime.record_cap_consume(capability=capability, action_hash=action_hash)


def record_endorsement(
    runtime: ProvenanceRuntime,
    *,
    challenge_id: str,
    action_hash: str,
    approved_by: str,
    canonical_action: JsonObject,
    cap_id: str | None = None,
    scope: JsonObject | None = None,
) -> Receipt:
    return runtime.record_endorsement(
        challenge_id=challenge_id,
        action_hash=action_hash,
        approved_by=approved_by,
        canonical_action=canonical_action,
        cap_id=cap_id,
        scope=scope,
    )


def record_delegation(
    runtime: ProvenanceRuntime,
    *,
    parent_agent: str,
    child_agent: str,
    parent_caps: tuple[str, ...],
    child_caps: tuple[str, ...],
    delegated_scope: JsonObject,
) -> Receipt:
    return runtime.record_delegation(
        parent_agent=parent_agent,
        child_agent=child_agent,
        parent_caps=parent_caps,
        child_caps=child_caps,
        delegated_scope=delegated_scope,
    )


def derive_value(
    runtime: ProvenanceRuntime,
    *,
    op: str,
    inputs: tuple[ValueRef, ...],
    output_id: str,
    data_class: str,
    content: Any,
) -> tuple[ValueRef, Receipt]:
    return runtime.derive_value(
        op=op,
        inputs=inputs,
        output_id=output_id,
        data_class=data_class,
        content=content,
    )


def _content_hash(content: Any) -> str:
    encoded = canonical_json(content).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _unique_receipt_ids(values: tuple[ValueRef, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        for receipt_id in value.receipt_ids:
            if receipt_id not in seen:
                seen.add(receipt_id)
                result.append(receipt_id)
    return tuple(result)


def _derive_origins(inputs: tuple[ValueRef, ...], fallback: str) -> tuple[str, ...]:
    if not inputs:
        return (fallback,)
    seen: set[str] = set()
    origins: list[str] = []
    for value in inputs:
        source_ids = value.origins or (value.value_id,)
        for source_id in source_ids:
            if source_id not in seen:
                seen.add(source_id)
                origins.append(source_id)
    return tuple(origins)


def _derive_root(inputs: tuple[ValueRef, ...]) -> str:
    if not inputs:
        return "TOOL_OUTPUT"
    roots = tuple(value.provenance_root for value in inputs)
    if all(root == roots[0] for root in roots):
        root = roots[0]
        if root in TRUSTED_PROVENANCE_ROOTS:
            return root
        if root.endswith("_DERIVED"):
            return root
        return f"{root}_DERIVED"
    if any(root not in TRUSTED_PROVENANCE_ROOTS for root in roots):
        return "UNTRUSTED_DERIVED"
    return "TRUSTED_DERIVED"


def _with_receipt(value: ValueRef, receipt_id: str) -> ValueRef:
    if receipt_id in value.receipt_ids:
        return value
    return ValueRef(
        value_id=value.value_id,
        data_class=value.data_class,
        provenance_root=value.provenance_root,
        content_hash=value.content_hash,
        origins=value.origins,
        receipt_ids=(*value.receipt_ids, receipt_id),
        metadata=value.metadata,
    )
