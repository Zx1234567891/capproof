#!/usr/bin/env python3
"""Validate synthetic Hermes runtime capture events.

The runner reads replay JSON only. It does not import or run Hermes, install
dependencies, execute third-party commands, execute real tools, use network, or
run shell commands.
"""

from __future__ import annotations

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
    HermesCapturedEventAdapter,
    HermesCaptureMode,
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

ROOT = Path(__file__).resolve().parent
EXAMPLES_DIR = ROOT / "hermes_capture_examples"
REPORT_PATH = ROOT / "hermes_capture_validation_report.md"
SUMMARY_PATH = ROOT / "hermes_capture_examples" / "summary.json"
TASK_ID = "task_hermes_capture_validation"


@dataclass(frozen=True)
class CaptureCase:
    case_id: str
    category: str
    hermes_runtime_event: dict[str, Any]
    expected_verdict: str
    expected_reason: str
    expected_executor_behavior: str
    notes: str
    setup: dict[str, Any]


@dataclass(frozen=True)
class CaptureCaseResult:
    case_id: str
    category: str
    hook_point: str
    capture_mode: str
    expected_verdict: str
    expected_reason: str
    actual_verdict: str
    actual_reason: str
    validation_valid: bool
    missing_fields: tuple[str, ...]
    observer_only_blocked: bool
    unsupported_fail_closed: bool
    executor_called: bool
    expected_executor_behavior: str
    mock_event: dict[str, Any] | None
    adapter_raw_event: dict[str, Any] | None
    capability_minted_from_stripped_memory: bool
    passed: bool
    notes: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate synthetic Hermes runtime capture events.")
    parser.add_argument("--json", action="store_true", help="print JSON summary to stdout")
    args = parser.parse_args()
    payload = run_validation()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        summary = payload["summary"]
        print(f"hermes capture events: {summary['total_events']}")
        print(f"passed: {summary['passed_events']}")
        print(f"failed: {summary['failed_events']}")
        print(f"allowed: {summary['allowed']}")
        print(f"denied: {summary['denied']}")
        print(f"ask: {summary['ask']}")
        print(f"AdapterCoverageGap: {summary['adapter_coverage_gap_count']}")
        print(f"observer_only_blocked_from_enforcement: {summary['observer_only_blocked_from_enforcement_count']}")
        print(f"executor_called_on_denied: {summary['executor_called_on_denied']}")
        print(f"report: {REPORT_PATH}")
    return 0 if payload["summary"]["failed_events"] == 0 else 1


def run_validation(*, examples_dir: Path = EXAMPLES_DIR, summary_path: Path = SUMMARY_PATH) -> dict[str, Any]:
    cases = load_cases(examples_dir)
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
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
    return payload


