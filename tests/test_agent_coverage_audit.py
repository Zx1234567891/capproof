import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_agent_coverage_audit import ROOT, run_audit


REQUIRED_ROW_KEYS = {
    "target_project",
    "source_file",
    "event_or_tool_surface",
    "action_kind",
    "possible_tool_name",
    "authority_bearing_fields",
    "observed_by_current_profile",
    "canonicalization_needed",
    "likely_hook_point",
    "suggested_capproof_role",
    "suggested_contract_update",
    "adapter_coverage_gap",
    "residual_risk",
    "recommended_test_case",
    "confidence",
}


def run_tmp_audit(tmp_path: Path, **repo_paths):
    root = tmp_path / "root"
    root.mkdir()
    (root / "kill_tests").mkdir()
    output = tmp_path / "audit"
    return run_audit(root=root, output_dir=output, **repo_paths), output


def rows(payload, *, project: str | None = None, kind: str | None = None):
    result = payload["coverage_matrix"]
    if project is not None:
        result = [row for row in result if row["target_project"] == project]
    if kind is not None:
        result = [row for row in result if row["action_kind"] == kind]
    return result


def fields_for(payload, kind: str) -> set[str]:
    for row in payload["coverage_matrix"]:
        if row["action_kind"] == kind:
            return set(row["authority_bearing_fields"])
    raise AssertionError(f"missing row for {kind}")


def test_repo_missing_generates_reports_without_failure(tmp_path: Path) -> None:
    payload, output = run_tmp_audit(tmp_path)

    assert payload["repo_status"]["opencode"]["status"] == "repo_missing"
    assert payload["repo_status"]["openclaw"]["status"] == "repo_missing"
    assert payload["repo_status"]["hermes"]["status"] == "repo_missing"
    assert (output / "opencode_audit.md").exists()
    assert (output / "openclaw_audit.md").exists()
    assert (output / "hermes_audit.md").exists()
    assert (output / "coverage_matrix.json").exists()


def test_coverage_matrix_json_schema_is_stable(tmp_path: Path) -> None:
    _payload, output = run_tmp_audit(tmp_path)
    data = json.loads((output / "coverage_matrix.json").read_text(encoding="utf-8"))

    assert {"repo_status", "coverage_matrix", "summary", "safety"} <= set(data)
    assert data["coverage_matrix"]
    assert REQUIRED_ROW_KEYS <= set(data["coverage_matrix"][0])
    assert isinstance(data["coverage_matrix"][0]["authority_bearing_fields"], list)
    assert isinstance(data["coverage_matrix"][0]["adapter_coverage_gap"], bool)


def test_repo_missing_rows_are_low_confidence(tmp_path: Path) -> None:
    payload, output = run_tmp_audit(tmp_path)
    rows_for_missing_repos = [
        row
        for row in payload["coverage_matrix"]
        if row["target_project"] in {"opencode", "openclaw", "hermes"}
    ]
    matrix_md = (output / "coverage_matrix.md").read_text(encoding="utf-8")

    assert rows_for_missing_repos
    assert all(row["source_file"] == "repo_missing" for row in rows_for_missing_repos)
    assert all(row["confidence"] == "low" for row in rows_for_missing_repos)
    assert "repo_missing" in matrix_md


def test_unknown_surfaces_are_marked_as_coverage_gap(tmp_path: Path) -> None:
    opencode = tmp_path / "opencode"
    opencode.mkdir()
    (opencode / "dynamic_tool.ts").write_text(
        "registerTool('mystery', { unknown_surface: userControlledValue })",
        encoding="utf-8",
    )

    payload, _output = run_tmp_audit(tmp_path, opencode_repo=opencode)
    unknown_rows = [
        row
        for row in rows(payload, project="opencode", kind="unknown")
        if "dynamic_tool.ts" in row["source_file"]
    ]

    assert unknown_rows
    assert all(row["adapter_coverage_gap"] for row in unknown_rows)
    assert all(row["observed_by_current_profile"] == "no" for row in unknown_rows)


def test_shell_surfaces_mark_required_fields(tmp_path: Path) -> None:
    payload, _output = run_tmp_audit(tmp_path)

    assert {"command", "args", "cwd", "env", "stdin"} <= fields_for(payload, "shell")


def test_file_write_surfaces_mark_path_overwrite_and_symlink_policy(tmp_path: Path) -> None:
    payload, _output = run_tmp_audit(tmp_path)

    assert {"path", "overwrite", "symlink_policy"} <= fields_for(payload, "file_write")


def test_network_surfaces_mark_url_method_headers_follow_redirects(tmp_path: Path) -> None:
    payload, _output = run_tmp_audit(tmp_path)

    assert {"url", "method", "headers", "follow_redirects"} <= fields_for(payload, "network")


def test_memory_surfaces_mark_content_origin_persistence_authority_claims(tmp_path: Path) -> None:
    payload, _output = run_tmp_audit(tmp_path)

    assert {"content", "origin", "persistence", "authority_claims"} <= fields_for(payload, "memory")


def test_delegation_surfaces_mark_parent_child_scope(tmp_path: Path) -> None:
    payload, _output = run_tmp_audit(tmp_path)

    assert {"parent_agent", "child_agent", "delegated_scope"} <= fields_for(payload, "delegation")


def test_harness_surfaces_cover_existing_kill_tests(tmp_path: Path) -> None:
    payload = run_audit(root=ROOT, output_dir=tmp_path / "audit")
    harness_rows = rows(payload, project="harness")

    assert payload["repo_status"]["harness"]["status"] == "available"
    assert any("kill tasks" in row["event_or_tool_surface"] for row in harness_rows)
    assert any(row["possible_tool_name"] == "HarnessAdapter" for row in harness_rows)


def test_audit_script_does_not_execute_third_party_commands(tmp_path: Path) -> None:
    payload, _output = run_tmp_audit(tmp_path)
    source = (ROOT / "run_agent_coverage_audit.py").read_text(encoding="utf-8")

    assert payload["safety"]["third_party_commands_executed"] is False
    assert payload["safety"]["real_agents_executed"] is False
    assert "subprocess.run" not in source
    assert "subprocess.Popen" not in source
    assert "os.system" not in source
