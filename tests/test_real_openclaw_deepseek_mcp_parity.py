from pathlib import Path
import json
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_real_openclaw_deepseek_mcp_parity as parity


def _patch_paths(monkeypatch, tmp_path: Path) -> None:
    integration = tmp_path / "real_agent_integrations" / "openclaw_mcp_server"
    monkeypatch.setattr(parity, "INTEGRATION_DIR", integration)
    monkeypatch.setattr(parity, "REPORT_DIR", integration / "reports")
    monkeypatch.setattr(parity, "TRACE_DIR", integration / "traces")
    monkeypatch.setattr(parity, "CONFIG_DIR", integration / "configs")
    monkeypatch.setattr(parity, "WORKSPACE_DIR", integration / "sandbox_workspace")
    monkeypatch.setattr(parity, "AUTH_EXAMPLES_DIR", integration / "auth_queue_examples")
    monkeypatch.setattr(parity, "CONFIG_PATH", integration / "configs" / "openclaw.capproof.deepseek.real.json5")
    monkeypatch.setattr(parity, "REPORT_PATH", integration / "reports" / "real_openclaw_deepseek_parity_report.md")
    monkeypatch.setattr(parity, "SUMMARY_PATH", integration / "reports" / "real_openclaw_deepseek_parity_summary.json")
    monkeypatch.setattr(parity, "LIVE_LOG_PATH", integration / "reports" / "real_openclaw_deepseek_parity_live.log")
    monkeypatch.setattr(parity, "TRACE_PATH", integration / "traces" / "real_openclaw_deepseek_parity_trace.jsonl")
    monkeypatch.setattr(parity, "EXACT_SCOPE_PATH", integration / "auth_queue_examples" / "exact.json")
    monkeypatch.setattr(parity, "AMPLIFIED_SCOPE_PATH", integration / "auth_queue_examples" / "amplified.json")
    parity.configure_smoke_paths()


def _fake_openclaw(tmp_path: Path) -> Path:
    binary = tmp_path / "external" / ".agent-runtimes" / "bin" / "openclaw"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/usr/bin/env python3\nprint('OpenClaw 2026.6.11 (test)')\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary


def test_require_real_missing_gates_fails(monkeypatch, tmp_path: Path) -> None:
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(parity.smoke, "OPENCLAW_BINARY", _fake_openclaw(tmp_path))
    for name in parity.REQUIRED_GATES:
        monkeypatch.delenv(name, raising=False)

    code = parity.main(["--require-real", "--fail-if-gate-missing"])

    assert code == 2
    summary = json.loads(parity.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["agent_parity_passed"] is False
    assert summary["reason"] == "blocked_missing_real_env_gate"


def test_preflight_does_not_mark_parity(monkeypatch, tmp_path: Path) -> None:
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(parity.smoke, "OPENCLAW_BINARY", _fake_openclaw(tmp_path))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-deepseek-secret-for-test")

    code = parity.main(["--preflight"])

    assert code == 0
    summary = json.loads(parity.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["status"] == "preflight"
    assert summary["agent_parity_passed"] is False
    assert summary["dry_run_counts_as_completion"] is False
    assert summary["deepseek_key_source"] == "DEEPSEEK_API_KEY"


def test_config_uses_env_placeholder_not_key(monkeypatch, tmp_path: Path) -> None:
    _patch_paths(monkeypatch, tmp_path)
    secret = "fake-deepseek-secret-should-not-appear"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    parity.ensure_dirs()
    parity.smoke.prepare_workspace(parity.WORKSPACE_DIR)
    parity.smoke.write_openclaw_config(parity.CONFIG_PATH, parity.WORKSPACE_DIR)

    text = parity.CONFIG_PATH.read_text(encoding="utf-8")

    assert secret not in text
    assert "${DEEPSEEK_API_KEY}" in text
    assert "deepseek" in text
    assert "capproof__capproof-request_authorization" in text


def test_completion_requires_ask_and_deepseek(monkeypatch, tmp_path: Path) -> None:
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(parity.smoke, "OPENCLAW_BINARY", _fake_openclaw(tmp_path))
    parity.ensure_dirs()
    parity.smoke.prepare_workspace(parity.WORKSPACE_DIR)
    parity.smoke.write_openclaw_config(parity.CONFIG_PATH, parity.WORKSPACE_DIR)
    preflight = parity.build_preflight()
    summary = parity.base_summary(preflight, status="running", reason="running")
    summary.update(
        {
            "real_agent_process_ran": True,
            "deepseek_real_call": True,
            "standard_capproof_mcp_server_used": True,
            "tools_list_observed": True,
            "tools_call_observed": True,
            "allow_read_write_command_observed": True,
            "deny_outside_path_raw_shell_attacker_observed": True,
            "ask_pending_request_created": False,
            "trusted_approval_executed": False,
            "approval_receipt_generated": False,
            "rerun_allow_observed": False,
            "llm_metadata_approval_rejected": True,
        }
    )

    assert parity.completion_reason(summary).startswith("blocked_ask_pending_request_created")


def test_report_redacts_key(monkeypatch, tmp_path: Path) -> None:
    _patch_paths(monkeypatch, tmp_path)
    secret = "fake-deepseek-secret-should-not-appear"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    parity.ensure_dirs()
    summary = parity.base_summary(
        {
            "real_environment_policy_active": True,
            "agent_binary": "openclaw",
            "agent_version": "OpenClaw test",
            "standard_capproof_mcp_server_configured": True,
        },
        status="preflight",
        reason="readiness",
    )
    summary["commands"] = [{"stderr_tail": secret}]

    parity.write_artifacts(summary)

    combined = parity.SUMMARY_PATH.read_text(encoding="utf-8") + parity.REPORT_PATH.read_text(encoding="utf-8")
    assert secret not in combined
    assert "production-level OpenClaw protection" in combined
