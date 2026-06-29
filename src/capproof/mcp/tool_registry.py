"""Tool registry for the CapProof MCP server."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from capproof.mcp.context import CapProofMCPContext
from capproof.mcp.schemas import MCPToolHandler, MCPToolSpec
from capproof.serialization import JsonObject


def default_tool_registry() -> dict[str, MCPToolHandler]:
    handlers = (
        _echo_summary(),
        _send_message_mock(),
        _read_workspace_file(),
        _write_workspace_file(),
        _run_command_template(),
        _get_trace(),
        _request_authorization(),
    )
    return {handler.spec.name: handler for handler in handlers}


def _echo_summary() -> MCPToolHandler:
    return MCPToolHandler(
        spec=MCPToolSpec(
            name="capproof.echo_summary",
            description="Echo an existing summary value through CapProof's mock transform path.",
            input_schema={
                "type": "object",
                "properties": {
                    "body_ref": {"type": "string", "default": "val_summary"},
                },
                "additionalProperties": False,
            },
            authority_bearing_fields=(),
            read_only=True,
        ),
        to_raw_event=lambda args, ctx: _raw_event(
            ctx,
            tool="summarize",
            trace_suffix="echo_summary",
            input_args={"input": str(args.get("body_ref", "val_summary"))},
        ),
    )


def _send_message_mock() -> MCPToolHandler:
    return MCPToolHandler(
        spec=MCPToolSpec(
            name="capproof.send_message_mock",
            description="Mock-send a message after CapProof verifies recipient authority.",
            input_schema={
                "type": "object",
                "required": ["recipient", "body_ref"],
                "properties": {
                    "recipient": {"type": "string"},
                    "body_ref": {"type": "string"},
                    "platform": {"type": "string"},
                    "channel": {"type": "string"},
                },
                "additionalProperties": False,
            },
            authority_bearing_fields=("recipient",),
            destructive=True,
        ),
        to_raw_event=lambda args, ctx: _raw_event(
            ctx,
            tool="send_message",
            trace_suffix="send_message_mock",
            input_args=_compact(
                {
                    "recipient": str(args.get("recipient", "")),
                    "body_ref": str(args.get("body_ref", "val_summary")),
                    "platform": args.get("platform"),
                    "channel": args.get("channel"),
                }
            ),
        ),
    )


def _read_workspace_file() -> MCPToolHandler:
    return MCPToolHandler(
        spec=MCPToolSpec(
            name="capproof.read_workspace_file",
            description="Read a workspace file through CapProof path authority checks; returns mock read metadata.",
            input_schema={
                "type": "object",
                "required": ["path"],
                "properties": {"path": {"type": "string"}},
                "additionalProperties": False,
            },
            authority_bearing_fields=("path",),
            read_only=True,
        ),
        to_raw_event=lambda args, ctx: _raw_event(
            ctx,
            tool="read_file",
            trace_suffix="read_workspace_file",
            input_args={"path": str(args.get("path", ""))},
        ),
    )


def _write_workspace_file() -> MCPToolHandler:
    return MCPToolHandler(
        spec=MCPToolSpec(
            name="capproof.write_workspace_file",
            description="Write a workspace file through CapProof path authority checks; executor is mock/local workspace only.",
            input_schema={
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "content_ref": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": False},
                    "mode": {"type": "string", "enum": ["create", "append", "overwrite"]},
                },
                "additionalProperties": False,
            },
            authority_bearing_fields=("path", "mode", "overwrite"),
            destructive=True,
        ),
        to_raw_event=lambda args, ctx: _raw_event(
            ctx,
            tool="write_file",
            trace_suffix="write_workspace_file",
            input_args=_compact(
                {
                    "path": str(args.get("path", "")),
                    "content": args.get("content", args.get("content_ref", "val_summary")),
                    "overwrite": bool(args.get("overwrite", False)),
                    "mode": args.get("mode"),
                }
            ),
        ),
    )


def _run_command_template() -> MCPToolHandler:
    return MCPToolHandler(
        spec=MCPToolSpec(
            name="capproof.run_command_template",
            description="Run an allowlisted command template through CapProof; raw shell strings are denied.",
            input_schema={
                "type": "object",
                "required": ["command_template"],
                "properties": {
                    "command_template": {"type": "string"},
                    "args": {"type": "object"},
                    "cwd": {"type": "string"},
                    "env": {"type": "object"},
                    "stdin": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
            authority_bearing_fields=("command_template", "args", "cwd", "env", "stdin"),
            destructive=True,
        ),
        to_raw_event=lambda args, ctx: _raw_event(
            ctx,
            tool="run_shell",
            trace_suffix="run_command_template",
            input_args={
                "command_template": str(args.get("command_template", "")),
                "args": dict(args.get("args", {})) if isinstance(args.get("args", {}), dict) else args.get("args"),
                "cwd": str(args.get("cwd", str(ctx.workspace))),
                "env": dict(args.get("env", {})) if isinstance(args.get("env", {}), dict) else {},
                "stdin": args.get("stdin"),
            },
        ),
    )


def _get_trace() -> MCPToolHandler:
    return MCPToolHandler(
        spec=MCPToolSpec(
            name="capproof.get_trace",
            description="Return recent user-visible CapProof MCP workflow trace entries.",
            input_schema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 200}},
                "additionalProperties": False,
            },
            read_only=True,
        ),
        admin_handler=lambda args, ctx: {"entries": ctx.trace_recorder.tail(int(args.get("limit", 50)))},
    )


def _request_authorization() -> MCPToolHandler:
    return MCPToolHandler(
        spec=MCPToolSpec(
            name="capproof.request_authorization",
            description="Create an authorization request record; this does not mint capability.",
            input_schema={
                "type": "object",
                "required": ["reason"],
                "properties": {
                    "reason": {"type": "string"},
                    "requested_tool": {"type": "string"},
                    "requested_scope": {"type": "object"},
                },
                "additionalProperties": False,
            },
            authority_bearing_fields=("requested_scope",),
        ),
        admin_handler=lambda args, _ctx: _authorization_request_payload(args),
    )


def _raw_event(ctx: CapProofMCPContext, *, tool: str, trace_suffix: str, input_args: JsonObject) -> JsonObject:
    return {
        "source": "hermes",
        "event_type": "tool_call",
        "tool": tool,
        "agent_id": ctx.agent_id,
        "task_id": ctx.task_id,
        "trace_id": f"mcp_{trace_suffix}",
        "input": input_args,
        "metadata": {
            "source_component": "capproof_mcp_server",
            "mcp_metadata_cannot_mint_capability": True,
        },
    }


def _compact(value: Mapping[str, Any]) -> JsonObject:
    return {key: item for key, item in value.items() if item is not None}


def _authorization_request_payload(args: Mapping[str, Any]) -> JsonObject:
    request = {
        "request_id": "pending_auth_request",
        "reason": str(args.get("reason", "")),
        "requested_tool": str(args.get("requested_tool", "")),
        "requested_scope": args.get("requested_scope", {}),
        "status": "pending",
    }
    return {
        "verdict": "ASK",
        "reason": "AuthorizationRequested",
        "capability_minted": False,
        "pending_authorization_request": request,
        "request": request,
    }
