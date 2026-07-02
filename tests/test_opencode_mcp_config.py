import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_agent_mcp_client_audit as audit


def _jsonc_to_json(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))


def test_opencode_config_template_uses_capproof_mcp_server() -> None:
    audit.write_opencode_config()
    data = json.loads(_jsonc_to_json(audit.OPENCODE_CONFIG.read_text(encoding="utf-8")))

    capproof = data["mcpServers"]["capproof"]
    assert capproof["command"] == "python"
    assert capproof["args"][0] == "tools/run_capproof_mcp_server.py"
    assert "--stdio" in capproof["args"]
    assert "--sandboxed-real-execution" in capproof["args"]
    assert data["securityBoundary"]["metadataCannotMintCapability"] is True
    assert data["securityBoundary"]["llmOutputCannotAllowToolCall"] is True
    assert data["securityBoundary"]["denyAskExecutorCalled"] is False
    assert data["securityBoundary"]["productionLevelProtectionClaim"] is False


def test_opencode_config_contains_no_api_key_or_secret_literal() -> None:
    audit.write_opencode_config()
    text = audit.OPENCODE_CONFIG.read_text(encoding="utf-8")

    assert not re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
    assert "DEEPSEEK_API_KEY" not in text
    assert "TOKEN" not in text
    assert "SECRET" not in text


def test_opencode_report_keeps_real_integration_non_claim(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCODE_REPO", str(tmp_path / "missing-opencode"))
    summary = audit.build_summary(dict(__import__("os").environ))
    report = audit.render_client_report(summary.opencode, client_title="OpenCode")

    assert "did not run real OpenCode" in report
    assert "does not claim real OpenCode/OpenClaw integration" in report
    assert "Production-level protection: false" in report
