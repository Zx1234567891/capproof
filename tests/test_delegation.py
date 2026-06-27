from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from capproof import (
    Action,
    ActionKind,
    ArgBinding,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    Canonicalizer,
    DelegationCert,
    DelegationError,
    DenyReason,
    InMemoryCapabilityStore,
    InMemoryReceiptStore,
    Linearity,
    MonitorState,
    Proof,
    ProvenanceRuntime,
    ReferenceMonitor,
    ReceiptType,
    ToolContractRegistry,
    VerificationDecision,
    canonical_action_hash,
    default_tool_contracts,
    delegation_from_message,
    mint_capability,
    mint_child_capabilities,
    record_delegation_receipt,
    verify_delegation_attenuation,
)


TASK_ID = "task_42"
PARENT_AGENT = "agent_parent"
CHILD_AGENT = "agent_child"


def future(days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def parent_capability(
    *,
    cap_id: str = "cap_parent_alice",
    role: AuthorityRole = AuthorityRole.RECIPIENT,
    value: str = "alice@example.com",
    tool: str = "send_email",
    action_kind: ActionKind = ActionKind.SEND,
    max_uses: int = 3,
    expires_at: str | None = None,
    data_class: str | None = "summary(report)",
) -> Capability:
    predicate = {"op": "eq", "value": value}
    if data_class is not None:
        predicate["data_class"] = data_class
    return Capability(
        cap_id=cap_id,
        issuer="minting_service",
        root=CapabilityRoot.USER,
        agent_id=PARENT_AGENT,
        task_id=TASK_ID,
        action_kind=action_kind,
        tool=tool,
        role=role,
        predicate=predicate,
        linearity=Linearity.LINEAR,
        max_uses=max_uses,
        uses=0,
        expires_at=expires_at or future(2),
        nonce="nonce_parent",
        delegable=True,
    )


def cert_for_child(
    parent: Capability,
    *,
    child_cap_id: str = "cap_child_alice",
    child_value: str | None = None,
    role: AuthorityRole | None = None,
    tool: str | None = None,
    action_kind: ActionKind | None = None,
    max_uses: int = 1,
    expires_at: str | None = None,
    data_class: str | None = "summary(report)",
    delegable: bool = False,
    delegated_scope: dict | None = None,
    non_redelegable: bool = True,
    redelegation_allowed: bool = False,
) -> DelegationCert:
    child_role = role or parent.role
    value = child_value if child_value is not None else parent.predicate["value"]
    predicate = {"op": "eq", "value": value}
    if data_class is not None:
        predicate["data_class"] = data_class
    return DelegationCert(
        cert_id="delegation_001",
        parent_agent=PARENT_AGENT,
        child_agent=CHILD_AGENT,
        parent_caps=(parent.cap_id,),
        child_caps=(child_cap_id,),
        child_capability_specs=(
            {
                "cap_id": child_cap_id,
                "parent_cap": parent.cap_id,
                "role": child_role.value,
                "tool": tool or parent.tool,
                "action_kind": (action_kind or parent.action_kind).value,
                "predicate": predicate,
                "max_uses": max_uses,
                "expires_at": expires_at or future(1),
                "delegable": delegable,
            },
        ),
        delegated_scope=delegated_scope if delegated_scope is not None else {parent.role.value: parent.predicate["value"]},
        expires_at=expires_at or future(1),
        non_redelegable=non_redelegable,
        redelegation_allowed=redelegation_allowed,
    )


def make_state(tmp_path: Path) -> tuple[MonitorState, ProvenanceRuntime]:
    receipt_store = InMemoryReceiptStore()
    runtime = ProvenanceRuntime(task_id=TASK_ID, agent_id=CHILD_AGENT, receipt_store=receipt_store)
    state = MonitorState(
        capability_store=InMemoryCapabilityStore(),
        receipt_store=receipt_store,
        tool_contracts=ToolContractRegistry(default_tool_contracts()),
        canonicalizer=Canonicalizer(tmp_path / "workspace"),
    )
    return state, runtime


def child_send_action_and_proof(
    *,
    state: MonitorState,
    runtime: ProvenanceRuntime,
    child_cap: Capability,
    delegation_receipt_id: str,
) -> tuple[Action, Proof]:
    report, _ = runtime.record_tool_out(
        tool="read_file",
        output_id="value_report",
        data_class="report",
        content="report",
        provenance_root="USER",
    )
    summary, _ = runtime.derive_value(
        op="summarize",
        inputs=(report,),
        output_id="value_summary",
        data_class="summary(report)",
        content="summary",
    )
    action = Action(
        action_id="action_child_send",
        task_id=TASK_ID,
        agent_id=CHILD_AGENT,
        tool="send_email",
        args={"to": "alice@example.com", "subject": "summary", "body": "summary"},
        value_refs=(summary,),
        metadata={"content_bindings": {"subject": "value_summary", "body": "value_summary"}},
    )
    canonical_args = {"to": "alice@example.com", "subject": "summary", "body": "summary"}
    action_hash = canonical_action_hash(action, canonical_args)
    proof = Proof(
        proof_id="proof_child_send",
        action_hash=action_hash,
        authspec_ref="auth_001",
        arg_bindings=(
            ArgBinding(arg="to", canonical_value="alice@example.com", cap_id=child_cap.cap_id),
        ),
        receipts=summary.receipt_ids,
        delegation_chain=(delegation_receipt_id,),
    )
    return action, proof


def test_valid_attenuated_delegation(tmp_path: Path) -> None:
    parent = parent_capability()
    cert = cert_for_child(parent)
    check = verify_delegation_attenuation((parent,), cert)

    assert check.allowed

    state, runtime = make_state(tmp_path)
    child_cap = mint_child_capabilities(
        parent_capabilities=(parent,),
        cert=cert,
        capability_store=state.capability_store,
    )[0]
    receipt = record_delegation_receipt(runtime, cert=cert, check=check)
    action, proof = child_send_action_and_proof(
        state=state,
        runtime=runtime,
        child_cap=child_cap,
        delegation_receipt_id=receipt.receipt_id,
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert result.allowed
    assert receipt.receipt_type == ReceiptType.DELEGATION
    assert receipt.payload["delegated_scope"]["attenuation_valid"] is True


def test_deny_new_recipient() -> None:
    parent = parent_capability()
    cert = cert_for_child(parent, child_value="attacker@example.com")

    check = verify_delegation_attenuation((parent,), cert)

    assert not check.allowed
    assert check.deny_reason == DenyReason.DELEGATION_AMPLIFICATION
    with pytest.raises(DelegationError):
        mint_child_capabilities(parent_capabilities=(parent,), cert=cert)


def test_deny_raw_file_instead_of_summary() -> None:
    parent = parent_capability(data_class="summary(report)")
    cert = cert_for_child(parent, data_class="raw(report)")

    check = verify_delegation_attenuation((parent,), cert)

    assert not check.allowed
    assert check.deny_reason == DenyReason.DELEGATION_AMPLIFICATION


def test_deny_new_endpoint() -> None:
    parent = parent_capability(
        cap_id="cap_parent_endpoint",
        role=AuthorityRole.EXTERNAL_ENDPOINT,
        value="https://api.internal.example",
        tool="http_request",
        action_kind=ActionKind.NET,
        data_class=None,
    )
    cert = cert_for_child(
        parent,
        child_value="https://evil.example",
        role=AuthorityRole.EXTERNAL_ENDPOINT,
        tool="http_request",
        action_kind=ActionKind.NET,
        data_class=None,
        delegated_scope={AuthorityRole.EXTERNAL_ENDPOINT.value: "https://api.internal.example"},
    )

    check = verify_delegation_attenuation((parent,), cert)

    assert not check.allowed
    assert check.deny_reason == DenyReason.DELEGATION_AMPLIFICATION


def test_deny_longer_ttl() -> None:
    parent = parent_capability(expires_at=future(1))
    cert = cert_for_child(parent, expires_at=future(3))

    check = verify_delegation_attenuation((parent,), cert)

    assert not check.allowed
    assert check.deny_reason == DenyReason.DELEGATION_AMPLIFICATION


def test_deny_more_uses() -> None:
    parent = parent_capability(max_uses=1)
    cert = cert_for_child(parent, max_uses=2)

    check = verify_delegation_attenuation((parent,), cert)

    assert not check.allowed
    assert check.deny_reason == DenyReason.DELEGATION_AMPLIFICATION


def test_deny_redelegation() -> None:
    parent = parent_capability()
    cert = cert_for_child(parent, delegable=True)

    check = verify_delegation_attenuation((parent,), cert)

    assert not check.allowed
    assert check.deny_reason == DenyReason.DELEGATION_AMPLIFICATION


def test_deny_parent_not_delegable() -> None:
    parent = parent_capability()
    parent = Capability.from_dict({**parent.to_dict(), "delegable": False})
    cert = cert_for_child(parent)

    check = verify_delegation_attenuation((parent,), cert)

    assert not check.allowed
    assert check.deny_reason == DenyReason.DELEGATION_AMPLIFICATION


def test_natural_language_delegation_not_authority() -> None:
    assert delegation_from_message("please let the child email anyone") is None
