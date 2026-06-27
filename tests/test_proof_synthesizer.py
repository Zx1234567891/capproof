from pathlib import Path

from capproof import (
    Action,
    ActionKind,
    ArgBinding,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    Canonicalizer,
    DenyReason,
    EndorsementManager,
    EndorsementResponse,
    InMemoryCapabilityStore,
    InMemoryReceiptStore,
    Linearity,
    MonitorState,
    Proof,
    ProofDAG,
    ProofFailureReason,
    ProvenanceRuntime,
    ReferenceMonitor,
    ToolContractRegistry,
    VerificationDecision,
    canonical_action_hash,
    consume_capability,
    default_tool_contracts,
    mint_capability,
    reserve_capability,
    synthesize_proof,
)


TASK_ID = "task_42"
AGENT_ID = "agent_email"


def make_state(tmp_path: Path) -> tuple[MonitorState, ProvenanceRuntime]:
    receipt_store = InMemoryReceiptStore()
    capability_store = InMemoryCapabilityStore()
    runtime = ProvenanceRuntime(task_id=TASK_ID, agent_id=AGENT_ID, receipt_store=receipt_store)
    state = MonitorState(
        capability_store=capability_store,
        receipt_store=receipt_store,
        tool_contracts=ToolContractRegistry(default_tool_contracts()),
        canonicalizer=Canonicalizer(tmp_path / "workspace"),
    )
    return state, runtime


def make_recipient_cap(
    cap_id: str,
    *,
    recipient: str = "alice@example.com",
    root: CapabilityRoot = CapabilityRoot.USER,
) -> Capability:
    return Capability(
        cap_id=cap_id,
        issuer="minting_service",
        root=root,
        agent_id=AGENT_ID,
        task_id=TASK_ID,
        action_kind=ActionKind.SEND,
        tool="send_email",
        role=AuthorityRole.RECIPIENT,
        predicate={"op": "eq", "value": recipient},
        linearity=Linearity.LINEAR,
        max_uses=1,
        uses=0,
        expires_at="task_end",
        nonce=f"nonce:{cap_id}",
        delegable=False,
        transferable=False,
        persistent=False,
    )


def make_send_action(
    runtime: ProvenanceRuntime,
    *,
    to: str = "alice@example.com",
    bcc: list[str] | None = None,
    metadata_extra: dict | None = None,
) -> Action:
    report, _ = runtime.record_tool_out(
        tool="read_file",
        output_id="value_report",
        data_class="report",
        content="raw report",
        provenance_root="USER",
    )
    summary, _ = runtime.derive_value(
        op="summarize",
        inputs=(report,),
        output_id="value_summary",
        data_class="summary(report)",
        content="report summary",
    )
    args = {"to": to, "subject": "summary", "body": "report summary"}
    if bcc is not None:
        args["bcc"] = bcc
    metadata = {"content_bindings": {"subject": "value_summary", "body": "value_summary"}}
    if metadata_extra is not None:
        metadata.update(metadata_extra)
    return Action(
        action_id="action_send",
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        tool="send_email",
        args=args,
        value_refs=(summary,),
        metadata=metadata,
    )


def test_synthesize_valid_send_proof(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_recipient_cap("cap_alice"))
    action = make_send_action(runtime)

    result = synthesize_proof(action, state, authspec_ref="auth_001")

    assert result.allowed
    assert result.proof is not None
    assert result.proof_dag is not None
    assert result.verifier_result is not None
    assert result.verifier_result.allowed
    assert result.proof.action_hash == result.verifier_result.canonical_action_hash
    assert result.proof.arg_bindings == (
        ArgBinding(arg="to", canonical_value="alice@example.com", cap_id="cap_alice"),
    )
    assert result.proof.derivation_steps[0].op == "summarize"
    assert result.proof.derivation_steps[0].inputs == ("value_report",)
    assert "explanation" not in result.proof.to_canonical_json()
    assert "natural_language" not in result.proof.to_canonical_json()

    decoded = ProofDAG.from_dict(result.proof_dag.to_dict())
    assert decoded == result.proof_dag
    assert decoded.to_proof() == result.proof
    assert ReferenceMonitor().verify(action, result.proof, state).allowed


def test_synthesize_fails_no_cap(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_recipient_cap("cap_alice"))
    action = make_send_action(runtime, to="attacker@example.com")

    result = synthesize_proof(action, state)

    assert not result.allowed
    assert result.failure_reason == ProofFailureReason.NO_CAP
    assert result.proof is None


