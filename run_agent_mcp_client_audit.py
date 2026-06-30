#!/usr/bin/env python3
"""Stage 34O OpenCode/OpenClaw CapProof MCP reuse audit.

This script does not run OpenCode or OpenClaw. It generates reusable MCP client
configuration artifacts and validates the shared CapProof MCP server through a
local JSON-RPC dry-run.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
from typing import Any, Mapping

from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer
from capproof.serialization import JsonObject


ROOT = Path(__file__).resolve().parent
AUDIT_DIR = ROOT / "agent_coverage_audit"
OPENCODE_DIR = ROOT / "real_agent_integrations" / "opencode_mcp_server"
OPENCLAW_DIR = ROOT / "real_agent_integrations" / "openclaw_mcp_server"
OPENCODE_CONFIG = OPENCODE_DIR / "configs" / "opencode.capproof.mcp.example.jsonc"
OPENCLAW_COMMANDS = OPENCLAW_DIR / "configs" / "openclaw.capproof.mcp.commands.md"
OPENCODE_REPORT = OPENCODE_DIR / "reports" / "opencode_mcp_config_report.md"
OPENCODE_SUMMARY = OPENCODE_DIR / "reports" / "opencode_mcp_config_summary.json"
OPENCLAW_REPORT = OPENCLAW_DIR / "reports" / "openclaw_mcp_config_report.md"
OPENCLAW_SUMMARY = OPENCLAW_DIR / "reports" / "openclaw_mcp_config_summary.json"
MATRIX_JSON = AUDIT_DIR / "agent_mcp_client_matrix.json"
MATRIX_MD = AUDIT_DIR / "agent_mcp_client_matrix.md"
OPENCODE_AUDIT = AUDIT_DIR / "opencode_mcp_audit.md"
OPENCLAW_AUDIT = AUDIT_DIR / "openclaw_mcp_audit.md"

CAPROOF_COMMAND = ("python", "run_capproof_mcp_server.py", "--stdio", "--sandboxed-real-execution")
DENY_PATTERNS = ("external mcp", "real email", "raw shell", "production-level")


@dataclass(frozen=True)
class ClientAudit:
    client: str
    repo_path: str
    repo_exists: bool
    runtime_command: str
    runtime_available: bool
    files_scanned: int
    mcp_evidence: tuple[str, ...]
    observed_config_path: str
    real_agent_run: bool
    tools_list_observed_from_real_agent: bool
    tools_call_observed_from_real_agent: bool
    status: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class DryRunResult:
    tools_list_passed: bool
    tools_call_passed: bool
    tools_count: int
    tools: tuple[str, ...]
    allow_verdict: str
    allow_executor_called: bool
    deny_verdict: str
    deny_reason: str
    deny_executor_called: bool
    metadata_cannot_mint_capability: bool
    llm_output_cannot_allow_tool_call: bool


@dataclass(frozen=True)
class AgentMCPAuditSummary:
    stage: str
    opencode: ClientAudit
    openclaw: ClientAudit
    capproof_mcp_command: tuple[str, ...]
    uses_shared_capproof_mcp_server: bool
    forked_guard_logic: bool
    local_json_rpc_dry_run: DryRunResult
    opencode_config_template: str
    openclaw_command_template: str
    production_level_protection_claim: bool
    real_opencode_integration_claim: bool
    real_openclaw_integration_claim: bool
    external_mcp_claim: bool
    raw_shell_supported: bool
    arbitrary_filesystem_access_supported: bool
    api_key_written: bool


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 34O OpenCode/OpenClaw MCP reuse audit.")
    parser.add_argument("--all", action="store_true", help="run audit, generate configs, and dry-run local JSON-RPC")
    parser.add_argument("--report", action="store_true", help="write reports using current audit state")
    args = parser.parse_args()
    ensure_dirs()
    if args.all or args.report:
        summary = build_summary(os.environ)
        write_all_artifacts(summary)
        print(json.dumps(_json(summary), indent=2, sort_keys=True))
        return 0 if _summary_passed(summary) else 1
    parser.print_help()
    return 0


def build_summary(env: Mapping[str, str]) -> AgentMCPAuditSummary:
    opencode = audit_client("opencode", env=env)
    openclaw = audit_client("openclaw", env=env)
    dry_run = run_local_json_rpc_dry_run()
    return AgentMCPAuditSummary(
        stage="34O",
        opencode=opencode,
        openclaw=openclaw,
        capproof_mcp_command=CAPROOF_COMMAND,
        uses_shared_capproof_mcp_server=True,
        forked_guard_logic=False,
        local_json_rpc_dry_run=dry_run,
        opencode_config_template=str(OPENCODE_CONFIG),
        openclaw_command_template=str(OPENCLAW_COMMANDS),
        production_level_protection_claim=False,
        real_opencode_integration_claim=False,
        real_openclaw_integration_claim=False,
        external_mcp_claim=False,
        raw_shell_supported=False,
        arbitrary_filesystem_access_supported=False,
        api_key_written=False,
    )


def audit_client(client: str, *, env: Mapping[str, str]) -> ClientAudit:
    repo_path = resolve_repo_path(client, env)
    runtime_command = client
    runtime_available = shutil.which(runtime_command) is not None
    evidence: list[str] = []
    files_scanned = 0
    observed_config = ""
    if repo_path.exists():
        for path in _iter_small_text_files(repo_path):
            files_scanned += 1
            text = _safe_read(path)
            if not text:
                continue
            lowered = text.lower()
            if "mcp" in lowered:
                rel = str(path.relative_to(repo_path))
                evidence.append(rel)
                if not observed_config and any(token in lowered for token in ("mcpservers", "mcp_servers", "mcp server", "mcp add")):
                    observed_config = rel
            if len(evidence) >= 25:
                break
    status = "repo_present" if repo_path.exists() else "repo_missing"
    notes = _client_notes(client, repo_exists=repo_path.exists(), runtime_available=runtime_available)
    return ClientAudit(
        client=client,
        repo_path=str(repo_path),
        repo_exists=repo_path.exists(),
        runtime_command=runtime_command,
        runtime_available=runtime_available,
        files_scanned=files_scanned,
        mcp_evidence=tuple(evidence),
        observed_config_path=observed_config,
        real_agent_run=False,
        tools_list_observed_from_real_agent=False,
        tools_call_observed_from_real_agent=False,
        status=status,
        notes=notes,
    )


def resolve_repo_path(client: str, env: Mapping[str, str]) -> Path:
    if client == "opencode":
        return Path(env.get("OPENCODE_REPO", ROOT / "external" / "opencode"))
    if client == "openclaw":
        return Path(env.get("OPENCLAW_REPO", ROOT / "external" / "openclaw"))
    raise ValueError(f"unknown client: {client}")


def run_local_json_rpc_dry_run() -> DryRunResult:
    context = make_default_context(executor_mode="sandbox")
    server = CapProofMCPServer(context=context)
    list_response = server.handle_json_rpc({"jsonrpc": "2.0", "id": "stage34o:list", "method": "tools/list", "params": {}})
    tools = tuple(tool["name"] for tool in list_response["result"]["tools"])
    allow_response = server.handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": "stage34o:allow",
            "method": "tools/call",
            "params": {"name": "capproof.echo_summary", "arguments": {"body_ref": "val_summary"}},
        }
    )
    deny_response = server.handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": "stage34o:deny",
            "method": "tools/call",
            "params": {
                "name": "capproof.send_message_mock",
                "arguments": {"recipient": "attacker@example.com", "body_ref": "val_summary"},
                "_meta": {"attempt": "metadata cannot mint capability"},
            },
        }
    )
    allow_structured = allow_response["result"]["structuredContent"]
    deny_structured = deny_response["result"]["structuredContent"]
    return DryRunResult(
        tools_list_passed=bool(tools),
        tools_call_passed=allow_structured["verdict"] == "ALLOW" and deny_structured["verdict"] == "DENY",
        tools_count=len(tools),
        tools=tools,
        allow_verdict=str(allow_structured["verdict"]),
        allow_executor_called=bool(allow_structured["executor_called"]),
        deny_verdict=str(deny_structured["verdict"]),
        deny_reason=str(deny_structured["reason"]),
        deny_executor_called=bool(deny_structured["executor_called"]),
        metadata_cannot_mint_capability=bool(deny_structured["metadata_cannot_mint_capability"]),
        llm_output_cannot_allow_tool_call=bool(deny_structured["llm_output_cannot_allow_tool_call"]),
    )


def write_all_artifacts(summary: AgentMCPAuditSummary) -> None:
    ensure_dirs()
    write_opencode_config()
    write_openclaw_commands()
    OPENCODE_SUMMARY.write_text(json.dumps(_json(summary.opencode), indent=2, sort_keys=True), encoding="utf-8")
    OPENCLAW_SUMMARY.write_text(json.dumps(_json(summary.openclaw), indent=2, sort_keys=True), encoding="utf-8")
    MATRIX_JSON.write_text(json.dumps(_json(summary), indent=2, sort_keys=True), encoding="utf-8")
    OPENCODE_REPORT.write_text(render_client_report(summary.opencode, client_title="OpenCode"), encoding="utf-8")
    OPENCLAW_REPORT.write_text(render_client_report(summary.openclaw, client_title="OpenClaw"), encoding="utf-8")
    OPENCODE_AUDIT.write_text(render_audit_md(summary.opencode, client_title="OpenCode"), encoding="utf-8")
    OPENCLAW_AUDIT.write_text(render_audit_md(summary.openclaw, client_title="OpenClaw"), encoding="utf-8")
    MATRIX_MD.write_text(render_matrix_md(summary), encoding="utf-8")


def write_opencode_config() -> None:
    text = """{
  // Stage 34O example only. Do not write API keys here.
  // This config reuses the standard CapProof MCP server; it does not fork guard logic.
  "mcpServers": {
    "capproof": {
      "command": "python",
      "args": [
        "run_capproof_mcp_server.py",
        "--stdio",
        "--sandboxed-real-execution"
      ],
      "env": {
        "CAPPROOF_MCP_TRACE_PATH": "real_agent_integrations/opencode_mcp_server/reports/opencode_capproof_mcp_trace.jsonl"
      },
      "disabled": false
    }
  },
  "securityBoundary": {
    "metadataCannotMintCapability": true,
    "llmOutputCannotAllowToolCall": true,
    "denyAskExecutorCalled": false,
    "productionLevelProtectionClaim": false
  }
}
"""
    OPENCODE_CONFIG.write_text(text, encoding="utf-8")


def write_openclaw_commands() -> None:
    text = """# OpenClaw CapProof MCP Commands

