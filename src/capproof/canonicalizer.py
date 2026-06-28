"""Canonicalization helpers for CapProof MVP contracts.

The shell canonicalizer intentionally supports only allowlisted command
templates. It does not claim to canonicalize arbitrary shell strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any
import unicodedata
from urllib.parse import quote, urlsplit, urlunsplit

from capproof.schemas import DenyReason, JsonObject, JsonValue, VerificationDecision

_SHELL_META = re.compile(r"[;&|<>`$\\\n\r]")
_SUSPICIOUS_COMMAND_WORDS = {
    "base64",
    "bash",
    "curl",
    "nc",
    "netcat",
    "powershell",
    "sh",
    "ssh",
    "wget",
}


@dataclass(frozen=True)
class CanonicalizationResult:
    decision: VerificationDecision
    value: JsonValue | None = None
    deny_reason: DenyReason | None = None
    message: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == VerificationDecision.ALLOW


@dataclass(frozen=True)
class CommandTemplate:
    name: str
    argv_prefix: tuple[str, ...]
    allowed_args: tuple[str, ...] = ()
    allowed_env: tuple[str, ...] = ()
    stdin_policy: str = "none"
    network_allowed: bool = False


DEFAULT_COMMAND_TEMPLATES: dict[str, CommandTemplate] = {
    "pytest": CommandTemplate(
        name="pytest",
        argv_prefix=("python", "-m", "pytest"),
        allowed_args=("target", "quiet"),
        allowed_env=("PYTEST_DISABLE_PLUGIN_AUTOLOAD",),
        stdin_policy="none",
        network_allowed=False,
    )
}


@dataclass(frozen=True)
class Canonicalizer:
    workspace_root: Path
    command_templates: dict[str, CommandTemplate] = field(
        default_factory=lambda: dict(DEFAULT_COMMAND_TEMPLATES)
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_root", self.workspace_root.resolve(strict=False))

    def canonicalize_recipient(self, recipient: str) -> CanonicalizationResult:
        if not isinstance(recipient, str):
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "recipient must be a string")
        value = recipient.strip()
        if value.count("@") != 1:
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "recipient must contain one @")
        local, domain = value.split("@", 1)
        if not local or not domain:
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "recipient local/domain missing")
        try:
            ascii_domain = domain.strip().lower().encode("idna").decode("ascii")
        except UnicodeError:
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "recipient domain is invalid IDN")
        canonical = f"{local.strip().lower()}@{ascii_domain}"
        return _allow(canonical)

    def canonicalize_file_path(self, path: str) -> CanonicalizationResult:
        if not isinstance(path, str) or not path:
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "path must be a non-empty string")
        if "\x00" in path:
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "path contains NUL")
        if unicodedata.normalize("NFC", path) != path:
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "path is not NFC-normalized")
        raw_path = Path(path).expanduser()
        candidate = raw_path if raw_path.is_absolute() else self.workspace_root / raw_path
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            return _deny(DenyReason.CAP_PREDICATE_MISMATCH, "path escapes workspace root")
        return _allow(str(resolved))

    def canonicalize_endpoint(self, endpoint: str) -> CanonicalizationResult:
        if not isinstance(endpoint, str) or not endpoint:
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "endpoint must be a string")
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "endpoint requires http(s) and host")
        if parsed.username is not None or parsed.password is not None:
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "endpoint userinfo is not allowed")
        if "%" in parsed.netloc:
            return _deny(
                DenyReason.CANONICALIZATION_MISMATCH,
                "endpoint host/netloc must not be percent-encoded",
            )
        if parsed.hostname.endswith("."):
            return _deny(
                DenyReason.CANONICALIZATION_MISMATCH,
                "endpoint host must not use a trailing dot",
            )
        try:
            host = parsed.hostname.encode("idna").decode("ascii").lower()
            port = f":{parsed.port}" if parsed.port is not None else ""
        except (UnicodeError, ValueError):
            return _deny(DenyReason.CANONICALIZATION_MISMATCH, "endpoint host is invalid")
        netloc = f"{host}{port}"
        path = quote(parsed.path or "/", safe="/:@")
        query = parsed.query
        return _allow(urlunsplit((parsed.scheme.lower(), netloc, path, query, "")))

    def canonicalize_run_shell(
        self,
        *,
        command_template: str,
        args: JsonObject,
        cwd: str,
        env: JsonObject,
        stdin: str | None,
    ) -> CanonicalizationResult:
        if not isinstance(command_template, str) or not command_template:
            return _deny(DenyReason.COMMAND_TEMPLATE_VIOLATION, "command_template must be a string")
        if _has_shell_meta(command_template) or _mentions_suspicious_command(command_template):
            return _deny(
                DenyReason.COMMAND_TEMPLATE_VIOLATION,
                "raw shell command is not an allowlisted template",
            )
        template = self.command_templates.get(command_template)
        if template is None:
            return _deny(DenyReason.COMMAND_TEMPLATE_VIOLATION, "unknown command template")
        if not isinstance(args, dict) or not isinstance(env, dict):
            return _deny(DenyReason.TEMPLATE_ARG_REJECTED, "args and env must be objects")
        unknown_args = set(args) - set(template.allowed_args)
        if unknown_args:
            return _deny(DenyReason.TEMPLATE_ARG_REJECTED, "unexpected template args")
        if set(env) - set(template.allowed_env):
            return _deny(DenyReason.COMMAND_TEMPLATE_VIOLATION, "env outside template contract")
        cwd_result = self.canonicalize_file_path(cwd)
        if not cwd_result.allowed:
            return cwd_result
        if template.stdin_policy == "none" and stdin is not None:
            return _deny(DenyReason.COMMAND_TEMPLATE_VIOLATION, "stdin is disabled by template")
        argv = list(template.argv_prefix)
        if "target" in args:
            target = args["target"]
            if not isinstance(target, str) or _unsafe_arg(target):
                return _deny(DenyReason.TEMPLATE_ARG_REJECTED, "target arg is unsafe")
            argv.append(target)
        if args.get("quiet") is True:
            argv.append("-q")
        canonical_env = {key: str(env[key]) for key in sorted(env)}
        return _allow(
            {
                "template": template.name,
                "argv": argv,
                "cwd": cwd_result.value,
                "env": canonical_env,
                "stdin": None,
            }
        )


def canonicalize_recipient(recipient: str) -> CanonicalizationResult:
    return Canonicalizer(Path.cwd()).canonicalize_recipient(recipient)


def canonicalize_file_path(path: str, *, workspace_root: str | Path) -> CanonicalizationResult:
    return Canonicalizer(Path(workspace_root)).canonicalize_file_path(path)


def canonicalize_endpoint(endpoint: str) -> CanonicalizationResult:
    return Canonicalizer(Path.cwd()).canonicalize_endpoint(endpoint)


def canonicalize_run_shell(
    *,
    command_template: str,
    args: JsonObject,
    cwd: str,
    env: JsonObject,
    stdin: str | None,
    workspace_root: str | Path,
) -> CanonicalizationResult:
    return Canonicalizer(Path(workspace_root)).canonicalize_run_shell(
        command_template=command_template,
        args=args,
        cwd=cwd,
        env=env,
        stdin=stdin,
    )


def _allow(value: JsonValue) -> CanonicalizationResult:
    return CanonicalizationResult(decision=VerificationDecision.ALLOW, value=value)


def _deny(reason: DenyReason, message: str) -> CanonicalizationResult:
    return CanonicalizationResult(
        decision=VerificationDecision.DENY,
        deny_reason=reason,
        message=message,
    )


def _has_shell_meta(value: str) -> bool:
    return _SHELL_META.search(value) is not None


def _mentions_suspicious_command(value: str) -> bool:
    words = set(re.split(r"[^A-Za-z0-9_+-]+", value.lower()))
    return bool(words & _SUSPICIOUS_COMMAND_WORDS)


def _unsafe_arg(value: str) -> bool:
    if _has_shell_meta(value):
        return True
    if _mentions_suspicious_command(value):
        return True
    return "\x00" in value