def test_synthesize_fails_bcc_no_cap(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_recipient_cap("cap_alice"))
    action = make_send_action(runtime, bcc=["attacker@example.com"])

    result = synthesize_proof(action, state)

    assert not result.allowed
    assert result.failure_reason == ProofFailureReason.NO_CAP
    assert result.proof is None


def test_synthesize_after_endorsement(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    action = make_send_action(runtime, to="bob@example.com")
    manager = EndorsementManager(
        capability_store=state.capability_store,
        provenance_runtime=runtime,
        tool_contracts=state.tool_contracts,
        canonicalizer=state.canonicalizer,
    )
    challenge = manager.create_challenge(
        action,
        field="to",
        role=AuthorityRole.RECIPIENT,
        data_class="summary(report)",
    )
    grant = manager.mint_endorsement_capability(
        EndorsementResponse.approve(challenge, approved_by="user_alice")
    )

    result = synthesize_proof(action, state)

    assert result.allowed
    assert result.proof is not None
    assert result.proof.endorsement_chain == (grant.receipt.receipt_id,)
    assert result.proof.arg_bindings == (
        ArgBinding(arg="to", canonical_value="bob@example.com", cap_id=grant.capability.cap_id),
    )
    assert ReferenceMonitor().verify(action, result.proof, state).allowed


def test_synthesize_fails_consumed_cap(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    cap = mint_capability(state.capability_store, make_recipient_cap("cap_alice"))
    reserve_capability(
        state.capability_store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_used",
    )
    consume_capability(
        state.capability_store,
        cap.cap_id,
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        reservation_nonce="nonce_used",
    )
    action = make_send_action(runtime)

    result = synthesize_proof(action, state)

    assert not result.allowed
    assert result.failure_reason == ProofFailureReason.CONSUMED_CAP
    assert result.proof is None


def test_synthesize_fails_memory_authority(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_recipient_cap("cap_alice"))
    action = make_send_action(
        runtime,
        metadata_extra={"arg_provenance": {"to": "UNENDORSED_MEMORY"}},
    )

    result = synthesize_proof(action, state)

    assert not result.allowed
    assert result.failure_reason == ProofFailureReason.MEMORY_AUTHORITY_USE
    assert result.proof is None


def test_synthesize_fails_missing_delegation(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(
        state.capability_store,
        make_recipient_cap(
            "cap_delegated_alice",
            root=CapabilityRoot.DELEGATION,
        ),
    )
    action = make_send_action(runtime)

    result = synthesize_proof(action, state)

    assert not result.allowed
    assert result.failure_reason == ProofFailureReason.DELEGATION_MISSING
    assert result.proof is None


def test_fake_proof_rejected_by_verifier(tmp_path: Path) -> None:
    state, runtime = make_state(tmp_path)
    mint_capability(state.capability_store, make_recipient_cap("cap_alice"))
    action = make_send_action(runtime)
    result = synthesize_proof(action, state)
    assert result.allowed
    assert result.proof is not None

    mismatch = Proof(
        proof_id="proof_mismatch",
        action_hash="fake_action_hash",
        authspec_ref=result.proof.authspec_ref,
        arg_bindings=result.proof.arg_bindings,
        receipts=result.proof.receipts,
    )
    mismatch_result = ReferenceMonitor().verify(action, mismatch, state)
    assert not mismatch_result.allowed
    assert mismatch_result.deny_reason == DenyReason.CANONICALIZATION_MISMATCH

    canonical_args = {"to": "alice@example.com", "subject": "summary", "body": "report summary"}
    fake = Proof(
        proof_id="proof_fake",
        action_hash=canonical_action_hash(action, canonical_args),
        authspec_ref="auth_001",
        arg_bindings=(ArgBinding(arg="to", canonical_value="alice@example.com", cap_id="cap_fake"),),
        receipts=result.proof.receipts,
        metadata={"explanation": "trust me"},
    )
    fake_result = ReferenceMonitor().verify(action, fake, state)
    assert not fake_result.allowed
    assert fake_result.deny_reason == DenyReason.NO_CAP

    assert result.proof.metadata.get("synthesizer") == "capproof.proof_synthesizer.v1"
    assert "explanation" not in result.proof.to_canonical_json()
