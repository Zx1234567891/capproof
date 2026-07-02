from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_artifact_reproduction_check as repro


def test_artifact_reproduction_check_reports_no_real_hermes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(repro, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(repro, "REPORT_MD", tmp_path / "artifact_reproduction_report.md")
    monkeypatch.setattr(repro, "SUMMARY_JSON", tmp_path / "artifact_reproduction_summary.json")
    monkeypatch.setattr(
        repro,
        "run_command",
        lambda command, env: {"command": " ".join(command), "returncode": 0, "stdout": "", "stderr": ""},
    )
    monkeypatch.setattr(repro, "scan_for_real_keys", lambda: {"ok": True, "matches": []})
    monkeypatch.setattr(repro, "tracked_forbidden_paths", lambda: {"ok": True, "tracked": []})

    summary = repro.run_checks(no_secret=True, local_only=True)
    repro.write_reports(summary)

    assert summary["passed"] is True
    assert summary["real_hermes_run"] is False
    assert summary["deepseek_called"] is False
    assert summary["real_email"] is False
    assert summary["external_mcp"] is False
    assert summary["production_level_protection_claim"] is False
    assert (tmp_path / "artifact_reproduction_report.md").exists()
    assert (tmp_path / "artifact_reproduction_summary.json").exists()


def test_secret_scan_detects_current_key(monkeypatch, tmp_path: Path) -> None:
    fake_key = "fake-deepseek-key-for-test"
    secret_file = tmp_path / "leak.txt"
    secret_file.write_text(fake_key, encoding="utf-8")
    monkeypatch.setenv("DEEPSEEK_API_KEY", fake_key)
    monkeypatch.setattr(repro, "tracked_paths", lambda: [secret_file])

    result = repro.scan_for_real_keys()

    assert result["ok"] is False
    assert "leak.txt" in result["matches"][0]


def test_reproduction_report_contains_non_claims() -> None:
    summary = {
        "passed": True,
        "default_no_secret": True,
        "default_local_only": True,
        "real_hermes_run": False,
        "deepseek_called": False,
        "real_email": False,
        "real_shell": False,
        "external_mcp": False,
        "secret_scan": {"ok": True, "matches": []},
        "tracked_forbidden_paths": {"tracked": []},
        "commands": [{"command": "python tools/run_capproof_mcp_server.py --list-tools", "returncode": 0}],
        "packaging_tests": {"command": "pytest packaging tests", "returncode": 0},
    }

    text = repro.format_markdown(summary)

    assert "No production-level Hermes protection" in text
    assert "No all-Hermes-tool-paths-covered claim" in text
    assert "No external MCP" in text
