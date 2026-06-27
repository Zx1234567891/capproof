from pathlib import Path

from capproof import (
    Action,
    ArgBinding,
    AuthorityRole,
    CapabilityStatus,
    Canonicalizer,
    DenyReason,
    EndorsementManager,
    EndorsementResponse,
    InMemoryCapabilityStore,
    InMemoryMemoryStore,
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
    memory_read,
)


TASK_ID = "task_42"
AGENT_ID = "agent_email"
USER_ID = "user_alice"


def make_state_and_manager(tmp_path: Path) -> tuple[MonitorState, ProvenanceRuntime, EndorsementManager]:
    receipt_store = InMemoryReceiptStore()
    capability_store = InMemoryCapabilityStore()
    tool_contracts = ToolContractRegistry(default_tool_contracts())
    canonicalizer = Canonicalizer(tmp_path / "workspace")
    runtime = ProvenanceRuntime(task_id=TASK_ID, agent_id=AGENT_ID, receipt_store=receipt_store)
    state = MonitorState(
        capability_store=capability_store,
        receipt_store=receipt_store,
        tool_contracts=tool_contracts,
        canonicalizer=canonicalizer,
    )
    manager = EndorsementManager(
        capability_store=capability_store,
        provenance_runtime=runtime,
        tool_contracts=tool_contracts,
        canonicalizer=canonicalizer,
    )
    return state, runtime, manager


def make_send_action_and_summary(
    runtime: ProvenanceRuntime,
    *,
    task_id: str = TASK_ID,
    agent_id: str = AGENT_ID,
    to: str = "bob@example.com",
    data_class: str = "summary(report)",
    output_id: str = "value_summary",
) -> Action:
    summary, _ = runtime.record_tool_out(
        tool="summarize",
        output_id=output_id,
        data_class=data_class,
        content="summary for Bob",
        provenance_root="USER",
    )
    return Action(
        action_id="action_send_bob",
        task_id=task_id,
        agent_id=agent_id,
        tool="send_email",
        args={"to": to, "subject": "summary", "body": "summary for Bob"},
        value_refs=(summary,),
        metadata={"content_bindings": {"subject": output_id, "body": output_id}},
    )


def proof_for(action: Action, *, state: MonitorState, cap_id: str, receipt_id: str) -> Proof:
    canonical_to = state.canonicalizer.canonicalize_recipient(action.args["to"]).value
    canonical_args = {
        "to": canonical_to,
        "subject": action.args["subject"],
        "body": action.args["body"],
    }
    return Proof(
        proof_id="proof_endorsed_send",
        action_hash=canonical_action_hash(action, canonical_args),
        authspec_ref="auth_001",
        arg_bindings=(ArgBinding(arg="to", canonical_value=canonical_to, cap_id=cap_id),),
        receipts=tuple(receipt_id for value in action.value_refs for receipt_id in value.receipt_ids),
        endorsement_chain=(receipt_id,),
    )


def mint_bob_endorsement(
    state: MonitorState,
    manager: EndorsementManager,
    action: Action,
):
    challenge = manager.create_challenge(
        action,
        field="to",
        role=AuthorityRole.RECIPIENT,
        data_class="summary(report)",
    )
    response = EndorsementResponse.approve(challenge, approved_by=USER_ID)
    grant = manager.mint_endorsement_capability(response)
    proof = proof_for(
        action,
        state=state,
        cap_id=grant.capability.cap_id,
        receipt_id=grant.receipt.receipt_id,
    )
    return challenge, grant, proof


def assert_denied(result, reason: DenyReason) -> None:
    assert not result.allowed
    assert result.deny_reason == reason


def test_one_shot_endorsement_allows_once(tmp_path: Path) -> None:
    state, runtime, manager = make_state_and_manager(tmp_path)
    action = make_send_action_and_summary(runtime)
    challenge, grant, proof = mint_bob_endorsement(state, manager, action)

    result = ReferenceMonitor().verify(action, proof, state)

    assert result.allowed
    assert grant.capability.root.value == "ENDORSEMENT"
    assert grant.capability.linearity == Linearity.LINEAR
    assert grant.capability.max_uses == 1
    assert grant.capability.transferable is False
    assert grant.capability.persistent is False
    assert grant.capability.task_id == TASK_ID
    assert grant.capability.agent_id == AGENT_ID
    assert grant.capability.predicate["value"] == "bob@example.com"
    assert grant.capability.predicate["data_class"] == "summary(report)"
    assert grant.capability.predicate["action_hash"] == proof.action_hash
    assert grant.receipt.receipt_type == ReceiptType.ENDORSEMENT
    assert grant.receipt.payload["scope"]["canonical_value"] == "bob@example.com"
    assert "summary for Bob" not in challenge.challenge_text()
    assert "subject" not in challenge.challenge_text().lower()

    consumed = manager.consume_endorsement_capability(
        grant.capability,
        action_hash=proof.action_hash,
        reservation_nonce="endorsement_once",
    )

    assert consumed.allowed
    assert consumed.capability is not None
    assert consumed.capability.status == CapabilityStatus.CONSUMED


