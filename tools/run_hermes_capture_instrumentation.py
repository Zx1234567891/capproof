#!/usr/bin/env python3
"""Hermes capture-only instrumentation fixture runner.

This runner processes fixture or trace JSON only. It does not run Hermes,
install dependencies, execute third-party commands, execute real tools, use
network, send messages, or run shell commands.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
from collections import defaultdict
import json
from pathlib import Path
import tempfile
from typing import Any

from run_hermes_capture_prototype import load_inputs, run_prototype

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTATION_DIR = ROOT / "hermes_capture_instrumentation"
FIXTURE_DIR = INSTRUMENTATION_DIR / "fixtures"
TRACES_DIR = INSTRUMENTATION_DIR / "traces"
REPORTS_DIR = INSTRUMENTATION_DIR / "reports"
TRACE_PATH = TRACES_DIR / "captured_events.jsonl"
SUMMARY_PATH = REPORTS_DIR / "capture_summary.json"
INTERNAL_REPORT_PATH = REPORTS_DIR / "capture_instrumentation_report.md"
ROOT_REPORT_PATH = ROOT / "hermes_capture_instrumentation_report.md"
PROTOTYPE_REPLAY_REPORT_PATH = REPORTS_DIR / "capture_replay_report.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hermes capture-only instrumentation fixture replay.")
    parser.add_argument("--fixture", default=None, help="fixture directory or JSON file")
    parser.add_argument("--trace", default=None, help="captured event JSONL trace to validate and replay")
    parser.add_argument("--validate", action="store_true", help="validate default trace if present, else fixtures")
    parser.add_argument("--report", action="store_true", help="print latest report paths, generating if needed")
    args = parser.parse_args()

    if args.report and not args.fixture and not args.trace and not args.validate:
        if not ROOT_REPORT_PATH.exists():
            run_instrumentation(fixture_path=FIXTURE_DIR)
        print(f"report: {ROOT_REPORT_PATH}")
        print(f"internal_report: {INTERNAL_REPORT_PATH}")
        print(f"summary: {SUMMARY_PATH}")
        print(f"trace: {TRACE_PATH}")
        return 0

    if args.trace:
        payload = run_instrumentation(trace_input_path=Path(args.trace))
    elif args.validate and TRACE_PATH.exists():
        payload = run_instrumentation(trace_input_path=TRACE_PATH)
    else:
        payload = run_instrumentation(fixture_path=Path(args.fixture) if args.fixture else FIXTURE_DIR)

    summary = payload["summary"]
    print(f"capture instrumentation events: {summary['total_events_processed']}")
    print(f"pre_execution_gate: {summary['pre_execution_gate']}")
    print(f"observer_only: {summary['observer_only_events']}")
    print(f"unsupported_or_missing: {summary['unsupported_missing_field_events']}")
    print(f"allowed: {summary['allowed']}")
    print(f"denied: {summary['denied']}")
    print(f"ask: {summary['ask']}")
    print(f"AdapterCoverageGap: {summary['adapter_coverage_gap_count']}")
    print(f"observer_only_blocked: {summary['observer_only_blocked_count']}")
    print(f"executor_called_on_deny: {summary['executor_called_on_deny']}")
    print(f"executor_called_on_ask: {summary['executor_called_on_ask']}")
    print(f"trace: {TRACE_PATH}")
    print(f"report: {ROOT_REPORT_PATH}")
    return 0 if summary["failed_expectations"] == 0 else 1


def run_instrumentation(
    *,
    fixture_path: Path | None = None,
    trace_input_path: Path | None = None,
    trace_path: Path = TRACE_PATH,
    summary_path: Path = SUMMARY_PATH,
    report_path: Path = INTERNAL_REPORT_PATH,
    root_report_path: Path = ROOT_REPORT_PATH,
    prototype_report_path: Path = PROTOTYPE_REPLAY_REPORT_PATH,
) -> dict[str, Any]:
    """Validate and replay captured fixture/trace events offline."""

    if trace_input_path is not None:
        replay_jsonl = _extract_trace_events(trace_input_path)
        payload = run_prototype(
            jsonl_path=replay_jsonl,
            trace_path=trace_path,
            summary_path=summary_path,
            report_path=prototype_report_path,
        )
        input_description = str(trace_input_path)
        original_inputs = load_inputs(input_path=FIXTURE_DIR, jsonl_path=replay_jsonl)
    else:
        fixture_input_path = fixture_path or FIXTURE_DIR
        payload = run_prototype(
            input_path=fixture_input_path,
            trace_path=trace_path,
            summary_path=summary_path,
            report_path=prototype_report_path,
        )
        input_description = str(fixture_input_path)
        original_inputs = load_inputs(input_path=fixture_input_path)

    _rewrite_trace_with_captured_events(trace_path, payload, original_inputs)
    report = render_instrumentation_report(payload, input_description=input_description, trace_path=trace_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    root_report_path.write_text(report, encoding="utf-8")
    return payload


def _extract_trace_events(trace_input_path: Path) -> Path:
    rows = []
    for line in trace_input_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows.append(dict(row.get("captured_event", row)))
    temp = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        prefix="capproof_hermes_trace_replay_",
        suffix=".jsonl",
        delete=False,
    )
    with temp:
        for row in rows:
            temp.write(json.dumps(row, sort_keys=True) + "\n")
    return Path(temp.name)


def _rewrite_trace_with_captured_events(
    trace_path: Path,
    payload: dict[str, Any],
    original_inputs: list[Any],
) -> None:
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    enriched_rows = []
    for index, line in enumerate(lines):
        row = json.loads(line)
        if index < len(original_inputs):
            row["captured_event"] = original_inputs[index].raw_event
        enriched_rows.append(row)
    trace_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in enriched_rows),
        encoding="utf-8",
    )


def render_instrumentation_report(payload: dict[str, Any], *, input_description: str, trace_path: Path) -> str:
    summary = payload["summary"]
    results = payload["results"]
    valid_schema_events = sum(result["validation_status"] == "valid" for result in results)
    hook_rows = _hook_rows(results)
    lines = [
        "# Hermes Capture-only Instrumentation Report",
        "",
        "## Stage Position",
        "",
        "Stage 24 is capture-only, record-only, and replay-only. It is not a real Hermes integration,",
        "not an enforcement wrapper, and not a claim that CapProof protects real Hermes. Hermes is not run,",
        "dependencies are not installed, third-party project commands are not executed, real tools are not",
        "called, no email/message is sent, no network is used, and no shell command is executed.",
        "",
        "The capture layer only records HermesRuntimeEvent-shaped JSON. The replay layer validates the",
        "captured events and performs an offline CapProof guard dry-run over pre_execution_gate events.",
        "`observer_only` events are recorded only and cannot produce enforcement ALLOW. Unsupported or",
        "missing-field events fail closed.",
        "",
        f"- Input: `{input_description}`",
        f"- Trace path: `{trace_path}`",
        "",
        "## Hook Coverage Table",
        "",
        "| Hook point | Required fields | Captured fields | Missing fields | Capture mode | Replay verdict | Enforcement readiness |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in hook_rows:
        lines.append(
            f"| {row['hook_point']} | {row['required_fields']} | {row['captured_fields']} | "
            f"{row['missing_fields']} | {row['capture_modes']} | {row['verdicts']} | {row['readiness']} |"
        )
    lines.extend(
        [
            "",
            "## Capture Summary",
            "",
            f"- Total fixture events: {summary['total_events_processed']}",
            f"- Pre-execution-gate events: {summary['pre_execution_gate']}",
            f"- Observer-only events: {summary['observer_only_events']}",
            f"- Unsupported / missing-field events: {summary['unsupported_missing_field_events']}",
            f"- Schema-valid events: {valid_schema_events}",
            f"- Missing-field events: {sum(bool(result['missing_fields']) for result in results)}",
            "",
            "## Replay Summary",
            "",
            f"- Allowed: {summary['allowed']}",
            f"- Denied: {summary['denied']}",
            f"- Ask: {summary['ask']}",
            f"- AdapterCoverageGap count: {summary['adapter_coverage_gap_count']}",
            f"- Observer-only blocked count: {summary['observer_only_blocked_count']}",
            f"- Executor called on deny: {summary['executor_called_on_deny']}",
            f"- Executor called on ask: {summary['executor_called_on_ask']}",
            "",
            "## Results",
            "",
            "| Case | Hook | Mode | Validation | Verdict | Reason | Executor |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for result in results:
        lines.append(
            f"| {result['case_id']} | {result['hook_point']} | {result['capture_mode']} | "
            f"{result['validation_status']} | {result['guard_verdict']} | {result['deny_reason']} | "
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
        lines.append("- None in the processed fixture set.")
    lines.extend(
        [
            "",
            "## Go / No-Go",
            "",
            "- Real Hermes runtime capture experiment: go, limited to capture-only instrumentation once hook availability is confirmed.",
            "- Enforcement wrapper: no-go.",
            "- Real Hermes integration claim: no.",
            "- Real Hermes hook samples are still required: yes.",
        ]
    )
    return "\n".join(lines) + "\n"


def _hook_rows(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result["hook_point"]].append(result)
    rows = []
    for hook_point in sorted(grouped):
        items = grouped[hook_point]
        captured = sorted({field for item in items for field in item["authority_bearing_fields"]})
        missing = sorted({field for item in items for field in item["missing_fields"]})
        modes = sorted({item["capture_mode"] for item in items})
        verdicts = sorted({item["guard_verdict"] for item in items})
        rows.append(
            {
                "hook_point": hook_point,
                "required_fields": _required_fields(hook_point),
                "captured_fields": ", ".join(captured) if captured else "none",
                "missing_fields": ", ".join(missing) if missing else "none",
                "capture_modes": ", ".join(modes),
                "verdicts": ", ".join(verdicts),
                "readiness": _readiness(hook_point, items),
            }
        )
    return rows


def _required_fields(hook_point: str) -> str:
    return {
        "tool_dispatcher_pre_call": "tool_name, original_args, effective_args, source_component",
        "terminal_backend_pre_exec": "command, cwd, env, stdin, terminal_backend",
        "mcp_pre_transport": "server, tool_name, arguments, transport.endpoint, headers",
        "memory_pre_write": "content, origin, persistent, authority_claims if present",
        "gateway_messaging_pre_send": "platform/target, recipient/target, body/body_ref/message",
        "subagent_delegation_pre_dispatch": "parent_agent, child_agent, goal/scope, cert_ref or explicit missing cert",
        "scheduler_cron_pre_register": "schedule_id, recurrence, action target",
        "scheduler_cron_pre_fire": "schedule_id, recurrence, action target",
        "skill_plugin_middleware_rewrite": "original_args, effective_args, source_component",
        "observer_posthoc": "posthoc observed fields only",
    }.get(hook_point, "unknown")


def _readiness(hook_point: str, items: list[dict[str, Any]]) -> str:
    if hook_point == "observer_posthoc":
        return "audit-only; cannot enforce"
    if any(item["missing_fields"] for item in items):
        return "fixture proves fail-closed for missing fields"
    if any(item["validation_status"] != "valid" for item in items):
        return "not enforcement-ready"
    return "synthetic pre-execution replay-ready; real runtime hook still unverified"


if __name__ == "__main__":
    raise SystemExit(main())
