from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_hermes_capproof_foreground as entry


SECRET = "redacted-test-secret-do-not-write"


def test_build_env_sets_required_gates_without_writing_key() -> None:
    env = entry.build_env({"DEEPSEEK_API_KEY": SECRET})

    for name, value in entry.REQUIRED_GATES.items():
        assert env[name] == value
    assert env["DEEPSEEK_API_KEY"] == SECRET
    assert env["DEEPSEEK_BASE_URL"] == "https://api.deepseek.com"
    assert env["DEEPSEEK_MODEL"] == "deepseek-v4-pro"


def test_missing_key_fails_before_real_run(monkeypatch, capsys) -> None:
    def fail_run(*args, **kwargs):
        raise AssertionError("real Hermes must not run without DEEPSEEK_API_KEY")

    monkeypatch.setattr(entry.foreground, "run_hermes_foreground", fail_run)

    rc = entry.main([], env={})

    out = capsys.readouterr().out
    assert rc == 2
    assert "DEEPSEEK_API_KEY is missing" in out
    assert "sk-" not in out


def test_dry_run_one_command_path(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate_artifacts(monkeypatch, tmp_path)

    rc = entry.main(["--dry-run"], env={})

    out = capsys.readouterr().out
    assert rc == 0
    assert "mode=dry-run" in out
    assert "passed=True" in out
    assert "tools_list_observed=True" in out
    assert "tools_call_observed=True" in out


def test_workflow_demo_path_uses_wrapped_foreground_runner(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate_artifacts(monkeypatch, tmp_path)

    def fake_run(env, validation):
        assert env["ALLOW_HERMES_DEEPSEEK_RUN"] == "1"
        assert env["ALLOW_CAPROOF_MCP_REAL_HERMES"] == "1"
        assert env["ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION"] == "1"
        assert env["ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO"] == "1"
        assert env["DEEPSEEK_API_KEY"] == SECRET
        rows = entry.foreground.run_local_tasks()
        return entry.foreground.HermesRunResult(
            attempted=True,
            allowed=True,
            command_hash=validation.command_hash,
            foreground=True,
            exit_code=0,
            response_received=True,
        )

    monkeypatch.setattr(entry.foreground, "run_hermes_foreground", fake_run)

    rc = entry.main(["--workflow-demo"], env={"DEEPSEEK_API_KEY": SECRET})

    out = capsys.readouterr().out
    assert rc == 0
    assert "mode=foreground" in out
    assert "passed=True" in out
    assert "hermes_started=True" in out
    assert "deepseek_called=True" in out
    assert SECRET not in out


def test_default_path_launches_tui_interactive_hermes_passthrough(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate_artifacts(monkeypatch, tmp_path)
    captured = {}

    def fake_run(command, cwd, env, check, shell):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        captured["check"] = check
        captured["shell"] = shell
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(entry.subprocess, "run", fake_run)

    rc = entry.main([], env={"DEEPSEEK_API_KEY": SECRET})

    streams = capsys.readouterr()
    assert rc == 0
    assert "CapProof MCP attached: yes" in streams.err
    assert captured["shell"] is False
    assert "-z" not in captured["command"]
    assert "--oneshot" not in captured["command"]
    assert "--tui" in captured["command"]
    assert "--cli" not in captured["command"]
    assert "-t" in captured["command"]
    assert "capproof_foreground" in captured["command"]
    assert captured["env"]["DEEPSEEK_API_KEY"] == SECRET
    assert captured["env"]["CAPPROOF_MCP_TRACE_PATH"]
    assert SECRET not in streams.out
    assert SECRET not in streams.err


def test_classic_flag_uses_classic_cli(monkeypatch, tmp_path: Path) -> None:
    _isolate_artifacts(monkeypatch, tmp_path)
    captured = {}

    def fake_run(command, cwd, env, check, shell):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(entry.subprocess, "run", fake_run)

    rc = entry.main(["--classic"], env={"DEEPSEEK_API_KEY": SECRET})

    assert rc == 0
    assert "--cli" in captured["command"]
    assert "--tui" not in captured["command"]


def test_tui_flag_uses_tui(monkeypatch, tmp_path: Path) -> None:
    _isolate_artifacts(monkeypatch, tmp_path)
    captured = {}

    def fake_run(command, cwd, env, check, shell):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(entry.subprocess, "run", fake_run)

    rc = entry.main(["--tui"], env={"DEEPSEEK_API_KEY": SECRET})

    assert rc == 0
    assert "--tui" in captured["command"]
    assert "--cli" not in captured["command"]


def test_unsafe_interactive_command_is_rejected(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate_artifacts(monkeypatch, tmp_path)

    def fail_run(*args, **kwargs):
        raise AssertionError("unsafe Hermes command must not run")

    monkeypatch.setattr(entry.subprocess, "run", fail_run)

    rc = entry.main(
        [],
        env={
            "DEEPSEEK_API_KEY": SECRET,
            "HERMES_INTERACTIVE_COMMAND": "hermes --tui --mcp http://evil.example/mcp",
        },
    )

    out = capsys.readouterr().out
    assert rc == 1
    assert "interactive command safety check" in out
    assert SECRET not in out


def test_preflight_is_one_command_safe(monkeypatch, tmp_path: Path, capsys) -> None:
    _isolate_artifacts(monkeypatch, tmp_path)

    rc = entry.main(["--preflight"], env={"DEEPSEEK_API_KEY": SECRET})

    out = capsys.readouterr().out
    assert rc == 0
    assert "preflight_run_allowed=True" in out
    assert "missing_env=none" in out
    assert SECRET not in out


def _isolate_artifacts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entry.foreground, "CONFIG_PATH", tmp_path / "hermes.capproof.foreground.mcp.json")
    monkeypatch.setattr(entry.foreground, "REPORT_PATH", tmp_path / "foreground_report.md")
    monkeypatch.setattr(entry.foreground, "SUMMARY_PATH", tmp_path / "foreground_summary.json")
    monkeypatch.setattr(entry.foreground, "LIVE_LOG_PATH", tmp_path / "foreground_live.log")
    monkeypatch.setattr(entry.foreground, "TRACE_PATH", tmp_path / "foreground_trace.jsonl")
    monkeypatch.setattr(entry.foreground, "SANDBOX_WORKSPACE", tmp_path / "workspace")
