from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_final_release_check as final


def test_claims_table_contains_required_proven_claims() -> None:
    rows = final.claims_evidence_rows()
    claims = {row["claim"]: row["status"] for row in rows}

    assert claims["Hermes local CapProof MCP parity"] == "proven"
    assert claims["OpenCode local CapProof MCP parity"] == "proven"
    assert claims["OpenClaw local CapProof MCP parity"] == "proven"
    assert claims["clean-room fresh-run reproduction passed"] == "proven"


def test_claims_table_contains_required_non_claims() -> None:
    rows = final.claims_evidence_rows()
    claims = {row["claim"]: row["status"] for row in rows}

    assert claims["production-level protection"] == "not_claimed"
    assert claims["OS-level network denial"] == "not_claimed"
    assert claims["MCP _meta authorization"] == "not_claimed"


def test_claims_consistency_requires_cleanroom_passed() -> None:
    assert final.claims_consistent({"cleanroom_passed": True}, final.claims_evidence_rows()) is True
    assert final.claims_consistent({"cleanroom_passed": False}, final.claims_evidence_rows()) is False
