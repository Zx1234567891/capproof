from datetime import UTC, datetime, timedelta

import pytest

from capproof import (
    ActionKind,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    CapabilityStatus,
    DenyReason,
    InMemoryCapabilityStore,
    Linearity,
    VerificationDecision,
    consume_capability,
    lookup_capability,
    mint_capability,
    reserve_capability,
    revoke_capability,
    validate_capability,
)


TASK_ID = "task_42"
AGENT_ID = "agent_email"


def make_capability(
    cap_id: str = "cap_001",
    *,
    linearity: Linearity = Linearity.LINEAR,
    max_uses: int = 1,
    uses: int = 0,
    expires_at: str = "task_end",
) -> Capability:
    return Capability(
        cap_id=cap_id,
        issuer="minting_service",
        root=CapabilityRoot.USER,
        agent_id=AGENT_ID,
        task_id=TASK_ID,
        action_kind=ActionKind.SEND,
        tool="send_email",
        role=AuthorityRole.RECIPIENT,
        predicate={"op": "eq", "value": "alice@example.com"},
        linearity=linearity,
        max_uses=max_uses,
        uses=uses,
        expires_at=expires_at,
        nonce="initial_nonce",
        status=CapabilityStatus.AVAILABLE,
        mac="schema-only-test-mac",
    )


def assert_denied(result, reason: DenyReason) -> None:
    assert result.decision == VerificationDecision.DENY
    assert result.allowed is False
    assert result.deny_reason == reason


def test_linear_cap_consumed_once() -> None:
    store = InMemoryCapabilityStore()
    cap = mint_capability(store, make_capability())

    reserved = reserve_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="reserve_nonce_1",
    )
    assert reserved.allowed
    assert reserved.capability is not None
    assert reserved.capability.status == CapabilityStatus.RESERVED

    consumed = consume_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="reserve_nonce_1",
    )
    assert consumed.allowed
    assert consumed.capability is not None
    assert consumed.capability.uses == 1
    assert consumed.capability.status == CapabilityStatus.CONSUMED

    replay = reserve_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="reserve_nonce_2",
    )
    assert_denied(replay, DenyReason.CONSUMED_CAP)


def test_consumed_cap_replay_denied() -> None:
    store = InMemoryCapabilityStore()
    cap = mint_capability(store, make_capability())
    reserve_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_replay",
    )
    consume_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_replay",
    )

    replay = consume_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_replay",
    )

    assert_denied(replay, DenyReason.CONSUMED_CAP)


def test_reserved_nonce_mismatch_denied() -> None:
    store = InMemoryCapabilityStore()
    cap = mint_capability(store, make_capability())
    reserve_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_original",
    )

    result = consume_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_replay",
    )

    assert_denied(result, DenyReason.CAP_INVALID)


def test_reserved_cap_double_reserve_denied() -> None:
    store = InMemoryCapabilityStore()
    cap = mint_capability(store, make_capability())
    first = reserve_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_first",
    )

    second = reserve_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_second",
    )

    assert first.allowed
    assert_denied(second, DenyReason.RESERVED_CAP)


def test_expired_cap_denied() -> None:
    store = InMemoryCapabilityStore()
    expired_at = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    cap = mint_capability(store, make_capability(expires_at=expired_at))

    result = validate_capability(store, cap.cap_id, task_id=TASK_ID, agent_id=AGENT_ID)

    assert_denied(result, DenyReason.EXPIRED_CAP)
    stored = lookup_capability(store, cap.cap_id)
    assert stored is not None
    assert stored.status == CapabilityStatus.EXPIRED


def test_revoked_cap_denied() -> None:
    store = InMemoryCapabilityStore()
    cap = mint_capability(store, make_capability())

    revoked = revoke_capability(store, cap.cap_id)
    assert revoked.allowed

    result = validate_capability(store, cap.cap_id, task_id=TASK_ID, agent_id=AGENT_ID)
    assert_denied(result, DenyReason.REVOKED_CAP)


def test_task_mismatch_denied() -> None:
    store = InMemoryCapabilityStore()
    cap = mint_capability(store, make_capability())

    result = validate_capability(store, cap.cap_id, task_id="task_other", agent_id=AGENT_ID)

    assert_denied(result, DenyReason.TASK_MISMATCH)


def test_agent_mismatch_denied() -> None:
    store = InMemoryCapabilityStore()
    cap = mint_capability(store, make_capability())

    result = validate_capability(store, cap.cap_id, task_id=TASK_ID, agent_id="agent_other")

    assert_denied(result, DenyReason.AGENT_MISMATCH)


def test_reusable_cap_multiple_uses() -> None:
    store = InMemoryCapabilityStore()
    cap = mint_capability(
        store,
        make_capability(
            cap_id="cap_reusable",
            linearity=Linearity.REUSABLE,
            max_uses=3,
        ),
    )

    first = consume_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="reusable_nonce_1",
    )
    second = consume_capability(
        store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="reusable_nonce_2",
    )

    assert first.allowed
    assert second.allowed
    assert second.capability is not None
    assert second.capability.uses == 2
    assert second.capability.status == CapabilityStatus.AVAILABLE


def test_fake_cap_id_denied() -> None:
    store = InMemoryCapabilityStore()
    mint_capability(store, make_capability())

    assert lookup_capability(store, "recipient == alice@example.com") is None
    result = validate_capability(
        store,
        "recipient == alice@example.com",
        task_id=TASK_ID,
        agent_id=AGENT_ID,
    )

    assert_denied(result, DenyReason.NO_CAP)


def test_mint_rejects_plain_string_capability() -> None:
    store = InMemoryCapabilityStore()

    with pytest.raises(TypeError):
        mint_capability(store, "cap_plain_string")  # type: ignore[arg-type]
