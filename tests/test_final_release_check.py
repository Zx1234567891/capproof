from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_final_release_check as final


def test_require_real_missing_gates_fails() -> None:
    rc = final.main(["--require-real", "--fail-if-gate-missing"])

    assert rc == 2
    summary = json.loads(final.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["final_release_passed"] is False


def test_preflight_is_not_completion() -> None:
    rc = final.main(["--preflight"])

    assert rc == 0
    summary = json.loads(final.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["final_release_passed"] is False
    assert summary["fresh_run"] is False


def test_reuse_existing_cleanroom_not_fresh() -> None:
    rc = final.main(["--reuse-existing-cleanroom", "--report"])

    assert rc == 0
    summary = json.loads(final.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["mode"] == "reuse_existing_cleanroom"
    assert summary["fresh_run"] is False
    assert summary["final_release_passed"] is False


def test_summary_schema_fields_exist() -> None:
    summary = final.build_summary(
        mode="preflight",
        fresh_run=False,
        preflight=final.build_preflight({}),
        command_result={},
        reason="readiness_only_not_completion_evidence",
        checks=stub_args(),
    )

    for field in (
        "final_release_passed",
        "cleanroom_passed",
        "evaluator_passed",
        "aggregate_agent_parity_passed",
        "real_key_scan",
        "forbidden_tracked_paths_count",
        "checksums_generated",
    ):
        assert field in summary


def test_final_pass_requires_fresh_run() -> None:
    summary = {
        "fresh_run": False,
        "cleanroom_passed": True,
        "evaluator_passed": True,
        "aggregate_agent_parity_passed": True,
        "hermes_parity": True,
        "opencode_parity": True,
        "openclaw_parity": True,
        "all_agents_deepseek": True,
        "all_key_source_env": True,
        "key_written": False,
        "real_key_scan": "REAL_KEY_NOT_FOUND",
        "forbidden_tracked_paths_count": 0,
        "claims_consistent_with_evidence": True,
        "production_level_overclaim": False,
        "core_verifier_modified": False,
        "reference_monitor_semantics_changed": False,
        "checksums_generated": True,
        "redaction_safe": True,
    }

    assert final.final_passed(summary) is False


def test_secret_scan_redacts_key_like_values() -> None:
    token = "sk-" + "1234567890abcdef1234567890abcdef"
    assert token not in final.redact("token " + token)


class stub_args:
    check_claims = True
    check_secrets = True
    check_forbidden_paths = True
    check_checksums = True
