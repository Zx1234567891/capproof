from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_hermes_trace_collection_plan as plan


def safe_env(tmp_path: Path) -> dict[str, str]:
    return {
        "ALLOW_HERMES_CAPTURE_RUN": "1",
        "HERMES_CAPTURE_COMMAND": (
            "timeout 20 python hermes_capture_mock.py --capture-only --mock-tools "
            "--no-real-tools --no-real-shell --trace $HERMES_CAPTURE_TRACE_PATH"
        ),
        "HERMES_CAPTURE_TRACE_PATH": str(tmp_path / "trace.jsonl"),
        "CAPPROOF_CAPTURE_ONLY": "1",
        "CAPPROOF_NO_REAL_TOOLS": "1",
        "NO_NETWORK": "1",
        "HERMES_TEST_WORKSPACE": str(tmp_path / "workspace"),
    }


def test_preflight_does_not_run_hermes(tmp_path: Path) -> None:
    result = plan.run_preflight(env={}, root=tmp_path)

    assert result.no_hermes_run is True
    assert result.no_dependency_install is True
    assert result.no_third_party_command is True
    assert result.no_real_tool_execution is True
    assert result.no_network is True


def test_missing_hermes_capture_command_denied(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env.pop("HERMES_CAPTURE_COMMAND")
    result = plan.validate_command(env=env)

    assert result.verdict == "DENY_CAPTURE_RUN"
    assert "HERMES_CAPTURE_COMMAND" in result.missing_env


def test_missing_allow_env_denied(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env.pop("ALLOW_HERMES_CAPTURE_RUN")
    result = plan.validate_command(env=env)

    assert result.verdict == "DENY_CAPTURE_RUN"
    assert "ALLOW_HERMES_CAPTURE_RUN" in result.missing_env


def test_unsafe_command_with_curl_denied(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env["HERMES_CAPTURE_COMMAND"] += " curl https://evil.example"
    result = plan.validate_command(env=env)

    assert result.verdict == "DENY_CAPTURE_RUN"
    assert "curl" in result.denied_patterns


def test_unsafe_command_with_sh_c_denied(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env["HERMES_CAPTURE_COMMAND"] = "timeout 20 sh -c 'echo capture' --trace $HERMES_CAPTURE_TRACE_PATH"
    result = plan.validate_command(env=env)

    assert result.verdict == "DENY_CAPTURE_RUN"
    assert "sh -c" in result.denied_patterns


def test_unsafe_command_with_pipe_denied(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env["HERMES_CAPTURE_COMMAND"] += " | tee out"
    result = plan.validate_command(env=env)

    assert result.verdict == "DENY_CAPTURE_RUN"
    assert "|" in result.denied_patterns


def test_unsafe_command_with_install_denied(tmp_path: Path) -> None:
    env = safe_env(tmp_path)
    env["HERMES_CAPTURE_COMMAND"] = "timeout 20 pip install hermes --capture-only --trace $HERMES_CAPTURE_TRACE_PATH"
    result = plan.validate_command(env=env)

    assert result.verdict == "DENY_CAPTURE_RUN"
    assert any("install" in item for item in result.denied_patterns)


def test_safe_mock_capture_command_passes_validation_but_is_not_executed(tmp_path: Path) -> None:
    result = plan.validate_command(env=safe_env(tmp_path))

    assert result.verdict == "ALLOW_CAPTURE_RUN_VALIDATION_ONLY"
    assert result.reason.endswith("command was not executed")
    assert all(result.required_checks.values())


def test_generated_trace_schema_contains_required_fields(tmp_path: Path) -> None:
    plan.generate_templates(root=tmp_path)
    schema = json.loads(
        (tmp_path / "hermes_trace_collection_plan" / "templates" / "captured_event_schema.json").read_text(
            encoding="utf-8"
        )
    )

    for field in (
        "event_id",
        "source",
        "hook_point",
        "capture_mode",
        "effective_args",
        "pre_execution_observed",
        "side_effect_already_happened",
    ):
        assert field in schema["required"]


def test_task_templates_contain_no_real_side_effect_condition(tmp_path: Path) -> None:
    plan.generate_templates(root=tmp_path)
    task_dir = tmp_path / "hermes_trace_collection_plan" / "templates" / "tasks"
    tasks = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(task_dir.glob("*.json"))]

    assert len(tasks) >= 8
    assert all(task["no_real_side_effect_condition"] for task in tasks)
    assert all("real" in task["no_real_side_effect_condition"].lower() or "mock" in task["no_real_side_effect_condition"].lower() for task in tasks)


def test_command_validation_report_generated(tmp_path: Path) -> None:
    plan.generate_templates(root=tmp_path)
    preflight = plan.run_preflight(env={}, root=tmp_path)
    validation = plan.validate_command(env={})
    plan.write_reports(preflight, validation, root=tmp_path)
    report = tmp_path / "hermes_trace_collection_plan" / "reports" / "command_validation_report.md"

    assert report.exists()
    assert "DENY_CAPTURE_RUN" in report.read_text(encoding="utf-8")


def test_go_no_go_report_says_enforcement_wrapper_no_go(tmp_path: Path) -> None:
    plan.generate_templates(root=tmp_path)
    plan.write_reports(plan.run_preflight(env={}, root=tmp_path), plan.validate_command(env={}), root=tmp_path)
    report = (tmp_path / "hermes_trace_collection_plan" / "reports" / "go_no_go.md").read_text(encoding="utf-8")

    assert "Enforcement wrapper: no-go" in report
    assert "Real Hermes integration claim: no-go" in report


def test_no_subprocess_call_in_default_preflight_tests(tmp_path: Path) -> None:
    assert not hasattr(plan, "subprocess")
    plan.run_preflight(env={}, root=tmp_path)


def test_no_network_use(tmp_path: Path) -> None:
    result = plan.run_preflight(env={}, root=tmp_path)

    assert result.no_network is True


def test_no_external_third_party_source_modification(tmp_path: Path) -> None:
    repo = tmp_path / "external" / "external" / "hermes-agent"
    repo.mkdir(parents=True)
    readme = repo / "README.md"
    readme.write_text("Hermes mock checkout", encoding="utf-8")

    plan.generate_templates(root=tmp_path)
    plan.run_preflight(env={}, root=tmp_path)

    assert readme.read_text(encoding="utf-8") == "Hermes mock checkout"
    assert sorted(path.relative_to(repo) for path in repo.rglob("*")) == [Path("README.md")]
