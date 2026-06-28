from pathlib import Path
import sys

from capproof import Canonicalizer, DenyReason, VerificationDecision, canonicalize_endpoint

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_adapter_bypass_gate import run_gate


def test_adapter_bypass_gate_denies_all_bypass_cases() -> None:
    results, summary = run_gate(write_artifacts=False)

    assert summary["total_cases"] >= 35
    assert summary["bypass_cases"] >= 30
    assert summary["benign_control_cases"] >= 5
    assert summary["unexpected_allow_count"] == 0
    assert summary["denied_bypass_cases"] == summary["bypass_cases"]
    assert summary["failed_cases"] == []
    assert all(item.passed for item in results)


def test_adapter_bypass_gate_benign_controls_allow() -> None:
    _results, summary = run_gate(write_artifacts=False)

    assert summary["benign_control_success_count"] == summary["benign_control_cases"]


def test_adapter_bypass_gate_covers_required_categories() -> None:
    _results, summary = run_gate(write_artifacts=False)

    assert summary["category_coverage"] == {
        "Benign controls": 5,
        "Email adapter bypass": 8,
        "File path bypass": 7,
        "Memory / delegation edge cases": 3,
        "Shell template bypass": 10,
        "URL / endpoint bypass": 8,
    }
    assert summary["adapter_coverage_gaps"] == 0


def test_endpoint_userinfo_fails_closed() -> None:
    result = canonicalize_endpoint("https://api.example.com@evil.com/ingest")

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.CANONICALIZATION_MISMATCH


def test_endpoint_percent_encoded_host_fails_closed() -> None:
    result = canonicalize_endpoint("https://api.example.com%2e.evil.com/ingest")

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.CANONICALIZATION_MISMATCH


def test_endpoint_trailing_dot_host_fails_closed() -> None:
    result = canonicalize_endpoint("https://api.example.com./ingest")

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.CANONICALIZATION_MISMATCH


def test_path_non_nfc_fails_closed(tmp_path: Path) -> None:
    result = Canonicalizer(tmp_path).canonicalize_file_path("reports/re\u0301sume.md")

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.CANONICALIZATION_MISMATCH
