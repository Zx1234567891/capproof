from datetime import UTC, datetime, timedelta
import inspect
from pathlib import Path

from capproof import (
    Action,
    ActionKind,
    ArgBinding,
    AuthorityRole,
    Canonicalizer,
    Capability,
    CapabilityRoot,
    CapabilityStatus,
    DenyReason,
    InMemoryCapabilityStore,
    InMemoryReceiptStore,
    Linearity,
    MonitorState,
    Proof,
    ProvenanceRuntime,
    ReceiptType,
    ReferenceMonitor,
    ToolContractRegistry,
    canonical_action_hash,
    default_tool_contracts,
    consume_capability,
    mint_capability,
    reserve_capability,
    revoke_capability,
)
import capproof.monitor as monitor_module


TASK_ID = "task_42"
AGENT_ID = "agent_email"


def make_state(tmp_path: Path) -> tuple[MonitorState, ProvenanceRuntime]:
    receipts = InMemoryReceiptStore()
    runtime = ProvenanceRuntime(task_id=TASK_ID, agent_id=AGENT_ID, receipt_store=receipts)
    state = MonitorState(
        capability_store=InMemoryCapabilityStore(),
        receipt_store=receipts,
        tool_contracts=ToolContractRegistry(default_tool_contracts()),
        canonicalizer=Canonicalizer(tmp_path / "workspace"),
    )
    return state, runtime


def make_capability(
    cap_id: str,
    *,
    recipient: str = "alice@example.com",
    task_id: str = TASK_ID,
    agent_id: str = AGENT_ID,
    root: CapabilityRoot = CapabilityRoot.USER,
    status: CapabilityStatus = CapabilityStatus.AVAILABLE,
    uses: int = 0,
    max_uses: int = 1,
    expires_at: str = "task_end",
    role: AuthorityRole = AuthorityRole.RECIPIENT,
    tool: str = "send_email",
) -> Capability:
    return Capability(
        cap_id=cap_id,
        issuer="minting_service",
        root=root,
        agent_id=agent_id,
        task_id=task_id,
        action_kind=ActionKind.SEND,
        tool=tool,
        role=role,
        predicate={"op": "eq", "value": recipient},
        linearity=Linearity.LINEAR,
        max_uses=max_uses,
        uses=uses,
        expires_at=expires_at,
        nonce="nonce_1",
        status=status,
    )


def make_authorized_action_and_proof(
    state: MonitorState,
    runtime: ProvenanceRuntime,
    *,
    to: str = "alice@example.com",
    bcc: list[str] | None = None,
    cap_id: str = "cap_alice",
    body_root: str = "USER",
    extra_bindings: tuple[ArgBinding, ...] = (),
    delegation_chain: tuple[str, ...] = (),
    endorsement_chain: tuple[str, ...] = (),
) -> tuple[Action, Proof]:
    report, _ = runtime.record_tool_out(
        tool="read_file",
        output_id="value_report",
        data_class="report",
        content="report body",
        provenance_root=body_root,
    )
    summary, _ = runtime.derive_value(
        op="summarize",
        inputs=(report,),
        output_id="value_summary",
        data_class="summary(report)",
        content="summary body",
    )
    args = {
        "to": to,
        "subject": "summary",
        "body": "summary body",
    }
    if bcc is not None:
        args["bcc"] = bcc
    action = Action(
        action_id="action_send",
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        tool="send_email",
        args=args,
        value_refs=(summary,),
        metadata={"content_bindings": {"subject": "value_summary", "body": "value_summary"}},
    )
    canonical_args = dict(args)
    canonical_args["to"] = state.canonicalizer.canonicalize_recipient(to).value
    if bcc is not None:
        canonical_args["bcc"] = [state.canonicalizer.canonicalize_recipient(item).value for item in bcc]
    action_hash = canonical_action_hash(action, canonical_args)
    proof = Proof(
        proof_id="proof_send",
        action_hash=action_hash,
        authspec_ref="auth_001",
        arg_bindings=(
            ArgBinding(arg="to", canonical_value=canonical_args["to"], cap_id=cap_id),
            *extra_bindings,
        ),
        receipts=summary.receipt_ids,
        delegation_chain=delegation_chain,
        endorsement_chain=endorsement_chain,
    )
    return action, proof


def assert_denied(result, reason: DenyReason) -> None:
    assert not result.allowed
    assert result.deny_reason == reason


