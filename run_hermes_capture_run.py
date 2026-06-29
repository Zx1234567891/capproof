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
SAFETY_LOGS_DIR = CAPTURE_RUN_DIR / "safety_logs"
DEFAULT_TRACE_PATH = TRACES_DIR / "captured_events.jsonl"
SUMMARY_PATH = REPORTS_DIR / "capture_run_summary.json"
CAPTURE_RUN_REPORT_PATH = REPORTS_DIR / "capture_run_report.md"
TRACE_VALIDATION_REPORT_PATH = REPORTS_DIR / "trace_validation_report.md"
HOOK_READINESS_REPORT_PATH = REPORTS_DIR / "hook_readiness_report.md"
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
    side_effect_blocked = sum(check.side_effect_already_happened is True for check in checks)
    return Stage28TraceValidation(
        trace_path=str(trace_path),
        trace_source=trace_source,
        total_events=len(rows),
        schema_valid_events=sum(_schema_valid(check) for check in checks),
        pre_execution_gate_events=sum(check.capture_mode == "pre_execution_gate" for check in checks),
        observer_only_events=sum(check.capture_mode == "observer_only" for check in checks),
        unsupported_events=sum(check.capture_mode == "unsupported" or check.fail_closed for check in checks),
        missing_field_events=max(stage_missing_events, replay_summary["unsupported_missing_field_events"]),
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
