"""Hermes runtime capture schema and replay bridge.

This module defines a capture-layer schema for future Hermes integration work.
It does not import or run Hermes, execute tools, mint capabilities, synthesize
proofs, or verify authorization. Enforcement still happens through
``CapProofMiddleware`` and the Reference Monitor after captured events are
converted into existing Hermes-like adapter events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from capproof.schemas import DenyReason, JsonObject, JsonValue
from capproof.serialization import stable_hash


class HermesHookPoint(str, Enum):
    TOOL_DISPATCHER_PRE_CALL = "tool_dispatcher_pre_call"
    TERMINAL_BACKEND_PRE_EXEC = "terminal_backend_pre_exec"
    MCP_PRE_TRANSPORT = "mcp_pre_transport"
    MEMORY_PRE_WRITE = "memory_pre_write"
    GATEWAY_MESSAGING_PRE_SEND = "gateway_messaging_pre_send"
    SUBAGENT_DELEGATION_PRE_DISPATCH = "subagent_delegation_pre_dispatch"
    SCHEDULER_CRON_PRE_REGISTER = "scheduler_cron_pre_register"
    SCHEDULER_CRON_PRE_FIRE = "scheduler_cron_pre_fire"
    SKILL_PLUGIN_MIDDLEWARE_REWRITE = "skill_plugin_middleware_rewrite"
    OBSERVER_POSTHOC = "observer_posthoc"


class HermesCaptureMode(str, Enum):
    PRE_EXECUTION_GATE = "pre_execution_gate"
    OBSERVER_ONLY = "observer_only"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class HermesCapturedToolCall:
    tool_name: str
    original_args: JsonObject = field(default_factory=dict)
    effective_args: JsonObject = field(default_factory=dict)
    source_component: str = ""
    authority_bearing_fields: tuple[str, ...] = ()

    @classmethod
    def from_event(cls, event: "HermesRuntimeEvent") -> "HermesCapturedToolCall":
        return cls(
            tool_name=event.tool_name,
            original_args=dict(event.original_args),
            effective_args=dict(event.effective_args),
            source_component=event.source_component,
            authority_bearing_fields=tuple(event.authority_bearing_fields),
        )

    def to_dict(self) -> JsonObject:
        return {
            "tool_name": self.tool_name,
            "original_args": dict(self.original_args),
            "effective_args": dict(self.effective_args),
            "source_component": self.source_component,
            "authority_bearing_fields": list(self.authority_bearing_fields),
        }


@dataclass(frozen=True)
class HermesRuntimeEvent:
    event_id: str
    hook_point: HermesHookPoint
    capture_mode: HermesCaptureMode
    session_id: str
    task_id: str
    agent_id: str
    tool_name: str
    original_args: JsonObject
    effective_args: JsonObject
    metadata: JsonObject
    source_component: str
    timestamp: str
    provenance_hint: str
    authority_bearing_fields: tuple[str, ...]
    raw_event_hash: str
    source: str = "hermes"
    parent_agent: str | None = None
    child_agent: str | None = None

    @classmethod
    def from_dict(cls, data: JsonObject) -> "HermesRuntimeEvent":
        raw_hash = data.get("raw_event_hash")
        if not raw_hash:
            raw_hash = stable_hash({key: value for key, value in data.items() if key != "raw_event_hash"})
        return cls(
            event_id=str(data.get("event_id", "")),
            source=str(data.get("source", "hermes")),
            hook_point=HermesHookPoint(str(data.get("hook_point", ""))),
            capture_mode=HermesCaptureMode(str(data.get("capture_mode", ""))),
            session_id=str(data.get("session_id", "")),
            task_id=str(data.get("task_id", "")),
            agent_id=str(data.get("agent_id", "")),
            parent_agent=_optional_string(data.get("parent_agent")),
            child_agent=_optional_string(data.get("child_agent")),
            tool_name=str(data.get("tool_name", "")),
            original_args=_json_object(data.get("original_args", {})),
            effective_args=_json_object(data.get("effective_args", {})),
            metadata=_json_object(data.get("metadata", {})),
            source_component=str(data.get("source_component", "")),
            timestamp=str(data.get("timestamp", "")),
            provenance_hint=str(data.get("provenance_hint", "")),
            authority_bearing_fields=tuple(str(item) for item in data.get("authority_bearing_fields", ())),
            raw_event_hash=str(raw_hash),
        )

    def to_dict(self) -> JsonObject:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "hook_point": self.hook_point.value,
            "capture_mode": self.capture_mode.value,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "parent_agent": self.parent_agent,
            "child_agent": self.child_agent,
            "tool_name": self.tool_name,
            "original_args": dict(self.original_args),
            "effective_args": dict(self.effective_args),
            "metadata": dict(self.metadata),
            "source_component": self.source_component,
            "timestamp": self.timestamp,
            "provenance_hint": self.provenance_hint,
            "authority_bearing_fields": list(self.authority_bearing_fields),
            "raw_event_hash": self.raw_event_hash,
        }


@dataclass(frozen=True)
class HermesCaptureValidationResult:
    event_id: str
    hook_point: str
    capture_mode: str
    valid: bool
    enforcement_allowed: bool
    missing_fields: tuple[str, ...] = ()
    authority_bearing_fields: tuple[str, ...] = ()
    captured_tool_call: HermesCapturedToolCall | None = None
    adapter_raw_event: JsonObject | None = None
    deny_reason: DenyReason | None = None
    message: str = ""

    def to_dict(self) -> JsonObject:
        return {
            "event_id": self.event_id,
            "hook_point": self.hook_point,
            "capture_mode": self.capture_mode,
            "valid": self.valid,
            "enforcement_allowed": self.enforcement_allowed,
            "missing_fields": list(self.missing_fields),
            "authority_bearing_fields": list(self.authority_bearing_fields),
            "captured_tool_call": self.captured_tool_call.to_dict() if self.captured_tool_call else None,
            "adapter_raw_event": self.adapter_raw_event,
            "deny_reason": self.deny_reason.value if self.deny_reason else None,
            "message": self.message,
        }


class HermesCapturedEventAdapter:
    """Validate captured Hermes events and bridge them into mock Hermes adapter events."""

    top_level_required = (
        "event_id",
        "source",
        "hook_point",
        "capture_mode",
        "session_id",
        "task_id",
        "agent_id",
        "parent_agent",
        "child_agent",
        "tool_name",
        "original_args",
        "effective_args",
        "metadata",
        "source_component",
        "timestamp",
        "provenance_hint",
        "authority_bearing_fields",
        "raw_event_hash",
    )

    def parse(self, data: JsonObject) -> HermesRuntimeEvent:
        return HermesRuntimeEvent.from_dict(data)

    def validate_dict(self, data: JsonObject) -> HermesCaptureValidationResult:
        missing = tuple(field for field in self.top_level_required if field not in data)
        try:
            event = self.parse(data)
        except (ValueError, TypeError) as exc:
            return HermesCaptureValidationResult(
                event_id=str(data.get("event_id", "")),
                hook_point=str(data.get("hook_point", "")),
                capture_mode=str(data.get("capture_mode", "")),
                valid=False,
                enforcement_allowed=False,
                missing_fields=missing,
                deny_reason=DenyReason.ADAPTER_COVERAGE_GAP,
                message=f"invalid Hermes runtime event schema: {exc}",
            )
        result = self.validate(event)
        if missing:
            return HermesCaptureValidationResult(
                event_id=result.event_id,
                hook_point=result.hook_point,
                capture_mode=result.capture_mode,
                valid=False,
                enforcement_allowed=False,
                missing_fields=tuple(dict.fromkeys((*missing, *result.missing_fields))),
                authority_bearing_fields=result.authority_bearing_fields,
                captured_tool_call=result.captured_tool_call,
                adapter_raw_event=None,
                deny_reason=DenyReason.ADAPTER_COVERAGE_GAP,
                message="captured event missing top-level schema fields",
            )
        return result

    def validate(self, event: HermesRuntimeEvent) -> HermesCaptureValidationResult:
        captured_call = HermesCapturedToolCall.from_event(event)
        if event.source != "hermes":
            return self._invalid(event, ("source",), "captured event source must be hermes", captured_call)
        if event.capture_mode == HermesCaptureMode.OBSERVER_ONLY:
            return self._invalid(
                event,
                (),
                "observer_only capture cannot support enforcement allow",
                captured_call,
            )
        if event.capture_mode == HermesCaptureMode.UNSUPPORTED:
            return self._invalid(event, (), "unsupported capture mode must fail closed", captured_call)

        missing = _missing_required_fields(event)
        if missing:
            return self._invalid(event, missing, "captured event is missing authority-bearing fields", captured_call)

        adapter_raw_event = self.to_adapter_raw_event(event)
        return HermesCaptureValidationResult(
            event_id=event.event_id,
            hook_point=event.hook_point.value,
            capture_mode=event.capture_mode.value,
            valid=True,
            enforcement_allowed=True,
            authority_bearing_fields=tuple(event.authority_bearing_fields),
            captured_tool_call=captured_call,
            adapter_raw_event=adapter_raw_event,
            message="pre_execution_gate event is complete",
        )

    def to_adapter_raw_event(self, event: HermesRuntimeEvent) -> JsonObject:
        metadata = {
            **dict(event.metadata),
            "capture_event_id": event.event_id,
            "capture_hook_point": event.hook_point.value,
            "capture_mode": event.capture_mode.value,
            "source_component": event.source_component,
            "provenance_hint": event.provenance_hint,
            "raw_event_hash": event.raw_event_hash,
            "authority_bearing_fields": list(event.authority_bearing_fields),
        }
        base: JsonObject = {
            "source": "hermes",
            "task_id": event.task_id,
            "agent_id": event.agent_id,
            "trace_id": event.event_id,
            "session_id": event.session_id,
            "metadata": metadata,
        }

        if event.hook_point == HermesHookPoint.TERMINAL_BACKEND_PRE_EXEC:
            return {
                **base,
                "event_type": "terminal",
                "tool": "terminal",
                "input": {
                    "command": event.effective_args.get("command"),
                    "workdir": event.effective_args.get("cwd"),
                    "env": event.effective_args.get("env"),
                    "stdin": event.effective_args.get("stdin"),
                    "terminal_backend": event.effective_args.get("terminal_backend"),
                },
            }
        if event.hook_point == HermesHookPoint.GATEWAY_MESSAGING_PRE_SEND:
            recipient = str(event.effective_args.get("recipient", ""))
            platform = str(event.effective_args.get("platform", ""))
            target = str(event.effective_args.get("target") or f"{platform}:{recipient}")
            return {
                **base,
                "event_type": "tool_call",
                "tool": "send_message",
                "input": {
                    "target": target,
                    "message": event.effective_args.get("body"),
                    "platform": platform,
                    "channel": event.effective_args.get("channel") or recipient,
                },
            }
        if event.hook_point == HermesHookPoint.MCP_PRE_TRANSPORT:
            server = str(event.effective_args.get("server", ""))
            tool_name = str(event.effective_args.get("tool_name") or event.tool_name)
            return {
                **base,
                "event_type": "mcp_tool_call",
                "tool": event.tool_name or f"mcp_{server}_{tool_name}",
                "input": {
                    "server": server,
                    "tool_name": tool_name,
                    "arguments": _json_object(event.effective_args.get("arguments", {})),
                    "transport": _json_object(event.effective_args.get("transport", {})),
                },
            }
        if event.hook_point == HermesHookPoint.MEMORY_PRE_WRITE:
            return {
                **base,
                "event_type": "memory_action",
                "tool": "memory",
                "input": {
                    "action": event.effective_args.get("action", "remember"),
                    "target": event.effective_args.get("target", "memory"),
                    "content": event.effective_args.get("content"),
                    "origin": event.effective_args.get("origin"),
                    "persistent": event.effective_args.get("persistent"),
                },
            }
        if event.hook_point == HermesHookPoint.SUBAGENT_DELEGATION_PRE_DISPATCH:
            return {
                **base,
                "event_type": "delegate_task",
                "tool": "delegate_task",
                "parent_agent": event.parent_agent,
                "child_agent": event.child_agent,
                "input": {
                    "parent_agent": event.parent_agent,
                    "child_agent": event.child_agent,
                    "goal": event.effective_args.get("goal"),
                    "context_ref": event.effective_args.get("context_ref", "val_summary"),
                    "toolsets": event.effective_args.get("toolsets", ()),
                    "role": event.effective_args.get("role", "assistant"),
                    "delegation_cert_ref": event.effective_args.get("cert_ref"),
                    "delegated_scope": event.effective_args.get("delegated_scope"),
                },
            }
        if event.hook_point in {
            HermesHookPoint.SCHEDULER_CRON_PRE_REGISTER,
            HermesHookPoint.SCHEDULER_CRON_PRE_FIRE,
        }:
            return {
                **base,
                "event_type": "cronjob",
                "tool": "cronjob",
                "input": {
                    "schedule_id": event.effective_args.get("schedule_id"),
                    "prompt": event.effective_args.get("prompt"),
                    "schedule": event.effective_args.get("recurrence"),
                    "deliver": event.effective_args.get("deliver"),
                    "recipient": event.effective_args.get("recipient"),
                    "target": event.effective_args.get("target"),
                    "body_ref": event.effective_args.get("body_ref", "val_summary"),
                    "script": event.effective_args.get("script"),
                    "workdir": event.effective_args.get("workdir"),
                    "action": event.effective_args.get("action", "create"),
                },
            }
        if event.hook_point == HermesHookPoint.SKILL_PLUGIN_MIDDLEWARE_REWRITE:
            return {
                **base,
                "event_type": "dispatcher_tool_call",
                "tool": event.tool_name,
                "input": {
                    "original_args": dict(event.original_args),
                    "effective_args": dict(event.effective_args),
                    "session_metadata": dict(event.metadata),
                },
            }
        if event.hook_point == HermesHookPoint.TOOL_DISPATCHER_PRE_CALL:
            return {
                **base,
                "event_type": "tool_call",
                "tool": event.tool_name,
                "input": dict(event.effective_args),
            }
        return {
            **base,
            "event_type": "unsupported",
            "tool": event.tool_name,
            "input": dict(event.effective_args),
        }

    def _invalid(
        self,
        event: HermesRuntimeEvent,
        missing_fields: tuple[str, ...],
        message: str,
        captured_call: HermesCapturedToolCall,
    ) -> HermesCaptureValidationResult:
        return HermesCaptureValidationResult(
            event_id=event.event_id,
            hook_point=event.hook_point.value,
            capture_mode=event.capture_mode.value,
            valid=False,
            enforcement_allowed=False,
            missing_fields=missing_fields,
            authority_bearing_fields=tuple(event.authority_bearing_fields),
            captured_tool_call=captured_call,
            deny_reason=DenyReason.ADAPTER_COVERAGE_GAP,
            message=message,
        )


def _missing_required_fields(event: HermesRuntimeEvent) -> tuple[str, ...]:
    if event.hook_point == HermesHookPoint.TERMINAL_BACKEND_PRE_EXEC:
        return _missing_paths(event.effective_args, ("command", "cwd", "env", "stdin"))
    if event.hook_point == HermesHookPoint.GATEWAY_MESSAGING_PRE_SEND:
        return _missing_paths(event.effective_args, ("platform", "recipient", "body"))
    if event.hook_point == HermesHookPoint.MCP_PRE_TRANSPORT:
        return _missing_paths(
            event.effective_args,
            ("server", "tool_name", "arguments", "transport.endpoint"),
        )
    if event.hook_point == HermesHookPoint.MEMORY_PRE_WRITE:
        return _missing_paths(event.effective_args, ("content", "origin", "persistent"))
    if event.hook_point == HermesHookPoint.SUBAGENT_DELEGATION_PRE_DISPATCH:
        missing = []
        if not event.parent_agent:
            missing.append("parent_agent")
        if not event.child_agent:
            missing.append("child_agent")
        if "delegated_scope" not in event.effective_args and "cert_ref" not in event.effective_args:
            missing.append("effective_args.delegated_scope_or_cert_ref")
        return tuple(missing)
    if event.hook_point in {
        HermesHookPoint.SCHEDULER_CRON_PRE_REGISTER,
        HermesHookPoint.SCHEDULER_CRON_PRE_FIRE,
    }:
        missing = list(_missing_paths(event.effective_args, ("schedule_id",)))
        if not any(
            key in event.effective_args and event.effective_args[key] not in ("", None, [], {})
            for key in ("recipient", "target", "url", "command", "script")
        ):
            missing.append("effective_args.action_target")
        return tuple(missing)
    if event.hook_point == HermesHookPoint.SKILL_PLUGIN_MIDDLEWARE_REWRITE:
        missing = []
        if not event.original_args:
            missing.append("original_args")
        if not event.effective_args:
            missing.append("effective_args")
        return tuple(missing)
    if event.hook_point == HermesHookPoint.TOOL_DISPATCHER_PRE_CALL:
        missing = []
        if not event.tool_name:
            missing.append("tool_name")
        if not event.original_args:
            missing.append("original_args")
        if not event.effective_args:
            missing.append("effective_args")
        return tuple(missing)
    return ("hook_point",)


def _missing_paths(values: JsonObject, paths: tuple[str, ...]) -> tuple[str, ...]:
    missing: list[str] = []
    for path in paths:
        current: Any = values
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                missing.append(f"effective_args.{path}")
                break
            current = current[part]
        else:
            if current == "" or (current is None and not path.endswith("stdin")):
                missing.append(f"effective_args.{path}")
    return tuple(missing)


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


def _optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
