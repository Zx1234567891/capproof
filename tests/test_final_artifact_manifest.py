from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_final_release_check as final


def test_manifest_lists_required_scripts_and_docs() -> None:
    manifest = final.release_manifest({"final_release_passed": True})

    assert "tools/run_real_agent_parity_evaluator.py" in manifest["important_scripts"]
    assert "tools/run_cleanroom_release_candidate.py" in manifest["important_scripts"]
    assert "docs/release/MCP_COMPATIBILITY.md" in manifest["important_docs"]
    assert "artifact_reports/cleanroom_release_candidate_summary.json" in manifest["important_reports"]


def test_manifest_json_generated_by_report() -> None:
    final.main(["--preflight"])
    data = json.loads(final.RELEASE_MANIFEST_JSON.read_text(encoding="utf-8"))

    assert data["artifact_name"]
    assert "artifact_cleanroom/" in data["ignored_runtime_paths"]


def test_checksums_exclude_self_files() -> None:
    paths = final.artifact_paths_for_checksums()

    assert "docs/release/FINAL_ARTIFACT_CHECKSUMS.md" not in paths
    assert "docs/release/FINAL_ARTIFACT_CHECKSUMS.json" not in paths
