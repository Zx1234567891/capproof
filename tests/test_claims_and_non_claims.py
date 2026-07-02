from pathlib import Path


def test_claims_and_non_claims_are_evidence_scoped() -> None:
    text = Path("CLAIMS_AND_NON_CLAIMS.md").read_text(encoding="utf-8")
    assert "Hermes foreground MCP path" in text
    assert "DeepSeek as Hermes model backend" in text
    assert "standard CapProof MCP `tools/list` and `tools/call`" in text
    assert "trusted ASK approval queue" in text
    assert "Foreground ASK -> trusted approve -> rerun ALLOW flow" in text
    assert "Metadata and LLM output cannot mint capability" in text
    assert "Production-level Hermes protection" in text
    assert "All Hermes tool paths covered" in text
    assert "OS-level network denial" in text
    assert "DeepSeek as safety TCB" in text
    assert "MCP `_meta` authorization" in text


def test_claims_docs_do_not_overclaim() -> None:
    text = Path("CLAIMS_AND_NON_CLAIMS.md").read_text(encoding="utf-8").lower()
    assert "does not claim production-level protection" in text
    assert "not claimed" in text
    assert "all hermes tool paths covered" in text
    assert "opencode/openclaw real integration" in text
