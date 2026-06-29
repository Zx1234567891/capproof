import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_hermes_mcp_coverage as coverage


def test_load_scenarios_covers_required_categories() -> None:
    scenarios = coverage.load_scenarios()
    categories = {scenario["category"] for scenario in scenarios}

    assert {
        "benign",
        "deny",
        "ask",
        "malformed",
        "prompt_variation",
        "metadata_injection",
        "multi_tool",
    } <= categories


def test_run_all_scenarios_generates_expected_matrix() -> None:
    summary = coverage.run_scenarios(coverage.load_scenarios())

    assert summary["total_scenarios"] >= 8
    assert summary["total_steps"] >= 13
    assert summary["failed_steps"] == 0
    assert summary["executor_called_on_deny_ask"] == 0
    assert summary["metadata_injection_unexpected_allow"] == 0
    assert summary["verdict_counts"]["ALLOW"] >= 1
    assert summary["verdict_counts"]["DENY"] >= 1
    assert summary["verdict_counts"]["ASK"] >= 1
    assert summary["verdict_counts"]["ERROR"] >= 1


def test_workflow_trace_rows_have_user_visible_fields() -> None:
    summary = coverage.run_scenarios(coverage.load_scenarios())

    for row in summary["workflow_trace"]:
        for field in (
            "user_task",
            "mcp_method",
            "tool_name",
            "original_arguments",
            "canonical_action_hash",
            "verdict",
            "reason",
            "proof_id",
            "executor_called",
        ):
            assert field in row


def test_reports_are_generated(tmp_path: Path, monkeypatch) -> None:
    matrix_json = tmp_path / "matrix.json"
    matrix_md = tmp_path / "matrix.md"
    monkeypatch.setattr(coverage, "MATRIX_JSON", matrix_json)
    monkeypatch.setattr(coverage, "MATRIX_MD", matrix_md)

    summary = coverage.run_scenarios(coverage.load_scenarios())
    coverage.write_reports(summary)

    assert matrix_json.exists()
    assert matrix_md.exists()
    loaded = json.loads(matrix_json.read_text(encoding="utf-8"))
    assert loaded["failed_steps"] == 0
    assert "Workflow Trace Matrix" in matrix_md.read_text(encoding="utf-8")


def test_list_scenarios_selection() -> None:
    selected = coverage.select_scenarios(coverage.load_scenarios(), "metadata_injection_attempt")

    assert len(selected) == 1
    assert selected[0]["scenario_id"] == "metadata_injection_attempt"
