import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_agent_mcp_client_audit as audit


def test_build_summary_records_missing_repos_without_running_agents(tmp_path: Path) -> None:
    env = {"OPENCODE_REPO": str(tmp_path / "missing-opencode"), "OPENCLAW_REPO": str(tmp_path / "missing-openclaw")}

    summary = audit.build_summary(env)

    assert summary.opencode.repo_exists is False
    assert summary.openclaw.repo_exists is False
    assert summary.opencode.real_agent_run is False
    assert summary.openclaw.real_agent_run is False
    assert summary.opencode.tools_list_observed_from_real_agent is False
    assert summary.openclaw.tools_call_observed_from_real_agent is False


def test_local_json_rpc_dry_run_reuses_capproof_mcp_server() -> None:
    summary = audit.build_summary({})
    dry = summary.local_json_rpc_dry_run

    assert summary.uses_shared_capproof_mcp_server is True
    assert summary.forked_guard_logic is False
    assert "run_capproof_mcp_server.py" in summary.capproof_mcp_command
    assert "--sandboxed-real-execution" in summary.capproof_mcp_command
    assert dry.tools_list_passed is True
    assert dry.tools_call_passed is True
    assert dry.tools_count == 7
    assert dry.allow_verdict == "ALLOW"
    assert dry.deny_verdict == "DENY"
    assert dry.deny_reason == "NoCap"
    assert dry.deny_executor_called is False


def test_metadata_and_llm_output_cannot_mint_or_allow() -> None:
    dry = audit.run_local_json_rpc_dry_run()

    assert dry.metadata_cannot_mint_capability is True
    assert dry.llm_output_cannot_allow_tool_call is True
    assert dry.deny_executor_called is False


def test_write_all_artifacts_generates_reports(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path / "agent_coverage_audit")
    monkeypatch.setattr(audit, "OPENCODE_DIR", tmp_path / "opencode")
    monkeypatch.setattr(audit, "OPENCLAW_DIR", tmp_path / "openclaw")
    monkeypatch.setattr(audit, "OPENCODE_CONFIG", tmp_path / "opencode" / "configs" / "opencode.capproof.mcp.example.jsonc")
    monkeypatch.setattr(audit, "OPENCLAW_COMMANDS", tmp_path / "openclaw" / "configs" / "openclaw.capproof.mcp.commands.md")
    monkeypatch.setattr(audit, "OPENCODE_REPORT", tmp_path / "opencode" / "reports" / "opencode_mcp_config_report.md")
    monkeypatch.setattr(audit, "OPENCODE_SUMMARY", tmp_path / "opencode" / "reports" / "opencode_mcp_config_summary.json")
    monkeypatch.setattr(audit, "OPENCLAW_REPORT", tmp_path / "openclaw" / "reports" / "openclaw_mcp_config_report.md")
    monkeypatch.setattr(audit, "OPENCLAW_SUMMARY", tmp_path / "openclaw" / "reports" / "openclaw_mcp_config_summary.json")
    monkeypatch.setattr(audit, "MATRIX_JSON", tmp_path / "agent_coverage_audit" / "agent_mcp_client_matrix.json")
    monkeypatch.setattr(audit, "MATRIX_MD", tmp_path / "agent_coverage_audit" / "agent_mcp_client_matrix.md")
    monkeypatch.setattr(audit, "OPENCODE_AUDIT", tmp_path / "agent_coverage_audit" / "opencode_mcp_audit.md")
    monkeypatch.setattr(audit, "OPENCLAW_AUDIT", tmp_path / "agent_coverage_audit" / "openclaw_mcp_audit.md")

    summary = audit.build_summary({})
    audit.write_all_artifacts(summary)

    assert audit.OPENCODE_CONFIG.exists()
    assert audit.OPENCLAW_COMMANDS.exists()
    assert audit.OPENCODE_AUDIT.exists()
    assert audit.OPENCLAW_AUDIT.exists()
    assert audit.MATRIX_JSON.exists()
    loaded = json.loads(audit.MATRIX_JSON.read_text(encoding="utf-8"))
    assert loaded["production_level_protection_claim"] is False
    combined = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*") if path.is_file())
    assert "sk-" not in combined
    assert "DEEPSEEK_API_KEY=" not in combined


def test_summary_does_not_claim_real_opencode_openclaw_integration() -> None:
    summary = audit.build_summary({})

    assert summary.real_opencode_integration_claim is False
    assert summary.real_openclaw_integration_claim is False
    assert summary.production_level_protection_claim is False
    assert summary.external_mcp_claim is False
    assert summary.raw_shell_supported is False
    assert summary.arbitrary_filesystem_access_supported is False
