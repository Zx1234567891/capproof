from pathlib import Path


def test_install_doc_contains_wrapper_commands_without_key() -> None:
    text = Path("docs/INSTALL_LOCAL_HERMES_WRAPPER.md").read_text(encoding="utf-8")
    assert "make install-local-hermes-wrapper" in text
    assert "~/.local/bin/hermes" in text
    assert "bin/hermes" in text
    assert "DEEPSEEK_API_KEY" in text
    assert "hermes --doctor" in text
    assert "hermes --where-trace" in text
    assert "hermes --trace-follow" in text
    assert "make uninstall-local-hermes-wrapper" in text
    assert "sk-" not in text


def test_makefile_targets_are_local_safe_by_default() -> None:
    text = Path("Makefile").read_text(encoding="utf-8")
    for target in (
        "install-local-hermes-wrapper",
        "uninstall-local-hermes-wrapper",
        "capproof-doctor",
        "capproof-trace",
        "capproof-trace-follow",
        "capproof-auth-queue",
        "capproof-smoke-local",
        "capproof-test-core",
        "capproof-test-full",
    ):
        assert f"{target}:" in text
    default_text = text.split("capproof-real-hermes-foreground:")[0]
    assert "DEEPSEEK_API_KEY" not in default_text
    assert "pip install" not in text


def test_reproduction_doc_separates_default_and_gated_real_runs() -> None:
    text = Path("docs/REPRODUCE_HERMES_CAPROOF_MCP.md").read_text(encoding="utf-8")
    assert "No-Secret Default Checks" in text
    assert "Gated Real Hermes Checks" in text
    assert "ALLOW_HERMES_DEEPSEEK_RUN=1" in text
    assert "ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1" in text
    assert 'DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY"' in text
    assert "What These Results Do Not Prove" in text
