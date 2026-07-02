from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_real_agent_parity_evaluator as evaluator


def test_require_real_missing_gates_fails() -> None:
    rc = evaluator.main(["--require-real", "--fail-if-gate-missing"])

    assert rc == 2
    summary = json.loads(evaluator.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["evaluator_passed"] is False
    assert summary["reason"] in {"blocked_missing_real_env_gate", "blocked_real_run_not_requested"}


def test_preflight_does_not_mark_completion() -> None:
    rc = evaluator.main(["--preflight"])

    assert rc == 0
    summary = json.loads(evaluator.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["evaluator_mode"] == "preflight"
    assert summary["fresh_run"] is False
    assert summary["evaluator_passed"] is False
    assert summary["dry_run_preflight_counts_as_completion"] is False


def test_gate_names_are_documented() -> None:
    preflight = evaluator.build_preflight({})

    assert "ALLOW_CAPROOF_REAL_OPENCODE_SMOKE" in preflight["required_gates"]
    assert "ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE" in preflight["required_gates"]
    assert "ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO" in preflight["required_gates"]
    assert "DEEPSEEK_API_KEY" in preflight["required_gates"]
    assert preflight["missing_gates"]


def test_summary_schema_fields_exist() -> None:
    summary = evaluator.build_summary(
        evaluator_mode="reuse_existing",
        selected_agents=["hermes", "opencode", "openclaw"],
        preflight=evaluator.build_preflight({"DEEPSEEK_API_KEY": "dummy"}),
        command_results=[],
        fresh_run=False,
        reason="reuse_existing_reports_not_fresh_evidence",
    )

    assert "evaluator_passed" in summary
    assert "agents" in summary
    assert "secret_scan" in summary
    assert "forbidden_tracked_paths_count" in summary
    assert summary["reuse_existing_reports_not_fresh_evidence"] is True


def test_reuse_existing_reports_is_not_fresh_run() -> None:
    rc = evaluator.main(["--reuse-existing-reports", "--report"])

    assert rc == 0
    summary = json.loads(evaluator.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["evaluator_mode"] == "reuse_existing"
    assert summary["fresh_run"] is False
    assert summary["reuse_existing_reports_not_fresh_evidence"] is True


def test_report_contains_real_non_real_distinction() -> None:
    evaluator.main(["--preflight"])
    text = evaluator.REPORT_PATH.read_text(encoding="utf-8")

    assert "Preflight and dry-run are readiness only" in text
    assert "no production-level protection" in text


def test_claims_index_has_proven_and_not_claimed_rows() -> None:
    claims = evaluator.claims_index()
    statuses = {row["status"] for row in claims}
    names = {row["claim"] for row in claims}

    assert "proven" in statuses
    assert "not_claimed" in statuses
    assert "DeepSeek backend used by all three via DEEPSEEK_API_KEY" in names
    assert "production-level protection" in names


def test_generated_report_is_redaction_safe() -> None:
    raw = "prefix " + "sk-" + "1234567890abcdef1234567890abcdef" + " suffix"
    assert "sk-1234567890" not in evaluator.redact(raw)


def test_secret_scan_allows_only_known_dummy_fixture() -> None:
    assert "sk-test-secret-do-not-write" in evaluator.ALLOWED_DUMMY_SECRETS
    assert ("sk-" + "real-looking-value") not in evaluator.ALLOWED_DUMMY_SECRETS


def test_fresh_run_wiring_uses_existing_real_scripts() -> None:
    assert "tools/run_real_environment_validation.py" in evaluator.REAL_COMMANDS["hermes"]
    assert "tools/run_real_opencode_deepseek_mcp_parity.py" in evaluator.REAL_COMMANDS["opencode"]
    assert "tools/run_real_openclaw_deepseek_mcp_parity.py" in evaluator.REAL_COMMANDS["openclaw"]
