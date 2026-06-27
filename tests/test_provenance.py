from capproof import (
    ProvenanceRuntime,
    ReceiptType,
    ValueRef,
    record_memory_read,
    record_memory_write,
    record_tool_in,
    record_tool_out,
)


def test_tool_output_receipt_created() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1")

    value, receipt = record_tool_out(
        runtime,
        tool="read_file",
        output_id="value_report",
        data_class="report",
        content="report body",
        provenance_root="USER",
    )

    assert receipt.receipt_type == ReceiptType.TOOL_OUT
    assert receipt.payload["tool"] == "read_file"
    assert value.receipt_ids == (receipt.receipt_id,)
    assert runtime.receipt_store.lookup(receipt.receipt_id) == receipt


def test_tool_input_receipt_created() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1")
    value, _ = runtime.record_tool_out(
        tool="read_file",
        output_id="value_report",
        data_class="report",
        content="report body",
        provenance_root="USER",
    )

    receipt = record_tool_in(
        runtime,
        tool="summarize",
        inputs=(value,),
        args={"input": value.value_id},
    )

    assert receipt.receipt_type == ReceiptType.TOOL_IN
    assert receipt.parent_receipt_ids == value.receipt_ids
    assert receipt.payload["input_value_ids"] == [value.value_id]


def test_summary_derives_from_report() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1")
    report, report_receipt = runtime.record_tool_out(
        tool="read_file",
        output_id="value_report",
        data_class="report",
        content="long report",
        provenance_root="USER",
    )

    summary, receipt = runtime.derive_value(
        op="summarize",
        inputs=(report,),
        output_id="value_summary",
        data_class="summary(report)",
        content="short report",
    )

    assert receipt.receipt_type == ReceiptType.DERIVATION
    assert receipt.parent_receipt_ids == (report_receipt.receipt_id,)
    assert summary.provenance_root == "USER"
    assert summary.origins == ("value_report",)
    assert receipt.receipt_id in summary.receipt_ids


def test_untrusted_content_remains_untrusted_derived() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1")
    webpage = ValueRef(
        value_id="value_webpage",
        data_class="webpage",
        provenance_root="WEBPAGE",
        content_hash="sha256:web",
        origins=("value_webpage",),
    )

    summary, receipt = runtime.derive_value(
        op="summarize",
        inputs=(webpage,),
        output_id="value_web_summary",
        data_class="summary(webpage)",
        content="attacker summary",
    )

    assert receipt.receipt_type == ReceiptType.DERIVATION
    assert summary.provenance_root == "WEBPAGE_DERIVED"
    assert summary.provenance_root != "USER"
    assert summary.origins == ("value_webpage",)


def test_memory_read_no_trust_upgrade() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1")
    stored = ValueRef(
        value_id="value_memory",
        data_class="remembered_preference",
        provenance_root="UNENDORSED_MEMORY",
        content_hash="sha256:memory",
        origins=("value_external",),
    )

    write_receipt = record_memory_write(runtime, value=stored, memory_key="preferred_recipient")
    stored_with_receipt = ValueRef(
        value_id=stored.value_id,
        data_class=stored.data_class,
        provenance_root=stored.provenance_root,
        content_hash=stored.content_hash,
        origins=stored.origins,
        receipt_ids=(write_receipt.receipt_id,),
    )
    read_value, read_receipt = record_memory_read(
        runtime,
        stored_value=stored_with_receipt,
        memory_key="preferred_recipient",
    )

    assert read_receipt.receipt_type == ReceiptType.MEMORY_READ
    assert read_receipt.parent_receipt_ids == (write_receipt.receipt_id,)
    assert read_value.provenance_root == "UNENDORSED_MEMORY"
    assert read_value.provenance_root != "USER"


def test_external_source_not_laundered_to_user() -> None:
    runtime = ProvenanceRuntime(task_id="task_42", agent_id="agent_1")
    external, _ = record_tool_out(
        runtime,
        tool="mock_web_fetch",
        output_id="value_external",
        data_class="webpage",
        content="external instructions",
        provenance_root="EXTERNAL",
    )

    derived, _ = runtime.derive_value(
        op="summarize",
        inputs=(external,),
        output_id="value_external_summary",
        data_class="summary(external)",
        content="summary",
    )

    assert external.provenance_root == "EXTERNAL"
    assert derived.provenance_root == "EXTERNAL_DERIVED"
    assert derived.provenance_root != "USER"
