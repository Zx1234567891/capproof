from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_agent_runtime_gate as gate


def _probe(label: str, command: tuple[str, ...], *, ok: bool, output: str = "") -> gate.CommandProbe:
    return gate.CommandProbe(
        label=label,
        command=command,
        attempted=True,
        exit_code=0 if ok else 1,
        available=ok,
        output_excerpt=output,
        error="" if ok else output,
    )


def test_missing_runtimes_are_blocked_runtime_missing(monkeypatch) -> None:
    def fake_probe(label, command):
        return _probe(label, tuple(command), ok=False, output="")

    monkeypatch.setattr(gate, "run_probe", fake_probe)

    summary = gate.build_summary({})

    assert summary.stage == "39RT"
    assert summary.real_environment_policy_active is True
    assert summary.dry_run_counts_as_completion is False
    assert summary.opencode.runtime_present is False
    assert summary.openclaw.runtime_present is False
    assert summary.opencode.source_repo_present is True
    assert summary.openclaw.source_repo_present is True
    assert summary.opencode.real_smoke_eligible is False
    assert summary.openclaw.real_smoke_eligible is False
    assert summary.opencode.reason == "blocked_runtime_missing"
    assert summary.openclaw.reason == "blocked_runtime_missing"
    assert summary.opencode.blocked_runtime_missing is True
    assert summary.openclaw.blocked_runtime_missing is True
    assert summary.integration_claim_made is False


def test_missing_runtime_still_records_real_which_probe(monkeypatch) -> None:
    def fake_probe(label, command):
        return _probe(label, tuple(command), ok=False, output="")

    monkeypatch.setattr(gate, "run_probe", fake_probe)

    summary = gate.build_summary({})

    assert summary.opencode.probes[0].label == "which_opencode"
    assert summary.opencode.probes[0].attempted is True
    assert summary.openclaw.probes[0].label == "which_openclaw"
    assert summary.openclaw.probes[0].attempted is True


def test_config_template_alone_cannot_make_opencode_eligible(monkeypatch) -> None:
    calls = []

    def fake_probe(label, command):
        calls.append(label)
        if label == "which_opencode":
            return _probe(label, tuple(command), ok=False, output="")
        if label == "which_openclaw":
            return _probe(label, tuple(command), ok=False, output="")
        raise AssertionError("missing runtime should stop after discovery")

    monkeypatch.setattr(gate, "run_probe", fake_probe)

    summary = gate.build_summary({})

    assert summary.opencode.capproof_mcp_config_template_exists is True
    assert summary.opencode.capproof_mcp_command_referenced is True
    assert summary.opencode.source_repo_present is True
    assert summary.opencode.real_smoke_eligible is False
    assert calls == ["which_opencode", "which_openclaw"]


def test_fake_opencode_runtime_can_be_real_smoke_eligible(monkeypatch) -> None:
    def fake_probe(label, command):
        if label == "which_opencode":
            return _probe(label, tuple(command), ok=True, output="/usr/bin/opencode\n")
        if label == "opencode_version_dash":
            return _probe(label, tuple(command), ok=True, output="opencode 1.2.3\n")
        if label == "opencode_help":
            return _probe(label, tuple(command), ok=True, output="usage: opencode config mcp tools\n")
        if label == "which_openclaw":
            return _probe(label, tuple(command), ok=False, output="")
        return _probe(label, tuple(command), ok=False, output="")

    monkeypatch.setattr(gate, "run_probe", fake_probe)

    summary = gate.build_summary({})

    assert summary.opencode.runtime_present is True
    assert summary.opencode.source_repo_present is True
    assert summary.opencode.version_detected == "opencode 1.2.3"
    assert summary.opencode.config_load_supported is True
    assert summary.opencode.real_smoke_eligible is True
    assert summary.opencode.reason == "ok"
    assert summary.opencode.real_agent_process_run is False
    assert summary.opencode.tools_list_observed_from_real_agent is False
    assert summary.real_opencode_integration_claim is False


