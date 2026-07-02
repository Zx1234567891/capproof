#!/usr/bin/env python3
"""Generate the CapProof MCP compatibility matrix.

The matrix is artifact metadata only. It does not run Hermes, call DeepSeek, or
execute authority-bearing tools.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "artifact_reports"
MATRIX_MD = REPORT_DIR / "mcp_compatibility_matrix.md"
MATRIX_JSON = REPORT_DIR / "mcp_compatibility_matrix.json"


def compatibility_rows() -> list[dict[str, str]]:
    return [
        row("local stdio MCP server", "supported", "run_capproof_mcp_server.py --stdio", "python run_capproof_mcp_server.py --list-tools", "Local process stdio only."),
        row("initialize", "supported", "stdio server handles JSON-RPC initialize", "tests/test_capproof_mcp_protocol.py -q", "Used by Hermes standard MCP smoke."),
        row("tools/list", "supported", "7 CapProof tools observed", "python run_capproof_mcp_server.py --list-tools", "Also observed in real Hermes smoke."),
        row("tools/call", "supported", "standard CapProof MCP call path", "python run_capproof_mcp_server.py --self-test", "Authority-bearing tools enter guard path."),
        row("structuredContent", "supported", "tool responses include structuredContent", "tests/test_capproof_mcp_protocol.py -q", "Includes verdict, proof, trace, executor_called."),
        row("JSON-RPC stdio cleanliness", "supported", "stdout reserved for JSON-RPC", "tests/test_capproof_mcp_doctor.py -q", "Human logs go to stderr/live log/report/trace."),
        row("capproof.echo_summary", "supported", "tools/list exposes tool", "python run_capproof_mcp_server.py --list-tools", "No authority-bearing side effect."),
        row("capproof.send_message_mock", "supported", "ALLOW/DENY paths tested", "python run_capproof_mcp_server.py --self-test", "Mock only, no real email."),
        row("capproof.read_workspace_file", "supported", "workspace sandbox tests", "tests/test_capproof_mcp_sandbox_file_read.py -q", "Workspace-only subset."),
        row("capproof.write_workspace_file", "supported", "atomic write sandbox tests", "tests/test_capproof_mcp_sandbox_file_write.py -q", "Workspace-only subset."),
        row("capproof.run_command_template", "partial", "allowlisted command templates", "tests/test_capproof_mcp_sandbox_commands.py -q", "No raw shell support."),
        row("capproof.get_trace", "supported", "trace viewer and MCP trace tool", "tests/test_capproof_mcp_trace.py -q", "Local trace only."),
        row("capproof.request_authorization", "supported", "trusted ASK queue", "tests/test_capproof_mcp_ask_approval_flow.py -q", "ASK does not auto-mint capability."),
        row("resources", "not_claimed", "not implemented", "none", "No MCP resources claim."),
        row("prompts", "not_claimed", "not implemented", "none", "No MCP prompts claim."),
        row("sampling", "not_claimed", "not implemented", "none", "No MCP sampling claim."),
        row("elicitation", "not_claimed", "not implemented", "none", "No MCP elicitation claim."),
        row("Streamable HTTP", "not_claimed", "not implemented", "none", "Only local stdio is claimed."),
        row("OAuth / remote MCP authorization", "not_claimed", "not implemented", "none", "Trusted local CLI approval only."),
        row("external MCP server protection", "not_claimed", "not implemented", "none", "No external MCP claim."),
        row("all MCP transports", "not_claimed", "not implemented", "none", "Only local stdio subset."),
        row("all future/draft MCP versions", "not_claimed", "not implemented", "none", "Evidence is tied to current local profile."),
    ]


def row(feature: str, status: str, evidence: str, test_command: str, notes: str) -> dict[str, str]:
    return {
        "feature": feature,
        "status": status,
        "evidence": evidence,
        "test_command": test_command,
        "notes": notes,
    }


def generate() -> dict[str, Any]:
    rows = compatibility_rows()
    supported = sum(1 for item in rows if item["status"] == "supported")
    partial = sum(1 for item in rows if item["status"] == "partial")
    not_claimed = sum(1 for item in rows if item["status"] == "not_claimed")
    return {
        "profile": "CapProof local stdio MCP compatibility profile",
        "supported_protocol_subset": [
            "local stdio MCP server",
            "initialize",
            "tools/list",
            "tools/call",
            "structuredContent",
            "JSON-RPC stdio cleanliness",
        ],
        "tools_count": 7,
        "rows": rows,
        "summary": {
            "supported": supported,
            "partial": partial,
            "not_claimed": not_claimed,
            "production_level_protection_claim": False,
            "all_mcp_transports_claim": False,
            "external_mcp_claim": False,
        },
    }


def write_reports(matrix: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    MATRIX_JSON.write_text(json.dumps(matrix, indent=2, sort_keys=True), encoding="utf-8")
    MATRIX_MD.write_text(format_markdown(matrix), encoding="utf-8")


def format_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# MCP Compatibility Matrix",
        "",
        "## Summary",
        "",
        f"- profile: {matrix['profile']}",
        f"- tools count: {matrix['tools_count']}",
        f"- supported: {matrix['summary']['supported']}",
        f"- partial: {matrix['summary']['partial']}",
        f"- not claimed: {matrix['summary']['not_claimed']}",
        f"- production-level protection claim: {str(matrix['summary']['production_level_protection_claim']).lower()}",
        "",
        "## Matrix",
        "",
        "| feature | status | evidence | test command | notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in matrix["rows"]:
        lines.append(
            f"| {item['feature']} | {item['status']} | {item['evidence']} | `{item['test_command']}` | {item['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Non-Claims",
            "",
            "- resources",
            "- prompts",
            "- sampling",
            "- elicitation",
            "- Streamable HTTP",
            "- OAuth / remote MCP authorization",
            "- external MCP server protection",
            "- all MCP transports",
            "- all future/draft MCP versions",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate CapProof MCP compatibility matrix.")
    parser.add_argument("--report", action="store_true", help="write markdown and JSON reports")
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    args = parser.parse_args(argv)

    matrix = generate()
    if args.report or not args.json:
        write_reports(matrix)
    if args.json:
        print(json.dumps(matrix, indent=2, sort_keys=True))
    else:
        print(format_markdown(matrix))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
