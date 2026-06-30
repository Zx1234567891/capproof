from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_agent_runtime_gate as gate


def test_missing_runtimes_are_graceful_no_go(monkeypatch) -> None:
    monkeypatch.setattr(gate, "_which", lambda command: "")

    summary = gate.build_summary({})

    assert summary.opencode.runtime_present is False
    assert summary.openclaw.runtime_present is False
    assert summary.opencode.real_smoke_eligible is False
    assert summary.openclaw.real_smoke_eligible is False
    assert "runtime_missing" in summary.opencode.reason
    assert "runtime_missing" in summary.openclaw.reason
    assert summary.real_opencode_integration_claim is False
    assert summary.real_openclaw_integration_claim is False


def test_missing_runtime_does_not_probe_subprocess(monkeypatch) -> None:
    monkeypatch.setattr(gate, "_which", lambda command: "")

    def fail_probe(command):
        raise AssertionError("missing runtimes must not run metadata probes")

    monkeypatch.setattr(gate, "_run_probe", fail_probe)

    summary = gate.build_summary({})

    assert summary.opencode.probes == ()
    assert summary.openclaw.probes == ()


def test_fake_opencode_runtime_can_be_metadata_eligible(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "opencode.capproof.mcp.example.jsonc"
    config.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(gate, "_which", lambda command: "/usr/bin/opencode" if command == "opencode" else "")

    def fake_probe(command):
        output = "opencode 1.2.3\nmcp server config tools"
        return gate.CommandProbe(tuple(command), True, 0, True, output, "")

    monkeypatch.setattr(gate, "_run_probe", fake_probe)

    summary = gate.build_summary({"OPENCODE_CONFIG": str(config)})

    assert summary.opencode.runtime_present is True
    assert summary.opencode.version_detected is True
    assert summary.opencode.config_path_detected is True
    assert summary.opencode.can_load_capproof_mcp_config is True
    assert summary.opencode.real_smoke_eligible is True
    assert summary.opencode.real_agent_process_run is False
    assert summary.opencode.tools_list_observed_from_real_agent is False


def test_fake_openclaw_runtime_can_be_metadata_eligible(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "openclaw.capproof.mcp.commands.md"
    config.write_text("openclaw mcp add capproof", encoding="utf-8")
    monkeypatch.setattr(gate, "_which", lambda command: "/usr/bin/openclaw" if command == "openclaw" else "")

    def fake_probe(command):
        output = "openclaw 0.4.0\nmcp status doctor probe tools add"
        return gate.CommandProbe(tuple(command), True, 0, True, output, "")

    monkeypatch.setattr(gate, "_run_probe", fake_probe)

    summary = gate.build_summary({"OPENCLAW_CONFIG": str(config)})

    assert summary.openclaw.runtime_present is True
    assert summary.openclaw.version_detected is True
    assert summary.openclaw.mcp_status_available is True
    assert summary.openclaw.mcp_doctor_probe_available is True
    assert summary.openclaw.mcp_tools_available is True
    assert summary.openclaw.can_load_capproof_mcp_config is True
    assert summary.openclaw.real_smoke_eligible is True
    assert summary.openclaw.real_agent_process_run is False


def test_write_artifacts_generates_runtime_gate_reports(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(gate, "SUMMARY_JSON", tmp_path / "agent_runtime_gate_summary.json")
    monkeypatch.setattr(gate, "REPORT_MD", tmp_path / "agent_runtime_gate_report.md")
    monkeypatch.setattr(gate, "_which", lambda command: "")

    summary = gate.build_summary({})
    gate.write_artifacts(summary)

    assert gate.SUMMARY_JSON.exists()
    assert gate.REPORT_MD.exists()
    report = gate.REPORT_MD.read_text(encoding="utf-8")
    combined = report + gate.SUMMARY_JSON.read_text(encoding="utf-8")
    assert "Stage 34R-G only detects local OpenCode/OpenClaw runtime readiness" in report
    assert "real_opencode_integration_claim: False" in report
    assert "real_openclaw_integration_claim: False" in report
    assert "python run_capproof_mcp_server.py --stdio --sandboxed-real-execution" in report
    assert not re.search(r"sk-[A-Za-z0-9_-]{12,}", combined)


def test_runtime_gate_reuses_capproof_mcp_without_forking_guard(monkeypatch) -> None:
    monkeypatch.setattr(gate, "_which", lambda command: "")

    summary = gate.build_summary({})

    assert summary.uses_shared_capproof_mcp_server is True
    assert "run_capproof_mcp_server.py" in summary.capproof_mcp_command
    assert "--sandboxed-real-execution" in summary.capproof_mcp_command
    assert summary.forked_guard_logic is False
    assert summary.production_level_protection_claim is False
    assert summary.api_key_written is False
    assert summary.external_or_venv_committed is False