def load_cases(examples_dir: Path) -> list[CaptureCase]:
    cases: list[CaptureCase] = []
    for category in ("supported_pre_execution", "deny_pre_execution", "observer_only", "unsupported"):
        root = examples_dir / category
        for path in sorted(root.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            cases.append(
                CaptureCase(
                    case_id=str(data["case_id"]),
                    category=str(data.get("category", category)),
                    hermes_runtime_event=dict(data["hermes_runtime_event"]),
                    expected_verdict=str(data["expected_verdict"]),
                    expected_reason=str(data.get("expected_reason", "")),
                    expected_executor_behavior=str(data["expected_executor_behavior"]),
                    notes=str(data.get("notes", "")),
                    setup=dict(data.get("setup", {})),
                )
            )
    return cases


def run_case(case: CaptureCase) -> CaptureCaseResult:
    workspace = Path(tempfile.mkdtemp(prefix=f"capproof_capture_{case.case_id}_")) / "project"
    workspace.mkdir(parents=True, exist_ok=True)
    state = MonitorState(
        capability_store=InMemoryCapabilityStore(),
        receipt_store=InMemoryReceiptStore(),
        tool_contracts=profile_tool_contract_registry(),
        canonicalizer=Canonicalizer(workspace),
    )
    event = expand_placeholders(case.hermes_runtime_event, workspace)
    setup = expand_placeholders(case.setup, workspace)
    apply_setup(state, setup)
    runtime_state = make_runtime_state(state)
    bridge = HermesCapturedEventAdapter()
    validation = bridge.validate_dict(event)
    actual_verdict = VerificationDecision.DENY.value
    actual_reason = DenyReason.ADAPTER_COVERAGE_GAP.value
    executor_called = False
    mock_event: dict[str, Any] | None = None
    adapter_raw_event = validation.adapter_raw_event
    if validation.valid and validation.enforcement_allowed and adapter_raw_event is not None:
        middleware = CapProofMiddleware(
            AgentAdapterRegistry(
                default_profile_agent_adapters(
                    tool_contracts=state.tool_contracts,
                    canonicalizer=state.canonicalizer,
                )
            )
        )
        decision = middleware.guard(adapter_raw_event, runtime_state)
        execution = GuardedExecutor(MockExecutor(workspace)).execute_if_allowed(decision)
        actual_verdict = decision.decision.value
        actual_reason = decision.deny_reason.value if decision.deny_reason else ""
        executor_called = execution.executed
        mock_event = execution.mock_event

    caps_after = runtime_state.monitor_state.capability_store.list_capabilities()
    minted_from_stripped_memory = (
        case.case_id == "memory_authority_pre_write"
        and any(cap.root.value.startswith("MEMORY") for cap in caps_after)
    )
    observer_only_blocked = (
        validation.capture_mode == HermesCaptureMode.OBSERVER_ONLY.value
        and actual_verdict == VerificationDecision.DENY.value
    )
    unsupported_fail_closed = (
        case.category == "unsupported"
        and actual_verdict == VerificationDecision.DENY.value
        and actual_reason == DenyReason.ADAPTER_COVERAGE_GAP.value
    )
    memory_stripped_ok = True
    if case.case_id == "memory_authority_pre_write":
        args = mock_event.get("args", {}) if mock_event else {}
        memory_stripped_ok = (
            mock_event is not None
            and mock_event.get("mock_tool") == "memory_write"
            and args.get("authority_claims") == {}
            and args.get("stripped_authority") is True
            and not minted_from_stripped_memory
        )
    passed = (
        actual_verdict == case.expected_verdict
        and (case.expected_reason == "" or actual_reason == case.expected_reason)
        and executor_called == (case.expected_executor_behavior == "called")
        and memory_stripped_ok
    )
    return CaptureCaseResult(
        case_id=case.case_id,
        category=case.category,
        hook_point=validation.hook_point,
        capture_mode=validation.capture_mode,
        expected_verdict=case.expected_verdict,
        expected_reason=case.expected_reason,
        actual_verdict=actual_verdict,
        actual_reason=actual_reason,
        validation_valid=validation.valid,
        missing_fields=tuple(validation.missing_fields),
        observer_only_blocked=observer_only_blocked,
        unsupported_fail_closed=unsupported_fail_closed,
        executor_called=executor_called,
        expected_executor_behavior=case.expected_executor_behavior,
        mock_event=mock_event,
        adapter_raw_event=adapter_raw_event,
        capability_minted_from_stripped_memory=minted_from_stripped_memory,
        passed=passed,
        notes=case.notes,
    )


def make_runtime_state(state: MonitorState) -> AgentRuntimeState:
    runtime = ProvenanceRuntime(task_id=TASK_ID, agent_id="hermes_mock", receipt_store=state.receipt_store)
    values = {}
    for value_id, tool, data_class, content in (
        ("val_summary", "summarize", "summary(report)", "summary"),
        ("val_report", "read_file", "report", "report"),
        ("val_doc", "read_file", "doc", "doc"),
        ("val_patch", "read_file", "patch", "patch"),
    ):
        value, _receipt = runtime.record_tool_out(
            tool=tool,
            output_id=value_id,
            data_class=data_class,
            content=content,
            provenance_root="USER",
        )
        values[value.value_id] = value
    return AgentRuntimeState(monitor_state=state, value_refs=values, authspec_ref="hermes_capture_validation")


def apply_setup(state: MonitorState, setup: dict[str, Any]) -> None:
    for cap in setup.get("capabilities", ()):
        mint_case_capability(state, dict(cap))
    for item in setup.get("delegations", ()):
        mint_delegation(state, dict(item))


def mint_case_capability(state: MonitorState, cap: dict[str, Any]) -> None:
    role = AuthorityRole(str(cap["role"]))
    tool = str(cap["tool"])
    raw_value = cap["value"]
    value = raw_value if cap.get("already_canonical") else canonical_value(state, role, raw_value)
    mint_capability(
        state.capability_store,
        Capability(
            cap_id=str(cap["cap_id"]),
            issuer="hermes_capture_validation",
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
                    "recipient": canonical_value(
                        state,
                        AuthorityRole.RECIPIENT,
                        item.get("allowed_recipient", item["recipient"]),
                    ),
                    "attenuation_valid": bool(item.get("attenuation_valid", True)),
                },
            },
            issued_at="2026-06-28T00:00:00Z",
        )
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
        "write_file": ActionKind.WRITE,
        "run_shell": ActionKind.EXEC,
        "http_post": ActionKind.NET,
        "cron_send_email": ActionKind.SEND,
        "cron_send_message": ActionKind.SEND,
    }.get(tool, ActionKind.TRANSFORM)


