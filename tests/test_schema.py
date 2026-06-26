from capproof import (
    Action,
    ActionKind,
    ArgBinding,
    AuthSpec,
    AuthorityField,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    CapabilityStatus,
    CapabilityUse,
    DerivationStep,
    Linearity,
    Proof,
    Receipt,
    ReceiptType,
    ToolContract,
    ValueRef,
)


def test_authspec_serialization_round_trip_is_stable() -> None:
    authspec = AuthSpec(
        auth_id="auth_001",
        task_id="task_42",
        principal="user_alice",
        intent="summarize_and_send",
        resources=({"kind": "file", "path": "/workspace/report.pdf", "permission": "read"},),
        transforms=({"op": "summarize", "input": "/workspace/report.pdf"},),
        actions=(
            {
                "tool": "send_email",
                "recipient": "alice@example.com",
                "binding_status": "explicit",
            },
        ),
        forbidden=("raw_file_egress", "shell_exec"),
    )

    encoded = authspec.to_canonical_json()
    decoded = AuthSpec.from_dict(authspec.to_dict())

    assert decoded == authspec
    assert decoded.to_canonical_json() == encoded
    assert authspec.to_canonical_json() == authspec.to_canonical_json()
    assert authspec.stable_hash() == decoded.stable_hash()


def test_capability_serialization_round_trip_and_required_security_fields() -> None:
    capability = Capability(
        cap_id="cap_opaque_001",
        issuer="minting_service",
        root=CapabilityRoot.USER,
        agent_id="agent_email",
        task_id="task_42",
        action_kind=ActionKind.SEND,
        tool="send_email",
        role=AuthorityRole.RECIPIENT,
        predicate={"op": "eq", "value": "alice@example.com"},
        linearity=Linearity.LINEAR,
        max_uses=1,
        uses=0,
        expires_at="task_end",
        nonce="nonce_001",
        status=CapabilityStatus.AVAILABLE,
        mac="test-mac",
    )

    decoded = Capability.from_dict(capability.to_dict())
    serialized = capability.to_dict()

    assert decoded == capability
    assert capability.to_canonical_json() == decoded.to_canonical_json()
    assert capability.stable_hash() == decoded.stable_hash()
    assert capability.handle() == "cap_opaque_001"
    assert isinstance(serialized["predicate"], dict)
    assert "agent_id" in serialized
    assert "task_id" in serialized
    assert "nonce" in serialized
    assert "expires_at" in serialized
    assert "max_uses" in serialized
    assert "uses" in serialized
    assert "linearity" in serialized
    assert "authorization_text" not in serialized
    assert "natural_language_authorization" not in serialized


def test_action_canonical_hash_is_stable_across_dict_order() -> None:
    value_ref = ValueRef(
        value_id="value_summary",
        data_class="summary(report.pdf)",
        provenance_root="USER",
        content_hash="sha256:abc",
    )
    action_a = Action(
        action_id="action_a",
        task_id="task_42",
        agent_id="agent_email",
        tool="send_email",
        args={"to": "alice@example.com", "body": {"class": "summary", "source": "report.pdf"}},
        value_refs=(value_ref,),
    )
    action_b = Action(
        action_id="action_b",
        task_id="task_42",
        agent_id="agent_email",
        tool="send_email",
        args={"body": {"source": "report.pdf", "class": "summary"}, "to": "alice@example.com"},
        value_refs=(ValueRef.from_dict(value_ref.to_dict()),),
    )

    assert action_a.action_hash() == action_b.action_hash()
    assert action_a.action_hash() == action_a.action_hash()
    assert Action.from_dict(action_a.to_dict()).action_hash() == action_a.action_hash()


def test_proof_serialization_and_proof_hash_are_stable() -> None:
    action = Action(
        action_id="action_001",
        task_id="task_42",
        agent_id="agent_email",
        tool="send_email",
        args={"to": "alice@example.com", "body": "summary"},
    )
    receipt = Receipt(
        receipt_id="receipt_001",
        receipt_type=ReceiptType.DERIVATION,
        task_id="task_42",
        agent_id="agent_email",
        subject_hash=action.action_hash(),
        payload={"op": "summarize", "input": "value_report", "output": "value_summary"},
        issued_at="2026-06-26T00:00:00Z",
        signature="test-signature",
    )
    proof = Proof(
        proof_id="proof_001",
        action_hash=action.action_hash(),
        authspec_ref="auth_001",
        capability_uses=(
            CapabilityUse(
                cap_id="cap_opaque_001",
                role=AuthorityRole.RECIPIENT,
                reserved_nonce="nonce_001",
            ),
        ),
        arg_bindings=(
            ArgBinding(
                arg="to",
                canonical_value="alice@example.com",
                cap_id="cap_opaque_001",
            ),
        ),
        derivation_steps=(
            DerivationStep(
                output_class="summary(report.pdf)",
                op="summarize",
                inputs=("value_report",),
                receipt_id=receipt.receipt_id,
            ),
        ),
        receipts=(receipt.receipt_id,),
    )

    decoded = Proof.from_dict(proof.to_dict())

    assert decoded == proof
    assert proof.to_canonical_json() == decoded.to_canonical_json()
    assert proof.proof_hash() == decoded.proof_hash()
    assert proof.proof_hash() == proof.proof_hash()


def test_tool_contract_schema_marks_authority_bearing_fields() -> None:
    contract = ToolContract(
        tool="send_email",
        args_schema={"type": "object"},
        authority=(
            AuthorityField(name="to", role=AuthorityRole.RECIPIENT),
            AuthorityField(name="bcc", role=AuthorityRole.RECIPIENT),
            AuthorityField(name="attachments", role=AuthorityRole.FILE_PATH, access="read"),
        ),
        side_effects=("egress(to,cc,bcc)", "reads(attachments)"),
        coverage_fields=("to", "cc", "bcc", "reply_to", "headers", "attachments"),
        high_impact_fields=("to", "cc", "bcc", "reply_to", "attachments"),
    )

    decoded = ToolContract.from_dict(contract.to_dict())
    authority_names = {field.name for field in decoded.authority}

    assert decoded == contract
    assert decoded.to_canonical_json() == contract.to_canonical_json()
    assert {"to", "bcc", "attachments"} <= authority_names
    assert "bcc" in decoded.coverage_fields
    assert "attachments" in decoded.coverage_fields