Stage 34O does not run OpenClaw. These commands document the outbound MCP
server configuration path that should be used in a later explicitly authorized
real OpenClaw run.

Important distinction:

- `openclaw mcp serve` means OpenClaw acting as an MCP server.
- `openclaw mcp add/status/doctor/probe/tools` manages outbound MCP servers
  available to OpenClaw as a client.

CapProof should be registered as an outbound MCP server:

```bash
openclaw mcp add capproof --command python --arg run_capproof_mcp_server.py --arg --stdio --arg --sandboxed-real-execution
openclaw mcp doctor capproof --probe
openclaw mcp tools capproof
```

Security notes:

- This reuses the standard CapProof MCP server.
- It does not fork CapProof guard or Reference Monitor logic.
- MCP metadata, tool metadata, plugin metadata, and LLM output cannot mint capability.
- DENY/ASK must not execute an executor.
- This is not a production-level protection claim.
"""
    OPENCLAW_COMMANDS.write_text(text, encoding="utf-8")


def render_client_report(audit: ClientAudit, *, client_title: str) -> str:
    return "\n".join(
        [
            f"# {client_title} CapProof MCP Config Report",
            "",
            "## Stage Positioning",
            "",
            "- Stage 34O is audit/config/dry-run only.",
            f"- Stage 34O did not run real {client_title}.",
            "- It does not claim real OpenCode/OpenClaw integration.",
            "- It does not claim production-level protection.",
            "- It reuses the standard CapProof MCP server.",
            "",
            "## Runtime / Repo Status",
            "",
            f"- repo_path: `{audit.repo_path}`",
            f"- repo_exists: {audit.repo_exists}",
            f"- runtime_command: `{audit.runtime_command}`",
            f"- runtime_available: {audit.runtime_available}",
            f"- files_scanned: {audit.files_scanned}",
            f"- observed_config_path: `{audit.observed_config_path}`",
            f"- status: {audit.status}",
            "",
            "## MCP Evidence",
            "",
            *(f"- `{item}`" for item in audit.mcp_evidence[:20]),
            "",
            "## Non-Claims",
            "",
            "- Real agent process run: false.",
            "- Real agent `tools/list` observed: false.",
            "- Real agent `tools/call` observed: false.",
            "- Production-level protection: false.",
            "- OpenCode/OpenClaw metadata cannot mint capability.",
        ]
    ) + "\n"


def render_audit_md(audit: ClientAudit, *, client_title: str) -> str:
    notes = "\n".join(f"- {note}" for note in audit.notes)
    return f"""# {client_title} MCP Reuse Audit

