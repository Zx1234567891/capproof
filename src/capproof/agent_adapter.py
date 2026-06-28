"""Agent tool-call adapter layer for CapProof.

This module converts framework-shaped tool-call events into CapProof
``Action`` objects, asks the proof synthesizer for a witness, and then relies
on the Reference Monitor as the final allow/deny boundary. It contains no real
tool execution and does not call model APIs.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path
import tempfile
from typing import Any, Protocol

import capproof.monitor as monitor_module
from capproof.canonicalizer import Canonicalizer
from capproof.contracts import ToolContractRegistry, default_tool_contract_registry
from capproof.monitor import MonitorState, ReferenceMonitor, VerificationResult, canonical_action_hash
from capproof.proof_synthesizer import ProofFailureReason, ProofSynthesisResult, synthesize_proof
from capproof.schemas import (
    Action,
    AuthorityRole,
    DenyReason,
    JsonObject,
    JsonValue,
    Proof,
    ValueRef,
    VerificationDecision,
)


@dataclass(frozen=True)
class AgentAction:
    agent_id: str
    task_id: str
    tool_name: str
    raw_args: JsonObject
    source_agent_type: str
    trace_id: str
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True)
class CanonicalToolCall:
    tool_name: str
    canonical_args: JsonObject
    action_hash: str
    authority_bearing_fields: tuple[str, ...]
    contract_id: str


class ToolCallAdapter(Protocol):
    def supports(self, raw_event: JsonObject) -> bool:
        """Return whether this adapter can parse the raw event shape."""

    def parse(self, raw_event: JsonObject) -> AgentAction:
        """Parse a raw framework event into an AgentAction."""

    def canonicalize(self, agent_action: AgentAction) -> CanonicalToolCall:
        """Canonicalize the action arguments according to trusted contracts."""


@dataclass(frozen=True)
class AgentRuntimeState:
    monitor_state: MonitorState
    value_refs: dict[str, ValueRef] = field(default_factory=dict)
    authspec_ref: str = "agent_adapter"


@dataclass(frozen=True)
class GuardDecision:
    decision: VerificationDecision
    agent_action: AgentAction | None = None
    action: Action | None = None
    canonical_call: CanonicalToolCall | None = None
    proof: Proof | None = None
    proof_result: ProofSynthesisResult | None = None
    verifier_result: VerificationResult | None = None
    deny_reason: DenyReason | None = None
    failure_reason: ProofFailureReason | None = None
    endorsement_challenge: JsonObject | None = None
    message: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == VerificationDecision.ALLOW


@dataclass(frozen=True)
class ExecutionResult:
    decision: VerificationDecision
    executed: bool
    mock_event: JsonObject | None = None
    endorsement_challenge: JsonObject | None = None
    message: str = ""


class AdapterError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        deny_reason: DenyReason | None = None,
        failure_reason: ProofFailureReason | None = None,
    ) -> None:
        super().__init__(message)
        self.deny_reason = deny_reason
        self.failure_reason = failure_reason


class _BaseAdapter:
    source_agent_type = "base"

    def __init__(
        self,
        *,
        tool_contracts: ToolContractRegistry | None = None,
        canonicalizer: Canonicalizer | None = None,
    ) -> None:
        self.tool_contracts = tool_contracts or default_tool_contract_registry()
        self.canonicalizer = canonicalizer or Canonicalizer(Path.cwd())

    def canonicalize(self, agent_action: AgentAction) -> CanonicalToolCall:
        contract = self.tool_contracts.get(agent_action.tool_name)
        if contract is None:
            raise AdapterError(
                "unknown tool",
                deny_reason=DenyReason.UNKNOWN_TOOL,
                failure_reason=ProofFailureReason.UNKNOWN_TOOL,
            )
        action = _action_from_agent_action(agent_action, value_refs={})
        canonical = monitor_module._canonicalize_action(action, contract, self.canonicalizer)
        if not canonical.allowed or canonical.args is None:
            raise AdapterError(
                canonical.message,
                deny_reason=canonical.deny_reason or DenyReason.CANONICALIZATION_MISMATCH,
                failure_reason=_proof_failure_from_deny(canonical.deny_reason),
            )
        return CanonicalToolCall(
            tool_name=agent_action.tool_name,
            canonical_args=canonical.args,
            action_hash=canonical_action_hash(action, canonical.args),
            authority_bearing_fields=tuple(field.name for field in contract.authority),
            contract_id=f"default:{contract.tool}",
        )


class LangGraphLikeAdapter(_BaseAdapter):
    source_agent_type = "langgraph_like"

    def supports(self, raw_event: JsonObject) -> bool:
        return isinstance(raw_event, dict) and "tool" in raw_event and "args" in raw_event

    def parse(self, raw_event: JsonObject) -> AgentAction:
        args = raw_event.get("args")
        if not isinstance(args, dict):
            raise AdapterError(
                "LangGraph-like args must be an object",
                deny_reason=DenyReason.CANONICALIZATION_MISMATCH,
                failure_reason=ProofFailureReason.CANONICALIZATION_MISMATCH,
            )
        metadata = _metadata(raw_event)
        tool_name = str(raw_event.get("tool", ""))
        return AgentAction(
            agent_id=str(raw_event.get("agent_id") or metadata.get("agent_id") or "agent_langgraph"),
            task_id=str(raw_event.get("task_id") or metadata.get("task_id") or "task_default"),
            tool_name=tool_name,
            raw_args=_normalize_tool_args(tool_name, args),
            source_agent_type=self.source_agent_type,
            trace_id=str(raw_event.get("trace_id") or raw_event.get("id") or "langgraph_event"),
            metadata=metadata,
        )


class OpenAIToolCallingLikeAdapter(_BaseAdapter):
    source_agent_type = "openai_tool_calling_like"

    def supports(self, raw_event: JsonObject) -> bool:
        return (
            isinstance(raw_event, dict)
            and raw_event.get("type") == "function_call"
            and "name" in raw_event
            and "arguments" in raw_event
        )

    def parse(self, raw_event: JsonObject) -> AgentAction:
        raw_arguments = raw_event.get("arguments")
        if isinstance(raw_arguments, str):
            try:
                args = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                raise AdapterError(
                    "malformed JSON arguments",
                    deny_reason=DenyReason.CANONICALIZATION_MISMATCH,
                    failure_reason=ProofFailureReason.CANONICALIZATION_MISMATCH,
                ) from exc
        elif isinstance(raw_arguments, dict):
            args = raw_arguments
        else:
            raise AdapterError(
                "OpenAI-like arguments must be a JSON string or object",
                deny_reason=DenyReason.CANONICALIZATION_MISMATCH,
                failure_reason=ProofFailureReason.CANONICALIZATION_MISMATCH,
            )
        if not isinstance(args, dict):
            raise AdapterError(
                "OpenAI-like arguments must decode to an object",
                deny_reason=DenyReason.CANONICALIZATION_MISMATCH,
                failure_reason=ProofFailureReason.CANONICALIZATION_MISMATCH,
            )
        metadata = _metadata(raw_event)
        tool_name = str(raw_event.get("name", ""))
        return AgentAction(
            agent_id=str(raw_event.get("agent_id") or metadata.get("agent_id") or "agent_openai"),
            task_id=str(raw_event.get("task_id") or metadata.get("task_id") or "task_default"),
            tool_name=tool_name,
            raw_args=_normalize_tool_args(tool_name, args),
            source_agent_type=self.source_agent_type,
            trace_id=str(raw_event.get("call_id") or raw_event.get("trace_id") or "openai_call"),
            metadata=metadata,
        )


class CodingAgentLikeAdapter(_BaseAdapter):
    source_agent_type = "coding_agent_like"

    def supports(self, raw_event: JsonObject) -> bool:
        return isinstance(raw_event, dict) and raw_event.get("kind") == "tool_use" and "tool_name" in raw_event

    def parse(self, raw_event: JsonObject) -> AgentAction:
        args = raw_event.get("input", {})
        if not isinstance(args, dict):
            raise AdapterError(
                "coding-agent input must be an object",
                deny_reason=DenyReason.CANONICALIZATION_MISMATCH,
                failure_reason=ProofFailureReason.CANONICALIZATION_MISMATCH,
            )
        metadata = _metadata(raw_event)
        tool_name = str(raw_event.get("tool_name", ""))
        agent_id = str(raw_event.get("agent") or raw_event.get("agent_id") or metadata.get("agent_id") or "agent_coding")
        return AgentAction(
            agent_id=agent_id,
            task_id=str(raw_event.get("task_id") or metadata.get("task_id") or "task_default"),
            tool_name=tool_name,
            raw_args=_normalize_tool_args(tool_name, args),
            source_agent_type=self.source_agent_type,
            trace_id=str(raw_event.get("trace_id") or raw_event.get("id") or "coding_tool_use"),
            metadata=metadata,
        )


class CapProofMiddleware:
    def __init__(
        self,
        adapters: tuple[ToolCallAdapter, ...],
        *,
        monitor: ReferenceMonitor | None = None,
    ) -> None:
        self.adapters = adapters
        self.monitor = monitor or ReferenceMonitor()

    def guard(self, raw_event: JsonObject, runtime_state: AgentRuntimeState) -> GuardDecision:
        adapter = self._select_adapter(raw_event)
        if adapter is None:
            return _guard_deny(
                DenyReason.UNKNOWN_TOOL,
                ProofFailureReason.UNKNOWN_TOOL,
                "no adapter supports raw event",
            )
        try:
            agent_action = adapter.parse(raw_event)
            canonical_call = adapter.canonicalize(agent_action)
            action = _action_from_agent_action(agent_action, value_refs=runtime_state.value_refs)
            canonical_call = _canonical_call_for_action(action, runtime_state.monitor_state, canonical_call)
        except AdapterError as exc:
            return _guard_deny(
                exc.deny_reason or DenyReason.CANONICALIZATION_MISMATCH,
                exc.failure_reason or ProofFailureReason.CANONICALIZATION_MISMATCH,
                str(exc),
            )

        proof_result = synthesize_proof(
            action,
            runtime_state.monitor_state,
            authspec_ref=runtime_state.authspec_ref,
        )
        if proof_result.failure_reason == ProofFailureReason.ENDORSEMENT_REQUIRED:
            return GuardDecision(
                decision=VerificationDecision.ASK,
                agent_action=agent_action,
                action=action,
                canonical_call=canonical_call,
                proof_result=proof_result,
                failure_reason=proof_result.failure_reason,
                endorsement_challenge=_endorsement_challenge(action, canonical_call),
                message=proof_result.message or "endorsement required",
            )
        if not proof_result.allowed or proof_result.proof is None:
            return GuardDecision(
                decision=VerificationDecision.DENY,
                agent_action=agent_action,
                action=action,
                canonical_call=canonical_call,
                proof_result=proof_result,
                deny_reason=_deny_from_proof_failure(proof_result.failure_reason),
                failure_reason=proof_result.failure_reason,
                message=proof_result.message,
            )

        verifier_result = self.monitor.verify(action, proof_result.proof, runtime_state.monitor_state)
        if not verifier_result.allowed:
            return GuardDecision(
                decision=VerificationDecision.DENY,
                agent_action=agent_action,
                action=action,
                canonical_call=canonical_call,
                proof=proof_result.proof,
                proof_result=proof_result,
                verifier_result=verifier_result,
                deny_reason=verifier_result.deny_reason,
                failure_reason=_proof_failure_from_deny(verifier_result.deny_reason),
                message=verifier_result.message,
            )
        return GuardDecision(
            decision=VerificationDecision.ALLOW,
            agent_action=agent_action,
            action=action,
            canonical_call=canonical_call,
            proof=proof_result.proof,
            proof_result=proof_result,
            verifier_result=verifier_result,
        )

    def _select_adapter(self, raw_event: JsonObject) -> ToolCallAdapter | None:
        for adapter in self.adapters:
            if adapter.supports(raw_event):
                return adapter
        return None


class GuardedExecutor:
    def __init__(self, executor: "MockExecutor") -> None:
        self.executor = executor

    def execute_if_allowed(self, decision: GuardDecision) -> ExecutionResult:
        if decision.decision == VerificationDecision.ASK:
            return ExecutionResult(
                decision=VerificationDecision.ASK,
                executed=False,
                endorsement_challenge=decision.endorsement_challenge,
                message="endorsement required",
            )
        if decision.decision != VerificationDecision.ALLOW or decision.canonical_call is None:
            return ExecutionResult(
                decision=VerificationDecision.DENY,
                executed=False,
                message=decision.message,
            )
        return ExecutionResult(
            decision=VerificationDecision.ALLOW,
            executed=True,
            mock_event=self.executor.execute(decision.canonical_call),
        )


class MockExecutor:
    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self.workspace_root = Path(workspace_root or tempfile.mkdtemp(prefix="capproof_mock_")).resolve(
            strict=False
        )
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.executions: list[JsonObject] = []
        self.real_email_sent = False
        self.real_network_called = False
        self.real_shell_executed = False

    def execute(self, call: CanonicalToolCall) -> JsonObject:
        if call.tool_name == "send_email":
            event = {"mock_tool": "send_email", "args": call.canonical_args}
        elif call.tool_name == "write_file":
            event = self._mock_write_file(call.canonical_args)
        elif call.tool_name == "run_shell":
            event = {"mock_tool": "run_shell_template", "would_execute": call.canonical_args}
        elif call.tool_name == "read_file":
            event = {"mock_tool": "read_file", "args": call.canonical_args}
        elif call.tool_name == "summarize":
            event = {"mock_tool": "summarize", "args": call.canonical_args}
        else:
            event = {"mock_tool": call.tool_name, "args": call.canonical_args}
        self.executions.append(event)
        return event

    def _mock_write_file(self, args: JsonObject) -> JsonObject:
        path = Path(str(args.get("path", ""))).resolve(strict=False)
        try:
            path.relative_to(self.workspace_root)
        except ValueError:
            return {"mock_tool": "write_file", "written": False, "reason": "outside mock workspace"}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(args.get("content", "")), encoding="utf-8")
        return {"mock_tool": "write_file", "written": True, "path": str(path)}


def default_agent_adapters(
    *,
    tool_contracts: ToolContractRegistry | None = None,
    canonicalizer: Canonicalizer | None = None,
) -> tuple[ToolCallAdapter, ...]:
    return (
        LangGraphLikeAdapter(tool_contracts=tool_contracts, canonicalizer=canonicalizer),
        OpenAIToolCallingLikeAdapter(tool_contracts=tool_contracts, canonicalizer=canonicalizer),
        CodingAgentLikeAdapter(tool_contracts=tool_contracts, canonicalizer=canonicalizer),
    )


def _metadata(raw_event: JsonObject) -> JsonObject:
    metadata = raw_event.get("metadata", {})
    return dict(metadata) if isinstance(metadata, dict) else {}


def _normalize_tool_args(tool_name: str, args: JsonObject) -> JsonObject:
    if tool_name == "send_email":
        normalized = dict(args)
        if "subject" not in normalized and "body" in normalized:
            normalized["subject"] = "summary"
        return normalized
    if tool_name == "run_shell":
        return _normalize_run_shell_args(args)
    return dict(args)


def _normalize_run_shell_args(args: JsonObject) -> JsonObject:
    normalized = dict(args)
    if "command_template" not in normalized and "command" in normalized:
        normalized["command_template"] = str(normalized.pop("command"))
    raw_args = normalized.get("args", {})
    if isinstance(raw_args, list):
        if len(raw_args) == 0:
            normalized["args"] = {}
        elif len(raw_args) == 1:
            normalized["args"] = {"target": str(raw_args[0])}
        else:
            normalized["args"] = {"argv": [str(item) for item in raw_args]}
    elif isinstance(raw_args, dict):
        normalized["args"] = dict(raw_args)
    else:
        normalized["args"] = {"target": str(raw_args)}
    normalized.setdefault("cwd", ".")
    normalized.setdefault("env", {})
    normalized.setdefault("stdin", None)
    return normalized


def _action_from_agent_action(
    agent_action: AgentAction,
    *,
    value_refs: dict[str, ValueRef],
) -> Action:
    content_bindings, bound_refs = _content_bindings(agent_action, value_refs)
    metadata = dict(agent_action.metadata)
    if content_bindings:
        metadata["content_bindings"] = content_bindings
    metadata.setdefault("source_agent_type", agent_action.source_agent_type)
    metadata.setdefault("trace_id", agent_action.trace_id)
    return Action(
        action_id=f"action:{agent_action.trace_id}",
        task_id=agent_action.task_id,
        agent_id=agent_action.agent_id,
        tool=agent_action.tool_name,
        args=dict(agent_action.raw_args),
        value_refs=tuple(bound_refs),
        metadata=metadata,
    )


def _content_bindings(
    agent_action: AgentAction,
    value_refs: dict[str, ValueRef],
) -> tuple[dict[str, str], list[ValueRef]]:
    bindings: dict[str, str] = {}
    bound_ref_ids: list[str] = []
    for field_name, value in agent_action.raw_args.items():
        if isinstance(value, str) and value in value_refs:
            bindings[field_name] = value
            bound_ref_ids.append(value)
    body_value = agent_action.raw_args.get("body")
    if (
        agent_action.tool_name == "send_email"
        and "subject" in agent_action.raw_args
        and "subject" not in bindings
        and isinstance(body_value, str)
        and body_value in value_refs
    ):
        bindings["subject"] = body_value
        bound_ref_ids.append(body_value)
    unique_ref_ids = list(dict.fromkeys(bound_ref_ids))
    return bindings, [value_refs[value_id] for value_id in unique_ref_ids]


def _canonical_call_for_action(
    action: Action,
    state: MonitorState,
    previous: CanonicalToolCall,
) -> CanonicalToolCall:
    contract = state.tool_contracts.get(action.tool)
    if contract is None:
        raise AdapterError(
            "unknown tool",
            deny_reason=DenyReason.UNKNOWN_TOOL,
            failure_reason=ProofFailureReason.UNKNOWN_TOOL,
        )
    canonical = monitor_module._canonicalize_action(action, contract, state.canonicalizer)
    if not canonical.allowed or canonical.args is None:
        raise AdapterError(
            canonical.message,
            deny_reason=canonical.deny_reason or DenyReason.CANONICALIZATION_MISMATCH,
            failure_reason=_proof_failure_from_deny(canonical.deny_reason),
        )
    return replace(
        previous,
        canonical_args=canonical.args,
        action_hash=canonical_action_hash(action, canonical.args),
        authority_bearing_fields=tuple(field.name for field in contract.authority),
        contract_id=f"default:{contract.tool}",
    )


def _endorsement_challenge(action: Action, canonical_call: CanonicalToolCall) -> JsonObject:
    return {
        "type": "endorsement_challenge",
        "task_id": action.task_id,
        "agent_id": action.agent_id,
        "tool_name": action.tool,
        "action_hash": canonical_call.action_hash,
        "scope": canonical_call.canonical_args,
        "linearity": "one-shot",
        "persistent": False,
        "transferable": False,
    }


def _guard_deny(
    deny_reason: DenyReason,
    failure_reason: ProofFailureReason,
    message: str,
) -> GuardDecision:
    return GuardDecision(
        decision=VerificationDecision.DENY,
        deny_reason=deny_reason,
        failure_reason=failure_reason,
        message=message,
    )


def _proof_failure_from_deny(reason: DenyReason | None) -> ProofFailureReason:
    if reason is None:
        return ProofFailureReason.VERIFIER_REJECTED
    mapping = {
        DenyReason.UNKNOWN_TOOL: ProofFailureReason.UNKNOWN_TOOL,
        DenyReason.CANONICALIZATION_MISMATCH: ProofFailureReason.CANONICALIZATION_MISMATCH,
        DenyReason.ADAPTER_COVERAGE_GAP: ProofFailureReason.ADAPTER_COVERAGE_GAP,
        DenyReason.NO_CAP: ProofFailureReason.NO_CAP,
        DenyReason.CAP_INVALID: ProofFailureReason.CAP_INVALID,
        DenyReason.EXPIRED_CAP: ProofFailureReason.EXPIRED_CAP,
        DenyReason.REVOKED_CAP: ProofFailureReason.REVOKED_CAP,
        DenyReason.CONSUMED_CAP: ProofFailureReason.CONSUMED_CAP,
        DenyReason.RESERVED_CAP: ProofFailureReason.RESERVED_CAP,
        DenyReason.TASK_MISMATCH: ProofFailureReason.TASK_MISMATCH,
        DenyReason.AGENT_MISMATCH: ProofFailureReason.AGENT_MISMATCH,
        DenyReason.MEMORY_AUTHORITY_USE: ProofFailureReason.MEMORY_AUTHORITY_USE,
        DenyReason.MISSING_RECEIPT: ProofFailureReason.MISSING_RECEIPT,
        DenyReason.DELEGATION_MISSING: ProofFailureReason.DELEGATION_MISSING,
        DenyReason.DELEGATION_AMPLIFICATION: ProofFailureReason.DELEGATION_AMPLIFICATION,
        DenyReason.ENDORSEMENT_SCOPE_ERROR: ProofFailureReason.ENDORSEMENT_SCOPE_ERROR,
        DenyReason.DATA_CLASS_MISMATCH: ProofFailureReason.DATA_CLASS_MISMATCH,
        DenyReason.COMMAND_TEMPLATE_VIOLATION: ProofFailureReason.CANONICALIZATION_MISMATCH,
        DenyReason.TEMPLATE_ARG_REJECTED: ProofFailureReason.CANONICALIZATION_MISMATCH,
    }
    return mapping.get(reason, ProofFailureReason.VERIFIER_REJECTED)


def _deny_from_proof_failure(reason: ProofFailureReason | None) -> DenyReason | None:
    if reason is None:
        return None
    mapping = {
        ProofFailureReason.UNKNOWN_TOOL: DenyReason.UNKNOWN_TOOL,
        ProofFailureReason.CANONICALIZATION_MISMATCH: DenyReason.CANONICALIZATION_MISMATCH,
        ProofFailureReason.ADAPTER_COVERAGE_GAP: DenyReason.ADAPTER_COVERAGE_GAP,
        ProofFailureReason.NO_CAP: DenyReason.NO_CAP,
        ProofFailureReason.EXPIRED_CAP: DenyReason.EXPIRED_CAP,
        ProofFailureReason.REVOKED_CAP: DenyReason.REVOKED_CAP,
        ProofFailureReason.CONSUMED_CAP: DenyReason.CONSUMED_CAP,
        ProofFailureReason.RESERVED_CAP: DenyReason.RESERVED_CAP,
        ProofFailureReason.CAP_INVALID: DenyReason.CAP_INVALID,
        ProofFailureReason.TASK_MISMATCH: DenyReason.TASK_MISMATCH,
        ProofFailureReason.AGENT_MISMATCH: DenyReason.AGENT_MISMATCH,
        ProofFailureReason.MEMORY_AUTHORITY_USE: DenyReason.MEMORY_AUTHORITY_USE,
        ProofFailureReason.MISSING_RECEIPT: DenyReason.MISSING_RECEIPT,
        ProofFailureReason.DELEGATION_MISSING: DenyReason.DELEGATION_MISSING,
        ProofFailureReason.DELEGATION_AMPLIFICATION: DenyReason.DELEGATION_AMPLIFICATION,
        ProofFailureReason.ENDORSEMENT_SCOPE_ERROR: DenyReason.ENDORSEMENT_SCOPE_ERROR,
        ProofFailureReason.DATA_CLASS_MISMATCH: DenyReason.DATA_CLASS_MISMATCH,
    }
    return mapping.get(reason)


def _json_value(value: Any) -> JsonValue:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return str(value)