def expand_placeholders(value: Any, workspace: Path) -> Any:
    if isinstance(value, str):
        return value.replace("$WORKSPACE", str(workspace))
    if isinstance(value, list):
        return [expand_placeholders(item, workspace) for item in value]
    if isinstance(value, dict):
        return {str(key): expand_placeholders(item, workspace) for key, item in value.items()}
    return value


def summarize(results: list[CaptureCaseResult]) -> dict[str, Any]:
    pre_execution = [result for result in results if result.capture_mode == "pre_execution_gate"]
    observer = [result for result in results if result.capture_mode == "observer_only"]
    unsupported = [result for result in results if result.category == "unsupported"]
    return {
        "total_events": len(results),
        "pre_execution_gate_events": len(pre_execution),
        "observer_only_events": len(observer),
        "unsupported_events": len(unsupported),
        "passed_events": sum(result.passed for result in results),
        "failed_events": sum(not result.passed for result in results),
        "allowed": sum(result.actual_verdict == "ALLOW" for result in results),
        "denied": sum(result.actual_verdict == "DENY" for result in results),
        "ask": sum(result.actual_verdict == "ASK" for result in results),
        "adapter_coverage_gap_count": sum(result.actual_reason == "AdapterCoverageGap" for result in results),
        "observer_only_blocked_from_enforcement_count": sum(result.observer_only_blocked for result in results),
        "unsupported_fail_closed_count": sum(result.unsupported_fail_closed for result in results),
        "executor_called_on_denied": sum(
            result.actual_verdict == "DENY" and result.executor_called for result in results
        ),
        "executor_called_on_ask": sum(
            result.actual_verdict == "ASK" and result.executor_called for result in results
        ),
        "capability_minted_from_stripped_memory": sum(
            result.capability_minted_from_stripped_memory for result in results
        ),
    }


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Hermes Capture Validation Report",
        "",
        "This validates synthetic captured Hermes runtime events only. It is not a real Hermes integration.",
        "Hermes is not run, dependencies are not installed, third-party commands are not executed,",
        "real tools are not called, no network is used, and no shell command is executed.",
        "",
        "Only `pre_execution_gate` events can support future enforcement claims.",
        "`observer_only` events are blocked from enforcement allow. Unsupported or incomplete events fail closed.",
        "",
        "## Summary",
        "",
        f"- Total synthetic events: {summary['total_events']}",
        f"- Pre-execution gate events: {summary['pre_execution_gate_events']}",
        f"- Observer-only events: {summary['observer_only_events']}",
        f"- Unsupported events: {summary['unsupported_events']}",
        f"- Allowed: {summary['allowed']}",
        f"- Denied: {summary['denied']}",
        f"- Ask: {summary['ask']}",
        f"- AdapterCoverageGap count: {summary['adapter_coverage_gap_count']}",
        f"- Observer-only blocked from enforcement: {summary['observer_only_blocked_from_enforcement_count']}",
        f"- Executor called on denied: {summary['executor_called_on_denied']}",
        f"- Executor called on ask: {summary['executor_called_on_ask']}",
        f"- Capability minted from stripped memory: {summary['capability_minted_from_stripped_memory']}",
        "",
        "## Results",
        "",
        "| Case | Category | Hook | Mode | Expected | Actual | Reason | Missing fields | Executor | Pass |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in payload["results"]:
        lines.append(
            f"| {result['case_id']} | {result['category']} | {result['hook_point']} | "
            f"{result['capture_mode']} | {result['expected_verdict']} | {result['actual_verdict']} | "
            f"{result['actual_reason']} | {', '.join(result['missing_fields'])} | "
            f"{'called' if result['executor_called'] else 'not_called'} | {result['passed']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Passing validation means the capture schema and replay bridge work for these synthetic events.",
            "- It does not mean real Hermes hooks exist or have the same runtime payloads.",
            "- Runtime event samples are still required before a real Hermes wrapper claim.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
