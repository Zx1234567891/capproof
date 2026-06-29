from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_hermes_capture_run as stage28
import run_hermes_runtime_capture_experiment as runtime_experiment


ROOT = Path(__file__).resolve().parents[1]
MANUAL_DIR = ROOT / "hermes_capture_run" / "imported_traces" / "manual"
SUPPORTED_TRACE = MANUAL_DIR / "supported_trace.jsonl"
DENIED_TRACE = MANUAL_DIR / "denied_trace.jsonl"
MIXED_TRACE = MANUAL_DIR / "mixed_trace.jsonl"


def run_import(trace_path: Path, tmp_path: Path) -> dict:
    return stage28.run_stage28(import_trace_path=trace_path, env={}, root=tmp_path)


def test_supported_trace_jsonl_can_be_parsed(tmp_path: Path) -> None:
    payload = run_import(SUPPORTED_TRACE, tmp_path)
    validation = payload["summary"]["trace_validation"]

    assert validation["total_events"] == 3
    assert validation["schema_valid_events"] == 3
    assert validation["pre_execution_gate_events"] == 3
    assert validation["allowed"] == 3
    assert validation["denied"] == 0
    assert validation["AdapterCoverageGap"] == 0


def test_denied_trace_unauthorized_events_all_deny(tmp_path: Path) -> None:
    payload = run_import(DENIED_TRACE, tmp_path)
    validation = payload["summary"]["trace_validation"]

    assert validation["total_events"] == 4
    assert validation["allowed"] == 0
    assert validation["denied"] == 4
    assert validation["executor_called_on_deny"] == 0


def test_mixed_trace_observer_only_blocked_from_enforcement(tmp_path: Path) -> None:
    payload = run_import(MIXED_TRACE, tmp_path)
    validation = payload["summary"]["trace_validation"]

    assert validation["observer_only_events"] == 1
    assert validation["observer_only_blocked"] == 1
    assert validation["allowed"] == 1


def test_mixed_trace_missing_field_is_adapter_coverage_gap(tmp_path: Path) -> None:
    payload = run_import(MIXED_TRACE, tmp_path)
    validation = payload["summary"]["trace_validation"]
    terminal = payload["summary"]["hook_readiness"]["terminal"]

    assert validation["missing_field_events"] >= 1
    assert validation["AdapterCoverageGap"] >= 1
    assert "effective_args.cwd" in terminal["missing_fields"]


def test_side_effect_already_happened_blocks_enforcement_claim(tmp_path: Path) -> None:
    payload = run_import(MIXED_TRACE, tmp_path)
    validation = payload["summary"]["trace_validation"]
    terminal = payload["summary"]["hook_readiness"]["terminal"]

    assert validation["side_effect_blocked"] == 1
    assert terminal["side_effect_already_happened"] == "yes"
    assert terminal["enforcement_ready"] == "no"


def test_deny_and_ask_do_not_execute_mock_executor(tmp_path: Path) -> None:
    payload = run_import(DENIED_TRACE, tmp_path)
    validation = payload["summary"]["trace_validation"]

    assert validation["executor_called_on_deny"] == 0
    assert validation["executor_called_on_ask"] == 0


def test_trace_reports_are_generated(tmp_path: Path) -> None:
    payload = run_import(SUPPORTED_TRACE, tmp_path)

    assert payload["summary"]["trace_source"] == "imported trace"
    assert (tmp_path / "hermes_capture_run" / "reports" / "capture_run_report.md").exists()
    assert (tmp_path / "hermes_capture_run" / "reports" / "trace_validation_report.md").exists()
    assert (tmp_path / "hermes_capture_run" / "reports" / "hook_readiness_report.md").exists()


def test_manual_trace_import_report_is_generated(tmp_path: Path) -> None:
    manual_dir = tmp_path / "hermes_capture_run" / "imported_traces" / "manual"
    manual_dir.mkdir(parents=True)
    for trace in (SUPPORTED_TRACE, DENIED_TRACE, MIXED_TRACE):
        shutil.copyfile(trace, manual_dir / trace.name)

    stage28.write_manual_trace_import_report_if_available(root=tmp_path)
    report_path = tmp_path / "hermes_capture_run" / "reports" / "manual_trace_import_report.md"
    report = report_path.read_text(encoding="utf-8")

    assert "Total events: 12" in report
    assert "Observer-only blocked" in report
    assert "Real Hermes runtime: not run" in report


def test_import_does_not_run_hermes_or_subprocess(monkeypatch, tmp_path: Path) -> None:
    def fail_run(*_args, **_kwargs):
        raise AssertionError("subprocess.run must not be called for trace import")

    monkeypatch.setattr(runtime_experiment.subprocess, "run", fail_run)
    payload = run_import(SUPPORTED_TRACE, tmp_path)

    assert payload["summary"]["capture_run"]["run_attempted"] is False


def test_import_does_not_use_network(tmp_path: Path) -> None:
    payload = run_import(SUPPORTED_TRACE, tmp_path)

    assert payload["summary"]["safety_status"]["no_real_network"] is True
    assert payload["summary"]["safety_status"]["no_real_tool_execution"] is True


def test_import_does_not_modify_external_source(tmp_path: Path) -> None:
    repo = tmp_path / "external" / "external" / "hermes-agent"
    repo.mkdir(parents=True)
    marker = repo / "README.md"
    marker.write_text("Hermes local checkout fixture", encoding="utf-8")
    before = marker.read_text(encoding="utf-8")

    stage28.run_stage28(
        import_trace_path=SUPPORTED_TRACE,
        env={"HERMES_REPO": str(repo)},
        root=tmp_path,
    )

    assert marker.read_text(encoding="utf-8") == before
