from capproof import (
    ActionKind,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    InMemoryReceiptStore,
    Linearity,
    ProvenanceRuntime,
    Receipt,
    ReceiptType,
    ValueRef,
    lookup_receipt,
    record_cap_consume,
    record_cap_mint,
    record_delegation,
    record_endorsement,
    trace_receipt_chain,
)


def test_receipt_hash_stable() -> None:
    receipt = Receipt(
        receipt_id="receipt_001",
        receipt_type=ReceiptType.TOOL_OUT,
        task_id="task_42",
        agent_id="agent_1",
        subject_hash="subject-hash",
        payload={"tool": "read_file", "output": "value_report"},
        issued_at="2026-06-27T00:00:00Z",
        parent_receipt_ids=("receipt_parent",),
    )

    decoded = Receipt.from_dict(receipt.to_dict())

    assert decoded == receipt
    assert receipt.receipt_hash() == decoded.receipt_hash()
    assert receipt.receipt_hash() == receipt.receipt_hash()


def test_receipt_chain_traceable() -> None:
    store = InMemoryReceiptStore()
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1", receipt_store=store)
    report, report_receipt = runtime.record_tool_out(
        tool="read_file",
        output_id="value_report",
        data_class="report",
        content="report text",
        provenance_root="USER",
    )
    summary, summary_receipt = runtime.derive_value(
        op="summarize",
        inputs=(report,),
        output_id="value_summary",
        data_class="summary(report)",
        content="short report",
    )

    chain = trace_receipt_chain(store, summary_receipt.receipt_id)

    assert summary.receipt_ids[-1] == summary_receipt.receipt_id
    assert [receipt.receipt_id for receipt in chain] == [
        report_receipt.receipt_id,
        summary_receipt.receipt_id,
    ]
    assert lookup_receipt(store, summary_receipt.receipt_id) == summary_receipt


def test_endorsement_receipt_created() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1")

    receipt = record_endorsement(
        runtime,
        challenge_id="challenge_1",
        action_hash="action_hash_1",
        approved_by="user_alice",
        canonical_action={"tool": "send_email", "to": "alice@example.com"},
    )

    assert receipt.receipt_type == ReceiptType.ENDORSEMENT
    assert receipt.payload["challenge_id"] == "challenge_1"
    assert receipt.payload["action_hash"] == "action_hash_1"
    assert runtime.receipt_store.lookup(receipt.receipt_id) == receipt


def test_delegation_receipt_created() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_parent")

    receipt = record_delegation(
        runtime,
        parent_agent="agent_parent",
        child_agent="agent_child",
        parent_caps=("cap_parent",),
        child_caps=("cap_child",),
        delegated_scope={"recipient": "alice@example.com"},
    )

    assert receipt.receipt_type == ReceiptType.DELEGATION
    assert receipt.payload["parent_agent"] == "agent_parent"
    assert receipt.payload["child_agent"] == "agent_child"
    assert receipt.payload["parent_caps"] == ["cap_parent"]
    assert runtime.receipt_store.lookup(receipt.receipt_id) == receipt


def test_cap_mint_and_consume_receipts_created() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1")
    capability = Capability(
        cap_id="cap_001",
        issuer="minting_service",
        root=CapabilityRoot.USER,
        agent_id="agent_1",
        task_id="task_42",
        action_kind=ActionKind.SEND,
        tool="send_email",
        role=AuthorityRole.RECIPIENT,
        predicate={"op": "eq", "value": "alice@example.com"},
        linearity=Linearity.LINEAR,
        max_uses=1,
        uses=1,
        expires_at="task_end",
        nonce="nonce_1",
    )

    mint_receipt = record_cap_mint(runtime, capability=capability)
    consume_receipt = record_cap_consume(
        runtime,
        capability=capability,
        action_hash="action_hash_1",
    )

    assert mint_receipt.receipt_type == ReceiptType.CAP_MINT
    assert consume_receipt.receipt_type == ReceiptType.CAP_CONSUME
    assert consume_receipt.payload["cap_id"] == "cap_001"


def test_receipt_ids_support_proof_reference() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1")
    value = ValueRef(
        value_id="value_external",
        data_class="webpage",
        provenance_root="WEBPAGE",
        content_hash="sha256:web",
        origins=("value_external",),
    )
    receipt = runtime.record_memory_write(value=value, memory_key="ticket")

    assert runtime.receipt_store.lookup(receipt.receipt_id) is not None
    assert receipt.receipt_hash()
