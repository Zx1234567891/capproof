"""Runtime context for the CapProof MCP product layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile

from capproof.agent_adapter import (
    AgentAdapterRegistry,
    AgentRuntimeState,
    CapProofMiddleware,
    HermesAgentLikeAdapter,
    GuardedExecutor,
)
from capproof.canonicalizer import Canonicalizer
from capproof.capability_store import InMemoryCapabilityStore, mint_capability
from capproof.mcp.executors import MCPMockExecutor
from capproof.mcp.trace import TraceRecorder
from capproof.monitor import MonitorState
from capproof.provenance import ProvenanceRuntime
from capproof.receipts import InMemoryReceiptStore
from capproof.schemas import (
    ActionKind,
    AuthorityRole,
    Capability,
    CapabilityRoot,
    Linearity,
)
from capproof.agent_adapter import profile_tool_contract_registry


DEFAULT_TASK_ID = "hermes_mcp_test"
DEFAULT_AGENT_ID = "hermes_agent"


@dataclass
class CapProofMCPContext:
    workspace: Path
    trace_path: Path
    task_id: str
    agent_id: str
    monitor_state: MonitorState
    runtime_state: AgentRuntimeState
    middleware: CapProofMiddleware
    guarded_executor: GuardedExecutor
    executor: MCPMockExecutor
    trace_recorder: TraceRecorder


def make_default_context(
    *,
    workspace: str | Path | None = None,
    trace_path: str | Path | None = None,
    task_id: str = DEFAULT_TASK_ID,
    agent_id: str = DEFAULT_AGENT_ID,
) -> CapProofMCPContext:
    workspace_path = Path(workspace or tempfile.mkdtemp(prefix="capproof_mcp_workspace_")).resolve(
        strict=False
    )
    workspace_path.mkdir(parents=True, exist_ok=True)
    trace_file = Path(trace_path or workspace_path / "capproof_mcp_trace.jsonl")
    trace_file.parent.mkdir(parents=True, exist_ok=True)
    monitor_state = MonitorState(
        capability_store=InMemoryCapabilityStore(),
        receipt_store=InMemoryReceiptStore(),
        tool_contracts=profile_tool_contract_registry(),
        canonicalizer=Canonicalizer(workspace_path),
    )
    runtime = ProvenanceRuntime(task_id=task_id, agent_id=agent_id, receipt_store=monitor_state.receipt_store)
    value, _receipt = runtime.record_tool_out(
        tool="summarize",
        output_id="val_summary",
        data_class="summary(report)",
        content="summary",
        provenance_root="USER",
    )
    _mint_default_capabilities(monitor_state, workspace_path=workspace_path, task_id=task_id, agent_id=agent_id)
    middleware = CapProofMiddleware(
        AgentAdapterRegistry(
            (
                HermesAgentLikeAdapter(
                    tool_contracts=monitor_state.tool_contracts,
                    canonicalizer=monitor_state.canonicalizer,
                ),
            )
        )
    )
    executor = MCPMockExecutor(workspace_path)
    return CapProofMCPContext(
        workspace=workspace_path,
        trace_path=trace_file,
        task_id=task_id,
        agent_id=agent_id,
        monitor_state=monitor_state,
        runtime_state=AgentRuntimeState(
            monitor_state=monitor_state,
            value_refs={value.value_id: value},
            authspec_ref="hermes_capproof_mcp_server",
        ),
        middleware=middleware,
        guarded_executor=GuardedExecutor(executor),
        executor=executor,
        trace_recorder=TraceRecorder(trace_file),
    )


def _mint_default_capabilities(
    state: MonitorState,
    *,
    workspace_path: Path,
    task_id: str,
    agent_id: str,
) -> None:
    alice = state.canonicalizer.canonicalize_recipient("alice@example.com").value
    workspace = str(workspace_path)
    caps = (
        Capability(
            cap_id="cap_mcp_send_message_alice",
            issuer="stage31m",
            root=CapabilityRoot.USER,
            agent_id=agent_id,
            task_id=task_id,
            action_kind=ActionKind.SEND,
            tool="send_message",
            role=AuthorityRole.RECIPIENT,
            predicate={"op": "eq", "value": alice},
            linearity=Linearity.REUSABLE,
            max_uses=100,
            uses=0,
            expires_at="task_end",
            nonce="nonce:cap_mcp_send_message_alice",
        ),
        Capability(
            cap_id="cap_mcp_read_workspace",
            issuer="stage31m",
            root=CapabilityRoot.USER,
            agent_id=agent_id,
            task_id=task_id,
            action_kind=ActionKind.READ,
            tool="read_file",
            role=AuthorityRole.FILE_PATH,
            predicate={"op": "subtree", "root": workspace},
            linearity=Linearity.REUSABLE,
            max_uses=100,
            uses=0,
            expires_at="task_end",
            nonce="nonce:cap_mcp_read_workspace",
        ),
        Capability(
            cap_id="cap_mcp_write_workspace",
            issuer="stage31m",
            root=CapabilityRoot.USER,
            agent_id=agent_id,
            task_id=task_id,
            action_kind=ActionKind.WRITE,
            tool="write_file",
            role=AuthorityRole.FILE_PATH,
            predicate={"op": "subtree", "root": workspace},
            linearity=Linearity.REUSABLE,
            max_uses=100,
            uses=0,
            expires_at="task_end",
            nonce="nonce:cap_mcp_write_workspace",
        ),
        Capability(
            cap_id="cap_mcp_write_mode_create",
            issuer="stage31m",
            root=CapabilityRoot.USER,
            agent_id=agent_id,
            task_id=task_id,
            action_kind=ActionKind.WRITE,
            tool="write_file",
            role=AuthorityRole.COMMAND,
            predicate={"op": "in", "values": ["create", "overwrite", False, True]},
            linearity=Linearity.REUSABLE,
            max_uses=100,
            uses=0,
            expires_at="task_end",
            nonce="nonce:cap_mcp_write_mode_create",
        ),
        Capability(
            cap_id="cap_mcp_shell_template_pytest",
            issuer="stage31m",
            root=CapabilityRoot.USER,
            agent_id=agent_id,
            task_id=task_id,
            action_kind=ActionKind.EXEC,
            tool="run_shell",
            role=AuthorityRole.COMMAND,
            predicate={"op": "in", "values": ["pytest", {}, {"target": "tests/"}, {"quiet": True}]},
            linearity=Linearity.REUSABLE,
            max_uses=100,
            uses=0,
            expires_at="task_end",
            nonce="nonce:cap_mcp_shell_template_pytest",
        ),
        Capability(
            cap_id="cap_mcp_shell_cwd_workspace",
            issuer="stage31m",
            root=CapabilityRoot.USER,
            agent_id=agent_id,
            task_id=task_id,
            action_kind=ActionKind.EXEC,
            tool="run_shell",
            role=AuthorityRole.FILE_PATH,
            predicate={"op": "subtree", "root": workspace},
            linearity=Linearity.REUSABLE,
            max_uses=100,
            uses=0,
            expires_at="task_end",
            nonce="nonce:cap_mcp_shell_cwd_workspace",
        ),
    )
    for cap in caps:
        mint_capability(state.capability_store, cap)