## Scope

Stage 34O audits whether {client_title} can reuse the standard CapProof MCP
server as an outbound MCP server. It does not run {client_title}; it only checks
repo/runtime presence, generates config guidance, and validates CapProof locally
through JSON-RPC.

## Status

- repo_path: `{audit.repo_path}`
- repo_exists: {audit.repo_exists}
- runtime_available: {audit.runtime_available}
- files_scanned: {audit.files_scanned}
- observed_config_path: `{audit.observed_config_path}`
- real_agent_run: {audit.real_agent_run}
- tools_list_observed_from_real_agent: {audit.tools_list_observed_from_real_agent}
- tools_call_observed_from_real_agent: {audit.tools_call_observed_from_real_agent}
- status: {audit.status}

## Notes

{notes}

## Boundary

- Reuse the same `run_capproof_mcp_server.py --stdio --sandboxed-real-execution` server.
- Do not fork CapProof guard or Reference Monitor logic.
- Tool metadata, skill/plugin metadata, MCP metadata, and LLM output cannot mint capability.
- DENY/ASK executor_called must remain false.
- No production-level protection claim.
"""


def render_matrix_md(summary: AgentMCPAuditSummary) -> str:
    dry = summary.local_json_rpc_dry_run
    lines = [
        "# Agent MCP Client Matrix",
        "",
        "## Stage Positioning",
        "",
        "- Stage 34O is OpenCode/OpenClaw MCP reuse audit/config/dry-run only.",
        "- It does not run real OpenCode/OpenClaw.",
        "- It does not claim real OpenCode/OpenClaw integration.",
        "- It reuses the standard CapProof MCP server and does not fork guard logic.",
        "",
        "## Client Matrix",
        "",
        "| client | repo_exists | runtime_available | files_scanned | real_agent_run | real tools/list | real tools/call | status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for audit in (summary.opencode, summary.openclaw):
        lines.append(
            f"| {audit.client} | {audit.repo_exists} | {audit.runtime_available} | {audit.files_scanned} | "
            f"{audit.real_agent_run} | {audit.tools_list_observed_from_real_agent} | "
            f"{audit.tools_call_observed_from_real_agent} | {audit.status} |"
        )
    lines.extend(
        [
            "",
            "## Local JSON-RPC CapProof MCP Dry-Run",
            "",
            f"- tools_list_passed: {dry.tools_list_passed}",
            f"- tools_call_passed: {dry.tools_call_passed}",
            f"- tools_count: {dry.tools_count}",
            f"- allow_verdict: {dry.allow_verdict}",
            f"- allow_executor_called: {dry.allow_executor_called}",
            f"- deny_verdict: {dry.deny_verdict}",
            f"- deny_reason: {dry.deny_reason}",
            f"- deny_executor_called: {dry.deny_executor_called}",
            f"- metadata_cannot_mint_capability: {dry.metadata_cannot_mint_capability}",
            f"- llm_output_cannot_allow_tool_call: {dry.llm_output_cannot_allow_tool_call}",
            "",
            "## Non-Claims",
            "",
            f"- production_level_protection_claim: {summary.production_level_protection_claim}",
            f"- real_opencode_integration_claim: {summary.real_opencode_integration_claim}",
            f"- real_openclaw_integration_claim: {summary.real_openclaw_integration_claim}",
            f"- external_mcp_claim: {summary.external_mcp_claim}",
            f"- raw_shell_supported: {summary.raw_shell_supported}",
            f"- arbitrary_filesystem_access_supported: {summary.arbitrary_filesystem_access_supported}",
        ]
    )
    return "\n".join(lines) + "\n"


def _client_notes(client: str, *, repo_exists: bool, runtime_available: bool) -> tuple[str, ...]:
    notes = [
        "No real agent process was run.",
        "No real agent tools/list or tools/call observation is claimed.",
        "CapProof MCP config points to the shared standard server.",
    ]
    if not repo_exists:
        notes.append(f"{client} repo is missing; source-specific config schema still needs manual verification.")
    if not runtime_available:
        notes.append(f"{client} runtime command is not on PATH; runtime integration remains unverified.")
    return tuple(notes)


def _summary_passed(summary: AgentMCPAuditSummary) -> bool:
    dry = summary.local_json_rpc_dry_run
    return (
        summary.uses_shared_capproof_mcp_server
        and not summary.forked_guard_logic
        and dry.tools_list_passed
        and dry.tools_call_passed
        and dry.deny_executor_called is False
        and dry.metadata_cannot_mint_capability
        and dry.llm_output_cannot_allow_tool_call
        and not summary.production_level_protection_claim
        and not summary.real_opencode_integration_claim
        and not summary.real_openclaw_integration_claim
        and not summary.api_key_written
    )


def _iter_small_text_files(root: Path):
    allowed_suffixes = {".md", ".json", ".jsonc", ".yaml", ".yml", ".toml", ".txt", ".ts", ".tsx", ".js", ".py", ".go", ".rs"}
    ignored_parts = {".git", "node_modules", ".venv", "dist", "build", "__pycache__"}
    for path in root.rglob("*"):
        if any(part in ignored_parts for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in allowed_suffixes:
            yield path


def _safe_read(path: Path) -> str:
    try:
        if path.stat().st_size > 512_000:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def ensure_dirs() -> None:
    for directory in (
        AUDIT_DIR,
        OPENCODE_DIR / "configs",
        OPENCODE_DIR / "reports",
        OPENCLAW_DIR / "configs",
        OPENCLAW_DIR / "reports",
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _json(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, tuple):
        return [_json(item) for item in value]
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())
