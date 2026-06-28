from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_hermes_capture_prototype import INPUT_EXAMPLES_DIR, run_prototype


def run_payload(tmp_path: Path) -> dict:
    return run_prototype(
        input_path=INPUT_EXAMPLES_DIR,
        trace_path=tmp_path / "capture_trace.jsonl",
        summary_path=tmp_path / "capture_summary.json",
        report_path=tmp_path / "capture_report.md",
    )


def result_by_id(payload: dict, case_id: str) -> dict:
    for result in payload["results"]:
        if result["case_id"] == case_id:
            return result
    raise AssertionError(f"missing result for {case_id}")


def test_valid_terminal_pytest_pre_exec_allows_if_capability_exists(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_terminal_pytest")

    assert result["guard_verdict"] == "ALLOW"
    assert result["executor_called"] is True
    assert result["mock_event"]["mock_tool"] == "run_shell_template"


def test_raw_shell_pre_exec_denies(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_terminal_raw_shell")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "CommandTemplateViolation"
    assert result["executor_called"] is False


def test_terminal_missing_cwd_env_stdin_denies_adapter_gap(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_terminal_missing_fields")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert set(result["missing_fields"]) == {
        "effective_args.cwd",
        "effective_args.env",
        "effective_args.stdin",
    }


def test_gateway_authorized_recipient_allows(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_gateway_authorized")

    assert result["guard_verdict"] == "ALLOW"
    assert result["mock_event"]["mock_tool"] == "send_message"
    assert result["mock_event"]["args"]["recipient"] == "telegram:alice_chat"


def test_gateway_missing_recipient_denies_adapter_gap(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_gateway_missing_recipient")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert list(result["missing_fields"]) == ["effective_args.recipient"]


def test_mcp_evil_endpoint_denies_no_cap(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_mcp_evil_endpoint")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "NoCap"
    assert result["executor_called"] is False


def test_mcp_missing_transport_endpoint_denies_adapter_gap(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_mcp_missing_endpoint")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert list(result["missing_fields"]) == ["effective_args.transport.endpoint"]


def test_memory_authority_claim_stripped_and_no_capability_minted(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_memory_authority_claim")

    assert result["guard_verdict"] == "ALLOW"
    assert result["mock_event"]["mock_tool"] == "memory_write"
    assert result["mock_event"]["args"]["authority_claims"] == {}
    assert result["mock_event"]["args"]["stripped_authority"] is True
    assert result["capability_minted_from_stripped_memory"] is False


def test_delegation_without_cert_denies_delegation_missing(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_delegation_without_cert")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "DelegationMissing"
    assert result["executor_called"] is False


def test_middleware_effective_args_attacker_denies_no_cap(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_middleware_effective_attacker")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "NoCap"
    assert result["executor_called"] is False


def test_observer_only_event_cannot_produce_enforcement_allow(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_observer_posthoc_terminal")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert result["observer_only_blocked"] is True
    assert result["executor_called"] is False


def test_unsupported_event_fails_closed(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    result = result_by_id(payload, "proto_unsupported_capture_mode")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert result["unsupported_fail_closed"] is True
    assert result["executor_called"] is False


def test_deny_and_ask_never_call_executor(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    summary = payload["summary"]

    assert summary["executor_called_on_deny"] == 0
    assert summary["executor_called_on_ask"] == 0


def test_capture_trace_jsonl_written(tmp_path: Path) -> None:
    trace_path = tmp_path / "capture_trace.jsonl"
    payload = run_prototype(
        input_path=INPUT_EXAMPLES_DIR,
        trace_path=trace_path,
        summary_path=tmp_path / "capture_summary.json",
        report_path=tmp_path / "capture_report.md",
    )
    lines = trace_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == payload["summary"]["total_events_processed"]
    first = json.loads(lines[0])
    assert {
        "trace_id",
        "event_id",
        "hook_point",
        "capture_mode",
        "validation_status",
        "guard_verdict",
        "executor_called",
        "timestamp",
    } <= set(first)


def test_summary_json_schema_valid(tmp_path: Path) -> None:
    summary_path = tmp_path / "capture_summary.json"
    payload = run_prototype(
        input_path=INPUT_EXAMPLES_DIR,
        trace_path=tmp_path / "capture_trace.jsonl",
        summary_path=summary_path,
        report_path=tmp_path / "capture_report.md",
    )
    saved = json.loads(summary_path.read_text(encoding="utf-8"))

    assert saved["summary"] == payload["summary"]
    assert {
        "total_events_processed",
        "valid_pre_execution_gate_events",
        "observer_only_events",
        "unsupported_missing_field_events",
        "allowed",
        "denied",
        "ask",
        "adapter_coverage_gap_count",
        "observer_only_blocked_count",
        "executor_called_on_deny",
        "executor_called_on_ask",
        "trace_path",
    } <= set(payload["summary"])


def test_jsonl_input_supported(tmp_path: Path) -> None:
    payload = run_prototype(
        jsonl_path=INPUT_EXAMPLES_DIR / "events.jsonl",
        trace_path=tmp_path / "capture_trace.jsonl",
        summary_path=tmp_path / "capture_summary.json",
        report_path=tmp_path / "capture_report.md",
    )

    assert payload["summary"]["total_events_processed"] == 3
    assert payload["summary"]["allowed"] == 1
    assert payload["summary"]["denied"] == 2


def test_no_real_hermes_import_run_subprocess_or_shell(tmp_path: Path) -> None:
    payload = run_payload(tmp_path)
    safety = payload["safety"]

    assert safety["real_hermes_executed"] is False
    assert safety["dependencies_installed"] is False
    assert safety["third_party_commands_executed"] is False
    assert safety["real_tools_executed"] is False
    assert safety["network_used"] is False
    assert safety["real_shell_executed"] is False
