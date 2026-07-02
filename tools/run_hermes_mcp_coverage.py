#!/usr/bin/env python3
"""Run Hermes-local CapProof MCP scenario coverage over the local MCP server.

This runner does not run Hermes and does not call DeepSeek. It exercises the
productized CapProof MCP server through the standard JSON-RPC methods that
Hermes would use: ``tools/list`` and ``tools/call``.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
import json
from pathlib import Path
import tempfile
from typing import Any

from capproof.mcp.context import make_default_context
from capproof.mcp.server import CapProofMCPServer
from capproof.serialization import JsonObject


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "real_agent_integrations" / "hermes_mcp_server"
SCENARIO_DIR = BASE_DIR / "scenarios"
REPORT_DIR = BASE_DIR / "reports"
TRACE_DIR = BASE_DIR / "traces"
MATRIX_JSON = REPORT_DIR / "hermes_mcp_coverage_matrix.json"
MATRIX_MD = REPORT_DIR / "hermes_mcp_coverage_matrix.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CapProof MCP scenario coverage.")
    parser.add_argument("--list-scenarios", action="store_true", help="list available scenario IDs")
    parser.add_argument("--local-client", action="store_true", help="run scenarios with a local JSON-RPC MCP client")
    parser.add_argument("--scenario", default="all", help="scenario ID or all")
    parser.add_argument("--report", action="store_true", help="write or refresh coverage reports")
    args = parser.parse_args()

    ensure_dirs()
    scenarios = load_scenarios()
    if args.list_scenarios:
        print(json.dumps({"scenarios": [scenario["scenario_id"] for scenario in scenarios]}, indent=2, sort_keys=True))
        return 0
    if args.local_client:
        selected = select_scenarios(scenarios, args.scenario)
        summary = run_scenarios(selected)
        write_reports(summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["failed_steps"] == 0 and summary["executor_called_on_deny_ask"] == 0 else 1
    if args.report:
        summary = run_scenarios(scenarios)
        write_reports(summary)
        print(f"matrix_json: {MATRIX_JSON}")
        print(f"matrix_md: {MATRIX_MD}")
        return 0
    parser.print_help()
    return 0


def load_scenarios() -> list[JsonObject]:
    scenarios: list[JsonObject] = []
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["source_file"] = str(path)
            scenarios.append(data)
    return scenarios


def select_scenarios(scenarios: list[JsonObject], scenario_id: str) -> list[JsonObject]:
    if scenario_id == "all":
        return scenarios
    selected = [scenario for scenario in scenarios if scenario.get("scenario_id") == scenario_id]
    if not selected:
        raise SystemExit(f"unknown scenario: {scenario_id}")
    return selected


def run_scenarios(scenarios: list[JsonObject]) -> JsonObject:
    rows: list[JsonObject] = []
    scenario_summaries: list[JsonObject] = []
    for scenario in scenarios:
        scenario_id = str(scenario["scenario_id"])
        workspace = Path(tempfile.mkdtemp(prefix=f"capproof_mcp_{scenario_id}_"))
        trace_path = TRACE_DIR / f"{scenario_id}.jsonl"
        if trace_path.exists():
            trace_path.unlink()
        server = CapProofMCPServer(context=make_default_context(workspace=workspace, trace_path=trace_path))
        list_result = server.handle_json_rpc({"jsonrpc": "2.0", "id": f"{scenario_id}:list", "method": "tools/list", "params": {}})
        tools_discovered = bool(list_result and "result" in list_result and list_result["result"].get("tools"))
        scenario_rows: list[JsonObject] = []
        for index, step in enumerate(scenario.get("steps", []), start=1):
            row = run_step(server, scenario=scenario, step=step, index=index)
            row["tools_discovered"] = tools_discovered
            scenario_rows.append(row)
            rows.append(row)
        scenario_summaries.append(
            {
                "scenario_id": scenario_id,
                "category": scenario.get("category", ""),
                "user_task": scenario.get("user_task", ""),
                "steps": len(scenario_rows),
                "passed": all(row["expected_matched"] for row in scenario_rows),
                "trace_path": str(trace_path),
                "tools_discovered": tools_discovered,
            }
        )
    return summarize(rows=rows, scenario_summaries=scenario_summaries)


def run_step(server: CapProofMCPServer, *, scenario: JsonObject, step: JsonObject, index: int) -> JsonObject:
    scenario_id = str(scenario["scenario_id"])
    step_id = str(step.get("step_id", f"step_{index}"))
    method = str(step.get("method", "tools/call"))
    tool_name = str(step.get("tool_name", ""))
    arguments = step.get("arguments", {})
    params: JsonObject = {"name": tool_name, "arguments": arguments}
    params_metadata = _scenario_metadata(scenario, step)
    params.update(params_metadata)
    response = server.handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": f"{scenario_id}:{step_id}",
            "method": method,
            "params": params,
        }
    )
    if response is None:
        return _error_row(scenario, step, method=method, tool_name=tool_name, reason="NoResponse")
    if "error" in response:
        code = response["error"].get("code")
        reason = "InvalidParams" if code == -32602 else str(response["error"].get("message", "Error"))
        return _error_row(scenario, step, method=method, tool_name=tool_name, reason=reason, error_code=code)
    result = response["result"]
    structured = result.get("structuredContent", {}) if isinstance(result, dict) else {}
    trace = structured.get("trace", {}) if isinstance(structured, dict) else {}
    proof = structured.get("proof", {}) if isinstance(structured, dict) else {}
    verdict = str(structured.get("verdict", "UNKNOWN"))
    reason = str(structured.get("reason", ""))
    executor_called = bool(structured.get("executor_called", False))
    row = {
        "scenario_id": scenario_id,
        "category": scenario.get("category", ""),
        "step_id": step_id,
        "user_task": scenario.get("user_task", ""),
        "mcp_method": method,
        "tool_name": tool_name,
        "original_arguments": arguments,
        "canonical_action_hash": proof.get("canonical_action_hash"),
        "verdict": verdict,
        "reason": reason,
        "proof_id": proof.get("proof_id"),
        "executor_called": executor_called,
        "expected_verdict": step.get("expected_verdict"),
        "expected_reason": step.get("expected_reason"),
        "expected_executor_called": step.get("expected_executor_called"),
        "expected_matched": _matches(step, verdict=verdict, reason=reason, executor_called=executor_called),
        "trace_id": trace.get("trace_id"),
        "metadata_cannot_mint_capability": structured.get("metadata_cannot_mint_capability") is True,
        "pending_authorization_request": structured.get("pending_authorization_request"),
        "raw_trace": trace,
    }
    return row


def _error_row(
    scenario: JsonObject,
    step: JsonObject,
    *,
    method: str,
    tool_name: str,
    reason: str,
    error_code: object | None = None,
) -> JsonObject:
    verdict = "ERROR"
    executor_called = False
    return {
        "scenario_id": scenario["scenario_id"],
        "category": scenario.get("category", ""),
        "step_id": step.get("step_id", ""),
        "user_task": scenario.get("user_task", ""),
        "mcp_method": method,
        "tool_name": tool_name,
        "original_arguments": step.get("arguments", {}),
        "canonical_action_hash": None,
        "verdict": verdict,
        "reason": reason,
        "proof_id": None,
        "executor_called": executor_called,
        "expected_verdict": step.get("expected_verdict"),
        "expected_reason": step.get("expected_reason"),
        "expected_executor_called": step.get("expected_executor_called"),
        "expected_matched": _matches(step, verdict=verdict, reason=reason, executor_called=executor_called),
        "error_code": error_code,
        "metadata_cannot_mint_capability": True,
        "pending_authorization_request": None,
        "raw_trace": {},
    }


def _scenario_metadata(scenario: JsonObject, step: JsonObject) -> JsonObject:
    metadata = dict(step.get("params_metadata", {})) if isinstance(step.get("params_metadata", {}), dict) else {}
    meta = dict(metadata.get("_meta", {})) if isinstance(metadata.get("_meta", {}), dict) else {}
    meta.setdefault("user_task", str(scenario.get("user_task", "")))
    metadata["_meta"] = meta
    return metadata


def _matches(step: JsonObject, *, verdict: str, reason: str, executor_called: bool) -> bool:
    if step.get("expected_verdict") != verdict:
        return False
    expected_reason = step.get("expected_reason")
    if expected_reason and expected_reason != reason:
        return False
    if "expected_executor_called" in step and bool(step["expected_executor_called"]) != executor_called:
        return False
    return True


def summarize(*, rows: list[JsonObject], scenario_summaries: list[JsonObject]) -> JsonObject:
    verdict_counts: dict[str, int] = {}
    for row in rows:
        verdict_counts[str(row["verdict"])] = verdict_counts.get(str(row["verdict"]), 0) + 1
    deny_ask_executor = sum(
        1 for row in rows if row["verdict"] in {"DENY", "ASK"} and bool(row["executor_called"])
    )
    metadata_failures = sum(
        1 for row in rows if row["category"] == "metadata_injection" and row["verdict"] != "DENY"
    )
    return {
        "stage": "32H",
        "not_real_hermes_run": True,
        "not_deepseek_call": True,
        "production_level_protection_claim": False,
        "total_scenarios": len(scenario_summaries),
        "total_steps": len(rows),
        "passed_steps": sum(1 for row in rows if row["expected_matched"]),
        "failed_steps": sum(1 for row in rows if not row["expected_matched"]),
        "verdict_counts": verdict_counts,
        "executor_called_on_deny_ask": deny_ask_executor,
        "metadata_injection_unexpected_allow": metadata_failures,
        "tools_list_tools_call_standard": True,
        "scenario_summaries": scenario_summaries,
        "workflow_trace": rows,
    }


def write_reports(summary: JsonObject) -> None:
    ensure_dirs()
    MATRIX_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    MATRIX_MD.write_text(render_markdown(summary), encoding="utf-8")


def render_markdown(summary: JsonObject) -> str:
    lines = [
        "# Hermes MCP Coverage Matrix",
        "",
        "## Stage Positioning",
        "",
        "- Stage 32H expands Hermes-local MCP UX and coverage over local JSON-RPC MCP calls.",
        "- This report does not claim production-level Hermes protection.",
        "- This report does not run Hermes or call DeepSeek.",
        "- Authority-bearing calls still enter canonicalizer -> CapProofMiddleware.guard(...) -> Reference Monitor -> executor gate.",
        "- DENY/ASK executor_called must remain false.",
        "- Tool metadata, annotations, client metadata, and natural language cannot mint capability.",
        "",
        "## Summary",
        "",
        f"- total scenarios: {summary['total_scenarios']}",
        f"- total steps: {summary['total_steps']}",
        f"- passed steps: {summary['passed_steps']}",
        f"- failed steps: {summary['failed_steps']}",
        f"- verdict counts: `{json.dumps(summary['verdict_counts'], sort_keys=True)}`",
        f"- executor_called_on_deny_ask: {summary['executor_called_on_deny_ask']}",
        f"- metadata_injection_unexpected_allow: {summary['metadata_injection_unexpected_allow']}",
        "",
        "## Workflow Trace Matrix",
        "",
        "| scenario | category | step | user_task | MCP method | tool_name | original_arguments | canonical_action_hash | verdict | reason | proof_id | executor_called | expected_matched |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary["workflow_trace"]:
        lines.append(
            "| {scenario_id} | {category} | {step_id} | {user_task} | {mcp_method} | {tool_name} | `{args}` | `{hash}` | {verdict} | {reason} | `{proof}` | {executor} | {matched} |".format(
                scenario_id=row["scenario_id"],
                category=row["category"],
                step_id=row["step_id"],
                user_task=_md(row["user_task"]),
                mcp_method=row["mcp_method"],
                tool_name=row["tool_name"],
                args=json.dumps(row["original_arguments"], sort_keys=True),
                hash=row.get("canonical_action_hash") or "",
                verdict=row["verdict"],
                reason=row.get("reason") or "",
                proof=row.get("proof_id") or "",
                executor=row["executor_called"],
                matched=row["expected_matched"],
            )
        )
    return "\n".join(lines) + "\n"


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def ensure_dirs() -> None:
    for directory in (SCENARIO_DIR, REPORT_DIR, TRACE_DIR):
        directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
