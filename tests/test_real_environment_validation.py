from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_real_environment_validation as realenv


def test_require_real_missing_gates_fails(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate(monkeypatch, tmp_path)
    for name in realenv.REQUIRED_GATES:
        monkeypatch.delenv(name, raising=False)

    rc = realenv.main(["--require-real", "--fail-if-gate-missing", "--json"])

    out = capsys.readouterr().out
    assert rc != 0
    assert "blocked_missing_real_env_gate" in out
    assert "real_environment_passed" in out
    assert "true" not in out.split('"real_environment_passed": ', 1)[1].split(",", 1)[0]


def test_preflight_does_not_mark_real_environment_passed(monkeypatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)
    for name in realenv.REQUIRED_GATES:
        if name == "DEEPSEEK_API_KEY":
            monkeypatch.setenv(name, "fake-key")
        else:
            monkeypatch.setenv(name, "1")

    preflight = realenv.run_preflight(dict(realenv.os.environ))
    summary = realenv.build_summary(preflight=preflight, selected=realenv.SCENARIOS, command_results=[], observability_results=[])

    assert summary["preflight"]["gate_ready"] is True
    assert summary["real_environment_passed"] is False
    assert summary["status"] == "failed_or_not_run"


def test_summary_schema_fields_exist(monkeypatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)
    preflight = {"missing_gates": ["DEEPSEEK_API_KEY"], "gate_ready": False, "required_gates": list(realenv.REQUIRED_GATES)}

    summary = realenv.build_summary(preflight=preflight, selected=realenv.SCENARIOS, command_results=[], observability_results=[])

    for key in (
        "real_environment_passed",
        "real_hermes_foreground_run",
        "real_deepseek_call",
        "standard_mcp_server_used",
        "tools_list_observed",
        "tools_call_observed",
        "sandbox_read_executed",
        "sandbox_write_executed",
        "command_template_executed",
        "raw_shell_subprocess_started",
        "attacker_recipient_executor_called",
        "ask_pending_request_created",
        "trusted_approval_executed",
        "approval_receipt_generated",
        "rerun_allow_observed",
        "llm_claimed_approval_rejected",
        "mcp_meta_approval_rejected",
        "scope_amplification_rejected",
        "stdout_polluted_mcp_stdio",
        "key_leak_detected",
        "production_level_overclaim",
        "tests_summary",
    ):
        assert key in summary


def test_report_contains_real_non_real_distinction(monkeypatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)
    summary = realenv.build_summary(
        preflight={"missing_gates": ["DEEPSEEK_API_KEY"], "gate_ready": False, "required_gates": list(realenv.REQUIRED_GATES)},
        selected=realenv.SCENARIOS,
        command_results=[],
        observability_results=[],
    )

    text = realenv.render_report(summary)

    assert "Dry-run and preflight are safety readiness only" in text
    assert "real_environment_passed" in text
    assert "No production-level Hermes protection" in text


def test_gate_names_are_documented() -> None:
    text = Path("REAL_ENVIRONMENT_VALIDATION.md").read_text(encoding="utf-8")
    for name in realenv.REQUIRED_GATES:
        assert name in text
    assert "not completion evidence" in text


def test_prohibited_claims_absent_from_policy() -> None:
    text = Path("REAL_ENVIRONMENT_VALIDATION.md").read_text(encoding="utf-8")
    assert "Production wrapper protection" in text
    assert "OS-level network denial unless implemented and tested" in text
    assert "DeepSeek remains outside the CapProof safety TCB" in text


def test_generated_report_is_redaction_safe(monkeypatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)
    secret = "fake-real-env-key"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    result = {"label": "cmd", "command": "python x", "returncode": 0, "stdout_tail": secret, "stderr_tail": ""}

    redacted = realenv.redact(result["stdout_tail"], dict(realenv.os.environ))

    assert secret not in redacted
    assert "[REDACTED]" in redacted


def test_integration_with_existing_scripts_is_wired() -> None:
    commands = {label: " ".join(command) for label, command in realenv.REAL_COMMANDS}
    assert "run_real_hermes_foreground_mcp_demo.py" in commands["foreground"]
    assert "run_real_hermes_sandbox_mcp_smoke.py" in commands["sandbox"]
    assert "run_real_hermes_foreground_ask_flow.py" in commands["ask"]
    assert len(realenv.REAL_COMMANDS) == 3


def _isolate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(realenv, "ARTIFACT_REPORT_DIR", tmp_path / "artifact_reports")
    monkeypatch.setattr(realenv, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(realenv, "TRACE_DIR", tmp_path / "traces")
    monkeypatch.setattr(realenv, "REPORT_PATH", tmp_path / "artifact_reports" / "real_environment_validation_report.md")
    monkeypatch.setattr(realenv, "SUMMARY_PATH", tmp_path / "artifact_reports" / "real_environment_validation_summary.json")
    monkeypatch.setattr(realenv, "LIVE_LOG_PATH", tmp_path / "reports" / "real_environment_validation_live.log")
    monkeypatch.setattr(realenv, "TRACE_PATH", tmp_path / "traces" / "real_environment_validation_trace.jsonl")
    monkeypatch.setattr(realenv, "MATRIX_MD_PATH", tmp_path / "reports" / "real_environment_validation_matrix.md")
    monkeypatch.setattr(realenv, "MATRIX_JSON_PATH", tmp_path / "reports" / "real_environment_validation_matrix.json")
    monkeypatch.setattr(
        realenv,
        "SUMMARY_FILES",
        {
            "foreground": tmp_path / "missing_foreground.json",
            "sandbox": tmp_path / "missing_sandbox.json",
            "ask": tmp_path / "missing_ask.json",
            "doctor": tmp_path / "missing_doctor.json",
        },
    )
