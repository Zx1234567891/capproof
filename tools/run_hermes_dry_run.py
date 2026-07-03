#!/usr/bin/env python3
"""Hermes supported-subset dry-run harness.

This script evaluates mock/replay Hermes-like JSON events only. It does not
import or run Hermes, install dependencies, execute third-party commands,
execute real tools, send email, call networks, or run a shell.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

from capproof import (
    ActionKind,
    AgentAdapterRegistry,
    AgentRuntimeState,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    Canonicalizer,
    CapProofMiddleware,
    DenyReason,
    GuardedExecutor,
    InMemoryCapabilityStore,
    InMemoryReceiptStore,
    Linearity,
    MockExecutor,
    MonitorState,
    ProvenanceRuntime,
    Receipt,
    ReceiptType,
    VerificationDecision,
    default_profile_agent_adapters,
    mint_capability,
    profile_tool_contract_registry,
)

ROOT = Path(__file__).resolve().parents[1]
DRY_RUN_DIR = ROOT / "hermes_dry_run"
CASES_DIR = DRY_RUN_DIR / "cases"
REPORTS_DIR = DRY_RUN_DIR / "reports"
REPORT_PATH = ROOT / "artifact_reports" / "hermes_dry_run_report.md"
TASK_ID = "task_hermes_dry_run"


@dataclass(frozen=True)
class DryRunCase:
    case_id: str
    category: str
    hermes_event: dict[str, Any]
    expected_verdict: str
    expected_reason: str
    expected_executor_behavior: str
    notes: str
    setup: dict[str, Any]


@dataclass(frozen=True)
class DryRunResult:
    case_id: str
    category: str
    expected_verdict: str
    expected_reason: str
    actual_verdict: str
    actual_reason: str
    executor_called: bool
    expected_executor_behavior: str
    passed: bool
    mock_event: dict[str, Any] | None
    message: str
    notes: str
    capability_minted_from_stripped_memory: bool = False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hermes mock dry-run cases through CapProof.")
    parser.add_argument("--category", choices=("supported", "sanitized", "deny", "unknown"), default=None)
    parser.add_argument("--json", action="store_true", help="print JSON summary to stdout")
    args = parser.parse_args()
    payload = run_dry_run(category=args.category)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"hermes dry-run cases: {payload['summary']['total_cases']}")
        print(f"passed: {payload['summary']['passed_cases']}")
        print(f"failed: {payload['summary']['failed_cases']}")
        print(f"sanitized_pass_count: {payload['summary']['sanitized_pass_count']}")
        print(f"deny_unexpected_allow_count: {payload['summary']['deny_unexpected_allow_count']}")
        print(f"unknown_fail_closed_count: {payload['summary']['unknown_fail_closed_count']}")
        print(f"executor_called_on_deny: {payload['summary']['executor_called_on_deny']}")
        print(f"executor_called_on_ask: {payload['summary']['executor_called_on_ask']}")
        print(f"capability_minted_from_stripped_memory: {payload['summary']['capability_minted_from_stripped_memory']}")
        print(f"report: {REPORT_PATH}")
    return 0 if payload["summary"]["failed_cases"] == 0 else 1


def run_dry_run(*, category: str | None = None, reports_dir: Path = REPORTS_DIR) -> dict[str, Any]:
    cases = load_cases(category=category)
    results = [run_case(case) for case in cases]
    payload = {
        "summary": summarize(results),
        "results": [asdict(result) for result in results],
        "safety": {
            "real_hermes_executed": False,
            "dependencies_installed": False,
            "third_party_commands_executed": False,
            "real_tools_executed": False,
            "network_used": False,
            "real_shell_executed": False,
        },
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
    return payload


def load_cases(*, category: str | None = None) -> list[DryRunCase]:
    roots = [CASES_DIR / category] if category else [
        CASES_DIR / name for name in ("supported", "sanitized", "deny", "unknown")
    ]
    cases: list[DryRunCase] = []
    for root in roots:
        for path in sorted(root.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            cases.append(
                DryRunCase(
                    case_id=str(data["case_id"]),
                    category=str(data["category"]),
                    hermes_event=dict(data["hermes_event"]),
                    expected_verdict=str(data["expected_verdict"]),
                    expected_reason=str(data.get("expected_reason", "")),
                    expected_executor_behavior=str(data["expected_executor_behavior"]),
                    notes=str(data.get("notes", "")),
                    setup=dict(data.get("setup", {})),
                )
            )
    return cases


def run_case(case: DryRunCase) -> DryRunResult:
    workspace = Path(tempfile.mkdtemp(prefix=f"capproof_hermes_{case.case_id}_")) / "project"
    workspace.mkdir(parents=True, exist_ok=True)
    state = MonitorState(
        capability_store=InMemoryCapabilityStore(),
        receipt_store=InMemoryReceiptStore(),
        tool_contracts=profile_tool_contract_registry(),
        canonicalizer=Canonicalizer(workspace),
    )
    event = expand_placeholders(case.hermes_event, workspace)
    apply_setup(state, expand_placeholders(case.setup, workspace))
    runtime_state = make_runtime_state(state, agent_id=str(event.get("agent_id", "hermes_mock")))
    middleware = CapProofMiddleware(
        AgentAdapterRegistry(
            default_profile_agent_adapters(
                tool_contracts=state.tool_contracts,
                canonicalizer=state.canonicalizer,
            )
        )
    )
    decision = middleware.guard(event, runtime_state)
    executor = MockExecutor(workspace)
    execution = GuardedExecutor(executor).execute_if_allowed(decision)
    actual_verdict = decision.decision.value
    actual_reason = decision.deny_reason.value if decision.deny_reason else ""
    executor_called = execution.executed
    caps_after = runtime_state.monitor_state.capability_store.list_capabilities()
    minted_from_stripped_memory = (
        case.category == "sanitized"
        and any(cap.root.value.startswith("MEMORY") for cap in caps_after)
    )
    sanitized_ok = True
    if case.category == "sanitized":
        args = execution.mock_event.get("args", {}) if execution.mock_event else {}
        sanitized_ok = (
            execution.mock_event is not None
            and execution.mock_event.get("mock_tool") == "memory_write"
            and args.get("authority_claims") == {}
            and args.get("stripped_authority") is True
            and not minted_from_stripped_memory
        )
    passed = (
        actual_verdict == case.expected_verdict
        and (case.expected_reason == "" or actual_reason == case.expected_reason)
        and executor_called == (case.expected_executor_behavior == "called")
        and sanitized_ok
    )
    if executor.real_email_sent or executor.real_network_called or executor.real_shell_executed:
        passed = False
    return DryRunResult(
        case_id=case.case_id,
        category=case.category,
        expected_verdict=case.expected_verdict,
        expected_reason=case.expected_reason,
        actual_verdict=actual_verdict,
        actual_reason=actual_reason,
        executor_called=executor_called,
        expected_executor_behavior=case.expected_executor_behavior,
        passed=passed,
        mock_event=execution.mock_event,
        message=decision.message,
        notes=case.notes,
        capability_minted_from_stripped_memory=minted_from_stripped_memory,
    )


def make_runtime_state(state: MonitorState, *, agent_id: str) -> AgentRuntimeState:
    runtime = ProvenanceRuntime(task_id=TASK_ID, agent_id=agent_id, receipt_store=state.receipt_store)
    values = {}
    for value_id, tool, data_class, content in (
        ("val_summary", "summarize", "summary(report)", "summary"),
        ("val_report", "read_file", "report", "report"),
        ("val_doc", "read_file", "doc", "doc"),
        ("val_patch", "read_file", "patch", "patch"),
        ("val_policy", "read_file", "policy", "policy"),
    ):
        value, _receipt = runtime.record_tool_out(
            tool=tool,
            output_id=value_id,
            data_class=data_class,
            content=content,
            provenance_root="USER",
        )
        values[value.value_id] = value
    return AgentRuntimeState(monitor_state=state, value_refs=values, authspec_ref="hermes_dry_run")


def apply_setup(state: MonitorState, setup: dict[str, Any]) -> None:
    for cap in setup.get("capabilities", ()):
        mint_case_capability(state, dict(cap))
    for item in setup.get("delegations", ()):
        mint_delegation(state, dict(item))


def mint_delegation(state: MonitorState, item: dict[str, Any]) -> None:
    cap_id = str(item["cap_id"])
    recipient = canonical_value(state, AuthorityRole.RECIPIENT, item["recipient"])
    mint_case_capability(
        state,
        {
            "cap_id": cap_id,
            "agent_id": item.get("child_agent", "email_agent"),
            "tool": "send_email",
            "role": "recipient",
            "value": recipient,
            "root": "DELEGATION",
            "already_canonical": True,
        },
    )
    state.receipt_store.append(
        Receipt(
            receipt_id=str(item.get("receipt_id", f"receipt_{cap_id}")),
            receipt_type=ReceiptType.DELEGATION,
            task_id=TASK_ID,
            agent_id=str(item.get("parent_agent", "research_agent")),
            subject_hash="delegation",
            payload={
                "parent_agent": str(item.get("parent_agent", "research_agent")),
                "child_agent": str(item.get("child_agent", "email_agent")),
                "parent_caps": tuple(item.get("parent_caps", ("cap_parent",))),
                "child_caps": (cap_id,),
                "delegated_scope": {
                    "recipient": canonical_value(state, AuthorityRole.RECIPIENT, item.get("allowed_recipient", item["recipient"])),
                    "attenuation_valid": bool(item.get("attenuation_valid", True)),
                },
            },
            issued_at="2026-06-28T00:00:00Z",
        )
    )


def mint_case_capability(state: MonitorState, cap: dict[str, Any]) -> None:
    role = AuthorityRole(str(cap["role"]))
    tool = str(cap["tool"])
    raw_value = cap["value"]
    value = raw_value if cap.get("already_canonical") else canonical_value(state, role, raw_value)
    mint_capability(
        state.capability_store,
        Capability(
            cap_id=str(cap["cap_id"]),
            issuer="hermes_dry_run",
            root=CapabilityRoot(str(cap.get("root", "USER"))),
            agent_id=str(cap.get("agent_id", "hermes_mock")),
            task_id=str(cap.get("task_id", TASK_ID)),
            action_kind=action_kind_for_tool(tool),
            tool=tool,
            role=role,
            predicate={"op": "eq", "value": value},
            linearity=Linearity.REUSABLE,
            max_uses=100,
            uses=0,
            expires_at="task_end",
            nonce=f"nonce:{cap['cap_id']}",
        ),
    )


def canonical_value(state: MonitorState, role: AuthorityRole, value: Any) -> Any:
    if role == AuthorityRole.RECIPIENT:
        return state.canonicalizer.canonicalize_recipient(str(value)).value
    if role == AuthorityRole.FILE_PATH:
        return state.canonicalizer.canonicalize_file_path(str(value)).value
    if role == AuthorityRole.EXTERNAL_ENDPOINT:
        return state.canonicalizer.canonicalize_endpoint(str(value)).value
    return value


def action_kind_for_tool(tool: str) -> ActionKind:
    return {
        "send_email": ActionKind.SEND,
        "send_message": ActionKind.SEND,
        "cron_send_email": ActionKind.SEND,
        "cron_send_message": ActionKind.SEND,
        "write_file": ActionKind.WRITE,
        "run_shell": ActionKind.EXEC,
        "http_post": ActionKind.NET,
    }.get(tool, ActionKind.TRANSFORM)


def expand_placeholders(value: Any, workspace: Path) -> Any:
    if isinstance(value, str):
        return value.replace("$WORKSPACE", str(workspace))
    if isinstance(value, list):
        return [expand_placeholders(item, workspace) for item in value]
    if isinstance(value, dict):
        return {str(key): expand_placeholders(item, workspace) for key, item in value.items()}
    return value


def summarize(results: list[DryRunResult]) -> dict[str, Any]:
    supported = [result for result in results if result.category == "supported"]
    sanitized = [result for result in results if result.category == "sanitized"]
    deny = [result for result in results if result.category == "deny"]
    unknown = [result for result in results if result.category == "unknown"]
    expected_deny = [result for result in deny if result.expected_verdict == "DENY"]
    summary = {
        "total_cases": len(results),
        "supported_cases": len(supported),
        "sanitized_cases": len(sanitized),
        "explicit_deny_cases": len(deny),
        "unknown_cases": len(unknown),
        "passed_cases": sum(result.passed for result in results),
        "failed_cases": sum(not result.passed for result in results),
        "supported_allow_count": sum(result.actual_verdict == "ALLOW" for result in supported),
        "supported_pass_count": sum(result.passed for result in supported),
        "sanitized_pass_count": sum(result.passed for result in sanitized),
        "sanitized_allow_count": sum(result.actual_verdict == "ALLOW" for result in sanitized),
        "supported_unexpected_deny_count": sum(
            result.expected_verdict in {"ALLOW", "ASK"} and result.actual_verdict == "DENY" for result in supported
        ),
        "deny_expected_deny_count": sum(result.actual_verdict == "DENY" for result in expected_deny),
        "deny_unexpected_allow_count": sum(
            result.expected_verdict == "DENY" and result.actual_verdict == "ALLOW" for result in deny
        ),
        "unknown_fail_closed_count": sum(result.actual_verdict == "DENY" for result in unknown),
        "executor_called_on_deny": sum(result.actual_verdict == "DENY" and result.executor_called for result in results),
        "executor_called_on_ask": sum(result.actual_verdict == "ASK" and result.executor_called for result in results),
        "capability_minted_from_stripped_memory": sum(
            result.capability_minted_from_stripped_memory for result in sanitized
        ),
        "unsupported_or_unknown_surfaces": [result.case_id for result in unknown],
        "remaining_gaps": (
            "terminal background/pty/streaming",
            "non-http MCP resources/prompts/stdio command transport",
            "gateway media/reaction/thread fields",
            "provider memory remote container metadata",
            "delegate_task ACP fields",
            "cronjob lifecycle update/disable/fire",
            "full patch conflict semantics",
            "runtime dispatcher tool_request variants",
        ),
    }
    return summary


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Hermes Supported-Subset Dry-Run Report",
        "",
        "This is a dry-run over mock Hermes-like JSON events derived from observed source shapes.",
        "It is not a real Hermes integration. Hermes is not run, dependencies are not installed,",
        "third-party commands are not executed, real tools are not called, no network is used,",
        "and no shell command is executed.",
        "",
        "## Summary",
        "",
        f"- Total cases: {summary['total_cases']}",
        f"- Supported cases: {summary['supported_cases']}",
        f"- Sanitized / stripped allow cases: {summary['sanitized_cases']}",
        f"- Explicit deny cases: {summary['explicit_deny_cases']}",
        f"- Unknown cases: {summary['unknown_cases']}",
        f"- Supported ALLOW count: {summary['supported_allow_count']}",
        f"- Supported pass count: {summary['supported_pass_count']}",
        f"- Sanitized pass count: {summary['sanitized_pass_count']}",
        f"- Supported unexpected deny count: {summary['supported_unexpected_deny_count']}",
        f"- Deny expected DENY count: {summary['deny_expected_deny_count']}",
        f"- Deny unexpected allow count: {summary['deny_unexpected_allow_count']}",
        f"- Unknown fail-closed count: {summary['unknown_fail_closed_count']}",
        f"- Executor called on DENY: {summary['executor_called_on_deny']}",
        f"- Executor called on ASK: {summary['executor_called_on_ask']}",
        f"- Capability minted from stripped memory: {summary['capability_minted_from_stripped_memory']}",
        "",
        "Memory stripping ALLOW cases only mean content-only safe memory writes.",
        "They do not accept the authority claim and do not mint capabilities.",
        "",
        "## Results",
        "",
        "| Case | Category | Expected | Actual | Reason | Executor | Pass |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in payload["results"]:
        lines.append(
            f"| {result['case_id']} | {result['category']} | {result['expected_verdict']} | "
            f"{result['actual_verdict']} | {result['actual_reason']} | "
            f"{'called' if result['executor_called'] else 'not_called'} | {result['passed']} |"
        )
    lines.extend(
        [
            "",
            "## Remaining Gaps",
            "",
        ]
    )
    for gap in summary["remaining_gaps"]:
        lines.append(f"- {gap}")
    lines.extend(
        [
            "",
            "## Go / No-Go",
            "",
            "- Supported-subset dry-run can be used for mock replay evaluation.",
            "- Real Hermes integration is not claimed.",
            "- Runtime event capture is still required before a real Hermes wrapper claim.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
