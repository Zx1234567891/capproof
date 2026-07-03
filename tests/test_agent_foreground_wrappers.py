from __future__ import annotations

import os
from pathlib import Path
import subprocess

import run_opencode_capproof_foreground as opencode_entry
import run_openclaw_capproof_foreground as openclaw_entry


SECRET = "redacted-agent-wrapper-secret"


def test_opencode_wrapper_launches_real_binary_path_with_capproof_config(monkeypatch, tmp_path: Path, capsys) -> None:
    binary = isolate_opencode(monkeypatch, tmp_path)
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="1.17.13\n", stderr="")

    monkeypatch.setattr(opencode_entry.subprocess, "run", fake_run)

    rc = opencode_entry.main([], env={"DEEPSEEK_API_KEY": SECRET})

    streams = capsys.readouterr()
    assert rc == 0
    assert calls[-1][0] == [str(binary)]
    assert calls[-1][1]["shell"] is False
    assert calls[-1][1]["env"]["DEEPSEEK_API_KEY"] == SECRET
    assert "CapProof MCP attached: yes" in streams.err
    assert "agent: OpenCode" in streams.err
    assert SECRET not in streams.out
    assert SECRET not in streams.err
    assert SECRET not in opencode_entry.parity.CONFIG_PATH.read_text()
    assert "tools/run_capproof_mcp_server.py" in opencode_entry.parity.CONFIG_PATH.read_text()


def test_opencode_wrapper_missing_key_fails_before_agent_run(monkeypatch, tmp_path: Path, capsys) -> None:
    isolate_opencode(monkeypatch, tmp_path)

    def fail_run(*args, **kwargs):
        raise AssertionError("OpenCode must not run without DEEPSEEK_API_KEY")

    monkeypatch.setattr(opencode_entry.subprocess, "run", fail_run)

    rc = opencode_entry.main([], env={})

    out = capsys.readouterr().out
    assert rc == 2
    assert "DEEPSEEK_API_KEY is missing" in out
    assert "sk-" not in out


def test_openclaw_wrapper_registers_mcp_then_launches_profile(monkeypatch, tmp_path: Path, capsys) -> None:
    binary = isolate_openclaw(monkeypatch, tmp_path)
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="OpenClaw 2026.6.11\n", stderr="")

    monkeypatch.setattr(openclaw_entry.subprocess, "run", fake_run)

    rc = openclaw_entry.main([], env={"DEEPSEEK_API_KEY": SECRET})

    streams = capsys.readouterr()
    assert rc == 0
    assert calls[0][0][0] == str(binary)
    assert calls[0][0][1:5] == ["--profile", "capproof", "mcp", "add"]
    assert "tools/run_capproof_mcp_server.py" in calls[0][0]
    assert calls[-1][0] == [str(binary), "--profile", "capproof", "tui", "--local", "--session", "main"]
    assert calls[-1][1]["shell"] is False
    assert calls[-1][1]["env"]["DEEPSEEK_API_KEY"] == SECRET
    assert "CapProof MCP attached: yes" in streams.err
    assert "agent: OpenClaw" in streams.err
    assert SECRET not in streams.out
    assert SECRET not in streams.err
    assert SECRET not in openclaw_entry.RUNTIME_CONFIG.read_text()
    assert "${DEEPSEEK_API_KEY}" in openclaw_entry.RUNTIME_CONFIG.read_text()


def test_openclaw_wrapper_passthrough_prepends_capproof_profile(monkeypatch, tmp_path: Path) -> None:
    binary = isolate_openclaw(monkeypatch, tmp_path)
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(openclaw_entry.subprocess, "run", fake_run)

    rc = openclaw_entry.main(["agent", "--local", "--message", "hello"], env={"DEEPSEEK_API_KEY": SECRET})

    assert rc == 0
    assert calls[-1] == [str(binary), "--profile", "capproof", "agent", "--local", "--message", "hello"]


