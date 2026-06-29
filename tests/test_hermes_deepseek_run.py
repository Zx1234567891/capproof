from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_hermes_deepseek_setup as setup


SECRET = "sk-test-secret-do-not-write"


class Completed:
    def __init__(self, stdout: str = "capproof-ok\n", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def safe_env(tmp_path: Path) -> dict[str, str]:
    workspace = tmp_path / "hermes-test-workspace"
    workspace.mkdir(exist_ok=True)
    return {
        "ALLOW_HERMES_DEEPSEEK_RUN": "1",
        "DEEPSEEK_API_KEY": SECRET,
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEEPSEEK_MODEL": "deepseek-v4-pro",
        "HERMES_DEEPSEEK_COMMAND": 'hermes --no-tools --model deepseek-v4-pro --prompt "Reply with exactly: capproof-ok"',
        "CAPPROOF_NO_REAL_TOOLS": "1",
        "NO_NETWORK_EXCEPT_DEEPSEEK": "1",
        "HERMES_TEST_WORKSPACE": str(workspace),
    }


def test_missing_allow_env_does_not_run(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env.pop("ALLOW_HERMES_DEEPSEEK_RUN")

    result = setup.validate_hermes_command(env=env)

    assert result.run_allowed is False
    assert result.verdict == "DENY_HERMES_DEEPSEEK_RUN"
    assert "ALLOW_HERMES_DEEPSEEK_RUN" in result.missing_env


def test_missing_hermes_command_does_not_run(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env.pop("HERMES_DEEPSEEK_COMMAND")

    result = setup.validate_hermes_command(env=env)

    assert result.run_allowed is False
    assert "HERMES_DEEPSEEK_COMMAND" in result.missing_env


def test_missing_deepseek_key_does_not_run(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env.pop("DEEPSEEK_API_KEY")

    result = setup.validate_hermes_command(env=env)

    assert result.run_allowed is False
    assert "DEEPSEEK_API_KEY" in result.missing_env


def test_unsafe_command_with_curl_rejected(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env["HERMES_DEEPSEEK_COMMAND"] = "hermes --no-tools --prompt capproof-ok && curl https://evil.example"

    result = setup.validate_hermes_command(env=env)

    assert result.run_allowed is False
    assert "curl" in result.denied_patterns


def test_unsafe_command_with_gateway_rejected(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env["HERMES_DEEPSEEK_COMMAND"] = "hermes gateway start --no-tools --prompt capproof-ok"

    result = setup.validate_hermes_command(env=env)

    assert result.run_allowed is False
    assert "hermes gateway" in result.denied_patterns


def test_unsafe_command_with_tools_enable_rejected(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env["HERMES_DEEPSEEK_COMMAND"] = "hermes tools enable --prompt capproof-ok"

    result = setup.validate_hermes_command(env=env)

    assert result.run_allowed is False
    assert "hermes tools enable" in result.denied_patterns


def test_safe_no_tools_command_validation_passes(tmp_path: Path) -> None:
    result = setup.validate_hermes_command(env=safe_env(tmp_path))

    assert result.run_allowed is True
    assert result.verdict == "ALLOW_HERMES_DEEPSEEK_RUN_VALIDATION_ONLY"
    assert result.required_checks["command_declares_no_tools"] is True
    assert result.required_checks["safe_prompt_marker"] is True


def test_no_tools_run_default_not_executed(tmp_path: Path) -> None:
    validation = setup.validate_hermes_command(env=safe_env(tmp_path))

    result = setup.load_or_default_hermes_run(validation, env=safe_env(tmp_path))

    assert result.run_attempted is False
    assert result.denial_reason == "not requested; --run-hermes-no-tools was not invoked"


def test_api_key_not_in_report_or_output(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    validation = setup.validate_hermes_command(env=env)
    calls: list[dict[str, object]] = []

    def fake_runner(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return Completed(stdout="capproof-ok\n")

    result = setup.run_hermes_no_tools(
        command_validation=validation,
        env=env,
        command_runner=fake_runner,
        root=tmp_path,
    )

    assert result.run_attempted is True
    assert result.key_leak_detected is False
    report_dir = tmp_path / "real_agent_integrations" / "hermes_deepseek" / "reports"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in report_dir.glob("*"))
    assert SECRET not in combined
    assert calls
    run_env = calls[0]["kwargs"]["env"]
    assert run_env["DEEPSEEK_API_KEY"] == SECRET
    assert run_env["HERMES_DISABLE_TOOLS"] == "1"
    assert run_env["HERMES_DISABLE_GATEWAY"] == "1"
    assert run_env["HERMES_DISABLE_MCP"] == "1"


def test_tool_call_output_marks_violation(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    validation = setup.validate_hermes_command(env=env)

    result = setup.run_hermes_no_tools(
        command_validation=validation,
        env=env,
        command_runner=lambda *args, **kwargs: Completed(stdout="tool_call: send_message"),
        root=tmp_path,
    )

    assert result.tool_call_detected is True


def test_shell_mcp_gateway_output_marks_violation(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    validation = setup.validate_hermes_command(env=env)

    result = setup.run_hermes_no_tools(
        command_validation=validation,
        env=env,
        command_runner=lambda *args, **kwargs: Completed(stdout="run_shell mcp gateway send_message"),
        root=tmp_path,
    )

    assert result.shell_detected is True
    assert result.mcp_detected is True
    assert result.gateway_detected is True


def test_tests_do_not_call_deepseek_or_real_hermes_by_default(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    validation = setup.validate_hermes_command(env=env)
    result = setup.load_or_default_hermes_run(validation, env=env)
    smoke = setup.run_smoke_test(env={"DEEPSEEK_API_KEY": SECRET}, root=tmp_path)

    assert result.run_attempted is False
    assert smoke.run_attempted is False


def test_external_source_not_modified_by_validation(tmp_path: Path) -> None:
    external = tmp_path / "external" / "external" / "hermes-agent"
    external.mkdir(parents=True)
    marker = external / "README.md"
    marker.write_text("unchanged", encoding="utf-8")

    setup.validate_hermes_command(env=safe_env(tmp_path))

    assert marker.read_text(encoding="utf-8") == "unchanged"
