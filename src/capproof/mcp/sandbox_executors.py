"""Sandboxed real executors for the CapProof MCP product layer."""

from __future__ import annotations

from pathlib import Path
import subprocess

from capproof.agent_adapter import CanonicalToolCall
from capproof.mcp.command_templates import build_command_plan, minimal_command_env
from capproof.mcp.executors import MCPMockExecutor
from capproof.mcp.sandbox import WorkspaceSandbox
from capproof.mcp.sandbox_policy import SandboxPolicy, SandboxPolicyError
from capproof.serialization import JsonObject


class SandboxedMCPExecutor(MCPMockExecutor):
    """Executor that performs only workspace-local file IO and templates.

    Unsupported tools still fall back to ``MCPMockExecutor``. The sandbox does
    not authorize anything; it only constrains an already-ALLOWed call.
    """

    def __init__(self, workspace_root: str | Path, *, policy: SandboxPolicy | None = None) -> None:
        super().__init__(workspace_root)
        self.policy = policy or SandboxPolicy(self.workspace_root)
        self.workspace_sandbox = WorkspaceSandbox(self.policy)
        self.real_file_reads = 0
        self.real_file_writes = 0
        self.real_command_templates = 0

    def execute(self, call: CanonicalToolCall) -> JsonObject:
        if call.tool_name == "read_file":
            event = self._sandbox_read_file(call.canonical_args)
        elif call.tool_name == "write_file":
            event = self._sandbox_write_file(call.canonical_args)
        elif call.tool_name == "run_shell":
            event = self._sandbox_run_command_template(call.canonical_args)
        else:
            event = super().execute(call)
            event["executor"] = "mock_fallback"
            return event
        self.executions.append(event)
        return event

    def _sandbox_read_file(self, args: JsonObject) -> JsonObject:
        try:
            event = self.workspace_sandbox.read_text(str(args.get("path", "")))
        except SandboxPolicyError as exc:
            return _refused("read_workspace_file", exc.reason)
        self.real_file_reads += 1
        event["executor"] = "sandboxed_real"
        event["executed"] = True
        return event

    def _sandbox_write_file(self, args: JsonObject) -> JsonObject:
        try:
            event = self.workspace_sandbox.write_text(
                str(args.get("path", "")),
                str(args.get("content", "")),
                overwrite=bool(args.get("overwrite", False) or args.get("mode") == "overwrite"),
            )
        except SandboxPolicyError as exc:
            return _refused("write_workspace_file", exc.reason)
        self.real_file_writes += 1
        event["executor"] = "sandboxed_real"
        event["executed"] = True
        return event

    def _sandbox_run_command_template(self, args: JsonObject) -> JsonObject:
        try:
            plan = build_command_plan(args, self.policy)
            completed = subprocess.run(
                list(plan.argv),
                cwd=str(plan.cwd),
                env=minimal_command_env(plan.env),
                input=plan.stdin,
                text=True,
                capture_output=True,
                timeout=plan.timeout_seconds,
                shell=False,
                check=False,
            )
        except SandboxPolicyError as exc:
            return _refused("run_command_template", exc.reason)
        except subprocess.TimeoutExpired as exc:
            return {
                "sandbox_tool": "run_command_template",
                "executor": "sandboxed_real",
                "executed": False,
                "timed_out": True,
                "shell": False,
                "stdout": _cap_text(str(exc.stdout or ""), self.policy.output_limit_bytes),
                "stderr": _cap_text(str(exc.stderr or ""), self.policy.output_limit_bytes),
            }
        self.real_command_templates += 1
        return {
            "sandbox_tool": "run_command_template",
            "executor": "sandboxed_real",
            "executed": True,
            "side_effect": "allowlisted_command_template",
            "template_id": plan.template_id,
            "argv": list(plan.argv),
            "cwd": str(plan.cwd),
            "shell": False,
            "timeout_seconds": plan.timeout_seconds,
            "stdout": _cap_text(completed.stdout, plan.output_limit_bytes),
            "stderr": _cap_text(completed.stderr, plan.output_limit_bytes),
            "stdout_truncated": len(completed.stdout.encode("utf-8")) > plan.output_limit_bytes,
            "stderr_truncated": len(completed.stderr.encode("utf-8")) > plan.output_limit_bytes,
            "returncode": completed.returncode,
        }


def _refused(tool: str, reason: str) -> JsonObject:
    return {
        "sandbox_tool": tool,
        "executor": "sandboxed_real",
        "executed": False,
        "sandbox_refused": True,
        "reason": reason,
    }


def _cap_text(value: str, limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    return encoded[:limit].decode("utf-8", errors="replace")
