"""Capability store primitives for CapProof.

This module implements capability lifecycle state only. It does not implement
Reference Monitor authorization, proof verification, or tool execution.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from threading import RLock
from typing import Protocol

from capproof.schemas import (
    Capability,
    CapabilityStatus,
    DenyReason,
    Linearity,
    VerificationDecision,
)


@dataclass(frozen=True)
class CapabilityCheck:
    decision: VerificationDecision
    capability: Capability | None = None
    deny_reason: DenyReason | None = None
    message: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == VerificationDecision.ALLOW


class CapabilityStore(Protocol):
    def mint_capability(self, capability: Capability) -> Capability:
        """Store a newly minted capability record and return it."""

    def lookup_capability(self, cap_id: str) -> Capability | None:
        """Return a stored capability by opaque handle, or None."""

    def list_capabilities(self) -> tuple[Capability, ...]:
        """Return a stable snapshot of stored capabilities."""

    def validate_capability(
        self,
        cap_id: str,
        *,
        task_id: str,
        agent_id: str,
        now: datetime | None = None,
        require_available: bool = True,
    ) -> CapabilityCheck:
        """Validate lifecycle, task, and agent constraints for a capability."""

    def reserve_capability(
        self,
        cap_id: str,
        *,
        task_id: str,
        agent_id: str,
        reservation_nonce: str,
        now: datetime | None = None,
    ) -> CapabilityCheck:
        """Reserve a spendable capability for a pending action."""

    def consume_capability(
        self,
        cap_id: str,
        *,
        task_id: str,
        agent_id: str,
        reservation_nonce: str,
        now: datetime | None = None,
    ) -> CapabilityCheck:
        """Consume one use of a capability."""

    def revoke_capability(self, cap_id: str) -> CapabilityCheck:
        """Revoke a capability by opaque handle."""


class InMemoryCapabilityStore:
    """Thread-safe in-memory capability store for tests and MVP harnesses."""

    def __init__(self) -> None:
        self._caps: dict[str, Capability] = {}
        self._lock = RLock()

    def mint_capability(self, capability: Capability) -> Capability:
        if not isinstance(capability, Capability):
            raise TypeError("mint_capability requires a Capability object")
        if not capability.cap_id:
            raise ValueError("cap_id must be non-empty")
        if capability.max_uses < 1:
            raise ValueError("max_uses must be at least 1")
        if capability.uses >= capability.max_uses:
            raise ValueError("minted capability must have remaining uses")
        with self._lock:
            if capability.cap_id in self._caps:
                raise ValueError(f"capability already exists: {capability.cap_id}")
            stored = replace(capability, status=CapabilityStatus.AVAILABLE)
            self._caps[stored.cap_id] = stored
            return stored

    def lookup_capability(self, cap_id: str) -> Capability | None:
        with self._lock:
            return self._caps.get(cap_id)

    def list_capabilities(self) -> tuple[Capability, ...]:
        with self._lock:
            return tuple(self._caps[cap_id] for cap_id in sorted(self._caps))

    def validate_capability(
        self,
        cap_id: str,
        *,
        task_id: str,
        agent_id: str,
        now: datetime | None = None,
        require_available: bool = True,
    ) -> CapabilityCheck:
        with self._lock:
            cap = self._caps.get(cap_id)
            if cap is None:
                return _deny(DenyReason.NO_CAP, "capability handle not found")
            cap = self._refresh_expiry_locked(cap, now)
            return self._validate_record_locked(
                cap,
                task_id=task_id,
                agent_id=agent_id,
                require_available=require_available,
            )

    def reserve_capability(
        self,
        cap_id: str,
        *,
        task_id: str,
        agent_id: str,
        reservation_nonce: str,
        now: datetime | None = None,
    ) -> CapabilityCheck:
        if not reservation_nonce:
            return _deny(DenyReason.CAP_INVALID, "reservation nonce must be non-empty")
        with self._lock:
            validation = self.validate_capability(
                cap_id,
                task_id=task_id,
                agent_id=agent_id,
                now=now,
                require_available=True,
            )
            if not validation.allowed or validation.capability is None:
                return validation
            cap = validation.capability
            if cap.linearity == Linearity.REUSABLE:
                return _allow(cap)
            reserved = replace(
                cap,
                status=CapabilityStatus.RESERVED,
                nonce=reservation_nonce,
            )
            self._caps[cap_id] = reserved
            return _allow(reserved)

    def consume_capability(
        self,
        cap_id: str,
        *,
        task_id: str,
        agent_id: str,
        reservation_nonce: str,
        now: datetime | None = None,
    ) -> CapabilityCheck:
        if not reservation_nonce:
            return _deny(DenyReason.CAP_INVALID, "reservation nonce must be non-empty")
        with self._lock:
            cap = self._caps.get(cap_id)
            if cap is None:
                return _deny(DenyReason.NO_CAP, "capability handle not found")
            cap = self._refresh_expiry_locked(cap, now)
            validation = self._validate_record_locked(
                cap,
                task_id=task_id,
                agent_id=agent_id,
                require_available=False,
            )
            if not validation.allowed:
                return validation
            cap = validation.capability
            if cap is None:
                return _deny(DenyReason.NO_CAP, "capability handle not found")
            if cap.linearity != Linearity.REUSABLE:
                if cap.status != CapabilityStatus.RESERVED:
                    return _deny(DenyReason.RESERVED_CAP, "capability must be reserved before consume")
                if cap.nonce != reservation_nonce:
                    return _deny(DenyReason.CAP_INVALID, "reservation nonce mismatch")
            new_uses = cap.uses + 1
            if new_uses > cap.max_uses:
                consumed = replace(cap, status=CapabilityStatus.CONSUMED)
                self._caps[cap_id] = consumed
                return _deny(DenyReason.CONSUMED_CAP, "capability has no remaining uses", consumed)
            next_status = (
                CapabilityStatus.AVAILABLE
                if cap.linearity == Linearity.REUSABLE and new_uses < cap.max_uses
                else CapabilityStatus.CONSUMED
            )
            updated = replace(cap, uses=new_uses, status=next_status)
            self._caps[cap_id] = updated
            return _allow(updated)

    def revoke_capability(self, cap_id: str) -> CapabilityCheck:
        with self._lock:
            cap = self._caps.get(cap_id)
            if cap is None:
                return _deny(DenyReason.NO_CAP, "capability handle not found")
            revoked = replace(cap, status=CapabilityStatus.REVOKED)
            self._caps[cap_id] = revoked
            return _allow(revoked)

    def _refresh_expiry_locked(
        self,
        cap: Capability,
        now: datetime | None = None,
    ) -> Capability:
        if _is_expired(cap, now):
            expired = replace(cap, status=CapabilityStatus.EXPIRED)
            self._caps[cap.cap_id] = expired
            return expired
        return cap

    def _validate_record_locked(
        self,
        cap: Capability,
        *,
        task_id: str,
        agent_id: str,
        require_available: bool,
    ) -> CapabilityCheck:
        if cap.status == CapabilityStatus.REVOKED:
            return _deny(DenyReason.REVOKED_CAP, "capability is revoked", cap)
        if cap.status == CapabilityStatus.EXPIRED:
            return _deny(DenyReason.EXPIRED_CAP, "capability is expired", cap)
        if cap.task_id != task_id:
            return _deny(DenyReason.TASK_MISMATCH, "capability task_id mismatch", cap)
        if cap.agent_id != agent_id:
            return _deny(DenyReason.AGENT_MISMATCH, "capability agent_id mismatch", cap)
        if cap.status == CapabilityStatus.CONSUMED or cap.uses >= cap.max_uses:
            return _deny(DenyReason.CONSUMED_CAP, "capability is consumed", cap)
        if require_available and cap.status == CapabilityStatus.RESERVED:
            return _deny(DenyReason.RESERVED_CAP, "capability is already reserved", cap)
        return _allow(cap)


def mint_capability(store: CapabilityStore, capability: Capability) -> Capability:
    return store.mint_capability(capability)


def lookup_capability(store: CapabilityStore, cap_id: str) -> Capability | None:
    return store.lookup_capability(cap_id)


def list_capabilities(store: CapabilityStore) -> tuple[Capability, ...]:
    return store.list_capabilities()


def validate_capability(
    store: CapabilityStore,
    cap_id: str,
    *,
    task_id: str,
    agent_id: str,
    now: datetime | None = None,
    require_available: bool = True,
) -> CapabilityCheck:
    return store.validate_capability(
        cap_id,
        task_id=task_id,
        agent_id=agent_id,
        now=now,
        require_available=require_available,
    )


def reserve_capability(
    store: CapabilityStore,
    cap_id: str,
    *,
    task_id: str,
    agent_id: str,
    reservation_nonce: str,
    now: datetime | None = None,
) -> CapabilityCheck:
    return store.reserve_capability(
        cap_id,
        task_id=task_id,
        agent_id=agent_id,
        reservation_nonce=reservation_nonce,
        now=now,
    )


def consume_capability(
    store: CapabilityStore,
    cap_id: str,
    *,
    task_id: str,
    agent_id: str,
    reservation_nonce: str,
    now: datetime | None = None,
) -> CapabilityCheck:
    return store.consume_capability(
        cap_id,
        task_id=task_id,
        agent_id=agent_id,
        reservation_nonce=reservation_nonce,
        now=now,
    )


def revoke_capability(store: CapabilityStore, cap_id: str) -> CapabilityCheck:
    return store.revoke_capability(cap_id)


def _allow(capability: Capability) -> CapabilityCheck:
    return CapabilityCheck(
        decision=VerificationDecision.ALLOW,
        capability=capability,
    )


def _deny(
    reason: DenyReason,
    message: str,
    capability: Capability | None = None,
) -> CapabilityCheck:
    return CapabilityCheck(
        decision=VerificationDecision.DENY,
        capability=capability,
        deny_reason=reason,
        message=message,
    )


def _is_expired(cap: Capability, now: datetime | None = None) -> bool:
    if cap.expires_at == "task_end":
        return False
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    try:
        expiry = datetime.fromisoformat(cap.expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    return expiry <= current