def test_fake_openclaw_runtime_can_be_real_smoke_eligible(monkeypatch) -> None:
    def fake_probe(label, command):
        if label == "which_opencode":
            return _probe(label, tuple(command), ok=False, output="")
        if label == "which_openclaw":
            return _probe(label, tuple(command), ok=True, output="/usr/bin/openclaw\n")
        if label == "openclaw_version_dash":
            return _probe(label, tuple(command), ok=True, output="openclaw 0.4.0\n")
        if label == "openclaw_mcp_status":
            return _probe(label, tuple(command), ok=True, output="capproof ok\n")
        if label == "openclaw_mcp_doctor_probe":
            return _probe(label, tuple(command), ok=True, output="probe ok\n")
        if label == "openclaw_mcp_tools":
            return _probe(label, tuple(command), ok=True, output="capproof tools\n")
        return _probe(label, tuple(command), ok=False, output="")

    monkeypatch.setattr(gate, "run_probe", fake_probe)

    summary = gate.build_summary({})

    assert summary.openclaw.runtime_present is True
    assert summary.openclaw.source_repo_present is True
    assert summary.openclaw.version_detected == "openclaw 0.4.0"
    assert summary.openclaw.mcp_status_available is True
    assert summary.openclaw.mcp_doctor_probe_available is True
    assert summary.openclaw.mcp_tools_available is True
    assert summary.openclaw.real_smoke_eligible is True
    assert summary.openclaw.real_agent_process_run is False
    assert summary.real_openclaw_integration_claim is False


def test_write_artifacts_generates_runtime_gate_reports(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(gate, "SUMMARY_JSON", tmp_path / "agent_runtime_gate_summary.json")
    monkeypatch.setattr(gate, "REPORT_MD", tmp_path / "agent_runtime_gate_report.md")
    monkeypatch.setattr(gate, "MATRIX_JSON", tmp_path / "agent_runtime_gate_matrix.json")
    monkeypatch.setattr(gate, "MATRIX_MD", tmp_path / "agent_runtime_gate_matrix.md")
    monkeypatch.setattr(gate, "OPENCODE_REPORT", tmp_path / "opencode_runtime_gate_report.md")
    monkeypatch.setattr(gate, "OPENCLAW_REPORT", tmp_path / "openclaw_runtime_gate_report.md")

    def fake_probe(label, command):
        return _probe(label, tuple(command), ok=False, output="")

    monkeypatch.setattr(gate, "run_probe", fake_probe)

    summary = gate.build_summary({})
    gate.write_artifacts(summary)

    assert gate.SUMMARY_JSON.exists()
    assert gate.REPORT_MD.exists()
    assert gate.MATRIX_JSON.exists()
    assert gate.MATRIX_MD.exists()
    assert gate.OPENCODE_REPORT.exists()
    assert gate.OPENCLAW_REPORT.exists()
    report = gate.REPORT_MD.read_text(encoding="utf-8")
    combined = report + gate.SUMMARY_JSON.read_text(encoding="utf-8")
    assert "Stage 39RT performs real local runtime discovery/version/probe commands" in report
    assert "blocked_runtime_missing" in report
    assert "integration_claim_made: False" in report
    assert "python run_capproof_mcp_server.py --stdio --sandboxed-real-execution" in report
    assert not re.search(r"sk-[A-Za-z0-9_-]{12,}", combined)


def test_runtime_gate_reuses_capproof_mcp_without_forking_guard(monkeypatch) -> None:
    def fake_probe(label, command):
        return _probe(label, tuple(command), ok=False, output="")

    monkeypatch.setattr(gate, "run_probe", fake_probe)

    summary = gate.build_summary({})

    assert summary.uses_shared_capproof_mcp_server is True
    assert "run_capproof_mcp_server.py" in summary.capproof_mcp_command
    assert "--sandboxed-real-execution" in summary.capproof_mcp_command
    assert summary.forked_guard_logic is False
    assert summary.production_level_protection_claim is False
    assert summary.api_key_written is False
    assert summary.external_venv_node_modules_runtime_cache_committed is False
