#!/usr/bin/env python3
"""User-facing CapProof MCP trace viewer.

This script reads JSONL traces produced by the standard CapProof MCP server.
It never calls Hermes or DeepSeek and redacts token-like strings before
displaying entries.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable

import run_real_hermes_foreground_mcp_demo as foreground


SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|api[_-]?key\s*[:=]\s*[^,\s\"']+|token\s*[:=]\s*[^,\s\"']+)", re.IGNORECASE)
DEFAULT_TRACE_PATH = foreground.TRACE_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="View CapProof MCP workflow traces.")
    parser.add_argument("--file", dest="trace_file", help="trace JSONL file to read")
    parser.add_argument("--latest", action="store_true", help="read the foreground Hermes CapProof MCP trace")
    parser.add_argument("--follow", action="store_true", help="follow the trace file like tail -f")
    parser.add_argument("--format", choices=("pretty", "json"), default="pretty", help="output format")
    parser.add_argument("--filter-verdict", choices=("ALLOW", "DENY", "ASK", "ERROR", "INFO"), help="only show this verdict")
    parser.add_argument("--filter-tool", help="only show this MCP tool name")
    parser.add_argument("--last", type=int, default=20, help="show the last N matching entries")
    args = parser.parse_args(argv)

    path = resolve_trace_path(args.trace_file, latest=args.latest)
    if args.follow:
        return follow_trace(path, args)
    entries, skipped = read_trace(path)
    entries = filter_entries(entries, verdict=args.filter_verdict, tool=args.filter_tool)
    if args.last > 0:
        entries = entries[-args.last :]
    write_entries(path=path, entries=entries, skipped=skipped, fmt=args.format)
    return 0


def resolve_trace_path(trace_file: str | None, *, latest: bool) -> Path:
    if trace_file:
        return Path(trace_file)
    return DEFAULT_TRACE_PATH


def read_trace(path: Path) -> tuple[list[dict[str, Any]], int]:
    if not path.exists():
        return [], 0
    entries: list[dict[str, Any]] = []
    skipped = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if isinstance(value, dict):
                entries.append(redact(value))
            else:
                skipped += 1
    return entries, skipped


def filter_entries(entries: Iterable[dict[str, Any]], *, verdict: str | None, tool: str | None) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        if verdict and entry_verdict(entry) != verdict:
            continue
        if tool and str(entry.get("tool_name", "")) != tool:
            continue
        filtered.append(entry)
    return filtered


def write_entries(*, path: Path, entries: list[dict[str, Any]], skipped: int, fmt: str) -> None:
    if fmt == "json":
        print(
            json.dumps(
                {
                    "trace_file": str(path),
                    "entry_count": len(entries),
                    "skipped_malformed_count": skipped,
                    "entries": entries,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    print(f"trace_file={path}")
    print(f"entry_count={len(entries)}")
    print(f"skipped_malformed_count={skipped}")
    for entry in entries:
        print(format_pretty(entry))


def format_pretty(entry: dict[str, Any]) -> str:
    mock_event = entry.get("mock_event") if isinstance(entry.get("mock_event"), dict) else {}
    sandbox_executed = bool(mock_event.get("executed"))
    sandbox_refused = bool(mock_event.get("sandbox_refused"))
    fields = [
        f"timestamp={format_timestamp(entry.get('timestamp'))}",
        f"user_task={entry.get('user_task', '') or ''}",
        f"mcp_method={entry.get('mcp_method', '')}",
        f"tool_name={entry.get('tool_name', '')}",
        f"verdict={entry_verdict(entry)}",
        f"reason={entry.get('reason', '') or 'none'}",
        f"proof_id={entry.get('proof_id') or 'none'}",
        f"executor_called={bool(entry.get('executor_called'))}",
        f"sandbox_executed={sandbox_executed}",
        f"sandbox_refused={sandbox_refused}",
        f"canonical_action_hash={entry.get('canonical_action_hash') or 'none'}",
    ]
    return " | ".join(fields)


def entry_verdict(entry: dict[str, Any]) -> str:
    return str(entry.get("capproof_verdict") or entry.get("verdict") or "")


def format_timestamp(value: Any) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(float(value)))
    except (TypeError, ValueError, OSError):
        return ""


def follow_trace(path: Path, args: argparse.Namespace) -> int:
    seen = 0
    try:
        while True:
            entries, skipped = read_trace(path)
            filtered = filter_entries(entries, verdict=args.filter_verdict, tool=args.filter_tool)
            new_entries = filtered[seen:]
            if new_entries:
                write_entries(path=path, entries=new_entries, skipped=skipped, fmt=args.format)
                seen = len(filtered)
            time.sleep(1.0)
    except KeyboardInterrupt:
        return 130


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return SECRET_RE.sub("[REDACTED]", value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if "key" in str(key).lower() or "token" in str(key).lower() or "secret" in str(key).lower():
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = redact(item)
        return redacted
    return value


if __name__ == "__main__":
    raise SystemExit(main())
