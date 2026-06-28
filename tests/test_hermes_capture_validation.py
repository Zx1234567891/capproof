from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_hermes_capture_validation import REPORT_PATH, run_validation


def result_by_id(payload: dict, case_id: str) -> dict:
    for result in payload["results"]:
        if result["case_id"] == case_id:
            return result
    raise AssertionError(f"missing result for {case_id}")


def test_valid_terminal_pre_exec_converts_and_allows_with_pytest_cap(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    result = result_by_id(payload, "terminal_pytest_pre_exec")

    assert result["validation_valid"] is True
    assert result["actual_verdict"] == "ALLOW"
    assert result["executor_called"] is True
    assert result["mock_event"]["mock_tool"] == "run_shell_template"
    assert result["adapter_raw_event"]["event_type"] == "terminal"


def test_raw_shell_pre_exec_denies(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    result = result_by_id(payload, "terminal_raw_shell_pre_exec")

    assert result["actual_verdict"] == "DENY"
    assert result["actual_reason"] == "CommandTemplateViolation"
    assert result["executor_called"] is False


def test_gateway_attacker_recipient_denies(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    result = result_by_id(payload, "send_message_attacker_pre_send")

    assert result["actual_verdict"] == "DENY"
    assert result["actual_reason"] == "NoCap"
    assert result["executor_called"] is False


def test_mcp_evil_endpoint_denies(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    result = result_by_id(payload, "mcp_evil_endpoint_pre_transport")

    assert result["actual_verdict"] == "DENY"
    assert result["actual_reason"] == "NoCap"
    assert result["executor_called"] is False


def test_memory_authority_pre_write_is_stripped(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    result = result_by_id(payload, "memory_authority_pre_write")

    assert result["actual_verdict"] == "ALLOW"
    assert result["executor_called"] is True
    assert result["mock_event"]["mock_tool"] == "memory_write"
    assert result["mock_event"]["args"]["authority_claims"] == {}
    assert result["mock_event"]["args"]["stripped_authority"] is True
    assert result["capability_minted_from_stripped_memory"] is False


def test_delegation_without_cert_denies(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    result = result_by_id(payload, "delegate_without_cert_pre_dispatch")

    assert result["actual_verdict"] == "DENY"
    assert result["actual_reason"] == "DelegationMissing"
    assert result["executor_called"] is False


def test_middleware_effective_args_attacker_denies(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    result = result_by_id(payload, "middleware_effective_args_attacker")

    assert result["actual_verdict"] == "DENY"
    assert result["actual_reason"] == "NoCap"
    assert result["executor_called"] is False
    assert result["adapter_raw_event"]["input"]["effective_args"]["target"] == "telegram:attacker_chat"


def test_observer_only_events_cannot_be_used_for_enforcement_allow(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    observer_results = [result for result in payload["results"] if result["category"] == "observer_only"]

    assert observer_results
    assert all(result["actual_verdict"] == "DENY" for result in observer_results)
    assert all(result["actual_reason"] == "AdapterCoverageGap" for result in observer_results)
    assert all(result["observer_only_blocked"] is True for result in observer_results)
    assert all(result["executor_called"] is False for result in observer_results)


def test_unsupported_missing_fields_fail_closed(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    unsupported_results = [result for result in payload["results"] if result["category"] == "unsupported"]

    assert unsupported_results
    assert all(result["actual_verdict"] == "DENY" for result in unsupported_results)
    assert all(result["actual_reason"] == "AdapterCoverageGap" for result in unsupported_results)
    assert all(result["missing_fields"] for result in unsupported_results)
    assert all(result["executor_called"] is False for result in unsupported_results)


def test_no_real_hermes_import_execution_network_or_shell(tmp_path: Path) -> None:
    payload = run_validation(summary_path=tmp_path / "summary.json")
    safety = payload["safety"]

    assert safety["real_hermes_executed"] is False
    assert safety["dependencies_installed"] is False
    assert safety["third_party_commands_executed"] is False
    assert safety["real_tools_executed"] is False
    assert safety["network_used"] is False
    assert safety["real_shell_executed"] is False


def test_summary_schema_and_report_generated(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    payload = run_validation(summary_path=summary_path)

    assert summary_path.exists()
    assert REPORT_PATH.exists()
    assert {
        "total_events",
        "pre_execution_gate_events",
        "observer_only_events",
        "unsupported_events",
        "allowed",
        "denied",
        "ask",
        "adapter_coverage_gap_count",
        "observer_only_blocked_from_enforcement_count",
        "executor_called_on_denied",
        "executor_called_on_ask",
    } <= set(payload["summary"])
