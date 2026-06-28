"""Capture-only Hermes hook wrappers.

These wrappers model where a future Hermes integration would record runtime
events. They only construct ``HermesRuntimeEvent`` values. They do not import
Hermes, run Hermes, call CapProof guard, execute tools, use subprocesses, or
perform network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from capproof.hermes_capture import HermesCaptureMode, HermesHookPoint, HermesRuntimeEvent
from capproof.schemas import JsonObject, JsonValue
from capproof.serialization import stable_hash

DEFAULT_SESSION_ID = "s_capture"
DEFAULT_TASK_ID = "task_1"
DEFAULT_AGENT_ID = "agent_main"
DEFAULT_TIMESTAMP = "2026-06-29T00:00:00Z"
DEFAULT_PROVENANCE = "capture_only_fixture"


@dataclass(frozen=True)
class _CaptureBase:
    session_id: str = DEFAULT_SESSION_ID
    task_id: str = DEFAULT_TASK_ID
    agent_id: str = DEFAULT_AGENT_ID
    timestamp: str = DEFAULT_TIMESTAMP
    provenance_hint: str = DEFAULT_PROVENANCE
    metadata: JsonObject = field(default_factory=dict)

    def _runtime_event(
        self,
        *,
        hook_point: HermesHookPoint,
        source_component: str,
        tool_name: str,
        original_args: JsonObject | None = None,
        effective_args: JsonObject | None = None,
        authority_bearing_fields: tuple[str, ...] = (),
        parent_agent: str | None = None,
        child_agent: str | None = None,
        capture_mode: HermesCaptureMode = HermesCaptureMode.PRE_EXECUTION_GATE,
        metadata: JsonObject | None = None,
    ) -> HermesRuntimeEvent:
        event_metadata = _json_object({**self.metadata, **(metadata or {}), "source_component": source_component})
        original = _json_object(original_args or {})
        effective = _json_object(effective_args or {})
        raw_payload = {
            "hook_point": hook_point.value,
            "capture_mode": capture_mode.value,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "agent_id": child_agent or self.agent_id,
            "parent_agent": parent_agent,
            "child_agent": child_agent,
            "tool_name": tool_name,
            "original_args": original,
            "effective_args": effective,
            "metadata": event_metadata,
            "source_component": source_component,
            "timestamp": self.timestamp,
            "provenance_hint": self.provenance_hint,
            "authority_bearing_fields": list(authority_bearing_fields),
        }
        raw_event_hash = stable_hash(raw_payload)
        return HermesRuntimeEvent(
            event_id=f"capture_{hook_point.value}_{raw_event_hash[:12]}",
            hook_point=hook_point,
            capture_mode=capture_mode,
            session_id=self.session_id,
            task_id=self.task_id,
            agent_id=child_agent or self.agent_id,
            parent_agent=parent_agent,
            child_agent=child_agent,
            tool_name=tool_name,
            original_args=original,
            effective_args=effective,
            metadata=event_metadata,
            source_component=source_component,
            timestamp=self.timestamp,
            provenance_hint=self.provenance_hint,
            authority_bearing_fields=authority_bearing_fields,
            raw_event_hash=raw_event_hash,
        )


@dataclass(frozen=True)
class ToolDispatcherCapture(_CaptureBase):
    """Record a tool dispatcher pre-call event without executing the tool."""

    def capture(
        self,
        *,
        tool_name: str,
        original_args: JsonObject,
        effective_args: JsonObject,
        session_metadata: JsonObject | None = None,
    ) -> HermesRuntimeEvent:
        return self._runtime_event(
            hook_point=HermesHookPoint.TOOL_DISPATCHER_PRE_CALL,
            source_component="tool_dispatcher",
            tool_name=tool_name,
            original_args=original_args,
            effective_args=effective_args,
            metadata=session_metadata,
            authority_bearing_fields=("tool_name", "original_args", "effective_args"),
        )


@dataclass(frozen=True)
class TerminalCapture(_CaptureBase):
    """Record a terminal backend pre-exec event without executing the command."""

    def capture(
        self,
        *,
        command: str,
        cwd: str | None,
        env: JsonObject | None,
        stdin: str | None,
        terminal_backend: str = "local",
    ) -> HermesRuntimeEvent:
        return self._runtime_event(
            hook_point=HermesHookPoint.TERMINAL_BACKEND_PRE_EXEC,
            source_component="terminal_backend",
            tool_name="terminal",
            original_args={"command": command, "cwd": cwd, "env": env, "stdin": stdin},
            effective_args={
                "command": command,
                "cwd": cwd,
                "env": env,
                "stdin": stdin,
                "terminal_backend": terminal_backend,
            },
            authority_bearing_fields=("command", "cwd", "env", "stdin", "terminal_backend"),
        )


@dataclass(frozen=True)
class MCPCapture(_CaptureBase):
    """Record an MCP pre-transport event without opening any transport."""

    def capture(
        self,
        *,
        server: str,
        tool_name: str,
        arguments: JsonObject,
        endpoint: str | None,
        headers: JsonObject | None = None,
        transport_type: str = "http",
    ) -> HermesRuntimeEvent:
        mcp_tool_name = f"mcp_{server}_{tool_name}" if server and tool_name else tool_name
        transport: JsonObject = {"type": transport_type}
        if endpoint is not None:
            transport["endpoint"] = endpoint
        effective_args = {
            "server": server,
            "tool_name": tool_name,
            "arguments": {**_json_object(arguments), "headers": _json_object(headers or {})},
            "transport": transport,
        }
        return self._runtime_event(
            hook_point=HermesHookPoint.MCP_PRE_TRANSPORT,
            source_component="mcp",
            tool_name=mcp_tool_name,
            original_args=effective_args,
            effective_args=effective_args,
            authority_bearing_fields=("server", "tool_name", "arguments.url", "arguments.headers", "transport.endpoint"),
        )


@dataclass(frozen=True)
class MemoryCapture(_CaptureBase):
    """Record a memory pre-write event without persisting anything itself."""

    def capture(
        self,
        *,
        content: str,
        origin: str | None,
        persistent: bool | None,
        target: str = "memory",
        authority_claims: JsonObject | None = None,
        action: str = "remember",
    ) -> HermesRuntimeEvent:
        effective_args = {
            "action": action,
            "target": target,
            "content": content,
            "origin": origin,
            "persistent": persistent,
        }
        if authority_claims:
            effective_args["authority_claims"] = _json_object(authority_claims)
        return self._runtime_event(
            hook_point=HermesHookPoint.MEMORY_PRE_WRITE,
            source_component="memory",
            tool_name="memory",
            original_args=effective_args,
            effective_args=effective_args,
            authority_bearing_fields=("content", "origin", "persistent", "authority_claims"),
        )


@dataclass(frozen=True)
class GatewayCapture(_CaptureBase):
    """Record a gateway/message pre-send event without sending it."""

    def capture(
        self,
        *,
        platform: str,
        recipient: str | None,
        body: str | None = None,
        body_ref: str | None = None,
        target: str | None = None,
        channel: str | None = None,
        attachments: list[JsonValue] | None = None,
        headers: JsonObject | None = None,
    ) -> HermesRuntimeEvent:
        effective_args = {
            "platform": platform,
            "recipient": recipient,
            "body": body if body is not None else body_ref,
            "target": target or (f"{platform}:{recipient}" if platform and recipient else None),
            "channel": channel or recipient,
            "attachments": attachments or [],
            "headers": _json_object(headers or {}),
        }
        return self._runtime_event(
            hook_point=HermesHookPoint.GATEWAY_MESSAGING_PRE_SEND,
            source_component="gateway",
            tool_name="send_message",
            original_args=effective_args,
            effective_args=effective_args,
            authority_bearing_fields=("platform", "recipient", "body", "attachments", "headers"),
        )


@dataclass(frozen=True)
class DelegationCapture(_CaptureBase):
    """Record subagent delegation pre-dispatch without invoking a child agent."""

    def capture(
        self,
        *,
        parent_agent: str | None,
        child_agent: str | None,
        goal: str,
        scope: JsonObject | None = None,
        cert_ref: str | None = None,
        toolsets: list[str] | None = None,
        context_ref: str = "val_summary",
        role: str = "assistant",
    ) -> HermesRuntimeEvent:
        effective_args = {
            "goal": goal,
            "context_ref": context_ref,
            "toolsets": toolsets or [],
            "role": role,
        }
        if scope is not None:
            effective_args["delegated_scope"] = _json_object(scope)
        if cert_ref is not None:
            effective_args["cert_ref"] = cert_ref
        return self._runtime_event(
            hook_point=HermesHookPoint.SUBAGENT_DELEGATION_PRE_DISPATCH,
            source_component="subagent",
            tool_name="delegate_task",
            original_args=effective_args,
            effective_args=effective_args,
            parent_agent=parent_agent,
            child_agent=child_agent,
            authority_bearing_fields=("parent_agent", "child_agent", "goal", "delegated_scope", "cert_ref", "toolsets"),
        )


@dataclass(frozen=True)
class SchedulerCapture(_CaptureBase):
    """Record scheduler/cron pre-register or pre-fire events without scheduling."""

    def capture(
        self,
        *,
        schedule_id: str | None,
        schedule: str | None,
        action: str,
        recipient: str | None = None,
        endpoint: str | None = None,
        command: str | None = None,
        workdir: str | None = None,
        body_ref: str | None = "val_summary",
        pre_fire: bool = False,
    ) -> HermesRuntimeEvent:
        effective_args = {
            "schedule_id": schedule_id,
            "recurrence": schedule,
            "action": action,
            "recipient": recipient,
            "url": endpoint,
            "command": command,
            "workdir": workdir,
            "body_ref": body_ref,
        }
        return self._runtime_event(
            hook_point=(
                HermesHookPoint.SCHEDULER_CRON_PRE_FIRE
                if pre_fire
                else HermesHookPoint.SCHEDULER_CRON_PRE_REGISTER
            ),
            source_component="scheduler",
            tool_name="cronjob",
            original_args=effective_args,
            effective_args=effective_args,
            authority_bearing_fields=("schedule_id", "recurrence", "recipient", "url", "command", "workdir"),
        )


@dataclass(frozen=True)
class MiddlewareRewriteCapture(_CaptureBase):
    """Record skill/plugin middleware rewrites without treating metadata as authority."""

    def capture(
        self,
        *,
        tool_name: str,
        original_args: JsonObject,
        effective_args: JsonObject,
        source_component: str = "skill_middleware",
    ) -> HermesRuntimeEvent:
        return self._runtime_event(
            hook_point=HermesHookPoint.SKILL_PLUGIN_MIDDLEWARE_REWRITE,
            source_component=source_component,
            tool_name=tool_name,
            original_args=original_args,
            effective_args=effective_args,
            metadata={"middleware_source": source_component},
            authority_bearing_fields=("original_args", "effective_args", "middleware_source"),
        )


def _json_object(value: Any) -> JsonObject:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return {}


def _json_value(value: Any) -> JsonValue:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return str(value)
