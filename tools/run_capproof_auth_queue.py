#!/usr/bin/env python3
"""Trusted local CLI for CapProof MCP ASK authorization requests."""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
import json
from pathlib import Path
import sys

from capproof.mcp.authorization_store import (
    AuthorizationStore,
    AuthorizationStoreError,
    default_authorization_paths,
    write_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage trusted local CapProof MCP ASK authorization queue.")
    parser.add_argument("--queue-dir", help="Override authorization queue directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List authorization requests.")

    show_parser = subparsers.add_parser("show", help="Show one authorization request.")
    show_parser.add_argument("request_id")

    approve_parser = subparsers.add_parser("approve", help="Approve a pending request with exact or narrower scope.")
    approve_parser.add_argument("request_id")
    approve_parser.add_argument("--scope-file", required=True)
    approve_parser.add_argument("--workspace", default="real_agent_integrations/hermes_mcp_server/sandbox_workspace")
    approve_parser.add_argument("--task-id", default="hermes_mcp_test")
    approve_parser.add_argument("--agent-id", default="hermes_agent")

    deny_parser = subparsers.add_parser("deny", help="Deny a pending request.")
    deny_parser.add_argument("request_id")
    deny_parser.add_argument("--reason", required=True)

    audit_parser = subparsers.add_parser("audit", help="Show audit events for one request.")
    audit_parser.add_argument("request_id")

    expire_parser = subparsers.add_parser("expire", help="Expire a pending request.")
    expire_parser.add_argument("request_id")

    subparsers.add_parser("doctor", help="Check queue health and write ASK reports.")

    args = parser.parse_args(argv)
    paths = default_authorization_paths()
    if args.queue_dir:
        queue_dir = Path(args.queue_dir).resolve(strict=False)
        paths = type(paths)(
            queue_dir=queue_dir,
            pending_path=queue_dir / "pending_authorizations.jsonl",
            receipts_path=queue_dir / "authorization_receipts.jsonl",
            audit_trace_path=paths.audit_trace_path,
            report_path=paths.report_path,
            summary_path=paths.summary_path,
        )
    store = AuthorizationStore(paths)

    try:
        if args.command == "list":
            return _print({"requests": [request.to_dict() for request in store.list_requests()]})
        if args.command == "show":
            return _print({"request": store.get_request(args.request_id).to_dict()})
        if args.command == "approve":
            scope = _read_scope(args.scope_file)
            receipt = store.approve(
                args.request_id,
                scope,
                workspace=args.workspace,
                task_id=args.task_id,
                agent_id=args.agent_id,
            )
            write_reports(store)
            return _print({"approved": True, "receipt": receipt.to_dict(), "capability_minted": True})
        if args.command == "deny":
            request = store.deny(args.request_id, reason=args.reason)
            write_reports(store)
            return _print({"denied": True, "request": request.to_dict(), "capability_minted": False})
        if args.command == "expire":
            request = store.expire(args.request_id)
            write_reports(store)
            return _print({"expired": True, "request": request.to_dict(), "capability_minted": False})
        if args.command == "audit":
            return _print({"events": _audit_events(store, args.request_id)})
        if args.command == "doctor":
            paths.audit_trace_path.parent.mkdir(parents=True, exist_ok=True)
            paths.audit_trace_path.touch(exist_ok=True)
            write_reports(store)
            summary = store.summary()
            summary["doctor_ok"] = True
            summary["report_path"] = str(paths.report_path)
            summary["summary_path"] = str(paths.summary_path)
            return _print(summary)
    except (AuthorizationStoreError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    return 2


def _read_scope(path: str) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AuthorizationStoreError("scope file must contain a JSON object")
    return value


def _audit_events(store: AuthorizationStore, request_id: str) -> list[dict[str, object]]:
    events = []
    for item in store._read_jsonl(store.paths.audit_trace_path):  # Product CLI diagnostic, not verifier logic.
        payload = item.get("payload", {})
        if not isinstance(payload, dict):
            continue
        if payload.get("request_id") == request_id:
            events.append(item)
            continue
        request = payload.get("request")
        if isinstance(request, dict) and request.get("request_id") == request_id:
            events.append(item)
            continue
        receipt = payload.get("receipt")
        if isinstance(receipt, dict) and receipt.get("request_id") == request_id:
            events.append(item)
    return events


def _print(payload: dict[str, object]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