def test_endorsement_replay_denied(tmp_path: Path) -> None:
    state, runtime, manager = make_state_and_manager(tmp_path)
    action = make_send_action_and_summary(runtime)
    _, grant, proof = mint_bob_endorsement(state, manager, action)
    consumed = manager.consume_endorsement_capability(
        grant.capability,
        action_hash=proof.action_hash,
        reservation_nonce="endorsement_once",
    )
    assert consumed.allowed

    result = ReferenceMonitor().verify(action, proof, state)

    assert_denied(result, DenyReason.CONSUMED_CAP)


def test_endorsement_wrong_recipient_denied(tmp_path: Path) -> None:
    state, runtime, manager = make_state_and_manager(tmp_path)
    original_action = make_send_action_and_summary(runtime)
    _, grant, _ = mint_bob_endorsement(state, manager, original_action)
    attacker_action = make_send_action_and_summary(
        runtime,
        to="attacker@example.com",
        output_id="value_summary_attacker",
    )
    proof = proof_for(
        attacker_action,
        state=state,
        cap_id=grant.capability.cap_id,
        receipt_id=grant.receipt.receipt_id,
    )

    result = ReferenceMonitor().verify(attacker_action, proof, state)

    assert_denied(result, DenyReason.CAP_PREDICATE_MISMATCH)


def test_endorsement_wrong_data_class_denied(tmp_path: Path) -> None:
    state, runtime, manager = make_state_and_manager(tmp_path)
    original_action = make_send_action_and_summary(runtime)
    _, grant, _ = mint_bob_endorsement(state, manager, original_action)
    raw_action = make_send_action_and_summary(
        runtime,
        data_class="raw_report",
        output_id="value_raw_report",
    )
    proof = proof_for(
        raw_action,
        state=state,
        cap_id=grant.capability.cap_id,
        receipt_id=grant.receipt.receipt_id,
    )

    result = ReferenceMonitor().verify(raw_action, proof, state)

    assert_denied(result, DenyReason.DATA_CLASS_MISMATCH)


def test_endorsement_cross_task_denied(tmp_path: Path) -> None:
    state, runtime, manager = make_state_and_manager(tmp_path)
    original_action = make_send_action_and_summary(runtime)
    _, grant, _ = mint_bob_endorsement(state, manager, original_action)
    other_task_action = make_send_action_and_summary(
        runtime,
        task_id="task_other",
        output_id="value_summary_other_task",
    )
    proof = proof_for(
        other_task_action,
        state=state,
        cap_id=grant.capability.cap_id,
        receipt_id=grant.receipt.receipt_id,
    )

    result = ReferenceMonitor().verify(other_task_action, proof, state)

    assert_denied(result, DenyReason.TASK_MISMATCH)


def test_endorsement_cross_agent_denied(tmp_path: Path) -> None:
    state, runtime, manager = make_state_and_manager(tmp_path)
    original_action = make_send_action_and_summary(runtime)
    _, grant, _ = mint_bob_endorsement(state, manager, original_action)
    other_agent_action = make_send_action_and_summary(
        runtime,
        agent_id="agent_other",
        output_id="value_summary_other_agent",
    )
    proof = proof_for(
        other_agent_action,
        state=state,
        cap_id=grant.capability.cap_id,
        receipt_id=grant.receipt.receipt_id,
    )

    result = ReferenceMonitor().verify(other_agent_action, proof, state)

    assert_denied(result, DenyReason.AGENT_MISMATCH)


def test_endorsement_not_persisted_to_memory(tmp_path: Path) -> None:
    state, runtime, manager = make_state_and_manager(tmp_path)
    memory = InMemoryMemoryStore(runtime)
    action = make_send_action_and_summary(runtime)
    challenge, grant, _ = mint_bob_endorsement(state, manager, action)

    assert grant.capability.persistent is False
    assert grant.receipt.payload["scope"]["persistent"] is False
    assert memory_read(memory, "preferred_recipient") is None
    assert memory_read(memory, "endorsement:bob@example.com") is None
    assert "from now on" not in challenge.challenge_text().lower()
    assert "always" not in challenge.challenge_text().lower()
    assert "preference" not in challenge.challenge_text().lower()
