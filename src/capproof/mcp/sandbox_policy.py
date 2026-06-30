"""Policy checks for the Stage 33S MCP sandbox executor.

The sandbox is not an authorization root. It only constrains effects after the
CapProof guard and Reference Monitor have already returned ALLOW.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class SandboxPolicyError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


SECRET_NAMES = {
    ".env",
    ".env.local",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}
SECRET_SUFFIXES = {".pem", ".key"}
SECRET_DIRS = {".git", ".ssh", ".aws", ".config"}


@dataclass(frozen=True)
class SandboxPolicy:
    workspace_root: Path
    max_file_bytes: int = 1024 * 1024
    command_timeout_seconds: int = 10
    output_limit_bytes: int = 8192
    allowed_env: tuple[str, ...] = ("PYTEST_DISABLE_PLUGIN_AUTOLOAD",)

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_root", self.workspace_root.resolve(strict=False))

    def resolve_workspace_path(self, path: str | Path, *, for_write: bool = False) -> Path:
        raw = Path(path)
        if not str(path):
            raise SandboxPolicyError("path_empty")
        if "\x00" in str(path):
            raise SandboxPolicyError("path_nul")
        candidate = raw if raw.is_absolute() else self.workspace_root / raw
        parent = candidate.parent.resolve(strict=False)
        if for_write:
            _ensure_under_workspace(parent, self.workspace_root, "parent_outside_workspace")
        resolved = candidate.resolve(strict=False)
        _ensure_under_workspace(resolved, self.workspace_root, "path_outside_workspace")
        self.ensure_not_secret_path(resolved)
        return resolved

    def ensure_readable_file(self, path: Path) -> None:
        if not path.exists():
            raise SandboxPolicyError("file_missing")
        if not path.is_file():
            raise SandboxPolicyError("not_regular_file")
        if path.stat().st_size > self.max_file_bytes:
            raise SandboxPolicyError("file_too_large")

    def ensure_write_allowed(self, path: Path, *, content: str, overwrite: bool) -> None:
        if len(content.encode("utf-8")) > self.max_file_bytes:
            raise SandboxPolicyError("content_too_large")
        if path.exists() and path.is_symlink():
            raise SandboxPolicyError("symlink_write_denied")
        if path.exists() and not overwrite:
            raise SandboxPolicyError("file_exists")
        path.parent.mkdir(parents=True, exist_ok=True)

    def sanitize_env(self, env: Mapping[str, object] | None) -> dict[str, str]:
        sanitized: dict[str, str] = {}
        for key, value in dict(env or {}).items():
            if key not in self.allowed_env:
                raise SandboxPolicyError("env_key_not_allowed")
            if _looks_secret_name(key):
                raise SandboxPolicyError("env_secret_key_denied")
            text = str(value)
            if len(text) > 1024:
                raise SandboxPolicyError("env_value_too_large")
            sanitized[key] = text
        return sanitized

    def ensure_cwd(self, cwd: str | Path) -> Path:
        resolved = self.resolve_workspace_path(cwd, for_write=False)
        if not resolved.exists():
            raise SandboxPolicyError("cwd_missing")
        if not resolved.is_dir():
            raise SandboxPolicyError("cwd_not_directory")
        return resolved

    def ensure_not_secret_path(self, path: Path) -> None:
        parts = set(path.relative_to(self.workspace_root).parts)
        if parts & SECRET_DIRS:
            raise SandboxPolicyError("secret_path_denied")
        name = path.name
        if name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES:
            raise SandboxPolicyError("secret_path_denied")


def _ensure_under_workspace(path: Path, workspace_root: Path, reason: str) -> None:
    try:
        path.relative_to(workspace_root)
    except ValueError as exc:
        raise SandboxPolicyError(reason) from exc


def _looks_secret_name(name: str) -> bool:
    upper = name.upper()
    return any(token in upper for token in ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"))
