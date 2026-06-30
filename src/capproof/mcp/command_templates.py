"""Allowlisted command templates for Stage 33S sandboxed execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Mapping

from capproof.mcp.sandbox_policy import SandboxPolicy, SandboxPolicyError
from capproof.serialization import JsonObject


SHELL_META_RE = re.compile(r"[;&|<>`$\\\n\r]")
SUSPICIOUS_WORDS = {"bash", "sh", "curl", "wget", "nc", "netcat", "ssh", "base64", "powershell"}


@dataclass(frozen=True)
class CommandExecutionPlan:
    template_id: str
    argv: tuple[str, ...]
    cwd: Path
    env: dict[str, str]
    stdin: str | None
    timeout_seconds: int
    output_limit_bytes: int
    shell: bool = False


def build_command_plan(args: JsonObject, policy: SandboxPolicy) -> CommandExecutionPlan:
    template_id = str(args.get("command_template", ""))
    if _unsafe_template_id(template_id):
        raise SandboxPolicyError("raw_shell_denied")
    if template_id != "pytest":
        raise SandboxPolicyError("unknown_template")
    template_args = args.get("args", {})
    if not isinstance(template_args, dict):
        raise SandboxPolicyError("template_args_not_object")
    unknown_args = set(template_args) - {"target", "quiet"}
    if unknown_args:
        raise SandboxPolicyError("template_arg_not_allowed")
    env = policy.sanitize_env(args.get("env", {}))
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    stdin = args.get("stdin")
    if stdin is not None:
        raise SandboxPolicyError("stdin_disabled")
    cwd = policy.ensure_cwd(str(args.get("cwd", policy.workspace_root)))
    argv = [sys.executable, "-m", "pytest"]
    target = template_args.get("target")
    if target is not None:
        if not isinstance(target, str) or _unsafe_arg(target):
            raise SandboxPolicyError("template_arg_unsafe")
        target_path = policy.resolve_workspace_path(cwd / target)
        try:
            display_target = str(target_path.relative_to(cwd))
        except ValueError:
            raise SandboxPolicyError("template_arg_outside_workspace")
        argv.append(display_target)
    if template_args.get("quiet") is True:
        argv.append("-q")
    return CommandExecutionPlan(
        template_id=template_id,
        argv=tuple(argv),
        cwd=cwd,
        env=env,
        stdin=None,
        timeout_seconds=policy.command_timeout_seconds,
        output_limit_bytes=policy.output_limit_bytes,
        shell=False,
    )


def minimal_command_env(allowed_env: Mapping[str, str]) -> dict[str, str]:
    return dict(allowed_env)


def _unsafe_template_id(value: str) -> bool:
    if not value or SHELL_META_RE.search(value):
        return True
    words = set(re.split(r"[^A-Za-z0-9_+-]+", value.lower()))
    return bool(words & SUSPICIOUS_WORDS)


def _unsafe_arg(value: str) -> bool:
    if "\x00" in value or SHELL_META_RE.search(value):
        return True
    words = set(re.split(r"[^A-Za-z0-9_+-]+", value.lower()))
    return bool(words & SUSPICIOUS_WORDS)
