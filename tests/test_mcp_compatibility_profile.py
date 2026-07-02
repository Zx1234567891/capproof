from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_mcp_compatibility_matrix as matrix


def test_mcp_compatibility_profile_lists_supported_subset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(matrix, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(matrix, "MATRIX_MD", tmp_path / "mcp_compatibility_matrix.md")
    monkeypatch.setattr(matrix, "MATRIX_JSON", tmp_path / "mcp_compatibility_matrix.json")

    payload = matrix.generate()
    matrix.write_reports(payload)

    statuses = {row["feature"]: row["status"] for row in payload["rows"]}
    assert statuses["local stdio MCP server"] == "supported"
    assert statuses["initialize"] == "supported"
    assert statuses["tools/list"] == "supported"
    assert statuses["tools/call"] == "supported"
    assert statuses["structuredContent"] == "supported"
    assert statuses["Streamable HTTP"] == "not_claimed"
    assert statuses["OAuth / remote MCP authorization"] == "not_claimed"
    assert payload["tools_count"] == 7
    assert payload["summary"]["production_level_protection_claim"] is False
    assert (tmp_path / "mcp_compatibility_matrix.md").exists()
    assert (tmp_path / "mcp_compatibility_matrix.json").exists()


def test_mcp_compatibility_doc_matches_non_claims() -> None:
    text = Path("MCP_COMPATIBILITY.md").read_text(encoding="utf-8")
    assert "local stdio MCP server" in text
    assert "tools/list" in text
    assert "tools/call" in text
    assert "structuredContent" in text
    assert "Streamable HTTP" in text
    assert "OAuth or remote MCP authorization" in text
    assert "External MCP server protection" in text
    assert "Production-level Hermes protection" in text