def test_allow_authorized_send(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice"))
    action, proof = make_authorized_action_and_proof(state, runtime)

    result = ReferenceMonitor().verify(action, proof, state)

    assert result.allowed


def test_deny_attacker_recipient_no_cap(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice"))
    action, proof = make_authorized_action_and_proof(
        state,
        runtime,
        to="attacker@example.com",
        cap_id="cap_missing",
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.NO_CAP)


def test_deny_bcc_attacker_no_cap(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice"))
    bcc_value = "attacker@example.com"
    bcc_binding = ArgBinding(arg="bcc", canonical_value=bcc_value, cap_id="cap_missing_bcc")
    action, proof = make_authorized_action_and_proof(
        state,
        runtime,
        bcc=[bcc_value],
        extra_bindings=(bcc_binding,),
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.NO_CAP)


def test_deny_consumed_cap(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    cap = mint_capability(state.capability_store, make_capability("cap_alice"))
    reserve_capability(
        state.capability_store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_consumed",
    )
    consume_capability(
        state.capability_store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_consumed",
    )
    action, proof = make_authorized_action_and_proof(state, runtime)

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.CONSUMED_CAP)


def test_deny_expired_cap(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    expired_at = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    mint_capability(state.capability_store, make_capability("cap_alice", expires_at=expired_at))
    action, proof = make_authorized_action_and_proof(state, runtime)

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.EXPIRED_CAP)


def test_deny_revoked_cap(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    cap = mint_capability(state.capability_store, make_capability("cap_alice"))
    revoke_capability(state.capability_store, cap.cap_id)
    action, proof = make_authorized_action_and_proof(state, runtime)

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.REVOKED_CAP)


def test_deny_task_mismatch(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice", task_id="task_other"))
    action, proof = make_authorized_action_and_proof(state, runtime)

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.TASK_MISMATCH)


def test_deny_agent_mismatch(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice", agent_id="agent_other"))
    action, proof = make_authorized_action_and_proof(state, runtime)

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.AGENT_MISMATCH)


def test_deny_missing_arg_binding(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice"))
    action, proof = make_authorized_action_and_proof(state, runtime)
    proof = Proof(
        proof_id=proof.proof_id,
        action_hash=proof.action_hash,
        authspec_ref=proof.authspec_ref,
        arg_bindings=(),
        receipts=proof.receipts,
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.MISSING_ARG_BINDING)


def test_deny_cap_predicate_mismatch(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice"))
    action, proof = make_authorized_action_and_proof(
        state,
        runtime,
        to="attacker@example.com",
        cap_id="cap_alice",
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.CAP_PREDICATE_MISMATCH)


def test_deny_source_mismatch(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(
        state.capability_store,
        make_capability("cap_file", role=AuthorityRole.FILE_PATH),
    )
    action, proof = make_authorized_action_and_proof(state, runtime, cap_id="cap_file")

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.SOURCE_MISMATCH)


def test_deny_missing_receipt(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice"))
    action, proof = make_authorized_action_and_proof(state, runtime)
    proof = Proof(
        proof_id=proof.proof_id,
        action_hash=proof.action_hash,
        authspec_ref=proof.authspec_ref,
        arg_bindings=proof.arg_bindings,
        receipts=(),
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.MISSING_RECEIPT)


def test_deny_memory_authority(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice"))
    action, proof = make_authorized_action_and_proof(state, runtime)
    action = Action(
        action_id=action.action_id,
        task_id=action.task_id,
        agent_id=action.agent_id,
        tool=action.tool,
        args=action.args,
        value_refs=action.value_refs,
        metadata={
            **action.metadata,
            "arg_provenance": {"to": "UNENDORSED_MEMORY"},
        },
    )
    proof = Proof(
        proof_id=proof.proof_id,
        action_hash=canonical_action_hash(
            action,
            {
                "to": "alice@example.com",
                "subject": "summary",
                "body": "summary body",
            },
        ),
        authspec_ref=proof.authspec_ref,
        arg_bindings=proof.arg_bindings,
        receipts=proof.receipts,
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.MEMORY_AUTHORITY_USE)


def test_deny_delegation_missing(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(
        state.capability_store,
        make_capability("cap_delegated", root=CapabilityRoot.DELEGATION),
    )
    action, proof = make_authorized_action_and_proof(
        state,
        runtime,
        cap_id="cap_delegated",
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.DELEGATION_MISSING)


def test_deny_delegation_amplification(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    cap = make_capability(
        "cap_delegated",
        recipient="attacker@example.com",
        root=CapabilityRoot.DELEGATION,
    )
    mint_capability(state.capability_store, cap)
    delegation_receipt = runtime.record_delegation(
        parent_agent="agent_parent",
        child_agent=AGENT_ID,
        parent_caps=("cap_parent",),
        child_caps=("cap_delegated",),
        delegated_scope={"recipient": "alice@example.com"},
    )
    action, proof = make_authorized_action_and_proof(
        state,
        runtime,
        to="attacker@example.com",
        cap_id="cap_delegated",
        delegation_chain=(delegation_receipt.receipt_id,),
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.DELEGATION_AMPLIFICATION)


def test_deny_endorsement_scope_error(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(
        state.capability_store,
        make_capability("cap_endorsed", root=CapabilityRoot.ENDORSEMENT),
    )
    endorsement = runtime.record_endorsement(
        challenge_id="challenge_1",
        action_hash="different_action_hash",
        approved_by="user_alice",
        canonical_action={"tool": "send_email", "to": "alice@example.com"},
    )
    action, proof = make_authorized_action_and_proof(
        state,
        runtime,
        cap_id="cap_endorsed",
        endorsement_chain=(endorsement.receipt_id,),
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.ENDORSEMENT_SCOPE_ERROR)


def test_deny_canonicalization_mismatch(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_capability("cap_alice"))
    action, proof = make_authorized_action_and_proof(state, runtime)
    action = Action(
        action_id=action.action_id,
        task_id=action.task_id,
        agent_id=action.agent_id,
        tool=action.tool,
        args={"to": "not-an-email", "subject": "summary", "body": "summary body"},
        value_refs=action.value_refs,
        metadata=action.metadata,
    )

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.CANONICALIZATION_MISMATCH)


def test_verifier_no_llm_dependency() -> None:
    source = inspect.getsource(monitor_module).lower()

    assert "openai" not in source
    assert "anthropic" not in source
    assert "llm" not in source
    assert "natural_language" not in source
    assert "requests" not in source
    assert "subprocess" not in source
