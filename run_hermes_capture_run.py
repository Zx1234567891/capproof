#!/usr/bin/env python3
"""Stage 28 Hermes capture-run / trace-import validation runner.

This runner is a capture-run local harness. It does not run Hermes by default,
does not install dependencies, does not execute third-party commands, does not
execute real tools, and is not an enforcement wrapper.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Mapping

from run_hermes_capture_prototype import run_prototype
import run_hermes_runtime_capture_experiment as runtime_experiment


ROOT = Path(__file__).resolve().parent
CAPTURE_RUN_DIR = ROOT / "hermes_capture_run"
TRACES_DIR = CAPTURE_RUN_DIR / "traces"
REPORTS_DIR = CAPTURE_RUN_DIR / "reports"
IMPORTED_TRACES_DIR = CAPTURE_RUN_DIR / "imported_traces"
MANUAL_TRACES_DIR = IMPORTED_TRACES_DIR / "manual"
SAFETY_LOGS_DIR = CAPTURE_RUN_DIR / "safety_logs"
DEFAULT_TRACE_PATH = TRACES_DIR / "captured_events.jsonl"
SUMMARY_PATH = REPORTS_DIR / "capture_run_summary.json"
CAPTURE_RUN_REPORT_PATH = REPORTS_DIR / "capture_run_report.md"
TRACE_VALIDATION_REPORT_PATH = REPORTS_DIR / "trace_validation_report.md"
HOOK_READINESS_REPORT_PATH = REPORTS_DIR / "hook_readiness_report.md"
MANUAL_TRACE_REPORT_PATH = REPORTS_DIR / "manual_trace_import_report.md"
TRACE_REPLAY_TRACE_PATH = TRACES_DIR / "replay_trace.jsonl"
TRACE_REPLAY_SUMMARY_PATH = REPORTS_DIR / "trace_replay_summary.json"
SAFETY_LOG_PATH = SAFETY_LOGS_DIR / "capture_run_safety_log.json"

STAGE28_REQUIRED_FIELDS = (
    "event_id",
    "source",
    "hook_point",
    "capture_mode",
    "session_id",
    "task_id",
    "agent_id",
    "tool_name",
    "original_args",
    "effective_args",
    "metadata",
    "source_component",
    "authority_bearing_fields",
    "raw_event_hash",
    "timestamp",
    "pre_execution_observed",
    "side_effect_already_happened",
)

HOOKS = {
    "tool_dispatcher": ("tool_dispatcher_pre_call",),
    "terminal": ("terminal_backend_pre_exec",),
    "MCP": ("mcp_pre_transport",),
    "memory": ("memory_pre_write",),
    "gateway": ("gateway_messaging_pre_send", "gateway_pre_send"),
    "delegation": ("subagent_delegation_pre_dispatch", "delegation_pre_dispatch"),
    "scheduler": ("scheduler_cron_pre_register", "scheduler_cron_pre_fire", "scheduler_pre_register"),
    "middleware_rewrite": ("skill_plugin_middleware_rewrite", "skill_middleware_rewrite"),
}


@dataclass(frozen=True)
class Stage28EventCheck:
    event_id: str
    hook_point: str
    capture_mode: str
    missing_schema_fields: tuple[str, ...] = ()
    source_valid: bool = True
    pre_execution_observed: bool | None = None
    side_effect_already_happened: bool | None = None

    @property
    def fail_closed(self) -> bool:
        return (
            bool(self.missing_schema_fields)
            or not self.source_valid
            or self.side_effect_already_happened is True
            or (self.capture_mode == "pre_execution_gate" and self.pre_execution_observed is not True)
        )


@dataclass(frozen=True)
class Stage28TraceValidation:
    trace_path: str
    trace_source: str
    total_events: int = 0
    schema_valid_events: int = 0
    pre_execution_gate_events: int = 0
    observer_only_events: int = 0
    unsupported_events: int = 0
    missing_field_events: int = 0
    allowed: int = 0
    denied: int = 0
    ask: int = 0
    adapter_coverage_gap: int = 0
    observer_only_blocked: int = 0
    executor_called_on_deny: int = 0
    executor_called_on_ask: int = 0
    side_effect_blocked: int = 0
    hook_readiness: dict[str, dict[str, Any]] = field(default_factory=dict)
    event_checks: tuple[Stage28EventCheck, ...] = ()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage 28 Hermes capture-run / trace-import gate.")
    parser.add_argument("--preflight", action="store_true", help="run no-run preflight")
    parser.add_argument("--import-trace", default=None, help="validate an existing Hermes runtime JSONL trace")
    parser.add_argument("--capture-run", action="store_true", help="attempt explicitly authorized capture-only run")
    parser.add_argument("--report", action="store_true", help="print or regenerate reports")
    args = parser.parse_args()

    if args.import_trace:
        payload = run_stage28(import_trace_path=Path(args.import_trace))
    elif args.capture_run:
        payload = run_stage28(capture_run_requested=True)
    else:
        payload = run_stage28(preflight_only=True)

    if args.report and not args.import_trace and not args.capture_run and not args.preflight:
        if not SUMMARY_PATH.exists():
            payload = run_stage28(preflight_only=True)
        print(f"capture_run_report: {CAPTURE_RUN_REPORT_PATH}")
        print(f"capture_run_summary: {SUMMARY_PATH}")
        print(f"trace_validation_report: {TRACE_VALIDATION_REPORT_PATH}")
        print(f"hook_readiness_report: {HOOK_READINESS_REPORT_PATH}")
        print(f"manual_trace_import_report: {MANUAL_TRACE_REPORT_PATH}")
        return 0

    summary = payload["summary"]
    capture = summary["capture_run"]
    trace = summary["trace_validation"]
    print(f"trace_source: {summary['trace_source']}")
    print(f"run_attempted: {capture['run_attempted']}")
    print(f"run_allowed: {capture['run_allowed']}")
    print(f"capture_run_state: {capture['state']}")
    print(f"trace_events: {trace['total_events']}")
    print(f"schema_valid_events: {trace['schema_valid_events']}")
    print(f"allowed: {trace['allowed']}")
    print(f"denied: {trace['denied']}")
    print(f"ask: {trace['ask']}")
    print(f"AdapterCoverageGap: {trace['AdapterCoverageGap']}")
    print(f"report: {CAPTURE_RUN_REPORT_PATH}")
    return 0


def run_stage28(
    *,
    preflight_only: bool = False,
    import_trace_path: Path | None = None,
    capture_run_requested: bool = False,
    env: Mapping[str, str] | None = None,
    command_runner: Callable[..., Any] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    _ensure_dirs(root)
    env_map = dict(os.environ if env is None else env)

    if import_trace_path is not None:
        imported_trace = _copy_imported_trace(import_trace_path, root=root)
        runtime_payload = runtime_experiment.run_experiment(preflight_only=True, env=env_map, root=root)
        trace_validation = validate_stage28_trace(imported_trace, trace_source="imported trace", root=root)
    elif capture_run_requested:
        runtime_payload = runtime_experiment.run_experiment(
            capture_run_requested=True,
            env=env_map,
            command_runner=command_runner,
            root=root,
        )
        capture = runtime_payload["summary"]["capture_run"]
        trace_path = Path(str(capture["trace_path"]))
        if capture["state"] == "completed" and trace_path.exists():
            trace_validation = validate_stage28_trace(trace_path, trace_source="capture-run generated trace", root=root)
        else:
            trace_validation = empty_trace_validation(
                trace_path=trace_path,
                trace_source="no-run" if not capture["run_attempted"] else "capture-run generated trace",
                root=root,
            )
    else:
        runtime_payload = runtime_experiment.run_experiment(preflight_only=True, env=env_map, root=root)
        trace_path = _path(root, DEFAULT_TRACE_PATH)
        trace_validation = empty_trace_validation(trace_path=trace_path, trace_source="no-run", root=root)

    payload = build_stage28_payload(runtime_payload, trace_validation)
    write_stage28_outputs(payload, root=root)
    return payload


def validate_stage28_trace(trace_path: Path, *, trace_source: str, root: Path = ROOT) -> Stage28TraceValidation:
    rows = _read_trace_rows(trace_path)
    checks = tuple(_check_event(row) for row in rows)
    replay_rows = [_to_replay_row(row, check) for row, check in zip(rows, checks)]
    replay_input = _write_temp_jsonl(replay_rows)
    replay_payload = run_prototype(
        jsonl_path=replay_input,
        trace_path=_path(root, TRACE_REPLAY_TRACE_PATH),
        summary_path=_path(root, TRACE_REPLAY_SUMMARY_PATH),
        report_path=_path(root, TRACE_VALIDATION_REPORT_PATH),
    )
    replay_summary = replay_payload["summary"]
    replay_results = replay_payload["results"]
    hook_readiness = build_hook_readiness(rows, checks, replay_results)
    stage_missing_events = sum(bool(check.missing_schema_fields) for check in checks)
    hook_missing_events = sum(bool(result.get("missing_fields")) for result in replay_results)
    side_effect_blocked = sum(check.side_effect_already_happened is True for check in checks)
    return Stage28TraceValidation(
        trace_path=str(trace_path),
        trace_source=trace_source,
        total_events=len(rows),
        schema_valid_events=sum(_schema_valid(check) for check in checks),
        pre_execution_gate_events=sum(check.capture_mode == "pre_execution_gate" for check in checks),
        observer_only_events=sum(check.capture_mode == "observer_only" for check in checks),
        unsupported_events=sum(check.capture_mode == "unsupported" or check.fail_closed for check in checks),
        missing_field_events=max(stage_missing_events, hook_missing_events),
        allowed=replay_summary["allowed"],
        denied=replay_summary["denied"],
        ask=replay_summary["ask"],
        adapter_coverage_gap=replay_summary["adapter_coverage_gap_count"],
        observer_only_blocked=replay_summary["observer_only_blocked_count"],
        executor_called_on_deny=replay_summary["executor_called_on_deny"],
        executor_called_on_ask=replay_summary["executor_called_on_ask"],
        side_effect_blocked=side_effect_blocked,
        hook_readiness=hook_readiness,
        event_checks=checks,
    )


def empty_trace_validation(*, trace_path: Path, trace_source: str, root: Path = ROOT) -> Stage28TraceValidation:
    return Stage28TraceValidation(
        trace_path=str(trace_path),
        trace_source=trace_source,
        hook_readiness=default_hook_readiness(),
    )


def build_stage28_payload(runtime_payload: dict[str, Any], trace_validation: Stage28TraceValidation) -> dict[str, Any]:
    runtime_summary = runtime_payload["summary"]
    runtime_capture = runtime_summary["capture_run"]
    run_allowed = bool(runtime_capture["run_attempted"])
    state = "DENY_CAPTURE_RUN" if runtime_capture["state"] == "not_run" else runtime_capture["state"]
    denial_reason = (
        runtime_summary["preflight"]["reason"]
        if runtime_capture["state"] == "not_run"
        else runtime_capture["reason"]
    )
    summary = {
        "trace_source": trace_validation.trace_source,
        "capture_run": {
            "run_attempted": runtime_capture["run_attempted"],
            "run_allowed": run_allowed,
            "state": state,
            "denial_reason": "" if run_allowed else denial_reason,
            "command_hash": runtime_capture["command_hash"] or "n/a",
            "timeout_seconds": runtime_capture["timeout_seconds"],
            "trace_path": trace_validation.trace_path,
            "events_captured": runtime_capture["events_captured"],
        },
        "safety_status": {
            "no_real_email": True,
            "no_real_network": True,
            "no_real_shell_high_risk_execution": True,
            "no_real_mcp_external_server": True,
            "no_dependency_install": True,
            "no_third_party_project_command": not runtime_capture["run_attempted"],
            "no_real_tool_execution": True,
            "no_secrets_used": True,
            "no_hermes_source_modification": True,
            "not_enforcement_wrapper": True,
        },
        "trace_validation": {
            "total_events": trace_validation.total_events,
            "schema_valid_events": trace_validation.schema_valid_events,
            "pre_execution_gate_events": trace_validation.pre_execution_gate_events,
            "observer_only_events": trace_validation.observer_only_events,
            "unsupported_events": trace_validation.unsupported_events,
            "missing_field_events": trace_validation.missing_field_events,
            "allowed": trace_validation.allowed,
            "denied": trace_validation.denied,
            "ask": trace_validation.ask,
            "AdapterCoverageGap": trace_validation.adapter_coverage_gap,
            "observer_only_blocked": trace_validation.observer_only_blocked,
            "executor_called_on_deny": trace_validation.executor_called_on_deny,
            "executor_called_on_ask": trace_validation.executor_called_on_ask,
            "side_effect_blocked": trace_validation.side_effect_blocked,
        },
        "hook_readiness": trace_validation.hook_readiness,
        "go_no_go": {
            "enforcement_wrapper": "no-go",
            "real_hermes_integration": False,
            "real_hermes_integration_claim": "no",
            "real_capture_trace_collected": (
                trace_validation.trace_source in {"imported trace", "capture-run generated trace"}
                and trace_validation.total_events > 0
                and trace_validation.schema_valid_events > 0
            ),
            "more_runtime_samples_needed": True,
            "blocking_hook_points": [
                hook for hook, data in trace_validation.hook_readiness.items()
                if data.get("enforcement_ready") != "yes"
            ],
        },
    }
    return {
        "summary": summary,
        "runtime_summary": runtime_summary,
        "event_checks": [
            {**asdict(check), "fail_closed": check.fail_closed}
            for check in trace_validation.event_checks
        ],
    }


def write_stage28_outputs(payload: dict[str, Any], *, root: Path = ROOT) -> None:
    _ensure_dirs(root)
    _path(root, SUMMARY_PATH).write_text(json.dumps(payload["summary"], indent=2, sort_keys=True), encoding="utf-8")
    _path(root, CAPTURE_RUN_REPORT_PATH).write_text(render_capture_run_report(payload), encoding="utf-8")
    _path(root, HOOK_READINESS_REPORT_PATH).write_text(render_hook_readiness_report(payload), encoding="utf-8")
    if payload["summary"]["trace_validation"]["total_events"] == 0:
        _path(root, TRACE_VALIDATION_REPORT_PATH).write_text(render_trace_validation_report(payload), encoding="utf-8")
    else:
        _path(root, TRACE_VALIDATION_REPORT_PATH).write_text(render_trace_validation_report(payload), encoding="utf-8")
    _path(root, SAFETY_LOG_PATH).write_text(
        json.dumps(
            {
                "capture_run": payload["summary"]["capture_run"],
                "safety_status": payload["summary"]["safety_status"],
                "go_no_go": payload["summary"]["go_no_go"],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    write_manual_trace_import_report_if_available(root=root)


def write_manual_trace_import_report_if_available(*, root: Path = ROOT) -> None:
    manual_dir = _path(root, MANUAL_TRACES_DIR)
    if not manual_dir.exists():
        return
    trace_paths = sorted(manual_dir.glob("*.jsonl"))
    if not trace_paths:
        return
    validations = []
    for trace_path in trace_paths:
        with tempfile.TemporaryDirectory(prefix="capproof_manual_trace_report_") as temp_root:
            validations.append(
                validate_stage28_trace(
                    trace_path,
                    trace_source=f"manual trace: {trace_path.name}",
                    root=Path(temp_root),
                )
            )
    report_path = _path(root, MANUAL_TRACE_REPORT_PATH)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_manual_trace_import_report(validations),
        encoding="utf-8",
    )


def render_manual_trace_import_report(validations: list[Stage28TraceValidation]) -> str:
    totals = aggregate_trace_validations(validations)
    readiness = aggregate_hook_readiness(validations)
    groups = {
        "original": [
            item for item in validations
            if Path(item.trace_path).name in {"supported_trace.jsonl", "denied_trace.jsonl", "mixed_trace.jsonl"}
        ],
        "expanded": [
            item for item in validations
            if Path(item.trace_path).name not in {"supported_trace.jsonl", "denied_trace.jsonl", "mixed_trace.jsonl"}
        ],
    }
    lines = [
        "# Manual Hermes Trace Import Report",
        "",
        "Stages 29A and 29B import hand-written Hermes runtime JSONL traces for offline validation only.",
        "This report covers manual JSONL trace-import validation only.",
        "This stage does not run Hermes, does not execute capture-run, does not install dependencies,",
        "does not execute third-party commands, does not execute real tools, does not use network,",
        "and does not modify Hermes source. It cannot support a real Hermes integration claim or a",
        "claim that true runtime capture has completed.",
        "",
        "This is not an enforcement wrapper. `observer_only` events cannot produce enforcement ALLOW,",
        "`side_effect_already_happened=true` events cannot support an enforcement claim, missing-field",
        "events must fail closed with `AdapterCoverageGap`, unsupported events must fail closed, and",
        "DENY / ASK decisions must not execute the mock executor.",
        "",
        "## Trace Files Imported",
        "",
    ]
    for validation in validations:
        lines.append(f"- `{validation.trace_path}`")
    lines.extend(
        [
            "",
            "## Aggregate Summary",
            "",
            f"- Trace files: {len(validations)}",
            f"- Total events: {totals['total_events']}",
            f"- Valid events: {totals['schema_valid_events']}",
            f"- Schema-valid events: {totals['schema_valid_events']}",
            f"- Pre-execution-gate events: {totals['pre_execution_gate_events']}",
            f"- Observer-only events: {totals['observer_only_events']}",
            f"- Unsupported events: {totals['unsupported_events']}",
            f"- Missing-field events: {totals['missing_field_events']}",
            f"- Side-effect-already-happened events: {totals['side_effect_blocked']}",
            f"- Allowed / denied / ask: {totals['allowed']} / {totals['denied']} / {totals['ask']}",
            f"- Allowed: {totals['allowed']}",
            f"- Denied: {totals['denied']}",
            f"- Ask: {totals['ask']}",
            f"- AdapterCoverageGap: {totals['AdapterCoverageGap']}",
            f"- Observer-only blocked: {totals['observer_only_blocked']}",
            f"- Side-effect posthoc blocked: {totals['side_effect_blocked']}",
            f"- Executor called on deny: {totals['executor_called_on_deny']}",
            f"- Executor called on ask: {totals['executor_called_on_ask']}",
            "",
            "## Original vs Expanded Trace Sets",
            "",
            "| Set | Trace files | Events | Valid | Pre-exec | Observer-only | Unsupported | Missing-field | Side-effect posthoc | Allow | Deny | Ask | AdapterCoverageGap |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            trace_group_row("original", groups["original"]),
            trace_group_row("expanded", groups["expanded"]),
            "",
            "## Per-trace Summary",
            "",
            "| Trace | Events | Valid | Pre-exec | Observer-only | Missing-field | Side-effect posthoc | Allow | Deny | Ask | AdapterCoverageGap |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    per_trace_notes = []
    for validation in validations:
        label = "supported" if Path(validation.trace_path).name.startswith("supported") else (
            "denied" if Path(validation.trace_path).name.startswith("denied") else (
                "mixed" if Path(validation.trace_path).name.startswith("mixed") else Path(validation.trace_path).stem
            )
        )
        lines.append(
            f"| {Path(validation.trace_path).name} | {validation.total_events} | "
            f"{validation.schema_valid_events} | {validation.pre_execution_gate_events} | "
            f"{validation.observer_only_events} | {validation.missing_field_events} | "
            f"{validation.side_effect_blocked} | {validation.allowed} | {validation.denied} | "
            f"{validation.ask} | {validation.adapter_coverage_gap} |"
        )
        per_trace_notes.append(
            f"- {label}: {validation.total_events} events, "
            f"{validation.allowed} ALLOW, {validation.denied} DENY, "
            f"{validation.adapter_coverage_gap} AdapterCoverageGap"
        )
    lines.extend(
        [
            "",
            "## Per-trace Results",
            "",
            *per_trace_notes,
            "",
            "## Key Scenario Results",
            "",
            "- dispatcher rewrite: effective attacker target -> DENY NoCap.",
            "- scheduler replay: authorized register ALLOW; unauthorized replay / mismatch DENY.",
            "- MCP unsupported: stdio, missing endpoint, resource/prompt -> DENY AdapterCoverageGap.",
            "- gateway attachment: attachment/thread and missing recipient -> DENY AdapterCoverageGap.",
            "- terminal edge cases: pty/background, missing fields, post-effect -> DENY AdapterCoverageGap.",
            "",
            "",
            "## Hook Readiness Summary",
            "",
            "| Hook | Observed in manual trace | Complete fields | Pre-execution observed | Side effect already happened | Enforcement-ready |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for hook, data in readiness.items():
        lines.append(
            f"| {hook} | {data['observed']} | {data['complete_fields']} | "
            f"{data['pre_execution_observed']} | {data['side_effect_already_happened']} | "
            f"{data['enforcement_ready']} |"
        )
    lines.extend(
        [
            "",
            "## Scope",
            "",
        "- Trace source: hand-written JSONL files from the original Stage 29A set and expanded Stage 29B set.",
            "- Capture-run: not executed.",
            "- Real Hermes runtime: not run.",
            "- Dependency install: not performed.",
            "- Third-party commands: not executed.",
            "- Real tool execution: not performed.",
            "- External network calls: not performed.",
            "- Real captured events: none in this stage.",
            "- Enforcement wrapper: no-go.",
            "- Real Hermes integration claim: no.",
            "- More runtime samples are still required before any enforcement wrapper discussion.",
        ]
    )
    return "\n".join(lines) + "\n"


def trace_group_row(label: str, validations: list[Stage28TraceValidation]) -> str:
    totals = aggregate_trace_validations(validations)
    return (
        f"| {label} | {len(validations)} | {totals['total_events']} | "
        f"{totals['schema_valid_events']} | {totals['pre_execution_gate_events']} | "
        f"{totals['observer_only_events']} | {totals['unsupported_events']} | "
        f"{totals['missing_field_events']} | {totals['side_effect_blocked']} | "
        f"{totals['allowed']} | {totals['denied']} | {totals['ask']} | "
        f"{totals['AdapterCoverageGap']} |"
    )


def aggregate_trace_validations(validations: list[Stage28TraceValidation]) -> dict[str, int]:
    return {
        "total_events": sum(item.total_events for item in validations),
        "schema_valid_events": sum(item.schema_valid_events for item in validations),
        "pre_execution_gate_events": sum(item.pre_execution_gate_events for item in validations),
        "observer_only_events": sum(item.observer_only_events for item in validations),
        "unsupported_events": sum(item.unsupported_events for item in validations),
        "missing_field_events": sum(item.missing_field_events for item in validations),
        "allowed": sum(item.allowed for item in validations),
        "denied": sum(item.denied for item in validations),
        "ask": sum(item.ask for item in validations),
        "AdapterCoverageGap": sum(item.adapter_coverage_gap for item in validations),
        "observer_only_blocked": sum(item.observer_only_blocked for item in validations),
        "executor_called_on_deny": sum(item.executor_called_on_deny for item in validations),
        "executor_called_on_ask": sum(item.executor_called_on_ask for item in validations),
        "side_effect_blocked": sum(item.side_effect_blocked for item in validations),
    }


def aggregate_hook_readiness(validations: list[Stage28TraceValidation]) -> dict[str, dict[str, Any]]:
    aggregate = default_hook_readiness()
    for hook in aggregate:
        rows = [validation.hook_readiness.get(hook, {}) for validation in validations]
        observed_rows = [row for row in rows if row.get("observed") == "yes"]
        if not observed_rows:
            continue
        complete_values = {str(row.get("complete_fields", "unknown")) for row in observed_rows}
        pre_values = {str(row.get("pre_execution_observed", "unknown")) for row in observed_rows}
        side_values = {str(row.get("side_effect_already_happened", "unknown")) for row in observed_rows}
        ready_values = {str(row.get("enforcement_ready", "no")) for row in observed_rows}
        aggregate[hook] = {
            "observed": "yes",
            "complete_fields": "yes" if complete_values == {"yes"} else "partial",
            "pre_execution_observed": "yes" if pre_values == {"yes"} else ("no" if "no" in pre_values else "unknown"),
            "side_effect_already_happened": "yes" if "yes" in side_values else ("no" if side_values == {"no"} else "unknown"),
            "enforcement_ready": "yes" if ready_values == {"yes"} else "no",
            "missing_fields": sorted(
                {
                    field
                    for row in observed_rows
                    for field in tuple(row.get("missing_fields", ()))
                }
            ),
        }
    return aggregate


def render_capture_run_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    capture = summary["capture_run"]
    trace = summary["trace_validation"]
    lines = [
        "# Hermes Capture-run Report",
        "",
        "Stage 28 is a capture-run safety gate, no-run preflight, and optional trace-import",
        "validation harness. It is not a real Hermes integration, not an enforcement wrapper,",
        "and not a claim that CapProof protects real Hermes.",
        "",
        "By default Hermes is not run. `--capture-run` is denied unless all explicit",
        "capture-only safety environment variables are present and the command passes safety checks.",
        "",
        "## Capture-run Decision",
        "",
        f"- Run attempted: {capture['run_attempted']}",
        f"- Run allowed: {capture['run_allowed']}",
        f"- State: {capture['state']}",
        f"- Denial reason: {capture['denial_reason'] or 'n/a'}",
        f"- Command hash: {capture['command_hash']}",
        f"- Timeout seconds: {capture['timeout_seconds']}",
        f"- Trace path: `{capture['trace_path']}`",
        f"- Events captured: {capture['events_captured']}",
        "",
        "## Trace Source",
        "",
        f"- Source: {summary['trace_source']}",
        "",
        "## Safety Status",
        "",
    ]
    for key, value in summary["safety_status"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Trace Validation Summary",
            "",
            f"- Total events: {trace['total_events']}",
            f"- Schema-valid events: {trace['schema_valid_events']}",
            f"- Pre-execution-gate events: {trace['pre_execution_gate_events']}",
            f"- Observer-only events: {trace['observer_only_events']}",
            f"- Unsupported events: {trace['unsupported_events']}",
            f"- Missing-field events: {trace['missing_field_events']}",
            f"- Allowed: {trace['allowed']}",
            f"- Denied: {trace['denied']}",
            f"- Ask: {trace['ask']}",
            f"- AdapterCoverageGap: {trace['AdapterCoverageGap']}",
            f"- Observer-only blocked: {trace['observer_only_blocked']}",
            f"- Executor called on deny: {trace['executor_called_on_deny']}",
            f"- Executor called on ask: {trace['executor_called_on_ask']}",
            f"- Side-effect-already-happened blocked: {trace['side_effect_blocked']}",
            "",
            "## Hook Readiness",
            "",
            "| Hook | Observed | Complete fields | Pre-execution observed | Side effect already happened | Enforcement-ready |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for hook, data in summary["hook_readiness"].items():
        lines.append(
            f"| {hook} | {data['observed']} | {data['complete_fields']} | "
            f"{data['pre_execution_observed']} | {data['side_effect_already_happened']} | "
            f"{data['enforcement_ready']} |"
        )
    lines.extend(
        [
            "",
            "## Go / No-Go",
            "",
            f"- Enforcement wrapper: {summary['go_no_go']['enforcement_wrapper']}.",
            f"- Real Hermes integration: {summary['go_no_go']['real_hermes_integration']}.",
            f"- Real Hermes integration claim: {summary['go_no_go']['real_hermes_integration_claim']}.",
            f"- Real capture trace collected: {summary['go_no_go']['real_capture_trace_collected']}.",
            f"- More runtime samples needed: {summary['go_no_go']['more_runtime_samples_needed']}.",
            f"- Blocking hook points: {', '.join(summary['go_no_go']['blocking_hook_points']) or 'none'}.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_trace_validation_report(payload: dict[str, Any]) -> str:
    trace = payload["summary"]["trace_validation"]
    lines = [
        "# Hermes Trace Validation Report",
        "",
        "Trace validation is offline only. It does not run Hermes, execute tools, send messages,",
        "connect to network services, or provide an enforcement-wrapper claim.",
        "",
        f"- Trace source: {payload['summary']['trace_source']}",
        f"- Total events: {trace['total_events']}",
        f"- Schema-valid events: {trace['schema_valid_events']}",
        f"- Missing-field events: {trace['missing_field_events']}",
        f"- AdapterCoverageGap: {trace['AdapterCoverageGap']}",
        f"- Observer-only blocked: {trace['observer_only_blocked']}",
        f"- Side-effect-already-happened blocked: {trace['side_effect_blocked']}",
        f"- Executor called on deny: {trace['executor_called_on_deny']}",
        f"- Executor called on ask: {trace['executor_called_on_ask']}",
        "",
        "## Event Checks",
        "",
        "| Event | Hook | Mode | Missing schema fields | Pre-exec observed | Side effect happened | Fail closed |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for check in payload["event_checks"]:
        missing = ", ".join(check["missing_schema_fields"]) or "none"
        lines.append(
            f"| {check['event_id']} | {check['hook_point']} | {check['capture_mode']} | {missing} | "
            f"{check['pre_execution_observed']} | {check['side_effect_already_happened']} | "
            f"{check['fail_closed']} |"
        )
    if not payload["event_checks"]:
        lines.append("| none | none | none | none | unknown | unknown | false |")
    return "\n".join(lines) + "\n"


def render_hook_readiness_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Hermes Hook Readiness Report",
        "",
        "Hook readiness is derived from imported or captured JSONL events only. Unknown hooks are",
        "not enforcement-ready. Observer-only or post-effect captures cannot support enforcement claims.",
        "",
        "| Hook | Observed | Complete fields | Pre-execution observed | Side effect already happened | Enforcement-ready | Missing fields |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for hook, data in payload["summary"]["hook_readiness"].items():
        lines.append(
            f"| {hook} | {data['observed']} | {data['complete_fields']} | "
            f"{data['pre_execution_observed']} | {data['side_effect_already_happened']} | "
            f"{data['enforcement_ready']} | {', '.join(data.get('missing_fields', ())) or 'none'} |"
        )
    return "\n".join(lines) + "\n"


def build_hook_readiness(
    rows: list[dict[str, Any]],
    checks: tuple[Stage28EventCheck, ...],
    replay_results: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    readiness = {}
    for hook, aliases in HOOKS.items():
        indexed = [
            (row, check, replay_results[index] if index < len(replay_results) else {})
            for index, (row, check) in enumerate(zip(rows, checks))
            if check.hook_point in aliases
        ]
        if not indexed:
            readiness[hook] = {
                "observed": "no",
                "complete_fields": "unknown",
                "pre_execution_observed": "unknown",
                "side_effect_already_happened": "unknown",
                "enforcement_ready": "no",
                "missing_fields": [],
            }
            continue
        missing = sorted(
            {
                field
                for _row, check, result in indexed
                for field in (*check.missing_schema_fields, *tuple(result.get("missing_fields", ())))
            }
        )
        pre_values = [check.pre_execution_observed for _row, check, _result in indexed]
        side_effect_values = [check.side_effect_already_happened for _row, check, _result in indexed]
        complete = not missing and all(result.get("validation_status") == "valid" for _row, check, result in indexed)
        pre_exec = all(value is True for value in pre_values)
        side_effect = any(value is True for value in side_effect_values)
        readiness[hook] = {
            "observed": "yes",
            "complete_fields": "yes" if complete else "partial",
            "pre_execution_observed": "yes" if pre_exec else ("no" if any(value is False for value in pre_values) else "unknown"),
            "side_effect_already_happened": "yes" if side_effect else ("no" if all(value is False for value in side_effect_values) else "unknown"),
            "enforcement_ready": "yes" if complete and pre_exec and not side_effect else "no",
            "missing_fields": missing,
        }
    return readiness


def default_hook_readiness() -> dict[str, dict[str, Any]]:
    return {
        hook: {
            "observed": "no",
            "complete_fields": "unknown",
            "pre_execution_observed": "unknown",
            "side_effect_already_happened": "unknown",
            "enforcement_ready": "no",
            "missing_fields": [],
        }
        for hook in HOOKS
    }


def _check_event(row: dict[str, Any]) -> Stage28EventCheck:
    event = dict(row.get("captured_event", row))
    missing = tuple(field for field in STAGE28_REQUIRED_FIELDS if field not in event)
    return Stage28EventCheck(
        event_id=str(event.get("event_id", event.get("case_id", ""))),
        hook_point=str(event.get("hook_point", "")),
        capture_mode=str(event.get("capture_mode", "unsupported")),
        missing_schema_fields=missing,
        source_valid=event.get("source") == "hermes",
        pre_execution_observed=_optional_bool(event.get("pre_execution_observed")),
        side_effect_already_happened=_optional_bool(event.get("side_effect_already_happened")),
    )


def _schema_valid(check: Stage28EventCheck) -> bool:
    return (
        not check.missing_schema_fields
        and check.source_valid
        and check.pre_execution_observed is not None
        and check.side_effect_already_happened is not None
    )


def _to_replay_row(row: dict[str, Any], check: Stage28EventCheck) -> dict[str, Any]:
    event = dict(row.get("captured_event", row))
    if check.fail_closed:
        event["capture_mode"] = "unsupported"
        event["expected_verdict"] = "DENY"
        event["expected_reason"] = "AdapterCoverageGap"
    return event


def _read_trace_rows(trace_path: Path) -> list[dict[str, Any]]:
    if not trace_path.exists():
        return []
    rows = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_temp_jsonl(rows: list[dict[str, Any]]) -> Path:
    temp = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        prefix="capproof_stage28_trace_",
        suffix=".jsonl",
        delete=False,
    )
    with temp:
        for row in rows:
            temp.write(json.dumps(row, sort_keys=True) + "\n")
    return Path(temp.name)


def _copy_imported_trace(trace_path: Path, *, root: Path) -> Path:
    target_dir = _path(root, IMPORTED_TRACES_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        trace_path.resolve().relative_to(target_dir.resolve())
        return trace_path
    except ValueError:
        pass
    target = target_dir / trace_path.name
    if trace_path.resolve() != target.resolve():
        shutil.copyfile(trace_path, target)
    return target


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _ensure_dirs(root: Path) -> None:
    for path in (TRACES_DIR, REPORTS_DIR, IMPORTED_TRACES_DIR, SAFETY_LOGS_DIR):
        _path(root, path).mkdir(parents=True, exist_ok=True)


def _path(root: Path, path: Path) -> Path:
    try:
        rel = path.relative_to(ROOT)
        return root / rel
    except ValueError:
        if path.is_absolute():
            return path
        return root / path


if __name__ == "__main__":
    raise SystemExit(main())
