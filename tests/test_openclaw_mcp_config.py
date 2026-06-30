from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_agent_mcp_client_audit as audit


def test_openclaw_commands_use_outbound_mcp_server_path() -> None:
    audit.write_openclaw_commands()
    text = audit.OPENCLAW_COMMANDS.read_text(encoding="utf-8")

    assert "`openclaw mcp serve` means OpenClaw acting as an MCP server" in text
    assert "openclaw mcp add capproof" in text
    assert "--command python" in text
    assert "--arg run_capproof_mcp_server.py" in text
    assert "--arg --stdio" in text
    assert "--arg --sandboxed-real-execution" in text
    assert "openclaw mcp doctor capproof --probe" in text
    assert "openclaw mcp tools capproof" in text


def test_openclaw_commands_contain_no_api_key_or_secret_literal() -> None:
    audit.write_openclaw_commands()
    text = audit.OPENCLAW_COMMANDS.read_text(encoding="utf-8")

    assert not re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
    assert "DEEPSEEK_API_KEY" not in text
    assert "TOKEN" not in text
    assert "SECRET" not in text


def test_openclaw_report_keeps_real_integration_non_claim(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_REPO", str(tmp_path / "missing-openclaw"))
    summary = audit.build_summary(dict(__import__("os").environ))
    report = audit.render_client_report(summary.openclaw, client_title="OpenClaw")

    assert "did not run real OpenClaw" in report
    assert "does not claim real OpenCode/OpenClaw integration" in report
    assert "Production-level protection: false" in report
