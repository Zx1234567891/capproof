"""Standard MCP JSON-RPC server surface for CapProof tools."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from capproof.agent_adapter import GuardDecision
from capproof.mcp.context import CapProofMCPContext, make_default_context
from capproof.mcp.errors import MCPError, invalid_params, invalid_request, method_not_found, tool_not_found
from capproof.mcp.schemas import MCPToolHandler, MCPToolResult
from capproof.mcp.tool_registry import default_tool_registry
from capproof.mcp.trace import MCPTraceEntry, new_trace_id
from capproof.schemas import VerificationDecision
from capproof.serialization import JsonObject


class CapProofMCPServer:
    def __init__(
        self,
        *,
        context: CapProofMCPContext | None = None,
        tool_registry: Mapping[str, MCPToolHandler] | None = None,
    ) -> None:
        self.context = context or make_default_context()
        self.tool_registry = dict(tool_registry or default_tool_registry())
        self._trace_index = 0

    def initialize_result(self) -> JsonObject:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "capproof-mcp-server", "version": "0.1.0"},
            "capabilities": {"tools": {"listChanged": False}},
        }

    def list_tools(self) -> JsonObject:
        return {"tools": [handler.spec.to_mcp_tool() for handler in self.tool_registry.values()]}

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        mcp_metadata: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        handler = self.tool_registry.get(name)
        if handler is None:
            raise tool_not_found(name)
        args = dict(arguments or {})
        metadata = dict(mcp_metadata or {})
        if handler.admin_handler is not None:
            return self._handle_admin_tool(name, args, handler, mcp_metadata=metadata).to_mcp_result()
        if handler.to_raw_event is None:
            raise invalid_params(f"tool has no handler: {name}")
        raw_event = handler.to_raw_event(args, self.context)
        decision = self.context.middleware.guard(raw_event, self.context.runtime_state)
        execution = self.context.guarded_executor.execute_if_allowed(decision)
        entry = self._record_guarded_trace(
            tool_name=name,
            arguments=args,
            mcp_metadata=metadata,
            decision=decision,
            executor_called=execution.executed,
            mock_event=execution.mock_event,
        )
        structured = _structured_from_entry(entry, decision)
        content_text = _content_text(name=name, entry=entry)
        return MCPToolResult(
            content=[{"type": "text", "text": content_text}],
            structured_content=structured,
            is_error=decision.decision != VerificationDecision.ALLOW,
        ).to_mcp_result()

    def handle_json_rpc(self, request: Mapping[str, Any]) -> JsonObject | None:
        if not isinstance(request, Mapping):
            raise invalid_request()
        method = str(request.get("method", ""))
        request_id = request.get("id")
        params = request.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise invalid_params("params must be an object")
        if method == "notifications/initialized":
            return None
        try:
            if method == "initialize":
                result = self.initialize_result()
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = self.list_tools()
                self._record_tools_list_trace()
            elif method == "tools/call":
                name = str(params.get("name", ""))
                arguments = params.get("arguments", {})
                if not isinstance(arguments, dict):
                    raise invalid_params("tools/call arguments must be an object")
                metadata = _extract_mcp_metadata(params)
                result = self.call_tool(name, arguments, mcp_metadata=metadata)
            else:
                raise method_not_found(method)
        except MCPError as exc:
            return _json_rpc_error(request_id, exc)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _handle_admin_tool(
        self,
        name: str,
        arguments: JsonObject,
        handler: MCPToolHandler,
        *,
        mcp_metadata: JsonObject | None = None,
    ) -> MCPToolResult:
        payload = handler.admin_handler(arguments, self.context)
        verdict = str(payload.get("verdict", "ALLOW"))
        reason = str(payload.get("reason", ""))
        metadata = dict(mcp_metadata or {})
        self._trace_index += 1
        entry = MCPTraceEntry(
            trace_id=new_trace_id(method="tools/call", tool_name=name, arguments=arguments, index=self._trace_index),
            timestamp=__import__("time").time(),
            mcp_method="tools/call",
            tool_name=name,
            arguments=arguments,
            original_arguments=dict(arguments),
            canonical_action_hash=None,
            capproof_verdict=verdict,
            proof_id=None,
            reason=reason,
            executor_called=False,
            user_task=_extract_user_task(arguments, metadata),
            authority_bearing_fields=handler.spec.authority_bearing_fields,
            mcp_metadata=metadata,
            raw_mcp_request={
                "method": "tools/call",
                "tool_name": name,
                "arguments": arguments,
                "mcp_metadata": metadata,
            },
            canonical_action=None,
            mock_event=None,
        )
        self.context.trace_recorder.append(entry)
        structured = {
            "tool_name": name,
            "verdict": verdict,
            "reason": reason,
            "executor_called": False,
            "capability_minted": bool(payload.get("capability_minted", False)),
            "pending_authorization_request": payload.get("pending_authorization_request"),
            "trace": entry.to_dict(),
            "payload": payload,
            "metadata_cannot_mint_capability": True,
            "llm_output_cannot_allow_tool_call": True,
        }
        return MCPToolResult(
            content=[{"type": "text", "text": f"{name}: {verdict} {reason}".strip()}],
            structured_content=structured,
            is_error=verdict != "ALLOW",
        )

    def _record_guarded_trace(
        self,
        *,
        tool_name: str,
        arguments: JsonObject,
        mcp_metadata: JsonObject,
        decision: GuardDecision,
        executor_called: bool,
        mock_event: JsonObject | None,
    ) -> MCPTraceEntry:
        self._trace_index += 1
        reason = ""
        if decision.deny_reason is not None:
            reason = decision.deny_reason.value
        elif decision.failure_reason is not None:
            reason = decision.failure_reason.value
        elif decision.message:
            reason = decision.message
        proof_id = decision.proof.proof_id if decision.proof is not None else None
        action_hash = decision.canonical_call.action_hash if decision.canonical_call is not None else None
        canonical_tool = decision.canonical_call.tool_name if decision.canonical_call is not None else None
        authority_fields = decision.canonical_call.authority_bearing_fields if decision.canonical_call is not None else ()
        entry = MCPTraceEntry(
            trace_id=new_trace_id(method="tools/call", tool_name=tool_name, arguments=arguments, index=self._trace_index),
            timestamp=__import__("time").time(),
            mcp_method="tools/call",
            tool_name=tool_name,
            arguments=arguments,
            original_arguments=dict(arguments),
            canonical_action_hash=action_hash,
            capproof_verdict=decision.decision.value,
            proof_id=proof_id,
            reason=reason,
            executor_called=executor_called,
            user_task=_extract_user_task(arguments, mcp_metadata),
            canonical_tool=canonical_tool,
            authority_bearing_fields=authority_fields,
            mcp_metadata=mcp_metadata,
            raw_mcp_request={
                "method": "tools/call",
                "tool_name": tool_name,
                "arguments": arguments,
                "mcp_metadata": mcp_metadata,
            },
            canonical_action=decision.action.to_dict() if decision.action is not None else None,
            mock_event=mock_event,
        )
        self.context.trace_recorder.append(entry)
        return entry

    def _record_tools_list_trace(self) -> None:
        self._trace_index += 1
        entry = MCPTraceEntry(
            trace_id=new_trace_id(method="tools/list", tool_name="", arguments={}, index=self._trace_index),
            timestamp=__import__("time").time(),
            mcp_method="tools/list",
            tool_name="",
            arguments={},
            original_arguments={},
            canonical_action_hash=None,
            capproof_verdict="INFO",
            proof_id=None,
            reason="tools_list",
            executor_called=False,
            authority_bearing_fields=(),
            raw_mcp_request={"method": "tools/list"},
            canonical_action=None,
            mock_event=None,
        )
        self.context.trace_recorder.append(entry)


def _structured_from_entry(entry: MCPTraceEntry, decision: GuardDecision) -> JsonObject:
    return {
        "tool_name": entry.tool_name,
        "user_task": entry.user_task,
        "canonical_tool": entry.canonical_tool,
        "verdict": entry.capproof_verdict,
        "proof": {
            "proof_id": entry.proof_id,
            "canonical_action_hash": entry.canonical_action_hash,
        },
        "reason": entry.reason,
        "executor_called": entry.executor_called,
        "original_arguments": entry.original_arguments,
        "mcp_metadata": entry.mcp_metadata,
        "authority_bearing_fields": list(entry.authority_bearing_fields),
        "trace": entry.to_dict(),
        "metadata_cannot_mint_capability": True,
        "llm_output_cannot_allow_tool_call": True,
        "endorsement_challenge": decision.endorsement_challenge,
    }


def _content_text(*, name: str, entry: MCPTraceEntry) -> str:
    parts = [
        f"{name}",
        f"verdict={entry.capproof_verdict}",
        f"reason={entry.reason or 'none'}",
        f"executor_called={entry.executor_called}",
        f"action_hash={entry.canonical_action_hash or 'none'}",
        f"proof_id={entry.proof_id or 'none'}",
    ]
    return " | ".join(parts)


def _json_rpc_error(request_id: Any, exc: MCPError) -> JsonObject:
    return {"jsonrpc": "2.0", "id": request_id, "error": exc.to_json()}


def _extract_mcp_metadata(params: JsonObject) -> JsonObject:
    metadata: JsonObject = {}
    for key in ("_meta", "clientInfo", "clientCapabilities"):
        value = params.get(key)
        if isinstance(value, dict):
            metadata[key] = value
    return metadata


def _extract_user_task(arguments: JsonObject, metadata: JsonObject) -> str:
    for source in (arguments, metadata.get("_meta", {}) if isinstance(metadata.get("_meta"), dict) else {}):
        value = source.get("user_task") if isinstance(source, dict) else None
        if isinstance(value, str):
            return value
    return ""
