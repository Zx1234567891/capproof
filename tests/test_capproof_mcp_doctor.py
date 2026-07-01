from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_capproof_mcp_doctor as doctor


def test_doctor_checks_local_mcp_without_printing_key(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate(monkeypatch, tmp_path)
    fake_key = "redacted-" + "doctor-secret"
    monkeypatch.setenv("DEEPSEEK_API_KEY", fake_key)

    rc = doctor.main(["--all"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "doctor_passed=True" in out
    assert "deepseek_api_key_present=True" in out
    assert "deepseek_api_key_value=REDACTED" in out
    assert fake_key not in out
    assert "tools_count=7" in out
    assert "mcp_stdio_stdout_pollution_check_passes=True" in out
    assert doctor.UX_REPORT.exists()
    assert doctor.UX_SUMMARY.exists()


def test_doctor_summary_contains_safety_boundary(monkeypatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)

    summary = doctor.run_checks()

    checks = summary["checks"]
    assert summary["passed"] is True
    assert checks["tools_list_ok"] is True
    assert checks["tools_count"] == 7
    assert checks["deepseek_not_safety_tcb"] is True
    assert checks["capproof_guard_gates_tools"] is True
    assert checks["production_level_protection_claim"] is False


def _isolate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(doctor.foreground, "TRACE_DIR", tmp_path / "traces")
    monkeypatch.setattr(doctor.foreground, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(doctor.foreground, "TRACE_PATH", tmp_path / "traces" / "foreground_trace.jsonl")
    monkeypatch.setattr(doctor.foreground, "LIVE_LOG_PATH", tmp_path / "reports" / "foreground_live.log")
    monkeypatch.setattr(doctor.foreground, "SANDBOX_WORKSPACE", tmp_path / "workspace")
    monkeypatch.setattr(doctor, "UX_REPORT", tmp_path / "reports" / "foreground_ux_report.md")
    monkeypatch.setattr(doctor, "UX_SUMMARY", tmp_path / "reports" / "foreground_ux_summary.json")