def test_wrapper_status_commands_do_not_require_key(monkeypatch, tmp_path: Path, capsys) -> None:
    isolate_opencode(monkeypatch, tmp_path)

    rc = opencode_entry.main(["--where-trace"], env={})

    out = capsys.readouterr().out
    assert rc == 0
    assert "trace_jsonl_path=" in out
    assert "auth_queue_dir=" in out


def test_bin_wrappers_are_executable() -> None:
    root = Path(__file__).resolve().parents[1]

    assert os.access(root / "bin" / "opencode", os.X_OK)
    assert os.access(root / "bin" / "openclaw", os.X_OK)


def isolate_opencode(monkeypatch, tmp_path: Path) -> Path:
    binary = tmp_path / "bin" / "opencode"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o755)
    monkeypatch.setattr(opencode_entry.parity.smoke, "OPENCODE_BINARY", binary)
    monkeypatch.setattr(opencode_entry.parity, "CONFIG_DIR", tmp_path / "configs")
    monkeypatch.setattr(opencode_entry.parity, "CONFIG_PATH", tmp_path / "configs" / "opencode.json")
    monkeypatch.setattr(opencode_entry.parity, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(opencode_entry.parity, "REPORT_PATH", tmp_path / "reports" / "report.md")
    monkeypatch.setattr(opencode_entry.parity, "SUMMARY_PATH", tmp_path / "reports" / "summary.json")
    monkeypatch.setattr(opencode_entry.parity, "LIVE_LOG_PATH", tmp_path / "reports" / "live.log")
    monkeypatch.setattr(opencode_entry.parity, "TRACE_DIR", tmp_path / "traces")
    monkeypatch.setattr(opencode_entry.parity, "TRACE_PATH", tmp_path / "traces" / "trace.jsonl")
    monkeypatch.setattr(opencode_entry.parity, "WORKSPACE_DIR", tmp_path / "workspace")
    monkeypatch.setattr(opencode_entry, "RUNTIME_DIR", tmp_path / "runtime")
    monkeypatch.setattr(opencode_entry, "RUNTIME_HOME", tmp_path / "runtime" / "home")
    monkeypatch.setattr(opencode_entry, "AUTH_QUEUE_DIR", tmp_path / "runtime" / "auth_queue")
    return binary


def isolate_openclaw(monkeypatch, tmp_path: Path) -> Path:
    binary = tmp_path / "bin" / "openclaw"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o755)
    monkeypatch.setattr(openclaw_entry.parity.smoke, "OPENCLAW_BINARY", binary)
    monkeypatch.setattr(openclaw_entry.parity, "CONFIG_DIR", tmp_path / "configs")
    monkeypatch.setattr(openclaw_entry.parity, "CONFIG_PATH", tmp_path / "configs" / "openclaw.json")
    monkeypatch.setattr(openclaw_entry.parity, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(openclaw_entry.parity, "REPORT_PATH", tmp_path / "reports" / "report.md")
    monkeypatch.setattr(openclaw_entry.parity, "SUMMARY_PATH", tmp_path / "reports" / "summary.json")
    monkeypatch.setattr(openclaw_entry.parity, "LIVE_LOG_PATH", tmp_path / "reports" / "live.log")
    monkeypatch.setattr(openclaw_entry.parity, "TRACE_DIR", tmp_path / "traces")
    monkeypatch.setattr(openclaw_entry.parity, "TRACE_PATH", tmp_path / "traces" / "trace.jsonl")
    monkeypatch.setattr(openclaw_entry.parity, "WORKSPACE_DIR", tmp_path / "workspace")
    monkeypatch.setattr(openclaw_entry, "RUNTIME_DIR", tmp_path / "runtime")
    monkeypatch.setattr(openclaw_entry, "RUNTIME_HOME", tmp_path / "runtime" / "home")
    monkeypatch.setattr(openclaw_entry, "AUTH_QUEUE_DIR", tmp_path / "runtime" / "auth_queue")
    monkeypatch.setattr(openclaw_entry, "RUNTIME_CONFIG", tmp_path / "runtime" / "home" / ".openclaw-capproof" / "openclaw.json")
    return binary
