#!/usr/bin/env python3
"""Hermes runtime capture prototype over JSON/JSONL events.

This prototype records and replays Hermes-like captured events only. It does
not run Hermes, install dependencies, execute third-party commands, execute
real tools, use network, send mail/messages, or run a shell.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
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
from capproof.serialization import stable_hash

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE_DIR = ROOT / "hermes_capture_prototype"
INPUT_EXAMPLES_DIR = PROTOTYPE_DIR / "input_examples"
TRACES_DIR = PROTOTYPE_DIR / "traces"
REPORTS_DIR = PROTOTYPE_DIR / "reports"
TRACE_PATH = TRACES_DIR / "capture_trace.jsonl"
SUMMARY_PATH = REPORTS_DIR / "capture_summary.json"
REPORT_PATH = REPORTS_DIR / "capture_prototype_report.md"
DEFAULT_TASK_ID = "task_1"

HOOK_ALIASES = {
    "gateway_pre_send": "gateway_messaging_pre_send",
    "delegation_pre_dispatch": "subagent_delegation_pre_dispatch",
    "scheduler_pre_register": "scheduler_cron_pre_register",
    "scheduler_pre_fire": "scheduler_cron_pre_fire",
    "skill_middleware_rewrite": "skill_plugin_middleware_rewrite",
    "posthoc_terminal_log": "observer_posthoc",
    "posthoc_message_sent_log": "observer_posthoc",
}


@dataclass(frozen=True)
class PrototypeInput:
    case_id: str
    source_path: str
    raw_event: dict[str, Any]
    expected_verdict: str | None = None
    expected_reason: str | None = None
    setup: dict[str, Any] | None = None


@dataclass(frozen=True)
class PrototypeResult:
    case_id: str
    source_path: str
    event_id: str
    hook_point: str
    capture_mode: str
    source_component: str
    tool_name: str
    raw_event_hash: str
    validation_status: str
    missing_fields: tuple[str, ...]
    authority_bearing_fields: tuple[str, ...]
    guard_verdict: str
    deny_reason: str
    executor_called: bool
    mock_event: dict[str, Any] | None
    observer_only_blocked: bool
    unsupported_fail_closed: bool
    capability_minted_from_stripped_memory: bool
    passed: bool
    timestamp: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hermes capture prototype over JSON/JSONL events.")
    parser.add_argument("--input", default=None, help="directory or JSON file containing captured events")
    parser.add_argument("--jsonl", default=None, help="JSONL file containing captured events")
    parser.add_argument("--report", action="store_true", help="print the latest report path without reprocessing")
    args = parser.parse_args()

    if args.report and not args.input and not args.jsonl:
        if not SUMMARY_PATH.exists():
            run_prototype(input_path=INPUT_EXAMPLES_DIR)
        print(f"report: {REPORT_PATH}")
        print(f"summary: {SUMMARY_PATH}")
        print(f"trace: {TRACE_PATH}")
        return 0

    payload = run_prototype(
        input_path=Path(args.input) if args.input else None,
        jsonl_path=Path(args.jsonl) if args.jsonl else None,
    )
    summary = payload["summary"]
    print(f"capture prototype events: {summary['total_events_processed']}")
    print(f"allowed: {summary['allowed']}")
    print(f"denied: {summary['denied']}")
    print(f"ask: {summary['ask']}")
    print(f"AdapterCoverageGap: {summary['adapter_coverage_gap_count']}")
    print(f"observer_only_blocked: {summary['observer_only_blocked_count']}")
    print(f"executor_called_on_deny: {summary['executor_called_on_deny']}")
    print(f"executor_called_on_ask: {summary['executor_called_on_ask']}")
    print(f"trace: {TRACE_PATH}")
    print(f"report: {REPORT_PATH}")
    return 0 if summary["failed_expectations"] == 0 else 1


def run_prototype(
    *,
    input_path: Path | None = None,
    jsonl_path: Path | None = None,
    trace_path: Path = TRACE_PATH,
    summary_path: Path = SUMMARY_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    inputs = load_inputs(input_path=input_path or INPUT_EXAMPLES_DIR, jsonl_path=jsonl_path)
    results = [process_input(item) for item in inputs]
    payload = {
        "summary": summarize(results, trace_path=trace_path),
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
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(trace_row(result), sort_keys=True) + "\n")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(payload, trace_path=trace_path), encoding="utf-8")
    return payload


def load_inputs(*, input_path: Path, jsonl_path: Path | None = None) -> list[PrototypeInput]:
    if jsonl_path is not None:
        return load_jsonl(jsonl_path)
    if input_path.is_dir():
        inputs: list[PrototypeInput] = []
        for path in sorted(input_path.rglob("*.json")):
            if path.name in {"summary.json", "capture_summary.json"}:
                continue
            inputs.extend(load_json_file(path))
        return inputs
    return load_json_file(input_path)


def load_jsonl(path: Path) -> list[PrototypeInput]:
    inputs = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        inputs.append(to_input(data, source_path=f"{path}:{index}"))
    return inputs


def load_json_file(path: Path) -> list[PrototypeInput]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [to_input(item, source_path=str(path)) for item in data]
    return [to_input(data, source_path=str(path))]


def to_input(data: dict[str, Any], *, source_path: str) -> PrototypeInput:
    raw_event = dict(data.get("hermes_runtime_event", data))
    case_id = str(data.get("case_id") or raw_event.get("event_id") or stable_hash(raw_event)[:12])
    return PrototypeInput(
        case_id=case_id,
        source_path=source_path,
        raw_event=raw_event,
        expected_verdict=data.get("expected_verdict"),
        expected_reason=data.get("expected_reason"),
        setup=dict(data.get("setup", {})),
    )


def process_input(item: PrototypeInput) -> PrototypeResult:
    workspace = Path(tempfile.mkdtemp(prefix=f"capproof_capture_proto_{item.case_id}_")) / "project"
    workspace.mkdir(parents=True, exist_ok=True)
    event = normalize_runtime_event(item.raw_event, case_id=item.case_id, workspace=workspace)
    state = MonitorState(
        capability_store=InMemoryCapabilityStore(),
        receipt_store=InMemoryReceiptStore(),
        tool_contracts=profile_tool_contract_registry(),
        canonicalizer=Canonicalizer(workspace),
    )
    seed_default_capabilities(state, event, workspace)
    apply_setup(state, expand_placeholders(item.setup or {}, workspace), task_id=str(event["task_id"]))
    runtime_state = make_runtime_state(
        state,
        task_id=str(event["task_id"]),
        agent_id=str(event.get("agent_id") or event.get("child_agent") or "hermes_mock"),
    )
    bridge = HermesCapturedEventAdapter()
    validation = bridge.validate_dict(event)
    guard_verdict = VerificationDecision.DENY.value
    deny_reason = DenyReason.ADAPTER_COVERAGE_GAP.value
    executor_called = False
    mock_event: dict[str, Any] | None = None
    if validation.valid and validation.enforcement_allowed and validation.adapter_raw_event is not None:
        middleware = CapProofMiddleware(
            AgentAdapterRegistry(
                default_profile_agent_adapters(
                    tool_contracts=state.tool_contracts,
                    canonicalizer=state.canonicalizer,
                )
            )
        )
        decision = middleware.guard(validation.adapter_raw_event, runtime_state)
        execution = GuardedExecutor(MockExecutor(workspace)).execute_if_allowed(decision)
        guard_verdict = decision.decision.value
        deny_reason = decision.deny_reason.value if decision.deny_reason else ""
        executor_called = execution.executed
        mock_event = execution.mock_event
    caps_after = state.capability_store.list_capabilities()
    minted_from_stripped_memory = (
        str(event["hook_point"]) == "memory_pre_write"
        and any(cap.root.value.startswith("MEMORY") for cap in caps_after)
    )
    observer_only_blocked = event["capture_mode"] == "observer_only" and guard_verdict == "DENY"
    unsupported_fail_closed = (
        (event["capture_mode"] == "unsupported" or bool(validation.missing_fields))
        and guard_verdict == "DENY"
        and deny_reason == DenyReason.ADAPTER_COVERAGE_GAP.value
    )
    expected_ok = True
    if item.expected_verdict:
        expected_ok = guard_verdict == item.expected_verdict
    if item.expected_reason:
        expected_ok = expected_ok and deny_reason == item.expected_reason
    return PrototypeResult(
        case_id=item.case_id,
        source_path=item.source_path,
        event_id=str(event["event_id"]),
        hook_point=str(validation.hook_point or event["hook_point"]),
        capture_mode=str(validation.capture_mode or event["capture_mode"]),
        source_component=str(event["source_component"]),
        tool_name=str(event["tool_name"]),
        raw_event_hash=str(event["raw_event_hash"]),
        validation_status="valid" if validation.valid else "invalid",
        missing_fields=tuple(validation.missing_fields),
        authority_bearing_fields=tuple(validation.authority_bearing_fields),
        guard_verdict=guard_verdict,
        deny_reason=deny_reason,
        executor_called=executor_called,
        mock_event=mock_event,
        observer_only_blocked=observer_only_blocked,
        unsupported_fail_closed=unsupported_fail_closed,
        capability_minted_from_stripped_memory=minted_from_stripped_memory,
        passed=expected_ok,
        timestamp=str(event["timestamp"]),
    )


def normalize_runtime_event(raw_event: dict[str, Any], *, case_id: str, workspace: Path) -> dict[str, Any]:
    raw = expand_placeholders(dict(raw_event), workspace)
    metadata = dict(raw.get("metadata", {})) if isinstance(raw.get("metadata", {}), dict) else {}
    hook_point = HOOK_ALIASES.get(str(raw.get("hook_point", "")), str(raw.get("hook_point", "")))
    capture_mode = str(raw.get("capture_mode", "unsupported"))
    effective_args = dict(raw.get("effective_args", {})) if isinstance(raw.get("effective_args", {}), dict) else {}
    original_args = dict(raw.get("original_args", {})) if isinstance(raw.get("original_args", {}), dict) else {}
    effective_args = normalize_effective_args(hook_point, effective_args)
    source_component = str(raw.get("source_component") or metadata.get("source_component") or infer_source_component(hook_point))
    child_agent = raw.get("child_agent")
    parent_agent = raw.get("parent_agent")
    agent_id = raw.get("agent_id") or child_agent or "hermes_mock"
    raw_hash = str(raw.get("raw_event_hash") or stable_hash(raw))
    return {
        "event_id": str(raw.get("event_id") or case_id),
        "source": str(raw.get("source", "hermes")),
        "hook_point": hook_point,
        "capture_mode": capture_mode,
        "session_id": str(raw.get("session_id", "")),
        "task_id": str(raw.get("task_id", DEFAULT_TASK_ID)),
        "agent_id": str(agent_id),
        "parent_agent": parent_agent,
        "child_agent": child_agent,
        "tool_name": str(raw.get("tool_name", "")),
        "original_args": original_args,
        "effective_args": effective_args,
        "metadata": metadata,
        "source_component": source_component,
        "timestamp": str(raw.get("timestamp", "2026-06-28T00:00:00Z")),
        "provenance_hint": str(raw.get("provenance_hint", "prototype_capture")),
        "authority_bearing_fields": list(raw.get("authority_bearing_fields") or infer_authority_fields(hook_point)),
        "raw_event_hash": raw_hash,
    }


def normalize_effective_args(hook_point: str, args: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(args)
    if hook_point == "gateway_messaging_pre_send":
        if "body" not in normalized:
            for key in ("body_ref", "message", "text"):
                if key in normalized:
                    normalized["body"] = normalized[key]
                    break
        target = normalized.get("target")
        if isinstance(target, str) and ":" in target:
            platform, recipient = target.split(":", 1)
            normalized.setdefault("platform", platform)
            normalized.setdefault("recipient", recipient)
    if hook_point in {"scheduler_cron_pre_register", "scheduler_cron_pre_fire"}:
        if "recurrence" not in normalized and "schedule" in normalized:
            normalized["recurrence"] = normalized["schedule"]
        if "action" not in normalized:
            normalized["action"] = "create"
    if hook_point == "subagent_delegation_pre_dispatch":
        if "cert_ref" not in normalized and "delegation_cert_ref" in normalized:
            normalized["cert_ref"] = normalized["delegation_cert_ref"]
    if hook_point == "mcp_pre_transport":
        transport = normalized.get("transport")
        if isinstance(transport, dict) and "endpoint" not in transport and "url" in transport:
            normalized["transport"] = {**transport, "endpoint": transport["url"]}
    return normalized


def seed_default_capabilities(state: MonitorState, event: dict[str, Any], workspace: Path) -> None:
    task_id = str(event["task_id"])
    agent_id = str(event.get("agent_id") or "hermes_mock")
    for cap in (
        {"cap_id": f"default_pytest_template_{agent_id}", "agent_id": agent_id, "task_id": task_id, "tool": "run_shell", "role": "command", "value": "pytest"},
        {"cap_id": f"default_pytest_args_{agent_id}", "agent_id": agent_id, "task_id": task_id, "tool": "run_shell", "role": "command", "value": {"target": "tests/"}},
        {"cap_id": f"default_pytest_cwd_{agent_id}", "agent_id": agent_id, "task_id": task_id, "tool": "run_shell", "role": "file_path", "value": str(workspace)},
        {"cap_id": f"default_msg_alice_{agent_id}", "agent_id": agent_id, "task_id": task_id, "tool": "send_message", "role": "recipient", "value": "telegram:alice_chat"},
        {"cap_id": f"default_mcp_url_{agent_id}", "agent_id": agent_id, "task_id": task_id, "tool": "http_post", "role": "external_endpoint", "value": "https://api.company.com/submit"},
        {"cap_id": f"default_mcp_transport_{agent_id}", "agent_id": agent_id, "task_id": task_id, "tool": "http_post", "role": "external_endpoint", "value": "https://api.company.com/mcp"},
        {"cap_id": f"default_cron_schedule_{agent_id}", "agent_id": agent_id, "task_id": task_id, "tool": "cron_send_email", "role": "command", "value": "nightly_report"},
        {"cap_id": f"default_cron_alice_{agent_id}", "agent_id": agent_id, "task_id": task_id, "tool": "cron_send_email", "role": "recipient", "value": "alice@example.com"},
    ):
        try:
            mint_case_capability(state, cap)
        except ValueError:
            pass
    if event.get("parent_agent") == "research_agent" or event.get("child_agent") == "email_agent":
        try:
            mint_delegation(
                state,
                {
                    "cap_id": "default_delegate_alice",
                    "task_id": task_id,
                    "parent_agent": "research_agent",
                    "child_agent": "email_agent",
                    "recipient": "alice@example.com",
                    "allowed_recipient": "alice@example.com",
                    "attenuation_valid": True,
                },
            )
        except ValueError:
            pass


def make_runtime_state(state: MonitorState, *, task_id: str, agent_id: str) -> AgentRuntimeState:
    runtime = ProvenanceRuntime(task_id=task_id, agent_id=agent_id, receipt_store=state.receipt_store)
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
    return AgentRuntimeState(monitor_state=state, value_refs=values, authspec_ref="hermes_capture_prototype")


def apply_setup(state: MonitorState, setup: dict[str, Any], *, task_id: str) -> None:
    for cap in setup.get("capabilities", ()):
        cap_data = dict(cap)
        cap_data.setdefault("task_id", task_id)
        mint_case_capability(state, cap_data)
    for item in setup.get("delegations", ()):
        item_data = dict(item)
        item_data.setdefault("task_id", task_id)
        mint_delegation(state, item_data)


def mint_case_capability(state: MonitorState, cap: dict[str, Any]) -> None:
    role = AuthorityRole(str(cap["role"]))
    tool = str(cap["tool"])
    raw_value = cap["value"]
    value = raw_value if cap.get("already_canonical") else canonical_value(state, role, raw_value)
    mint_capability(
        state.capability_store,
        Capability(
            cap_id=str(cap["cap_id"]),
            issuer="hermes_capture_prototype",
            root=CapabilityRoot(str(cap.get("root", "USER"))),
            agent_id=str(cap.get("agent_id", "hermes_mock")),
            task_id=str(cap.get("task_id", DEFAULT_TASK_ID)),
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
    task_id = str(item.get("task_id", DEFAULT_TASK_ID))
    recipient = canonical_value(state, AuthorityRole.RECIPIENT, item["recipient"])
    mint_case_capability(
        state,
        {
            "cap_id": cap_id,
            "agent_id": item.get("child_agent", "email_agent"),
            "task_id": task_id,
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
            task_id=task_id,
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


def summarize(results: list[PrototypeResult], *, trace_path: Path) -> dict[str, Any]:
    observer_only = [result for result in results if result.capture_mode == "observer_only"]
    pre_execution = [result for result in results if result.capture_mode == "pre_execution_gate"]
    unsupported = [
        result
        for result in results
        if result.capture_mode == "unsupported" or result.missing_fields or result.unsupported_fail_closed
    ]
    missing_fields = sorted({field for result in results for field in result.missing_fields})
    return {
        "total_events_processed": len(results),
        "pre_execution_gate": len(pre_execution),
        "valid_pre_execution_gate_events": sum(
            result.capture_mode == "pre_execution_gate" and result.validation_status == "valid"
            for result in results
        ),
        "observer_only_events": len(observer_only),
        "unsupported_missing_field_events": len(unsupported),
        "allowed": sum(result.guard_verdict == "ALLOW" for result in results),
        "denied": sum(result.guard_verdict == "DENY" for result in results),
        "ask": sum(result.guard_verdict == "ASK" for result in results),
        "adapter_coverage_gap_count": sum(result.deny_reason == "AdapterCoverageGap" for result in results),
        "observer_only_blocked_count": sum(result.observer_only_blocked for result in results),
        "unsupported_fail_closed_count": sum(result.unsupported_fail_closed for result in results),
        "executor_called_on_deny": sum(
            result.guard_verdict == "DENY" and result.executor_called for result in results
        ),
        "executor_called_on_ask": sum(
            result.guard_verdict == "ASK" and result.executor_called for result in results
        ),
        "failed_expectations": sum(not result.passed for result in results),
        "remaining_missing_hook_fields": missing_fields,
        "trace_path": str(trace_path),
        "ready_for_real_capture_only_instrumentation": True,
        "ready_for_enforcement_wrapper": False,
    }


def trace_row(result: PrototypeResult) -> dict[str, Any]:
    return {
        "trace_id": f"trace:{result.event_id}",
        "event_id": result.event_id,
        "hook_point": result.hook_point,
        "capture_mode": result.capture_mode,
        "source_component": result.source_component,
        "tool_name": result.tool_name,
        "raw_event_hash": result.raw_event_hash,
        "validation_status": result.validation_status,
        "missing_fields": list(result.missing_fields),
        "authority_bearing_fields": list(result.authority_bearing_fields),
        "guard_verdict": result.guard_verdict,
        "deny_reason": result.deny_reason,
        "executor_called": result.executor_called,
        "timestamp": result.timestamp,
    }


def render_report(payload: dict[str, Any], *, trace_path: Path) -> str:
    summary = payload["summary"]
    lines = [
        "# Hermes Capture Prototype Report",
        "",
        "This stage is not a real Hermes integration. Hermes is not run, dependencies are not installed,",
        "third-party project commands are not executed, real tools are not called, no network is used,",
        "and no shell command is executed. The prototype processes JSON / JSONL captured-event examples only.",
        "",
        "`pre_execution_gate` events can enter CapProof guard dry-run. `observer_only` events are recorded",
        "only and cannot produce enforcement ALLOW. Unsupported or missing-field events fail closed.",
        "DENY and ASK decisions do not call `MockExecutor`; ALLOW decisions use only `MockExecutor`.",
        "",
        "Future real integration must first verify that these hook points are available in Hermes runtime.",
        "",
        "## Summary",
        "",
        f"- Total events processed: {summary['total_events_processed']}",
        f"- Valid pre_execution_gate events: {summary['valid_pre_execution_gate_events']}",
        f"- Observer-only events: {summary['observer_only_events']}",
        f"- Unsupported / missing-field events: {summary['unsupported_missing_field_events']}",
        f"- Allowed: {summary['allowed']}",
        f"- Denied: {summary['denied']}",
        f"- Ask: {summary['ask']}",
        f"- AdapterCoverageGap count: {summary['adapter_coverage_gap_count']}",
        f"- Observer-only blocked count: {summary['observer_only_blocked_count']}",
        f"- Executor called on deny: {summary['executor_called_on_deny']}",
        f"- Executor called on ask: {summary['executor_called_on_ask']}",
        f"- Trace path: {trace_path}",
        f"- Ready for real capture-only instrumentation: {summary['ready_for_real_capture_only_instrumentation']}",
        f"- Ready for enforcement wrapper: {summary['ready_for_enforcement_wrapper']}",
        "",
        "## Hook Readiness",
        "",
        "| Hook | Required fields | Prototype support | Runtime verification needed |",
        "| --- | --- | --- | --- |",
        "| tool dispatcher | tool_name, original_args, effective_args, source_component | supported for synthetic send_message | yes |",
        "| terminal backend | command, cwd, env, stdin | supported for allowlisted templates; raw shell denied | yes |",
        "| MCP | server, tool_name, arguments, transport endpoint | supported for synthetic http_post | yes |",
        "| memory | content, origin, persistent | supported with authority stripping | yes |",
        "| gateway | platform/target, recipient/target, body/body_ref/message | supported for synthetic send_message | yes |",
        "| delegation | parent_agent, child_agent, goal/scope, cert ref or explicit missing cert | supported for synthetic delegate_task | yes |",
        "| scheduler | schedule_id plus action target | supported for synthetic cron registration | yes |",
        "| middleware rewrite | original_args, effective_args, source_component | supported; effective_args authorize | yes |",
        "",
        "## Results",
        "",
        "| Case | Hook | Mode | Verdict | Reason | Missing fields | Executor |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in payload["results"]:
        lines.append(
            f"| {result['case_id']} | {result['hook_point']} | {result['capture_mode']} | "
            f"{result['guard_verdict']} | {result['deny_reason']} | "
            f"{', '.join(result['missing_fields'])} | "
            f"{'called' if result['executor_called'] else 'not_called'} |"
        )
    lines.extend(
        [
            "",
            "## Remaining Missing Hook Fields",
            "",
        ]
    )
    if summary["remaining_missing_hook_fields"]:
        for field in summary["remaining_missing_hook_fields"]:
            lines.append(f"- {field}")
    else:
        lines.append("- None in the processed examples.")
    lines.extend(
        [
            "",
            "## Go / No-Go",
            "",
            "- Capture-only instrumentation prototype: go.",
            "- Enforcement wrapper: no-go until real Hermes runtime hook availability and payload samples are verified.",
            "- Real Hermes integration claim: no.",
        ]
    )
    return "\n".join(lines) + "\n"


def infer_source_component(hook_point: str) -> str:
    return {
        "tool_dispatcher_pre_call": "tool_dispatcher",
        "terminal_backend_pre_exec": "terminal_backend",
        "mcp_pre_transport": "mcp",
        "memory_pre_write": "memory",
        "gateway_messaging_pre_send": "gateway",
        "subagent_delegation_pre_dispatch": "subagent",
        "scheduler_cron_pre_register": "scheduler",
        "scheduler_cron_pre_fire": "scheduler",
        "skill_plugin_middleware_rewrite": "skill_middleware",
        "observer_posthoc": "observer",
    }.get(hook_point, "unknown")


def infer_authority_fields(hook_point: str) -> tuple[str, ...]:
    return {
        "tool_dispatcher_pre_call": ("tool_name", "effective_args"),
        "terminal_backend_pre_exec": ("command", "cwd", "env", "stdin"),
        "mcp_pre_transport": ("server", "tool_name", "arguments.url", "transport.endpoint", "headers"),
        "memory_pre_write": ("content", "origin", "persistent"),
        "gateway_messaging_pre_send": ("platform", "recipient", "body"),
        "subagent_delegation_pre_dispatch": ("parent_agent", "child_agent", "goal", "delegated_scope", "cert_ref"),
        "scheduler_cron_pre_register": ("schedule_id", "recipient", "target", "command", "workdir"),
        "scheduler_cron_pre_fire": ("schedule_id", "recipient", "target", "command", "workdir"),
        "skill_plugin_middleware_rewrite": ("original_args", "effective_args"),
        "observer_posthoc": ("observed_args",),
    }.get(hook_point, ())


def expand_placeholders(value: Any, workspace: Path) -> Any:
    if isinstance(value, str):
        return value.replace("$WORKSPACE", str(workspace)).replace("/workspace/project", str(workspace))
    if isinstance(value, list):
        return [expand_placeholders(item, workspace) for item in value]
    if isinstance(value, dict):
        return {str(key): expand_placeholders(item, workspace) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())
