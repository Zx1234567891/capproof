from pathlib import Path

from capproof import (
    Canonicalizer,
    DenyReason,
    VerificationDecision,
    canonicalize_endpoint,
)


def test_path_traversal_denied(tmp_path: Path) -> None:
    canonicalizer = Canonicalizer(tmp_path / "workspace")

    result = canonicalizer.canonicalize_file_path("../secrets.txt")

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.CAP_PREDICATE_MISMATCH


def test_file_path_normalization_allowed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    canonicalizer = Canonicalizer(workspace)

    result = canonicalizer.canonicalize_file_path("./reports/../report.txt")

    assert result.allowed
    assert result.value == str(workspace.resolve(strict=False) / "report.txt")


def test_endpoint_canonicalization_lowercases_idn_host() -> None:
    result = canonicalize_endpoint("HTTPS://ExAmPle.COM:443/a b?x=1")

    assert result.allowed
    assert result.value == "https://example.com:443/a%20b?x=1"


def test_endpoint_invalid_fail_closed() -> None:
    result = canonicalize_endpoint("not-a-valid-endpoint")

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.CANONICALIZATION_MISMATCH


def test_shell_sh_c_denied(tmp_path: Path) -> None:
    result = Canonicalizer(tmp_path).canonicalize_run_shell(
        command_template="sh -c",
        args={},
        cwd=".",
        env={},
        stdin=None,
    )

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.COMMAND_TEMPLATE_VIOLATION


def test_shell_pipe_denied(tmp_path: Path) -> None:
    result = Canonicalizer(tmp_path).canonicalize_run_shell(
        command_template="pytest | cat",
        args={},
        cwd=".",
        env={},
        stdin=None,
    )

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.COMMAND_TEMPLATE_VIOLATION


def test_shell_redirect_denied(tmp_path: Path) -> None:
    result = Canonicalizer(tmp_path).canonicalize_run_shell(
        command_template="pytest > out.txt",
        args={},
        cwd=".",
        env={},
        stdin=None,
    )

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.COMMAND_TEMPLATE_VIOLATION


def test_shell_base64_denied(tmp_path: Path) -> None:
    result = Canonicalizer(tmp_path).canonicalize_run_shell(
        command_template="base64",
        args={},
        cwd=".",
        env={},
        stdin=None,
    )

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.COMMAND_TEMPLATE_VIOLATION


def test_shell_network_command_denied(tmp_path: Path) -> None:
    result = Canonicalizer(tmp_path).canonicalize_run_shell(
        command_template="curl",
        args={},
        cwd=".",
        env={},
        stdin=None,
    )

    assert result.decision == VerificationDecision.DENY
    assert result.deny_reason == DenyReason.COMMAND_TEMPLATE_VIOLATION


def test_shell_allowlisted_pytest_allowed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    result = Canonicalizer(workspace).canonicalize_run_shell(
        command_template="pytest",
        args={"target": "tests", "quiet": True},
        cwd=".",
        env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        stdin=None,
    )

    assert result.allowed
    assert result.value == {
        "template": "pytest",
        "argv": ["python", "-m", "pytest", "tests", "-q"],
        "cwd": str(workspace.resolve(strict=False)),
        "env": {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        "stdin": None,
    }
