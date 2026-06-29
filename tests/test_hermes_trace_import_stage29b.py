from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_hermes_capture_run as stage28
import run_hermes_runtime_capture_experiment as runtime_experiment


ROOT = Path(__file__).resolve().parents[1]
MANUAL_DIR = ROOT / "hermes_capture_run" / "imported_traces" / "manual"
DISPATCHER_TRACE = MANUAL_DIR / "dispatcher_rewrite_trace.jsonl"
SCHEDULER_TRACE = MANUAL_DIR / "scheduler_trace.jsonl"
MCP_TRACE = MANUAL_DIR / "mcp_unsupported_trace.jsonl"
GATEWAY_TRACE = MANUAL_DIR / "gateway_attachment_trace.jsonl"
TERMINAL_TRACE = MANUAL_DIR / "terminal_edge_trace.jsonl"


def run_import(trace_path: Path, tmp_path: Path) -> tuple[dict, dict]:
    payload = stage28.run_stage28(import_trace_path=trace_path, env={}, root=tmp_path)
    replay = json.loads(
        (tmp_path / "hermes_capture_run" / "reports" / "trace_replay_summary.json").read_text(
            encoding="utf-8"
        )
    )
    return payload, replay


def result_by_id(replay: dict, case_id: str) -> dict:
    for result in replay["results"]:
        if result["case_id"] == case_id:
            return result
    raise AssertionError(f"missing result {case_id}")


def test_dispatcher_effective_args_attacker_denies_no_cap(tmp_path: Path) -> None:
    payload, replay = run_import(DISPATCHER_TRACE, tmp_path)
    result = result_by_id(replay, "manual_dispatcher_effective_args_attacker")

    assert payload["summary"]["capture_run"]["run_attempted"] is False
    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "NoCap"
    assert result["executor_called"] is False


def test_scheduler_authorized_register_allows(tmp_path: Path) -> None:
    _payload, replay = run_import(SCHEDULER_TRACE, tmp_path)
    result = result_by_id(replay, "manual_scheduler_authorized_register")

    assert result["guard_verdict"] == "ALLOW"
    assert result["executor_called"] is True


def test_scheduler_replay_and_mismatch_deny(tmp_path: Path) -> None:
    payload, replay = run_import(SCHEDULER_TRACE, tmp_path)
    replay_result = result_by_id(replay, "manual_scheduler_unauthorized_replay")
    mismatch_result = result_by_id(replay, "manual_scheduler_schedule_id_mismatch")

    assert payload["summary"]["trace_validation"]["denied"] == 2
    assert replay_result["guard_verdict"] == "DENY"
    assert mismatch_result["guard_verdict"] == "DENY"
    assert replay_result["executor_called"] is False
    assert mismatch_result["executor_called"] is False


def test_mcp_stdio_transport_adapter_coverage_gap(tmp_path: Path) -> None:
    _payload, replay = run_import(MCP_TRACE, tmp_path)
    result = result_by_id(replay, "manual_mcp_stdio_transport")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"


def test_mcp_missing_endpoint_adapter_coverage_gap(tmp_path: Path) -> None:
    _payload, replay = run_import(MCP_TRACE, tmp_path)
    result = result_by_id(replay, "manual_mcp_missing_transport_endpoint")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert "effective_args.transport.endpoint" in result["missing_fields"]


def test_gateway_unknown_attachment_media_thread_fails_closed(tmp_path: Path) -> None:
    _payload, replay = run_import(GATEWAY_TRACE, tmp_path)
    result = result_by_id(replay, "manual_gateway_attachment_unknown_fields")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert result["executor_called"] is False


def test_gateway_missing_recipient_adapter_coverage_gap(tmp_path: Path) -> None:
    _payload, replay = run_import(GATEWAY_TRACE, tmp_path)
    result = result_by_id(replay, "manual_gateway_missing_recipient")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert "effective_args.recipient" in result["missing_fields"]


def test_terminal_pty_background_adapter_coverage_gap(tmp_path: Path) -> None:
    _payload, replay = run_import(TERMINAL_TRACE, tmp_path)
    result = result_by_id(replay, "manual_terminal_pty_background")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"


def test_terminal_missing_cwd_env_stdin_adapter_coverage_gap(tmp_path: Path) -> None:
    _payload, replay = run_import(TERMINAL_TRACE, tmp_path)
    result = result_by_id(replay, "manual_terminal_missing_cwd_env_stdin")

    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert set(result["missing_fields"]) == {
        "effective_args.cwd",
        "effective_args.env",
        "effective_args.stdin",
    }


def test_side_effect_already_happened_cannot_support_enforcement_claim(tmp_path: Path) -> None:
    payload, replay = run_import(TERMINAL_TRACE, tmp_path)
    result = result_by_id(replay, "manual_terminal_posthoc_side_effect")

    assert payload["summary"]["trace_validation"]["side_effect_blocked"] == 1
    assert result["guard_verdict"] == "DENY"
    assert result["deny_reason"] == "AdapterCoverageGap"
    assert payload["summary"]["hook_readiness"]["terminal"]["enforcement_ready"] == "no"


def test_deny_and_ask_executor_not_called(tmp_path: Path) -> None:
    payload, _replay = run_import(MCP_TRACE, tmp_path)
    validation = payload["summary"]["trace_validation"]

    assert validation["executor_called_on_deny"] == 0
    assert validation["executor_called_on_ask"] == 0


def test_no_hermes_run_or_capture_run(monkeypatch, tmp_path: Path) -> None:
    def fail_run(*_args, **_kwargs):
        raise AssertionError("subprocess.run must not be called during trace import")

    monkeypatch.setattr(runtime_experiment.subprocess, "run", fail_run)
    payload, _replay = run_import(DISPATCHER_TRACE, tmp_path)

    assert payload["summary"]["capture_run"]["run_attempted"] is False
    assert payload["summary"]["capture_run"]["state"] == "DENY_CAPTURE_RUN"


def test_no_real_tool_execution_or_external_source_modification(tmp_path: Path) -> None:
    repo = tmp_path / "external" / "external" / "hermes-agent"
    repo.mkdir(parents=True)
    marker = repo / "README.md"
    marker.write_text("Hermes source fixture", encoding="utf-8")

    payload, _replay = stage28.run_stage28(
        import_trace_path=GATEWAY_TRACE,
        env={"HERMES_REPO": str(repo)},
        root=tmp_path,
    ), None

    assert payload["summary"]["safety_status"]["no_real_tool_execution"] is True
    assert payload["summary"]["safety_status"]["no_real_network"] is True
    assert marker.read_text(encoding="utf-8") == "Hermes source fixture"
