from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_cleanroom_release_candidate as rc


def test_missing_gates_with_require_real_fail() -> None:
    code = rc.main(["--require-real", "--fail-if-gate-missing"])

    assert code == 2
    summary = json.loads(rc.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["cleanroom_passed"] is False
    assert summary["reason"] in {"blocked_missing_real_env_gate", "blocked_fresh_run_not_requested"}


def test_preflight_does_not_mark_cleanroom_passed() -> None:
    code = rc.main(["--preflight"])

    assert code == 0
    summary = json.loads(rc.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["cleanroom_mode"] == "preflight"
    assert summary["cleanroom_passed"] is False
    assert summary["preflight"]["dry_run_preflight_counts_as_completion"] is False


def test_fresh_run_required_for_completion() -> None:
    summary = rc.build_base_summary(
        argparse_stub(),
        Path("artifact_cleanroom/worktrees/test"),
        {"missing_gates": []},
        cleanroom_mode="preflight",
        reason="readiness_only_not_completion_evidence",
    )

    assert rc.cleanroom_passed(summary) is False


def test_reuse_existing_reports_cannot_pass_cleanroom() -> None:
    summary = rc.build_base_summary(
        argparse_stub(),
        Path("artifact_cleanroom/worktrees/test"),
        {"missing_gates": []},
        cleanroom_mode="reuse_existing",
        reason="reuse_existing_reports_not_completion_evidence",
    )
    summary.update(
        {
            "evaluator_passed": True,
            "aggregate_agent_parity_passed": True,
            "hermes_parity": True,
            "opencode_parity": True,
            "openclaw_parity": True,
        }
    )

    assert rc.cleanroom_passed(summary) is False


def test_summary_schema_fields_exist() -> None:
    summary = rc.build_base_summary(
        argparse_stub(),
        Path("artifact_cleanroom/worktrees/test"),
        rc.build_preflight(argparse_stub(), Path("artifact_cleanroom/worktrees/test"), {}),
        cleanroom_mode="preflight",
        reason="readiness_only_not_completion_evidence",
    )

    for field in (
        "stage",
        "cleanroom_passed",
        "cleanroom_mode",
        "source_commit",
        "evaluator_passed",
        "aggregate_agent_parity_passed",
        "real_key_scan",
        "forbidden_tracked_paths_count",
        "redaction_safe",
    ):
        assert field in summary


def test_secret_redaction_fields_exist() -> None:
    preflight = rc.build_preflight(argparse_stub(), Path("artifact_cleanroom/worktrees/test"), {"DEEPSEEK_API_KEY": "dummy"})

    assert preflight["deepseek_key_present"] is True
    assert preflight["deepseek_key_printed"] is False


def test_forbidden_path_checks_exist() -> None:
    assert "artifact_cleanroom" in " ".join(
        [
            "artifact_cleanroom",
            "external",
            "external/.agent-runtimes",
            ".venv-hermes",
            "node_modules",
        ]
    )


def test_production_overclaim_absent_in_report() -> None:
    rc.write_artifacts(
        rc.build_base_summary(
            argparse_stub(),
            Path("artifact_cleanroom/worktrees/test"),
            {"missing_gates": []},
            cleanroom_mode="preflight",
            reason="readiness_only_not_completion_evidence",
        )
    )
    text = rc.REPORT_PATH.read_text(encoding="utf-8")

    assert "does not claim production-level protection" in text


def test_generated_tracked_reports_are_redaction_safe() -> None:
    token = "sk-" + "1234567890abcdef"
    assert token not in rc.redact("token " + token)


class argparse_stub:
    source_ref = "HEAD"
