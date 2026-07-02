#!/usr/bin/env python3
"""Hermes runtime capture-only experiment runner.

Default operation is no-run preflight and offline trace validation. The script
does not run Hermes unless ``--capture-run`` is requested and the explicit
ALLOW_HERMES_CAPTURE_RUN / HERMES_CAPTURE_COMMAND safety gate passes.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
from typing import Any, Callable, Mapping

from run_hermes_capture_prototype import run_prototype

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "hermes_runtime_capture_experiment"
PREFLIGHT_DIR = EXPERIMENT_DIR / "preflight"
TRACE_DIR = EXPERIMENT_DIR / "traces"
REPORTS_DIR = EXPERIMENT_DIR / "reports"
FIXTURE_DIR = EXPERIMENT_DIR / "fixtures"
PATCHES_DIR = EXPERIMENT_DIR / "patches"
DEFAULT_TRACE_PATH = TRACE_DIR / "events.jsonl"
VALIDATED_TRACE_PATH = TRACE_DIR / "validated_events.jsonl"
SUMMARY_PATH = REPORTS_DIR / "runtime_capture_summary.json"
REPORT_PATH = REPORTS_DIR / "runtime_capture_report.md"
PREFLIGHT_PATH = PREFLIGHT_DIR / "preflight_summary.json"
TRACE_REPLAY_REPORT_PATH = REPORTS_DIR / "trace_replay_report.md"
TRACE_REPLAY_SUMMARY_PATH = REPORTS_DIR / "trace_replay_summary.json"
CAPTURE_RUN_DIR = ROOT / "hermes_capture_run"
CAPTURE_RUN_TRACES_DIR = CAPTURE_RUN_DIR / "traces"
CAPTURE_RUN_REPORTS_DIR = CAPTURE_RUN_DIR / "reports"
CAPTURE_RUN_DEFAULT_TRACE_PATH = CAPTURE_RUN_TRACES_DIR / "captured_events.jsonl"
CAPTURE_RUN_REPORT_PATH = CAPTURE_RUN_REPORTS_DIR / "capture_run_report.md"
CAPTURE_RUN_SUMMARY_PATH = CAPTURE_RUN_REPORTS_DIR / "capture_run_summary.json"
CAPTURE_TIMEOUT_SECONDS = 20

HOOK_CANDIDATES = {
    "tool_dispatcher": ("tool_call", "function_call", "dispatch", "tool dispatcher", "tool_name"),
    "terminal": ("terminal", "shell", "command", "subprocess", "stdin", "cwd"),
    "mcp": ("mcp", "transport", "server", "tool_name", "endpoint"),
    "memory": ("memory", "remember", "persistent", "authority_claims"),
    "gateway": ("gateway", "message", "telegram", "discord", "recipient", "chat_id"),
    "delegation": ("delegate", "delegation", "subagent", "parent_agent", "child_agent"),
    "scheduler": ("schedule", "cron", "recurrence", "scheduled"),
    "middleware_rewrite": ("middleware", "rewrite", "effective_args", "original_args", "plugin", "skill"),
}

TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".toml", ".md", ".txt"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", "dist", "build", ".venv", "venv"}

UNSAFE_COMMAND_FRAGMENTS = (
    "curl",
    "wget",
    " nc ",
    "netcat",
    "ssh",
    "scp",
    "rsync",
    "rm -rf",
    "sudo",
    "sh -c",
    "bash -c",
    "|",
    ">",
    "<",
    "`",
    "$(",
    " pip install",
    " npm install",
    " pnpm install",
    " poetry install",
    " make install",
    "python -m http.server",
    "uvicorn",
    "flask run",
)
CAPTURE_ONLY_MARKERS = ("capture", "dry-run", "dry_run", "mock", "fixture", "no-real", "no_real")
SECRET_MARKERS = ("TOKEN=", "SECRET=", "PASSWORD=", "PRIVATE_KEY=", "API_KEY=")
EXTERNAL_URL_PATTERN = re.compile(r"https?://(?!localhost(?::|/|$)|127\.0\.0\.1(?::|/|$))[^\s'\"]+")
SERVER_START_FRAGMENTS = ("uvicorn", "flask run", "python -m http.server")
REQUIRED_CAPTURE_RUN_FLAGS = (
    ("CAPPROOF_CAPTURE_ONLY", "1"),
    ("CAPPROOF_NO_REAL_TOOLS", "1"),
    ("NO_NETWORK", "1"),
)


@dataclass(frozen=True)
class PreflightResult:
    repo_path: str
    repo_status: str
    files_scanned: int
    no_command_executed: bool
    hook_candidates: dict[str, dict[str, Any]]
    existing_trace: str | None
    safe_capture_feasibility: dict[str, Any]
    capture_run_allowed: bool
    reason: str


@dataclass(frozen=True)
class CaptureRunResult:
    run_attempted: bool
    state: str
    reason: str
    command_hash: str = ""
    timeout_seconds: int = CAPTURE_TIMEOUT_SECONDS
    trace_path: str = str(DEFAULT_TRACE_PATH)
    events_captured: int = 0
    no_real_tool_assertion: bool = False
    returncode: int | None = None


@dataclass(frozen=True)
class TraceValidationResult:
    trace_path: str
    total_events: int = 0
    schema_valid_events: int = 0
    pre_execution_gate_events: int = 0
    observer_only_events: int = 0
    unsupported_events: int = 0
    missing_field_events: int = 0
    allowed: int = 0
    denied: int = 0
    ask: int = 0
    adapter_coverage_gap_count: int = 0
    observer_only_blocked_count: int = 0
    executor_called_on_deny: int = 0
    executor_called_on_ask: int = 0
    hook_completeness: dict[str, dict[str, Any]] = field(default_factory=dict)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes runtime capture-only experiment.")
    parser.add_argument("--preflight", action="store_true", help="run no-run preflight")
    parser.add_argument("--validate-trace", default=None, help="validate and offline replay an existing JSONL trace")
    parser.add_argument("--report", action="store_true", help="print or generate latest report")
    parser.add_argument("--capture-run", action="store_true", help="attempt explicitly authorized capture-only command")
    args = parser.parse_args()

    if args.validate_trace:
        payload = run_experiment(validate_trace_path=Path(args.validate_trace))
    elif args.capture_run:
        payload = run_experiment(capture_run_requested=True)
    else:
        payload = run_experiment(preflight_only=True)

    if args.report and not args.preflight and not args.validate_trace and not args.capture_run:
        if not REPORT_PATH.exists():
            payload = run_experiment(preflight_only=True)
        print(f"report: {REPORT_PATH}")
        print(f"summary: {SUMMARY_PATH}")
        print(f"capture_run_report: {CAPTURE_RUN_REPORT_PATH}")
        print(f"capture_run_summary: {CAPTURE_RUN_SUMMARY_PATH}")
        return 0

    summary = payload["summary"]
    preflight = summary["preflight"]
    trace = summary["trace_validation"]
    capture = summary["capture_run"]
    print(f"repo_status: {preflight['repo_status']}")
    print(f"repo_path: {preflight['repo_path']}")
    print(f"files_scanned: {preflight['files_scanned']}")
    print(f"capture_run_allowed: {preflight['capture_run_allowed']}")
    print(f"capture_run_state: {capture['state']}")
    print(f"trace_events: {trace['total_events']}")
    print(f"allowed: {trace['allowed']}")
    print(f"denied: {trace['denied']}")
    print(f"ask: {trace['ask']}")
    print(f"AdapterCoverageGap: {trace['adapter_coverage_gap_count']}")
    print(f"report: {REPORT_PATH}")
    return 0


def run_experiment(
    *,
    preflight_only: bool = False,
    validate_trace_path: Path | None = None,
    capture_run_requested: bool = False,
    env: Mapping[str, str] | None = None,
    command_runner: Callable[..., Any] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    env_map = dict(os.environ if env is None else env)
    _ensure_dirs(root)
    preflight = run_preflight(env=env_map, root=root)
    capture_result = CaptureRunResult(
        run_attempted=False,
        state="not_run",
        reason="capture run not requested",
        trace_path=str(_path(root, CAPTURE_RUN_DEFAULT_TRACE_PATH)),
    )
    trace_result = TraceValidationResult(trace_path=str(validate_trace_path or _path(root, DEFAULT_TRACE_PATH)))

    if capture_run_requested:
        capture_result = run_capture_run(preflight, env=env_map, root=root, command_runner=command_runner)
        if capture_result.state == "completed" and Path(capture_result.trace_path).exists():
            trace_result = validate_trace(Path(capture_result.trace_path), root=root)
    elif validate_trace_path is not None:
        trace_result = validate_trace(validate_trace_path, root=root)
    elif not preflight_only and _path(root, DEFAULT_TRACE_PATH).exists():
        trace_result = validate_trace(_path(root, DEFAULT_TRACE_PATH), root=root)

    payload = build_payload(preflight=preflight, capture_run=capture_result, trace_validation=trace_result)
    write_outputs(payload, root=root)
    return payload


def run_preflight(*, env: Mapping[str, str] | None = None, root: Path = ROOT) -> PreflightResult:
    repo_path, repo_status = resolve_hermes_repo(env=env, root=root)
    files_scanned = 0
    hook_candidates = {name: {"hits": 0, "sample_files": []} for name in HOOK_CANDIDATES}
    if repo_path is not None and repo_path.exists():
        files_scanned, hook_candidates = scan_hook_candidates(repo_path)
    existing_trace = str(_path(root, DEFAULT_TRACE_PATH)) if _path(root, DEFAULT_TRACE_PATH).exists() else None
    explicit_allowed = (env or os.environ).get("ALLOW_HERMES_CAPTURE_RUN") == "1"
    command_present = bool((env or os.environ).get("HERMES_CAPTURE_COMMAND"))
    feasibility = {
        "clear_dry_run_or_mock_mode": False,
        "capture_without_tool_execution_confirmed": False,
        "pre_execution_capture_confirmed": False,
        "field_completeness_confirmed": False,
        "explicit_capture_run_env": explicit_allowed,
        "capture_command_present": command_present,
    }
    reason = "default no-run preflight: explicit capture-run authorization not provided"
    if repo_status == "repo_missing":
        reason = "Hermes repo missing; capture-run disabled"
    elif explicit_allowed and command_present:
        reason = "explicit env present, but command must still pass capture-run safety checks"
    return PreflightResult(
        repo_path=str(repo_path) if repo_path else "",
        repo_status=repo_status,
        files_scanned=files_scanned,
        no_command_executed=True,
        hook_candidates=hook_candidates,
        existing_trace=existing_trace,
        safe_capture_feasibility=feasibility,
        capture_run_allowed=False,
        reason=reason,
    )


def resolve_hermes_repo(*, env: Mapping[str, str] | None = None, root: Path = ROOT) -> tuple[Path | None, str]:
    env_map = env or os.environ
    candidates = []
    if env_map.get("HERMES_REPO"):
        candidates.append(Path(str(env_map["HERMES_REPO"])))
    candidates.extend((root / "external" / "hermes-agent", root / "external" / "external" / "hermes-agent"))
    for candidate in candidates:
        if candidate.exists():
            return candidate, "available"
    return candidates[0] if candidates else None, "repo_missing"


def scan_hook_candidates(repo_path: Path, *, max_files: int = 2000) -> tuple[int, dict[str, dict[str, Any]]]:
    files_scanned = 0
    hits = {name: {"hits": 0, "sample_files": []} for name in HOOK_CANDIDATES}
    for path in repo_path.rglob("*"):
        if files_scanned >= max_files:
            break
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        files_scanned += 1
        rel = str(path.relative_to(repo_path))
        for surface, keywords in HOOK_CANDIDATES.items():
            if any(keyword.lower() in text for keyword in keywords):
                hits[surface]["hits"] += 1
                if len(hits[surface]["sample_files"]) < 5:
                    hits[surface]["sample_files"].append(rel)
    return files_scanned, hits


def run_capture_run(
    preflight: PreflightResult,
    *,
    env: Mapping[str, str] | None = None,
    root: Path = ROOT,
    command_runner: Callable[..., Any] | None = None,
) -> CaptureRunResult:
    env_map = dict(os.environ if env is None else env)
    trace_path = _resolve_capture_trace_path(root, env_map.get("HERMES_CAPTURE_TRACE_PATH", ""))
    if env_map.get("ALLOW_HERMES_CAPTURE_RUN") != "1":
        return CaptureRunResult(
            run_attempted=False,
            state="DENY_CAPTURE_RUN",
            reason="ALLOW_HERMES_CAPTURE_RUN=1 is required",
            trace_path=str(trace_path),
        )
    command = env_map.get("HERMES_CAPTURE_COMMAND", "").strip()
    if not command:
        return CaptureRunResult(
            run_attempted=False,
            state="DENY_CAPTURE_RUN",
            reason="HERMES_CAPTURE_COMMAND is required",
            trace_path=str(trace_path),
        )
    if not env_map.get("HERMES_CAPTURE_TRACE_PATH"):
        return CaptureRunResult(
            run_attempted=False,
            state="DENY_CAPTURE_RUN",
            reason="HERMES_CAPTURE_TRACE_PATH is required",
            command_hash=hash_command(command),
            trace_path=str(trace_path),
        )
    for name, expected in REQUIRED_CAPTURE_RUN_FLAGS:
        if env_map.get(name) != expected:
            return CaptureRunResult(
                run_attempted=False,
                state="DENY_CAPTURE_RUN",
                reason=f"{name}={expected} is required",
                command_hash=hash_command(command),
                trace_path=str(trace_path),
            )
    workspace = env_map.get("HERMES_TEST_WORKSPACE", "").strip()
    if not workspace:
        return CaptureRunResult(
            run_attempted=False,
            state="DENY_CAPTURE_RUN",
            reason="HERMES_TEST_WORKSPACE is required",
            command_hash=hash_command(command),
            trace_path=str(trace_path),
        )
    if not Path(workspace).exists():
        return CaptureRunResult(
            run_attempted=False,
            state="DENY_CAPTURE_RUN",
            reason="HERMES_TEST_WORKSPACE must exist before capture-run",
            command_hash=hash_command(command),
            trace_path=str(trace_path),
        )
    repo_path = Path(preflight.repo_path) if preflight.repo_path else None
    if not repo_path or not repo_path.exists():
        return CaptureRunResult(
            run_attempted=False,
            state="DENY_CAPTURE_RUN",
            reason="HERMES_REPO must exist before capture-run",
            trace_path=str(trace_path),
        )
    safe, reason = validate_capture_command(command)
    if not safe:
        return CaptureRunResult(
            run_attempted=False,
            state="DENY_CAPTURE_RUN",
            reason=reason,
            command_hash=hash_command(command),
            trace_path=str(trace_path),
        )

    argv = shlex.split(command)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    run_env = dict(env_map)
    run_env.update(
        {
            "CAPTURE_ONLY": "1",
            "CAPPROOF_CAPTURE_ONLY": "1",
            "CAPPROOF_NO_REAL_TOOLS": "1",
            "NO_NETWORK": "1",
            "HERMES_CAPTURE_TRACE_PATH": str(trace_path),
        }
    )
    runner = command_runner or subprocess.run
    result = runner(
        argv,
        cwd=repo_path,
        env=run_env,
        timeout=CAPTURE_TIMEOUT_SECONDS,
        capture_output=True,
        text=True,
        check=False,
    )
    events_captured = count_jsonl_events(trace_path) if trace_path.exists() else 0
    return CaptureRunResult(
        run_attempted=True,
        state="completed" if getattr(result, "returncode", 1) == 0 else "command_failed",
        reason="capture command completed" if getattr(result, "returncode", 1) == 0 else "capture command returned non-zero",
        command_hash=hash_command(command),
        timeout_seconds=CAPTURE_TIMEOUT_SECONDS,
        trace_path=str(trace_path),
        events_captured=events_captured,
        no_real_tool_assertion=True,
        returncode=getattr(result, "returncode", None),
    )


def validate_capture_command(command: str) -> tuple[bool, str]:
    padded = f" {command.lower()} "
    if any(marker in command for marker in SECRET_MARKERS):
        return False, "command appears to contain token/secret environment material"
    for fragment in UNSAFE_COMMAND_FRAGMENTS:
        if fragment in padded:
            return False, f"unsafe capture command fragment rejected: {fragment.strip()}"
    if EXTERNAL_URL_PATTERN.search(command):
        return False, "unsafe capture command external URL rejected"
    if any(fragment in padded for fragment in SERVER_START_FRAGMENTS) and "mock" not in padded:
        return False, "unsafe capture command server start rejected unless explicitly mock-only"
    if not any(marker in padded for marker in CAPTURE_ONLY_MARKERS):
        return False, "command must clearly indicate capture-only / dry-run / mock-tool mode"
    try:
        shlex.split(command)
    except ValueError as exc:
        return False, f"command cannot be safely tokenized: {exc}"
    return True, "command passed capture-run preflight"


def validate_trace(trace_path: Path, *, root: Path = ROOT) -> TraceValidationResult:
    if not trace_path.exists():
        return TraceValidationResult(trace_path=str(trace_path))
    replay_jsonl = extract_trace_events(trace_path)
    payload = run_prototype(
        jsonl_path=replay_jsonl,
        trace_path=_path(root, VALIDATED_TRACE_PATH),
        summary_path=_path(root, TRACE_REPLAY_SUMMARY_PATH),
        report_path=_path(root, TRACE_REPLAY_REPORT_PATH),
    )
    summary = payload["summary"]
    results = payload["results"]
    return TraceValidationResult(
        trace_path=str(trace_path),
        total_events=summary["total_events_processed"],
        schema_valid_events=sum(result["validation_status"] == "valid" for result in results),
        pre_execution_gate_events=summary["pre_execution_gate"],
        observer_only_events=summary["observer_only_events"],
        unsupported_events=sum(result["capture_mode"] == "unsupported" for result in results),
        missing_field_events=sum(bool(result["missing_fields"]) for result in results),
        allowed=summary["allowed"],
        denied=summary["denied"],
        ask=summary["ask"],
        adapter_coverage_gap_count=summary["adapter_coverage_gap_count"],
        observer_only_blocked_count=summary["observer_only_blocked_count"],
        executor_called_on_deny=summary["executor_called_on_deny"],
        executor_called_on_ask=summary["executor_called_on_ask"],
        hook_completeness=hook_completeness(results),
    )


def extract_trace_events(trace_path: Path) -> Path:
    rows = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows.append(dict(row.get("captured_event", row)))
    temp = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        prefix="capproof_hermes_runtime_trace_",
        suffix=".jsonl",
        delete=False,
    )
    with temp:
        for row in rows:
            temp.write(json.dumps(row, sort_keys=True) + "\n")
    return Path(temp.name)


def hook_completeness(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for hook in HOOK_CANDIDATES:
        hook_name = _hook_to_runtime_name(hook)
        hook_results = [result for result in results if result["hook_point"] == hook_name]
        missing = sorted({field for result in hook_results for field in result["missing_fields"]})
        observed = bool(hook_results)
        complete = observed and not missing and all(result["validation_status"] == "valid" for result in hook_results)
        pre_execution = observed and all(result["capture_mode"] == "pre_execution_gate" for result in hook_results)
        out[hook] = {
            "observed": "yes" if observed else "no",
            "complete_fields": "yes" if complete else ("partial" if observed else "unknown"),
            "pre_execution": "yes" if pre_execution else ("no" if observed else "unknown"),
            "enforcement_ready": "partial" if complete else "no",
            "missing_fields": missing,
        }
    return out


def build_payload(
    *,
    preflight: PreflightResult,
    capture_run: CaptureRunResult,
    trace_validation: TraceValidationResult,
) -> dict[str, Any]:
    return {
        "summary": {
            "preflight": asdict(preflight),
            "capture_run": asdict(capture_run),
            "trace_validation": asdict(trace_validation),
            "safety": {
                "real_hermes_run": capture_run.run_attempted,
                "dependencies_installed": False,
                "third_party_commands_executed": capture_run.run_attempted,
                "real_tools_executed": False,
                "network_used": False,
                "hermes_source_modified": False,
                "reference_monitor_modified": False,
            },
        },
    }


def write_outputs(payload: dict[str, Any], *, root: Path = ROOT) -> None:
    _ensure_dirs(root)
    _path(root, SUMMARY_PATH).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _path(root, PREFLIGHT_PATH).write_text(
        json.dumps(payload["summary"]["preflight"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _path(root, REPORT_PATH).write_text(render_report(payload), encoding="utf-8")
    capture_run_summary = build_capture_run_summary(payload)
    _path(root, CAPTURE_RUN_SUMMARY_PATH).write_text(
        json.dumps(capture_run_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _path(root, CAPTURE_RUN_REPORT_PATH).write_text(
        render_capture_run_report(payload, capture_run_summary),
        encoding="utf-8",
    )


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    preflight = summary["preflight"]
    capture = summary["capture_run"]
    trace = summary["trace_validation"]
    hook_readiness = trace.get("hook_completeness") or default_hook_readiness(preflight)
    lines = [
        "# Hermes Runtime Capture Experiment Report",
        "",
        "## Stage Position",
        "",
        "Stage 25 is a capture-only runtime experiment. It is not an enforcement wrapper,",
        "not a real integration claim, and not a claim that CapProof protects real Hermes.",
        "Default preflight does not run Hermes, install dependencies, execute third-party commands,",
        "execute real tools, use network, send messages/email, or modify Hermes source.",
        "",
        "Capture-run remains denied unless `ALLOW_HERMES_CAPTURE_RUN=1`, `HERMES_CAPTURE_COMMAND`,",
        "`HERMES_CAPTURE_TRACE_PATH`, `CAPPROOF_CAPTURE_ONLY=1`, `CAPPROOF_NO_REAL_TOOLS=1`,",
        "`NO_NETWORK=1`, and `HERMES_TEST_WORKSPACE` are all set and the command passes",
        "capture-only safety checks. Only captured JSONL traces are",
        "trusted for validation; natural-language logs are not authorization evidence.",
        "",
        "## Preflight Summary",
        "",
        f"- Repo path: `{preflight['repo_path']}`",
        f"- Repo status: {preflight['repo_status']}",
        f"- Files scanned: {preflight['files_scanned']}",
        f"- No command executed: {preflight['no_command_executed']}",
        f"- Existing trace: {preflight['existing_trace'] or 'none'}",
        f"- Capture-run allowed: {preflight['capture_run_allowed']}",
        f"- Reason: {preflight['reason']}",
        "",
        "## Potential Hook Points",
        "",
        "| Hook | Candidate hits | Sample files |",
        "| --- | ---: | --- |",
    ]
    for hook, data in preflight["hook_candidates"].items():
        samples = ", ".join(data.get("sample_files", ())) or "none"
        lines.append(f"| {hook} | {data.get('hits', 0)} | {samples} |")
    lines.extend(
        [
            "",
            "## Capture Run Summary",
            "",
            f"- Run attempted: {capture['run_attempted']}",
            f"- State: {capture['state']}",
            f"- Reason: {capture['reason']}",
            f"- Command hash: {capture['command_hash'] or 'n/a'}",
            f"- Timeout seconds: {capture['timeout_seconds']}",
            f"- Trace path: `{capture['trace_path']}`",
            f"- Events captured: {capture['events_captured']}",
            f"- No real tool assertion: {capture['no_real_tool_assertion']}",
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
            f"- AdapterCoverageGap count: {trace['adapter_coverage_gap_count']}",
            f"- Observer-only blocked count: {trace['observer_only_blocked_count']}",
            f"- Executor called on deny: {trace['executor_called_on_deny']}",
            f"- Executor called on ask: {trace['executor_called_on_ask']}",
            "",
            "## Hook Completeness",
            "",
            "| Hook | Observed | Complete fields | Enforcement-ready | Missing fields |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for hook, data in hook_readiness.items():
        missing = ", ".join(data.get("missing_fields", ())) or "none"
        lines.append(
            f"| {hook} | {data.get('observed', 'unknown')} | {data.get('complete_fields', 'unknown')} | "
            f"{data.get('enforcement_ready', 'no')} | {missing} |"
        )
    lines.extend(
        [
            "",
            "## Go / No-Go",
            "",
            "- Enforcement wrapper: no-go.",
            "- Real Hermes integration claim: no.",
            "- Runtime capture experiment completed: yes, limited to no-run preflight and any supplied offline trace validation.",
            "- Next step: obtain or generate safe capture-only runtime traces, then verify pre-execution hook placement and field completeness.",
        ]
    )
    return "\n".join(lines) + "\n"


def default_hook_readiness(preflight: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        hook: {
            "observed": "unknown" if preflight["repo_status"] == "available" else "no",
            "complete_fields": "unknown",
            "pre_execution": "unknown",
            "enforcement_ready": "no",
            "missing_fields": [],
        }
        for hook in HOOK_CANDIDATES
    }


def build_capture_run_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    preflight = summary["preflight"]
    capture = summary["capture_run"]
    trace = summary["trace_validation"]
    hook_readiness = trace.get("hook_completeness") or default_hook_readiness(summary["preflight"])
    run_allowed = bool(capture["run_attempted"])
    state = "DENY_CAPTURE_RUN" if capture["state"] == "not_run" else capture["state"]
    denial_reason = preflight["reason"] if capture["state"] == "not_run" else capture["reason"]
    return {
        "capture_run": {
            "run_attempted": capture["run_attempted"],
            "run_allowed": run_allowed,
            "state": state,
            "denial_reason": "" if run_allowed else denial_reason,
            "command_hash": capture["command_hash"] or "n/a",
            "timeout_seconds": capture["timeout_seconds"],
            "trace_path": capture["trace_path"],
            "events_captured": capture["events_captured"],
        },
        "safety_status": {
            "no_real_email": True,
            "no_real_external_network": True,
            "no_real_shell_high_risk_execution": True,
            "no_real_mcp_external_server": True,
            "no_secrets_used": True,
            "no_hermes_source_modification": True,
            "not_enforcement_wrapper": True,
        },
        "trace_validation": {
            "total_events": trace["total_events"],
            "schema_valid_events": trace["schema_valid_events"],
            "pre_execution_gate_events": trace["pre_execution_gate_events"],
            "observer_only_events": trace["observer_only_events"],
            "unsupported_events": trace["unsupported_events"],
            "missing_field_events": trace["missing_field_events"],
            "allowed": trace["allowed"],
            "denied": trace["denied"],
            "ask": trace["ask"],
            "AdapterCoverageGap": trace["adapter_coverage_gap_count"],
            "observer_only_blocked": trace["observer_only_blocked_count"],
            "executor_called_on_deny": trace["executor_called_on_deny"],
            "executor_called_on_ask": trace["executor_called_on_ask"],
        },
        "hook_readiness": hook_readiness,
        "go_no_go": {
            "enforcement_wrapper": "no-go",
            "real_hermes_integration_claim": "no",
            "real_hermes_integration": False,
            "real_capture_trace_collected": bool(capture["events_captured"] and trace["schema_valid_events"]),
            "more_runtime_samples_needed": True,
        },
    }


def render_capture_run_report(payload: dict[str, Any], capture_run_summary: dict[str, Any]) -> str:
    capture = capture_run_summary["capture_run"]
    safety = capture_run_summary["safety_status"]
    trace = capture_run_summary["trace_validation"]
    hook_readiness = capture_run_summary["hook_readiness"]
    go_no_go = capture_run_summary["go_no_go"]
    lines = [
        "# Hermes Capture-run Report",
        "",
        "## Stage Position",
        "",
        "Stage 27 is a controlled capture-only run attempt. It is not an enforcement wrapper,",
        "does not claim that CapProof is integrated with or protects real Hermes, and does not",
        "trust natural-language logs as authorization evidence. If explicit capture-run",
        "authorization is absent, the run fails closed with `DENY_CAPTURE_RUN` and no Hermes",
        "process is started.",
        "",
        "The default no-run report means `ALLOW_HERMES_CAPTURE_RUN=1` and",
        "`HERMES_CAPTURE_COMMAND` were not both provided, so capture-run was not executed.",
        "",
        "## Capture-run Status",
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
        "## Safety Status",
        "",
    ]
    for key, value in safety.items():
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
            f"- Executor called on deny: {trace['executor_called_on_deny']}",
            f"- Executor called on ask: {trace['executor_called_on_ask']}",
            "",
            "## Hook Readiness",
            "",
            "| Hook | Observed | Complete fields | Pre-execution | Enforcement-ready | Missing fields |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for hook, data in hook_readiness.items():
        missing = ", ".join(data.get("missing_fields", ())) or "none"
        lines.append(
            f"| {hook} | {data.get('observed', 'unknown')} | {data.get('complete_fields', 'unknown')} | "
            f"{data.get('pre_execution', 'unknown')} | {data.get('enforcement_ready', 'no')} | {missing} |"
        )
    lines.extend(
        [
            "",
            "## Go / No-Go",
            "",
            f"- Enforcement wrapper: {go_no_go['enforcement_wrapper']}.",
            f"- Real Hermes integration claim: {go_no_go['real_hermes_integration_claim']}.",
            f"- Real Hermes integration: {go_no_go['real_hermes_integration']}.",
            f"- Real capture trace collected: {go_no_go['real_capture_trace_collected']}.",
            f"- More runtime samples needed: {go_no_go['more_runtime_samples_needed']}.",
        ]
    )
    return "\n".join(lines) + "\n"


def count_jsonl_events(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def hash_command(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8")).hexdigest()


def _hook_to_runtime_name(hook: str) -> str:
    return {
        "tool_dispatcher": "tool_dispatcher_pre_call",
        "terminal": "terminal_backend_pre_exec",
        "mcp": "mcp_pre_transport",
        "memory": "memory_pre_write",
        "gateway": "gateway_messaging_pre_send",
        "delegation": "subagent_delegation_pre_dispatch",
        "scheduler": "scheduler_cron_pre_register",
        "middleware_rewrite": "skill_plugin_middleware_rewrite",
    }[hook]


def _ensure_dirs(root: Path) -> None:
    for path in (
        PREFLIGHT_DIR,
        TRACE_DIR,
        REPORTS_DIR,
        FIXTURE_DIR,
        PATCHES_DIR,
        CAPTURE_RUN_TRACES_DIR,
        CAPTURE_RUN_REPORTS_DIR,
    ):
        _path(root, path).mkdir(parents=True, exist_ok=True)


def _path(root: Path, path: Path) -> Path:
    try:
        rel = path.relative_to(ROOT)
        return root / rel
    except ValueError:
        if path.is_absolute():
            return path
        return root / path


def _resolve_capture_trace_path(root: Path, env_value: str) -> Path:
    if not env_value:
        return _path(root, CAPTURE_RUN_DEFAULT_TRACE_PATH)
    trace_path = Path(env_value)
    if trace_path.is_absolute():
        return trace_path
    return root / trace_path


if __name__ == "__main__":
    raise SystemExit(main())
