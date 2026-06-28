#!/usr/bin/env python3
"""Static adapter coverage audit for agent profile integrations.

This script reads local source trees only. It does not clone repositories,
install dependencies, run third-party build/test commands, execute agents,
or execute tools.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
AUDIT_DIR = ROOT / "agent_coverage_audit"

TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".rst",
    ".txt",
}

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "agent_coverage_audit",
    ".venv",
    "venv",
}

GENERIC_SURFACE_KEYWORDS = {
    "tool",
    "tools",
    "hook",
    "watcher",
    "approval",
    "permission",
    "allow",
    "deny",
    "workflow",
}

ACTION_KEYWORDS = {
    "shell": ("shell", "exec", "subprocess", "terminal", "command", "stdin"),
    "file_write": ("write_file", "writefile", "write file", "overwrite", "patch", "diff", "edit"),
    "file_read": ("read_file", "readfile", "read file"),
    "network": ("http", "fetch", "url", "endpoint", "mcp", "request", "redirect"),
    "email_messaging": ("email", "message", "gateway", "recipient", "chat_id", "telegram"),
    "memory": ("memory", "remember", "persistence", "authority_claims"),
    "skill_plugin": ("skill", "plugin", "workflow step", "metadata"),
    "delegation": ("delegate", "delegation", "subagent", "parent_agent", "child_agent"),
    "scheduled": ("schedule", "scheduled", "cron", "recurrence"),
}

FIELDS_BY_KIND = {
    "shell": ("command", "args", "cwd", "env", "stdin", "terminal_backend"),
    "file_write": ("path", "mode", "overwrite", "diff", "patch", "symlink_policy", "workspace_root"),
    "file_read": ("path", "symlink_policy", "workspace_root"),
    "network": ("url", "host", "method", "headers", "body", "follow_redirects", "mcp_server", "tool_name"),
    "email_messaging": ("recipient", "channel", "platform", "chat_id", "body", "attachment", "headers"),
    "memory": ("content", "origin", "persistence", "authority_claims", "scope"),
    "skill_plugin": ("skill_id", "plugin_id", "tool_invoked", "metadata", "workflow_step", "external_endpoint"),
    "delegation": ("parent_agent", "child_agent", "delegated_scope", "requested_action", "task_id", "redelegation_flag"),
    "scheduled": ("schedule_id", "action", "recipient", "endpoint", "command", "recurrence", "task_binding"),
    "unknown": ("raw_event", "metadata", "tool_name"),
}

CANONICALIZATION_BY_KIND = {
    "shell": "template membership; command/args/cwd/env/stdin normalization",
    "file_write": "workspace-root path canonicalization; traversal/symlink fail closed",
    "file_read": "workspace-root path canonicalization; traversal/symlink fail closed",
    "network": "URL canonicalization; host/scheme/redirect/header policy",
    "email_messaging": "recipient/channel/header/attachment canonicalization",
    "memory": "authority stripping; persistence and origin labeling",
    "skill_plugin": "metadata untrusted; tool and endpoint extraction",
    "delegation": "certificate verification; attenuation and task/agent binding",
    "scheduled": "task/schedule binding; stale capability replay prevention",
    "unknown": "adapter coverage audit required before allow",
}

ROLE_BY_KIND = {
    "shell": "command + file_path + credential + content",
    "file_write": "file_path + command + content",
    "file_read": "file_path",
    "network": "external_endpoint + credential + content",
    "email_messaging": "recipient + file_path + credential + content",
    "memory": "content only; authority stripped",
    "skill_plugin": "control + external_endpoint + command + file_path",
    "delegation": "control + delegated capability scope",
    "scheduled": "control + task/schedule-bound authority",
    "unknown": "unknown; deny until modeled",
}


@dataclass(frozen=True)
class RepoStatus:
    target_project: str
    repo_path: str
    status: str
    files_scanned: int
    notes: str


@dataclass(frozen=True)
class CoverageRow:
    target_project: str
    source_file: str
    event_or_tool_surface: str
    action_kind: str
    possible_tool_name: str
    authority_bearing_fields: tuple[str, ...]
    observed_by_current_profile: str
    canonicalization_needed: str
    likely_hook_point: str
    suggested_capproof_role: str
    suggested_contract_update: str
    adapter_coverage_gap: bool
    residual_risk: str
    recommended_test_case: str
    confidence: str


EXPECTED_SURFACES: dict[str, tuple[dict[str, Any], ...]] = {
    "opencode": (
        {
            "surface": "terminal shell command proposal",
            "kind": "shell",
            "tool": "run_shell",
            "coverage": "yes",
            "hook": "terminal wrapper / tool-use event",
            "gap": False,
            "risk": "arbitrary shell if raw command bypasses template adapter",
            "test": "OpenCode build mode pytest allow; sh-c pipe redirect deny",
            "confidence": "medium",
        },
        {
            "surface": "file write/edit proposal",
            "kind": "file_write",
            "tool": "write_file",
            "coverage": "partial",
            "hook": "filesystem hook / tool-use event",
            "gap": True,
            "risk": "diff/patch/symlink metadata may be missing from mock profile",
            "test": "write_file path/overwrite/diff/symlink policy coverage",
            "confidence": "medium",
        },
        {
            "surface": "AGENTS.md / config / policy modification",
            "kind": "file_write",
            "tool": "write_file",
            "coverage": "partial",
            "hook": "filesystem hook before write",
            "gap": True,
            "risk": "future agent behavior can be changed by config/policy writes",
            "test": "AGENTS.md write requires explicit high-impact file capability",
            "confidence": "medium",
        },
        {
            "surface": "plan mode proposed action",
            "kind": "unknown",
            "tool": "proposed_action",
            "coverage": "partial",
            "hook": "agent event stream",
            "gap": True,
            "risk": "plan/build boundary may be framework-specific",
            "test": "plan mode never executes and produces proposed action only",
            "confidence": "low",
        },
    ),
    "openclaw": (
        {
            "surface": "legacy tool invocation",
            "kind": "unknown",
            "tool": "tool_call",
            "coverage": "partial",
            "hook": "compatibility wrapper",
            "gap": True,
            "risk": "legacy payload may hide tool-specific authority fields",
            "test": "unknown OpenClaw tool surface is denied until modeled",
            "confidence": "low",
        },
        {
            "surface": "watcher observed action",
            "kind": "skill_plugin",
            "tool": "watcher_event",
            "coverage": "partial",
            "hook": "watcher wrapper",
            "gap": True,
            "risk": "watcher observations must not become authorization roots",
            "test": "watcher can deny or ask but cannot mint capability",
            "confidence": "medium",
        },
        {
            "surface": "skill/plugin external endpoint action",
            "kind": "network",
            "tool": "http_post",
            "coverage": "yes",
            "hook": "skill/plugin tool wrapper",
            "gap": False,
            "risk": "metadata-driven endpoint exfiltration",
            "test": "skill http_post unauthorized endpoint denies NoCap",
            "confidence": "medium",
        },
        {
            "surface": "skill/plugin shell proposal",
            "kind": "shell",
            "tool": "run_shell",
            "coverage": "yes",
            "hook": "shell wrapper",
            "gap": False,
            "risk": "plugin workflow can hide shell exfiltration",
            "test": "plugin run_shell sh-c denied",
            "confidence": "medium",
        },
    ),
    "hermes": (
        {
            "surface": "tool invocation",
            "kind": "email_messaging",
            "tool": "send_email",
            "coverage": "yes",
            "hook": "tool wrapper",
            "gap": False,
            "risk": "unauthorized recipient or attachment egress",
            "test": "Hermes send_email Alice allow, attacker deny",
            "confidence": "medium",
        },
        {
            "surface": "skill action external endpoint",
            "kind": "network",
            "tool": "http_post",
            "coverage": "yes",
            "hook": "skill tool wrapper",
            "gap": False,
            "risk": "skill metadata exfiltration endpoint",
            "test": "Hermes skill http_post unauthorized endpoint deny",
            "confidence": "medium",
        },
        {
            "surface": "MCP tool call",
            "kind": "network",
            "tool": "http_post",
            "coverage": "partial",
            "hook": "MCP proxy",
            "gap": True,
            "risk": "server/tool metadata can select endpoint or hidden action",
            "test": "MCP server/tool/url/method/header field coverage",
            "confidence": "medium",
        },
        {
            "surface": "terminal backend shell action",
            "kind": "shell",
            "tool": "run_shell",
            "coverage": "yes",
            "hook": "terminal backend wrapper",
            "gap": False,
            "risk": "backend may accept arbitrary shell strings",
            "test": "terminal sh-c and stdin injection deny",
            "confidence": "medium",
        },
        {
            "surface": "memory write",
            "kind": "memory",
            "tool": "memory_write",
            "coverage": "partial",
            "hook": "memory backend wrapper",
            "gap": True,
            "risk": "persistent authority laundering through memory",
            "test": "authority_claims stripped and persistence scoped",
            "confidence": "medium",
        },
        {
            "surface": "subagent delegation",
            "kind": "delegation",
            "tool": "send_email",
            "coverage": "partial",
            "hook": "subagent/delegation gateway",
            "gap": True,
            "risk": "delegation amplification or missing certificate",
            "test": "delegation missing and amplification denied",
            "confidence": "medium",
        },
        {
            "surface": "gateway messaging action",
            "kind": "email_messaging",
            "tool": "send_message",
            "coverage": "partial",
            "hook": "gateway proxy",
            "gap": True,
            "risk": "platform/chat_id recipient ambiguity",
            "test": "gateway recipient/chat_id/channel field coverage",
            "confidence": "medium",
        },
        {
            "surface": "scheduled automation action",
            "kind": "scheduled",
            "tool": "send_email",
            "coverage": "partial",
            "hook": "scheduler wrapper",
            "gap": True,
            "risk": "stale capability replay or persistent task authority",
            "test": "scheduled action bound to schedule_id/task_id/cap scope",
            "confidence": "medium",
        },
    ),
    "harness": (
        {
            "surface": "kill-test action event",
            "kind": "unknown",
            "tool": "kill_test_action",
            "coverage": "yes",
            "hook": "HarnessAdapter before guard",
            "gap": False,
            "risk": "future AuthLaunderBench schema drift",
            "test": "attack and benign harness events use same guard flow",
            "confidence": "high",
        },
        {
            "surface": "observable oracle side-effect log",
            "kind": "unknown",
            "tool": "oracle",
            "coverage": "yes",
            "hook": "task-local oracle",
            "gap": False,
            "risk": "oracle must not depend on CapProof proof language",
            "test": "oracle checks observable unsafe/safe side effects only",
            "confidence": "high",
        },
    ),
}


def run_audit(
    *,
    root: Path = ROOT,
    output_dir: Path | None = None,
    opencode_repo: Path | None = None,
    openclaw_repo: Path | None = None,
    hermes_repo: Path | None = None,
) -> dict[str, Any]:
    out = output_dir or root / "agent_coverage_audit"
    out.mkdir(parents=True, exist_ok=True)
    repo_inputs = {
        "opencode": _resolve_repo("OPENCODE_REPO", opencode_repo, root / "external" / "opencode"),
        "openclaw": _resolve_repo("OPENCLAW_REPO", openclaw_repo, root / "external" / "openclaw"),
        "hermes": _resolve_repo("HERMES_REPO", hermes_repo, root / "external" / "hermes-agent"),
        "harness": root,
    }

    statuses: dict[str, RepoStatus] = {}
    rows: list[CoverageRow] = []
    for project, repo_path in repo_inputs.items():
        status, project_rows = audit_project(project, repo_path, root=root)
        statuses[project] = status
        rows.extend(project_rows)

    payload = {
        "repo_status": {project: asdict(status) for project, status in statuses.items()},
        "coverage_matrix": [serialize_row(row) for row in rows],
        "summary": summarize(rows, statuses),
        "safety": {
            "static_only": True,
            "third_party_commands_executed": False,
            "real_agents_executed": False,
            "real_tools_executed": False,
            "network_used": False,
        },
    }
    write_reports(out, payload)
    return payload


def audit_project(project: str, repo_path: Path, *, root: Path) -> tuple[RepoStatus, list[CoverageRow]]:
    expected_rows = [
        row_from_expected(project, item, repo_path)
        for item in EXPECTED_SURFACES[project]
    ]
    if project != "harness" and not repo_path.exists():
        return (
            RepoStatus(
                target_project=project,
                repo_path=str(repo_path),
                status="repo_missing",
                files_scanned=0,
                notes="repo not available; audit requires local checkout",
            ),
            expected_rows,
        )
    files = list(harness_candidate_files(root) if project == "harness" else candidate_files(repo_path))
    scanned_rows = scan_files(project, repo_path, files)
    if project == "harness":
        scanned_rows.extend(harness_rows(root))
    status = RepoStatus(
        target_project=project,
        repo_path=str(repo_path),
        status="available",
        files_scanned=len(files),
        notes="static read-only scan completed",
    )
    return status, dedupe_rows((*expected_rows, *scanned_rows))


def candidate_files(repo_path: Path) -> tuple[Path, ...]:
    if repo_path.is_file():
        return (repo_path,) if is_candidate_file(repo_path) else ()
    files: list[Path] = []
    for path in repo_path.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and is_candidate_file(path):
            files.append(path)
    return tuple(sorted(files)[:2500])


def harness_candidate_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in (root / "run_kill_tests.py", root / "tests" / "test_agent_profile_adapters.py"):
        if path.exists():
            files.append(path)
    kill_tests = root / "kill_tests"
    if kill_tests.exists():
        for path in kill_tests.rglob("*"):
            if path.is_file() and is_candidate_file(path):
                files.append(path)
    return tuple(sorted(files))


def is_candidate_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return path.name.lower() in {"readme", "license", "makefile", "dockerfile"}


def scan_files(project: str, repo_path: Path, files: tuple[Path, ...]) -> list[CoverageRow]:
    rows: list[CoverageRow] = []
    for path in files:
        text = read_text(path)
        if not text:
            continue
        lower = text.lower()
        matched = [
            kind
            for kind, keywords in ACTION_KEYWORDS.items()
            if any(keyword in lower for keyword in keywords)
        ]
        rel = relative_path(path, repo_path)
        for kind in matched:
            rows.append(row_from_scan(project, rel, kind))
        if has_unknown_surface(lower, matched):
            rows.append(row_from_scan(project, rel, "unknown"))
    return rows


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:500_000]
    except OSError:
        return ""


def has_unknown_surface(text: str, matched: list[str]) -> bool:
    if "unknown_surface" in text or "dynamic_tool" in text:
        return True
    if matched:
        return False
    return any(keyword in text for keyword in GENERIC_SURFACE_KEYWORDS)


def row_from_expected(project: str, item: dict[str, Any], repo_path: Path) -> CoverageRow:
    kind = str(item["kind"])
    repo_missing = project != "harness" and not repo_path.exists()
    return CoverageRow(
        target_project=project,
        source_file="repo_missing" if repo_missing else "expected_profile_surface",
        event_or_tool_surface=str(item["surface"]),
        action_kind=kind,
        possible_tool_name=str(item["tool"]),
        authority_bearing_fields=FIELDS_BY_KIND[kind],
        observed_by_current_profile=str(item["coverage"]),
        canonicalization_needed=CANONICALIZATION_BY_KIND[kind],
        likely_hook_point=str(item["hook"]),
        suggested_capproof_role=ROLE_BY_KIND[kind],
        suggested_contract_update=suggested_contract_update(kind, bool(item["gap"])),
        adapter_coverage_gap=bool(item["gap"]),
        residual_risk=str(item["risk"]),
        recommended_test_case=str(item["test"]),
        confidence="low" if repo_missing else str(item["confidence"]),
    )


def row_from_scan(project: str, source_file: str, kind: str) -> CoverageRow:
    coverage, gap = infer_current_coverage(project, kind)
    tool = infer_tool_name(kind)
    return CoverageRow(
        target_project=project,
        source_file=source_file,
        event_or_tool_surface=f"static keyword surface: {kind}",
        action_kind=kind,
        possible_tool_name=tool,
        authority_bearing_fields=FIELDS_BY_KIND[kind],
        observed_by_current_profile=coverage,
        canonicalization_needed=CANONICALIZATION_BY_KIND[kind],
        likely_hook_point=infer_hook_point(project, kind),
        suggested_capproof_role=ROLE_BY_KIND[kind],
        suggested_contract_update=suggested_contract_update(kind, gap),
        adapter_coverage_gap=gap,
        residual_risk=infer_residual_risk(kind),
        recommended_test_case=infer_test_case(project, kind),
        confidence="low",
    )


def harness_rows(root: Path) -> list[CoverageRow]:
    rows: list[CoverageRow] = []
    kill_tests = root / "kill_tests"
    if kill_tests.exists():
        rows.append(
            CoverageRow(
                target_project="harness",
                source_file="kill_tests/",
                event_or_tool_surface="12 kill tasks with benign/attack counterparts",
                action_kind="unknown",
                possible_tool_name="HarnessAdapter",
                authority_bearing_fields=FIELDS_BY_KIND["unknown"],
                observed_by_current_profile="yes",
                canonicalization_needed="event schema must preserve tool, input, mode, task_id, agent_id",
                likely_hook_point="run_kill_tests.py action construction",
                suggested_capproof_role="harness event wrapper",
                suggested_contract_update="Use HarnessAdapter event schema for future AuthLaunderBench inputs",
                adapter_coverage_gap=False,
                residual_risk="future tasks may introduce new tool surfaces",
                recommended_test_case="all kill_tests can be emitted as HarnessAdapter events",
                confidence="high",
            )
        )
    return rows


def infer_current_coverage(project: str, kind: str) -> tuple[str, bool]:
    if kind == "unknown":
        return "no", True
    coverage_map = {
        "opencode": {"shell": "yes", "file_write": "partial", "file_read": "no"},
        "openclaw": {"shell": "yes", "network": "yes", "skill_plugin": "partial", "file_write": "partial"},
        "hermes": {
            "shell": "yes",
            "network": "partial",
            "email_messaging": "partial",
            "memory": "partial",
            "skill_plugin": "partial",
            "delegation": "partial",
            "scheduled": "partial",
            "file_write": "partial",
        },
        "harness": {"shell": "yes", "file_write": "yes", "network": "yes", "email_messaging": "yes"},
    }
    coverage = coverage_map.get(project, {}).get(kind, "unknown")
    return coverage, coverage in {"no", "partial", "unknown"}


def infer_tool_name(kind: str) -> str:
    return {
        "shell": "run_shell",
        "file_write": "write_file",
        "file_read": "read_file",
        "network": "http_post",
        "email_messaging": "send_email/send_message",
        "memory": "memory_write",
        "skill_plugin": "skill_action",
        "delegation": "delegation",
        "scheduled": "scheduled_action",
        "unknown": "unknown",
    }[kind]


def infer_hook_point(project: str, kind: str) -> str:
    if kind == "shell":
        return "terminal/shell wrapper"
    if kind in {"network", "skill_plugin"}:
        return "tool wrapper / MCP proxy"
    if kind in {"file_write", "file_read"}:
        return "filesystem hook / tool wrapper"
    if kind == "memory":
        return "memory backend wrapper"
    if kind == "delegation":
        return "subagent delegation gateway"
    if kind == "scheduled":
        return "scheduler wrapper"
    if kind == "email_messaging":
        return "gateway/email tool wrapper"
    return f"{project} adapter coverage audit"


def infer_residual_risk(kind: str) -> str:
    return {
        "shell": "arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection",
        "file_write": "path traversal, symlink escape, config/policy/credential writes",
        "file_read": "secret file read, traversal, symlink escape",
        "network": "unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint",
        "email_messaging": "unauthorized recipient, hidden route, gateway exfiltration",
        "memory": "persistent authority laundering and policy memory poisoning",
        "skill_plugin": "workflow laundering and plugin metadata authority injection",
        "delegation": "delegation amplification and cross-agent replay",
        "scheduled": "stale capability replay and persistent scheduled exfiltration",
        "unknown": "unmodeled authority-bearing fields may be missed",
    }[kind]


def infer_test_case(project: str, kind: str) -> str:
    return f"{project} {kind} profile adapter field coverage and fail-closed test"


def suggested_contract_update(kind: str, gap: bool) -> str:
    if not gap:
        return "No profile contract update required before dry-run; keep audit tests."
    return f"Add/verify real adapter coverage for {', '.join(FIELDS_BY_KIND[kind])}."


def dedupe_rows(rows: tuple[CoverageRow, ...]) -> list[CoverageRow]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[CoverageRow] = []
    for row in rows:
        key = (row.target_project, row.source_file, row.event_or_tool_surface, row.action_kind)
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def serialize_row(row: CoverageRow) -> dict[str, Any]:
    data = asdict(row)
    data["authority_bearing_fields"] = list(row.authority_bearing_fields)
    return data


def summarize(rows: list[CoverageRow], statuses: dict[str, RepoStatus]) -> dict[str, Any]:
    total = len(rows)
    high_impact = sum(1 for row in rows if row.action_kind != "unknown")
    coverage = Counter(row.observed_by_current_profile for row in rows)
    gaps = [row for row in rows if row.adapter_coverage_gap]
    by_project = defaultdict(Counter)
    for row in rows:
        by_project[row.target_project][row.observed_by_current_profile] += 1
    return {
        "total_surfaces_scanned": total,
        "high_impact_surfaces_found": high_impact,
        "covered_by_current_profile": coverage["yes"],
        "partial_coverage": coverage["partial"],
        "uncovered_surfaces": coverage["no"] + coverage["unknown"],
        "coverage_gap_count": len(gaps),
        "repo_missing_count": sum(1 for status in statuses.values() if status.status == "repo_missing"),
        "top_coverage_gaps": [
            {
                "project": row.target_project,
                "surface": row.event_or_tool_surface,
                "gap": row.residual_risk,
                "recommended_test_case": row.recommended_test_case,
            }
            for row in gaps[:10]
        ],
        "by_project": {project: dict(counter) for project, counter in sorted(by_project.items())},
    }


def write_reports(out: Path, payload: dict[str, Any]) -> None:
    (out / "coverage_matrix.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    rows = [CoverageRow(**{**row, "authority_bearing_fields": tuple(row["authority_bearing_fields"])}) for row in payload["coverage_matrix"]]
    statuses = {
        project: RepoStatus(**status)
        for project, status in payload["repo_status"].items()
    }
    (out / "coverage_matrix.md").write_text(render_matrix_md(rows), encoding="utf-8")
    for project in ("opencode", "openclaw", "hermes", "harness"):
        (out / f"{project}_audit.md").write_text(
            render_project_md(project, statuses[project], [row for row in rows if row.target_project == project]),
            encoding="utf-8",
        )
    (out / "audit_summary.md").write_text(
        render_summary_md(payload["summary"], statuses, rows),
        encoding="utf-8",
    )


def render_matrix_md(rows: list[CoverageRow]) -> str:
    lines = [
        "# Agent Coverage Matrix",
        "",
        "| project | source/status | surface | fields | current adapter coverage | gap | recommended fix | priority | confidence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        priority = "high" if row.adapter_coverage_gap and row.action_kind != "unknown" else "medium" if row.adapter_coverage_gap else "low"
        lines.append(
            "| {project} | {source} | {surface} | {fields} | {coverage} | {gap} | {fix} | {priority} | {confidence} |".format(
                project=row.target_project,
                source=_md(row.source_file),
                surface=_md(row.event_or_tool_surface),
                fields=_md(", ".join(row.authority_bearing_fields)),
                coverage=row.observed_by_current_profile,
                gap="yes" if row.adapter_coverage_gap else "no",
                fix=_md(row.suggested_contract_update),
                priority=priority,
                confidence=row.confidence,
            )
        )
    return "\n".join(lines) + "\n"


def render_project_md(project: str, status: RepoStatus, rows: list[CoverageRow]) -> str:
    title = {
        "opencode": "OpenCode Audit",
        "openclaw": "OpenClaw Audit",
        "hermes": "Hermes Agent Audit",
        "harness": "CapProof Harness Audit",
    }[project]
    lines = [
        f"# {title}",
        "",
        f"- Repo status: `{status.status}`",
        f"- Repo path: `{status.repo_path}`",
        f"- Files scanned: {status.files_scanned}",
        f"- Notes: {status.notes}",
        "",
        "## Required Questions",
        "",
        *required_answers(project, status),
        "",
        "## Surfaces",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row.event_or_tool_surface}",
                "",
                f"- Source file: `{row.source_file}`",
                f"- Action kind: `{row.action_kind}`",
                f"- Possible tool: `{row.possible_tool_name}`",
                f"- Authority-bearing fields: {', '.join(row.authority_bearing_fields)}",
                f"- Current profile coverage: `{row.observed_by_current_profile}`",
                f"- Adapter coverage gap: {'yes' if row.adapter_coverage_gap else 'no'}",
                f"- Likely hook point: {row.likely_hook_point}",
                f"- Residual risk: {row.residual_risk}",
                f"- Recommended test case: {row.recommended_test_case}",
                f"- Confidence: `{row.confidence}`",
                "",
            ]
        )
    return "\n".join(lines)


def required_answers(project: str, status: RepoStatus) -> list[str]:
    missing = status.status == "repo_missing"
    missing_note = " Repo is missing, so this is a placeholder based on the Stage 17 mock profile." if missing else ""
    if project == "opencode":
        return [
            f"- Shell, file write/edit, and config/policy write surfaces are high-impact.{missing_note}",
            "- CLI wrapper, terminal wrapper, filesystem hook, MCP proxy, and tool-use event streams are candidate hook points.",
            "- AGENTS.md / config modifications can change future agent behavior and should be high-impact writes.",
            "- Plan mode should produce proposed actions only; build mode may enter guard.",
            "- Current gaps: real diff/patch metadata, symlink policy, config taxonomy, and exact plan/build event semantics.",
            "- Required tests: raw shell denial, config write cap, path traversal/symlink, diff/patch field coverage.",
        ]
    if project == "openclaw":
        return [
            f"- Watcher, skill, plugin, shell, file, and network surfaces need interception.{missing_note}",
            "- Watcher observations may trigger deny/ask but must not mint authority.",
            "- Skill/plugin metadata can introduce endpoint, shell, or file-write laundering risks.",
            "- Current gaps: legacy payload variants, plugin workflow step schema, hidden endpoint/header fields.",
            "- Compatibility and migration scenarios likely need an independent wrapper.",
            "- Required tests: watcher no-mint, skill endpoint cap, plugin shell denial, legacy unknown surface fail-closed.",
        ]
    if project == "hermes":
        return [
            f"- Tools, skills, MCP, memory, gateway, subagent, terminal backend, and scheduled actions are high-impact surfaces.{missing_note}",
            "- Memory has persistent authority laundering risk and must be stripped by default.",
            "- Subagent delegation requires Delegation Certificate evidence and attenuation.",
            "- Gateway recipients map to recipient authority; platform/chat_id semantics need explicit canonicalization.",
            "- MCP calls must map server/tool/url/method/headers/body into endpoint and content authority.",
            "- Terminal backend should be intercepted by a template-only wrapper.",
            "- Current gaps: gateway recipient taxonomy, MCP header/method/follow_redirects, schedule recurrence and replay scope.",
            "- Required tests: MCP field coverage, gateway chat_id, memory persistence, delegation amplification, scheduled replay.",
        ]
    return [
        "- Current kill_tests and run_kill_tests.py can be expressed as HarnessAdapter events for send/write/http scenarios.",
        "- Benign and attack modes should continue to share one guard flow.",
        "- Oracles are observable side-effect checks and should not depend on proof language.",
        "- HarnessAdapter does not bypass Reference Monitor; fake proof metadata remains ignored.",
        "- Future AuthLaunderBench inputs should use the HarnessAdapter event schema.",
    ]


def render_summary_md(
    summary: dict[str, Any],
    statuses: dict[str, RepoStatus],
    rows: list[CoverageRow],
) -> str:
    lines = [
        "# Agent Coverage Audit Summary",
        "",
        "Stage 18 is a static, read-only adapter coverage audit, not a real Agent integration stage.",
        "It does not run OpenCode, OpenClaw, Hermes, third-party project commands, agents, tools, email, network clients, or shell commands.",
        "It does not clone, build, install, or test third-party projects.",
        "When OpenCode, OpenClaw, or Hermes source checkouts are missing, their sections are placeholder / planned audits, not complete real-source audits.",
        "Coverage gaps in this report are a pre-integration risk inventory, not final vulnerability conclusions.",
        "",
        "## Repo Availability",
        "",
    ]
    for project, status in statuses.items():
        lines.append(f"- {project}: `{status.status}` at `{status.repo_path}`; files scanned: {status.files_scanned}")
    lines.extend(
        [
            "",
            "## Static Scan Scope",
            "",
            "- File types: `.py`, `.ts`, `.js`, `.json`, `.yaml`, `.yml`, `.toml`, README/docs/config text.",
            "- Keywords: tool, command, shell, exec, terminal, write_file, read_file, memory, mcp, skill, plugin, gateway, message, delegate, subagent, schedule, cron, hook, watcher, approval, permission, allow, deny.",
            "- Missing third-party repos are reported as `repo_missing`; no clone or network fetch is attempted.",
            "",
            "## Coverage Summary",
            "",
            f"- Total surfaces scanned: {summary['total_surfaces_scanned']}",
            f"- High-impact surfaces found: {summary['high_impact_surfaces_found']}",
            f"- Covered by current profile: {summary['covered_by_current_profile']}",
            f"- Partial coverage: {summary['partial_coverage']}",
            f"- Uncovered surfaces: {summary['uncovered_surfaces']}",
            f"- Coverage gap count: {summary['coverage_gap_count']}",
            "",
            "## Top Adapter Coverage Gaps",
            "",
        ]
    )
    for gap in summary["top_coverage_gaps"]:
        lines.append(f"- {gap['project']} / {gap['surface']}: {gap['gap']} -> {gap['recommended_test_case']}")
    lines.extend(
        [
            "",
            "## Recommended Integration Order",
            "",
            "1. HarnessAdapter schema hardening for future AuthLaunderBench inputs.",
            "2. OpenCode dry-run shell/file wrapper, because shell and filesystem surfaces are already modeled.",
            "3. Hermes MCP/gateway/memory/delegation dry-run wrappers after field coverage tests are expanded.",
            "4. OpenClaw compatibility wrapper once local source or event logs are available.",
            "",
            "## Go / No-Go",
            "",
            "- OpenCode dry-run wrapper: go only for mock/dry-run; no real execution until diff/patch/config field coverage is audited.",
            "- Hermes dry-run wrapper: partial go; MCP/gateway/schedule fields need more tests first.",
            "- OpenClaw compatibility wrapper: no-go for claims if repo is missing; go for placeholder compatibility tests only.",
            "- Blocking coverage gap: no single blocker for mock dry-run wrappers; real integration needs local source audits and adapter coverage tests.",
        ]
    )
    return "\n".join(lines) + "\n"


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _resolve_repo(env_name: str, arg_path: Path | None, default_path: Path) -> Path:
    if arg_path is not None:
        return arg_path
    env_value = os.environ.get(env_name)
    if env_value:
        return Path(env_value)
    return default_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opencode-repo", type=Path)
    parser.add_argument("--openclaw-repo", type=Path)
    parser.add_argument("--hermes-repo", type=Path)
    parser.add_argument("--output-dir", type=Path, default=AUDIT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = run_audit(
        output_dir=args.output_dir,
        opencode_repo=args.opencode_repo,
        openclaw_repo=args.openclaw_repo,
        hermes_repo=args.hermes_repo,
    )
    summary = payload["summary"]
    print("agent coverage audit complete")
    for project, status in payload["repo_status"].items():
        print(f"{project}: {status['status']} files_scanned={status['files_scanned']}")
    print(f"total_surfaces_scanned: {summary['total_surfaces_scanned']}")
    print(f"coverage_gap_count: {summary['coverage_gap_count']}")
    print(f"report: {args.output_dir / 'audit_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
