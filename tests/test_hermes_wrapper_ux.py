from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_hermes_capproof_foreground as entry


SECRET = "redacted-wrapper-secret"


def test_where_trace_outputs_paths_without_key(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate(monkeypatch, tmp_path)

    rc = entry.main(["--where-trace"], env={"DEEPSEEK_API_KEY": SECRET})

    out = capsys.readouterr().out
    assert rc == 0
    assert "foreground_trace_jsonl_path=" in out
    assert "foreground_live_log_path=" in out
    assert "sandbox_workspace_path=" in out
    assert SECRET not in out


def test_capproof_status_reports_latest_verdict(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(
        entry.run_capproof_mcp_doctor,
        "run_checks",
        lambda: {"checks": {"tools_count": 7}},
    )
    monkeypatch.setattr(
        entry.run_capproof_trace_viewer,
        "read_trace",
        lambda path: ([{"tool_name": "capproof.send_message_mock", "capproof_verdict": "DENY", "reason": "NoCap", "executor_called": False}], 0),
    )

    rc = entry.main(["--capproof-status"], env={})

    out = capsys.readouterr().out
    assert rc == 0
    assert "capproof_mcp_attached=True" in out
    assert "tools_count=7" in out
    assert "latest_verdict=DENY" in out
    assert "latest_reason=NoCap" in out


def test_doctor_subcommand_delegates_without_requiring_key(monkeypatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)
    captured = {}

    def fake_doctor(args):
        captured["args"] = args
        return 0

    monkeypatch.setattr(entry.run_capproof_mcp_doctor, "main", fake_doctor)

    rc = entry.main(["--doctor"], env={})

    assert rc == 0
    assert captured["args"] == ["--all"]


def test_trace_follow_subcommand_delegates_without_requiring_key(monkeypatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)
    captured = {}

    def fake_viewer(args):
        captured["args"] = args
        return 0

    monkeypatch.setattr(entry.run_capproof_trace_viewer, "main", fake_viewer)

    rc = entry.main(["--trace-follow"], env={})

    assert rc == 0
    assert captured["args"] == ["--latest", "--follow"]


def test_startup_banner_goes_to_stderr_and_uses_tui_default(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate(monkeypatch, tmp_path)
    captured = {}

    def fake_run(command, cwd, env, check, shell):
        captured["command"] = command
        captured["shell"] = shell
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(entry.subprocess, "run", fake_run)

    rc = entry.main([], env={"DEEPSEEK_API_KEY": SECRET})

    streams = capsys.readouterr()
    assert rc == 0
    assert "--tui" in captured["command"]
    assert "--cli" not in captured["command"]
    assert captured["shell"] is False
    assert "CapProof MCP attached: yes" in streams.err
    assert "MCP mode: stdio" in streams.err
    assert "sandboxed-real-execution: enabled" in streams.err
    assert "exposed tools: 7" in streams.err
    assert SECRET not in streams.out
    assert SECRET not in streams.err


def _isolate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entry.foreground, "CONFIG_PATH", tmp_path / "hermes.capproof.foreground.mcp.json")
    monkeypatch.setattr(entry.foreground, "REPORT_PATH", tmp_path / "foreground_report.md")
    monkeypatch.setattr(entry.foreground, "SUMMARY_PATH", tmp_path / "foreground_summary.json")
    monkeypatch.setattr(entry.foreground, "LIVE_LOG_PATH", tmp_path / "foreground_live.log")
    monkeypatch.setattr(entry.foreground, "TRACE_PATH", tmp_path / "foreground_trace.jsonl")
    monkeypatch.setattr(entry.foreground, "SANDBOX_WORKSPACE", tmp_path / "workspace")
    monkeypatch.setattr(entry.run_capproof_mcp_doctor, "UX_SUMMARY", tmp_path / "foreground_ux_summary.json")
