from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_hermes_dry_run import REPORT_PATH, run_dry_run


def test_supported_cases_run_and_allow_with_mock_executor(tmp_path: Path) -> None:
    payload = run_dry_run(category="supported", reports_dir=tmp_path / "reports")
    summary = payload["summary"]

    assert summary["total_cases"] >= 8
    assert summary["supported_unexpected_deny_count"] == 0
    assert summary["supported_allow_count"] == summary["total_cases"]
    assert all(result["actual_verdict"] == "ALLOW" for result in payload["results"])
    assert all(result["executor_called"] is True for result in payload["results"])
    assert all(result["mock_event"] is not None for result in payload["results"])


def test_deny_cases_run_without_unexpected_allow(tmp_path: Path) -> None:
    payload = run_dry_run(category="deny", reports_dir=tmp_path / "reports")
    summary = payload["summary"]

    assert summary["total_cases"] >= 12
    assert summary["sanitized_cases"] == 0
    assert summary["deny_unexpected_allow_count"] == 0
    assert summary["executor_called_on_deny"] == 0
    assert all(result["category"] == "deny" for result in payload["results"])
    assert all(result["actual_verdict"] == "DENY" for result in payload["results"])
    assert all(result["executor_called"] is False for result in payload["results"])


def test_sanitized_memory_cases_allow_content_only_and_mint_no_caps(tmp_path: Path) -> None:
    payload = run_dry_run(category="sanitized", reports_dir=tmp_path / "reports")
    summary = payload["summary"]

    assert summary["total_cases"] == 2
    assert summary["sanitized_cases"] == 2
    assert summary["sanitized_pass_count"] == 2
    assert summary["capability_minted_from_stripped_memory"] == 0
    assert all(result["category"] == "sanitized" for result in payload["results"])
    assert all(result["actual_verdict"] == "ALLOW" for result in payload["results"])
    assert all(result["executor_called"] is True for result in payload["results"])
    for result in payload["results"]:
        mock_event = result["mock_event"]
        assert mock_event["mock_tool"] == "memory_write"
        assert mock_event["args"]["authority_claims"] == {}
        assert mock_event["args"]["stripped_authority"] is True
        assert result["capability_minted_from_stripped_memory"] is False


def test_unknown_cases_fail_closed(tmp_path: Path) -> None:
    payload = run_dry_run(category="unknown", reports_dir=tmp_path / "reports")

    assert payload["summary"]["total_cases"] >= 4
    assert payload["summary"]["unknown_fail_closed_count"] == payload["summary"]["total_cases"]
    assert all(result["actual_verdict"] == "DENY" for result in payload["results"])
    assert all(result["actual_reason"] == "AdapterCoverageGap" for result in payload["results"])
    assert all(result["executor_called"] is False for result in payload["results"])


def test_executor_not_called_on_deny_or_ask(tmp_path: Path) -> None:
    payload = run_dry_run(reports_dir=tmp_path / "reports")

    assert payload["summary"]["executor_called_on_deny"] == 0
    assert payload["summary"]["executor_called_on_ask"] == 0


def test_no_real_hermes_network_shell_or_tool_execution(tmp_path: Path) -> None:
    payload = run_dry_run(reports_dir=tmp_path / "reports")
    safety = payload["safety"]

    assert safety["real_hermes_executed"] is False
    assert safety["dependencies_installed"] is False
    assert safety["third_party_commands_executed"] is False
    assert safety["real_tools_executed"] is False
    assert safety["network_used"] is False
    assert safety["real_shell_executed"] is False


def test_summary_json_schema_and_report_generated(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    payload = run_dry_run(reports_dir=reports_dir)
    summary_path = reports_dir / "summary.json"

    assert summary_path.exists()
    assert REPORT_PATH.exists()
    assert {
        "total_cases",
        "supported_cases",
        "sanitized_cases",
        "explicit_deny_cases",
        "unknown_cases",
        "supported_allow_count",
        "supported_pass_count",
        "sanitized_pass_count",
        "capability_minted_from_stripped_memory",
        "supported_unexpected_deny_count",
        "deny_expected_deny_count",
        "deny_unexpected_allow_count",
        "unknown_fail_closed_count",
        "executor_called_on_deny",
        "executor_called_on_ask",
        "remaining_gaps",
    } <= set(payload["summary"])
