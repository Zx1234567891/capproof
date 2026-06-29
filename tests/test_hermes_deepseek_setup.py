from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_hermes_deepseek_setup as setup


SECRET = "sk-test-secret-do-not-write"


def test_no_deepseek_api_key_preflight_passes_with_key_missing(tmp_path: Path) -> None:
    result = setup.run_preflight(env={}, root=tmp_path)

    assert result.key_present is False
    assert result.key_value_printed is False
    assert result.smoke_test_allowed is False
    assert result.no_deepseek_call is True


def test_deepseek_api_key_value_never_printed(tmp_path: Path) -> None:
    env = {"DEEPSEEK_API_KEY": SECRET}
    preflight = setup.run_preflight(env=env, root=tmp_path)
    audit = setup.run_hermes_config_audit(env={}, root=tmp_path)
    smoke = setup.run_smoke_test(env={"DEEPSEEK_API_KEY": SECRET}, root=tmp_path)
    setup.write_reports(preflight, audit, smoke, root=tmp_path)

    report_dir = tmp_path / "real_agent_integrations" / "hermes_deepseek" / "reports"
    for path in report_dir.glob("*"):
        assert SECRET not in path.read_text(encoding="utf-8")


def test_config_template_does_not_contain_real_key(tmp_path: Path) -> None:
    setup.generate_config_templates(root=tmp_path)

    template_dir = tmp_path / "real_agent_integrations" / "hermes_deepseek" / "templates"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in template_dir.glob("*"))
    assert SECRET not in combined
    assert "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}" in combined
    assert "provider: deepseek" in combined
    assert "default: deepseek-v4-pro" in combined


def test_smoke_test_skipped_unless_explicitly_allowed(tmp_path: Path) -> None:
    result = setup.run_smoke_test(env={"DEEPSEEK_API_KEY": SECRET}, root=tmp_path)

    assert result.run_attempted is False
    assert result.status == "smoke_test_skipped"


def test_hermes_run_denied_unless_explicitly_allowed(tmp_path: Path) -> None:
    allowed, reason = setup.check_hermes_deepseek_run({"DEEPSEEK_API_KEY": SECRET})

    assert allowed is False
    assert "missing explicit" in reason


def test_smoke_test_request_does_not_include_capability_or_secrets(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, headers: dict[str, str], body: bytes, timeout: float):
        captured["url"] = url
        captured["headers"] = dict(headers)
        captured["body"] = body.decode("utf-8")
        captured["timeout"] = timeout
        return 200, {"x-request-id": "req_mock"}, b'{"model":"deepseek-v4-pro","usage":{"total_tokens":3},"choices":[{"message":{"content":"ok"}}]}'

    result = setup.run_smoke_test(
        env={
            "ALLOW_DEEPSEEK_SMOKE_TEST": "1",
            "DEEPSEEK_API_KEY": SECRET,
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
            "DEEPSEEK_MODEL": "deepseek-v4-pro",
        },
        http_post=fake_post,
        root=tmp_path,
    )

    assert result.run_attempted is True
    assert result.status == "http_200"
    assert SECRET not in str(captured["body"])
    assert SECRET not in str(captured["url"])
    assert captured["headers"]["Authorization"] == f"Bearer {SECRET}"
    assert "capability" not in str(captured["body"]).lower()
    assert "trace" not in str(captured["body"]).lower()
    assert setup.SMOKE_PROMPT in str(captured["body"])
    report = tmp_path / "real_agent_integrations" / "hermes_deepseek" / "reports" / "deepseek_smoke_test_report.md"
    assert SECRET not in report.read_text(encoding="utf-8")


def test_unsafe_logging_redacts_key(tmp_path: Path) -> None:
    preflight = setup.run_preflight(env={"DEEPSEEK_API_KEY": SECRET}, root=tmp_path)
    audit = setup.run_hermes_config_audit(env={}, root=tmp_path)
    smoke = setup.SmokeTestResult(
        run_attempted=False,
        run_allowed=False,
        status="smoke_test_skipped",
        reason="not allowed",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
    )
    setup.write_reports(preflight, audit, smoke, root=tmp_path)

    report = tmp_path / "real_agent_integrations" / "hermes_deepseek" / "reports" / "deepseek_setup_report.md"
    text = report.read_text(encoding="utf-8")
    assert SECRET not in text
    assert "key_value_printed: False" in text


def test_generated_templates_use_environment_variables(tmp_path: Path) -> None:
    setup.generate_config_templates(root=tmp_path)
    template = (
        tmp_path
        / "real_agent_integrations"
        / "hermes_deepseek"
        / "templates"
        / "hermes_deepseek_config.example.yaml"
    ).read_text(encoding="utf-8")

    assert "provider: deepseek" in template
    assert "default: deepseek-v4-pro" in template
    assert "reasoning_effort: high" in template
    snippet = (
        tmp_path
        / "real_agent_integrations"
        / "hermes_deepseek"
        / "configs"
        / "hermes_config.deepseek.example.yaml"
    ).read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY" in snippet
    assert SECRET not in snippet


def test_hermes_config_audit_handles_repo_missing_gracefully(tmp_path: Path) -> None:
    audit = setup.run_hermes_config_audit(env={}, root=tmp_path)

    assert audit.repo_status == "repo_missing"
    assert audit.files_scanned == 0
    assert audit.needs_manual_verification


def test_hermes_config_audit_does_not_run_hermes(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "external" / "external" / "hermes-agent"
    repo.mkdir(parents=True)
    (repo / "README.md").write_text("Provider can use OpenAI compatible base_url and model.", encoding="utf-8")

    def fail_subprocess(*args, **kwargs):  # pragma: no cover - should never run
        raise AssertionError("Hermes config audit must not run subprocess")

    monkeypatch.setattr(setup.subprocess, "run", fail_subprocess)
    audit = setup.run_hermes_config_audit(env={}, root=tmp_path)

    assert audit.repo_status == "available"
    assert audit.files_scanned == 1


def test_deepseek_does_not_enter_capproof_tcb() -> None:
    boundary = setup.security_boundary()

    assert boundary["deepseek_in_capproof_tcb"] is False
    assert boundary["deepseek_can_mint_capability"] is False
    assert boundary["deepseek_can_allow_tool_call"] is False
    assert boundary["reference_monitor_final_authority"] is True


def test_llm_output_cannot_bypass_reference_monitor(tmp_path: Path) -> None:
    result = setup.run_preflight(env={"DEEPSEEK_API_KEY": SECRET}, root=tmp_path)

    assert result.security_boundary["llm_output_can_bypass_reference_monitor"] is False
    assert result.security_boundary["hermes_tool_calls_require_capproof_guard"] is True


def test_no_tool_execution_in_hermes_deepseek_setup_tests(tmp_path: Path) -> None:
    result = setup.run_preflight(env={}, root=tmp_path)
    smoke = setup.run_smoke_test(env={}, root=tmp_path)

    assert result.no_real_tool_execution is True
    assert smoke.no_tool_call is True
    assert smoke.no_hermes_run is True
