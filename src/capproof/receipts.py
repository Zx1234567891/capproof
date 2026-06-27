"""Receipt store primitives for CapProof."""

from __future__ import annotations

from threading import RLock
from typing import Protocol

from capproof.schemas import Receipt


class ReceiptStore(Protocol):
    def append(self, receipt: Receipt) -> Receipt:
        """Append a receipt and return the stored record."""

    def lookup(self, receipt_id: str) -> Receipt | None:
        """Return a receipt by id, or None."""

    def list_receipts(self) -> tuple[Receipt, ...]:
        """Return a stable snapshot of stored receipts."""

    def trace_chain(self, receipt_id: str) -> tuple[Receipt, ...]:
        """Return the parent receipts followed by the requested receipt."""


class InMemoryReceiptStore:
    """Append-only in-memory receipt store."""

    def __init__(self) -> None:
        self._receipts: dict[str, Receipt] = {}
        self._lock = RLock()

    def append(self, receipt: Receipt) -> Receipt:
        if not isinstance(receipt, Receipt):
            raise TypeError("append requires a Receipt object")
        if not receipt.receipt_id:
            raise ValueError("receipt_id must be non-empty")
        with self._lock:
            if receipt.receipt_id in self._receipts:
                raise ValueError(f"receipt already exists: {receipt.receipt_id}")
            self._receipts[receipt.receipt_id] = receipt
            return receipt

    def lookup(self, receipt_id: str) -> Receipt | None:
        with self._lock:
            return self._receipts.get(receipt_id)

    def list_receipts(self) -> tuple[Receipt, ...]:
        with self._lock:
            return tuple(self._receipts[receipt_id] for receipt_id in sorted(self._receipts))

    def trace_chain(self, receipt_id: str) -> tuple[Receipt, ...]:
        with self._lock:
            visited: set[str] = set()
            chain: list[Receipt] = []
            self._trace_locked(receipt_id, visited, chain)
            return tuple(chain)

    def _trace_locked(
        self,
        receipt_id: str,
        visited: set[str],
        chain: list[Receipt],
    ) -> None:
        if receipt_id in visited:
            return
        receipt = self._receipts.get(receipt_id)
        if receipt is None:
            return
        visited.add(receipt_id)
        for parent_id in receipt.parent_receipt_ids:
            self._trace_locked(parent_id, visited, chain)
        chain.append(receipt)


def append_receipt(store: ReceiptStore, receipt: Receipt) -> Receipt:
    return store.append(receipt)


def lookup_receipt(store: ReceiptStore, receipt_id: str) -> Receipt | None:
    return store.lookup(receipt_id)


def list_receipts(store: ReceiptStore) -> tuple[Receipt, ...]:
    return store.list_receipts()


def trace_receipt_chain(store: ReceiptStore, receipt_id: str) -> tuple[Receipt, ...]:
    return store.trace_chain(receipt_id)
