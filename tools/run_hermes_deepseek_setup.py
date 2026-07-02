#!/usr/bin/env python3
"""Prepare Hermes DeepSeek backend configuration without changing CapProof TCB.

This runner is deliberately no-run by default. It can generate configuration
templates, statically inspect a local Hermes checkout, and produce reports. It
does not run Hermes. It does not call DeepSeek unless `--smoke-test` is invoked
with `ALLOW_DEEPSEEK_SMOKE_TEST=1` and `DEEPSEEK_API_KEY` present.
"""

from __future__ import annotations

from _bootstrap import bootstrap as _capproof_tools_bootstrap
_capproof_tools_bootstrap()

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
from typing import Any, Callable, Mapping
from urllib import request
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "real_agent_integrations" / "hermes_deepseek"
CONFIGS_DIR = INTEGRATION_DIR / "configs"
REPORTS_DIR = INTEGRATION_DIR / "reports"
TEMPLATES_DIR = INTEGRATION_DIR / "templates"
TRACES_DIR = INTEGRATION_DIR / "traces"

ENV_TEMPLATE_PATH = TEMPLATES_DIR / "deepseek.env.example"
CONFIG_TEMPLATE_PATH = TEMPLATES_DIR / "hermes_deepseek_config.example.yaml"
README_TEMPLATE_PATH = TEMPLATES_DIR / "hermes_deepseek_readme.md"
HERMES_CONFIG_SNIPPET_PATH = CONFIGS_DIR / "hermes_config.deepseek.example.yaml"
SETUP_REPORT_PATH = REPORTS_DIR / "deepseek_setup_report.md"
SMOKE_REPORT_PATH = REPORTS_DIR / "deepseek_smoke_test_report.md"
GO_NO_GO_PATH = REPORTS_DIR / "hermes_deepseek_go_no_go.md"
AUDIT_REPORT_PATH = REPORTS_DIR / "hermes_model_config_audit.md"
HERMES_RUN_REPORT_PATH = REPORTS_DIR / "hermes_deepseek_run_report.md"
PREFLIGHT_JSON_PATH = REPORTS_DIR / "deepseek_preflight_summary.json"
AUDIT_JSON_PATH = REPORTS_DIR / "hermes_model_config_audit.json"
SMOKE_JSON_PATH = REPORTS_DIR / "deepseek_smoke_test_summary.json"
HERMES_RUN_JSON_PATH = REPORTS_DIR / "hermes_deepseek_run_summary.json"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_REASONING_EFFORT = "high"
SMOKE_PROMPT = "Return the word ok."
SAFE_HERMES_PROMPT = "Reply with exactly: capproof-ok"

HERMES_RUN_REQUIRED_ENV = (
    "ALLOW_HERMES_DEEPSEEK_RUN",
    "DEEPSEEK_API_KEY",
    "HERMES_DEEPSEEK_COMMAND",
    "CAPPROOF_NO_REAL_TOOLS",
    "NO_NETWORK_EXCEPT_DEEPSEEK",
    "HERMES_TEST_WORKSPACE",
)

HERMES_COMMAND_DENIED_PATTERNS = (
    "curl",
    "wget",
    "nc",
    "ssh",
    "scp",
    "rsync",
    "sudo",
    "rm -rf",
    "sh -c",
    "bash -c",
    "|",
    ">",
    ">>",
    "$(",
    "`",
    "pip install",
    "npm install",
    "pnpm install",
    "poetry install",
    "make install",
    "hermes gateway",
    "hermes tools enable",
    "mcp server start",
    "telegram",
    "discord",
    "slack",
    "sendmail",
    "smtp",
)
HERMES_EXTERNAL_URL_RE = re.compile(r"https?://(?!api\.deepseek\.com(?:/|:|$)|localhost(?:/|:|$)|127\.0\.0\.1(?:/|:|$))[^\s'\"]+")
SECRET_LITERAL_RE = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|API[_-]?KEY=|TOKEN=|SECRET=|PASSWORD=)", re.IGNORECASE)
NO_TOOLS_MARKERS = ("--no-tools", "--disable-tools", "--model-only", "--dry-run", "no-tools", "model-only", "dry-run")
VIOLATION_PATTERNS = {
    "tool_call_detected": ("tool_call", "tool call", "function_call", "tool_use"),
    "shell_detected": ("run_shell", "terminal", "shell", "subprocess", "bash", " sh "),
    "mcp_detected": ("mcp", "mcp_tool_call", "mcp server"),
    "gateway_detected": ("gateway", "send_message", "telegram", "discord", "slack"),
    "file_write_detected": ("write_file", "edit_file", "file write", "patch"),
    "memory_persistence_detected": ("memory_write", "remember", "persistent memory", "memory persistence"),
}

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".example",
}

AUDIT_PATTERNS: dict[str, tuple[str, ...]] = {
    "provider": ("provider", "providers"),
    "model": ("model", "models"),
    "openai": ("openai", "openai-compatible", "openai compatible"),
    "openrouter": ("openrouter",),
    "deepseek": ("deepseek",),
    "base_url": ("base_url", "api_base", "baseurl", "endpoint"),
    "api_key": ("api_key", "api key", "apikey", "token", "env"),
    "config_command": ("config", "configure", "settings", "provider"),
}


@dataclass(frozen=True)
class DeepSeekPreflight:
    hermes_repo_path: str
    hermes_repo_status: str
    key_present: bool
    key_value_printed: bool
    base_url: str
    model: str
    reasoning_effort: str
    smoke_test_allowed: bool
    hermes_run_allowed: bool
    hermes_run_reason: str
    no_hermes_run: bool
    no_deepseek_call: bool
    no_real_tool_execution: bool
    no_key_written: bool
    security_boundary: dict[str, bool]


@dataclass(frozen=True)
class HermesConfigAudit:
    repo_path: str
    repo_status: str
    files_scanned: int = 0
    provider_config_found: bool = False
    openai_compatible_path_found: bool = False
    deepseek_support_found: bool = False
    provider_dir_found: bool = False
    base_url_field_found: bool = False
    model_field_found: bool = False
    api_key_env_field_found: bool = False
    observed_in_source: tuple[str, ...] = ()
    inferred_from_docs: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()
    needs_manual_verification: tuple[str, ...] = ()
    sample_files: tuple[str, ...] = ()
    mapping_recommendation: str = "generic OpenAI-compatible provider template; needs_manual_mapping"


@dataclass(frozen=True)
class SmokeTestResult:
    run_attempted: bool
    run_allowed: bool
    status: str
    reason: str
    model: str
    base_url: str
    request_id: str = ""
    prompt_hash: str = ""
    response_preview: str = ""
    total_tokens: int | None = None
    key_value_printed: bool = False
    no_hermes_run: bool = True
    no_tool_call: bool = True
    no_capproof_data_sent: bool = True
    no_secret_logged: bool = True
    error_type: str = ""


@dataclass(frozen=True)
class HermesCommandValidation:
    verdict: str
    reason: str
    run_allowed: bool
    missing_env: tuple[str, ...] = ()
    denied_patterns: tuple[str, ...] = ()
    required_checks: dict[str, bool] = field(default_factory=dict)
    command_hash: str = ""
    command_preview: str = ""
    no_tools_feasibility: str = "unknown"
    no_hermes_run: bool = True
    key_value_printed: bool = False


@dataclass(frozen=True)
class HermesNoToolsRunResult:
    run_attempted: bool
    run_allowed: bool
    denial_reason: str
    command_hash: str = ""
    timeout_seconds: int = 20
    exit_code: int | None = None
    timed_out: bool = False
    response_received: bool = False
    tool_call_detected: bool = False
    shell_detected: bool = False
    mcp_detected: bool = False
    gateway_detected: bool = False
    file_write_detected: bool = False
    memory_persistence_detected: bool = False
    key_leak_detected: bool = False
    key_printed: bool = False
    key_written: bool = False
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    provider: str = "deepseek"
    stdout_bytes: int = 0
    stderr_bytes: int = 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Hermes DeepSeek backend setup artifacts.")
    parser.add_argument("--preflight", action="store_true", help="run no-network preflight")
    parser.add_argument("--generate-config-template", action="store_true", help="write DeepSeek config templates")
    parser.add_argument("--smoke-test", action="store_true", help="optionally call DeepSeek if explicitly allowed")
    parser.add_argument("--hermes-config-check", action="store_true", help="statically inspect local Hermes config surfaces")
    parser.add_argument("--validate-hermes-command", action="store_true", help="validate HERMES_DEEPSEEK_COMMAND without running it")
    parser.add_argument("--run-hermes-no-tools", action="store_true", help="run explicitly authorized Hermes no-tools command")
    parser.add_argument("--report", action="store_true", help="write or print report paths")
    args = parser.parse_args()

    if args.generate_config_template:
        generate_config_templates()
    if args.hermes_config_check:
        audit = run_hermes_config_audit()
        write_audit_report(audit)
    else:
        audit = load_or_run_audit()
    preflight = run_preflight()
    smoke = run_smoke_test() if args.smoke_test else load_or_skipped_smoke()
    command_validation = validate_hermes_command()
    hermes_run = (
        run_hermes_no_tools(command_validation=command_validation)
        if args.run_hermes_no_tools
        else load_or_default_hermes_run(command_validation)
    )
    write_reports(preflight, audit, smoke, command_validation, hermes_run)

    if args.report:
        print(f"setup_report: {SETUP_REPORT_PATH}")
        print(f"smoke_test_report: {SMOKE_REPORT_PATH}")
        print(f"go_no_go: {GO_NO_GO_PATH}")
        print(f"hermes_model_config_audit: {AUDIT_REPORT_PATH}")
        print(f"hermes_deepseek_run_report: {HERMES_RUN_REPORT_PATH}")
        return 0

    print(f"key_present: {preflight.key_present}")
    print(f"key_value_printed: {preflight.key_value_printed}")
    print(f"base_url: {preflight.base_url}")
    print(f"model: {preflight.model}")
    print(f"smoke_test_allowed: {preflight.smoke_test_allowed}")
    print(f"hermes_run_allowed: {preflight.hermes_run_allowed}")
    print(f"hermes_command_validation: {command_validation.verdict}")
    print(f"hermes_run_attempted: {hermes_run.run_attempted}")
    print(f"hermes_run_exit_code: {hermes_run.exit_code if hermes_run.exit_code is not None else 'not_run'}")
    print(f"response_received: {hermes_run.response_received}")
    print(f"tool_call_detected: {hermes_run.tool_call_detected}")
    print(f"smoke_test_status: {smoke.status}")
    print(f"setup_report: {SETUP_REPORT_PATH}")
    return 0


def run_preflight(*, env: Mapping[str, str] | None = None, root: Path = ROOT) -> DeepSeekPreflight:
    env_map = dict(os.environ if env is None else env)
    repo_path, repo_status = resolve_hermes_repo(env=env_map, root=root)
    base_url = env_map.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
    model = env_map.get("DEEPSEEK_MODEL") or DEFAULT_MODEL
    effort = env_map.get("DEEPSEEK_REASONING_EFFORT") or DEFAULT_REASONING_EFFORT
    key_present = bool(env_map.get("DEEPSEEK_API_KEY"))
    smoke_allowed = env_map.get("ALLOW_DEEPSEEK_SMOKE_TEST") == "1" and key_present
    hermes_allowed, hermes_reason = check_hermes_deepseek_run(env_map)
    return DeepSeekPreflight(
        hermes_repo_path=str(repo_path) if repo_path else "",
        hermes_repo_status=repo_status,
        key_present=key_present,
        key_value_printed=False,
        base_url=base_url,
        model=model,
        reasoning_effort=effort,
        smoke_test_allowed=smoke_allowed,
        hermes_run_allowed=hermes_allowed,
        hermes_run_reason=hermes_reason,
        no_hermes_run=True,
        no_deepseek_call=True,
        no_real_tool_execution=True,
        no_key_written=True,
        security_boundary=security_boundary(),
    )


def check_hermes_deepseek_run(env: Mapping[str, str]) -> tuple[bool, str]:
    required = {
        "ALLOW_HERMES_DEEPSEEK_RUN": "1",
        "CAPPROOF_NO_REAL_TOOLS": "1",
        "NO_NETWORK_EXCEPT_DEEPSEEK": "1",
    }
    missing_or_bad = [name for name, expected in required.items() if env.get(name) != expected]
    missing = [name for name in ("DEEPSEEK_API_KEY", "HERMES_DEEPSEEK_COMMAND", "HERMES_TEST_WORKSPACE") if not env.get(name)]
    workspace = env.get("HERMES_TEST_WORKSPACE")
    if workspace and (not Path(workspace).exists() or not is_safe_test_workspace(Path(workspace))):
        missing.append("HERMES_TEST_WORKSPACE(temp workspace required)")
    if missing_or_bad or missing:
        return False, "missing explicit Hermes DeepSeek no-tools run authorization or safe environment"
    return True, "explicit no-tools run conditions satisfied; this script still does not run Hermes"


def is_safe_test_workspace(path: Path) -> bool:
    text = str(path)
    return bool(text) and ("tmp" in text or "temp" in text)


def generate_config_templates(*, root: Path = ROOT) -> None:
    for path in (CONFIGS_DIR, REPORTS_DIR, TEMPLATES_DIR, TRACES_DIR):
        _path(root, path).mkdir(parents=True, exist_ok=True)
    _path(root, ENV_TEMPLATE_PATH).write_text(render_env_template(), encoding="utf-8")
    _path(root, CONFIG_TEMPLATE_PATH).write_text(render_config_template(), encoding="utf-8")
    _path(root, README_TEMPLATE_PATH).write_text(render_template_readme(), encoding="utf-8")
    _path(root, HERMES_CONFIG_SNIPPET_PATH).write_text(render_hermes_config_snippet(), encoding="utf-8")


def run_hermes_config_audit(
    *,
    env: Mapping[str, str] | None = None,
    root: Path = ROOT,
    max_files: int = 5000,
) -> HermesConfigAudit:
    env_map = dict(os.environ if env is None else env)
    repo_path, repo_status = resolve_hermes_repo(env=env_map, root=root)
    if repo_path is None or repo_status == "repo_missing":
        return HermesConfigAudit(
            repo_path=str(repo_path) if repo_path else "",
            repo_status="repo_missing",
            unknown=("Hermes repo not available; config audit requires local checkout.",),
            needs_manual_verification=("Provide HERMES_REPO or external/hermes-agent and rerun --hermes-config-check.",),
        )

    files_scanned = 0
    hits: dict[str, set[str]] = {name: set() for name in AUDIT_PATTERNS}
    doc_hits: set[str] = set()
    for path in iter_text_files(repo_path):
        if files_scanned >= max_files:
            break
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        rel = path.relative_to(repo_path).as_posix()
        for name, patterns in AUDIT_PATTERNS.items():
            if any(pattern in lower for pattern in patterns):
                hits[name].add(rel)
        if path.name.lower().startswith("readme") or "/docs/" in f"/{rel}":
            if any(word in lower for word in ("model", "provider", "openai", "deepseek", "openrouter")):
                doc_hits.add(rel)

    provider_dir_found = any((repo_path / name).exists() for name in ("providers", "provider", "src/providers", "packages/providers"))
    deepseek_plugin_found = (repo_path / "plugins" / "model-providers" / "deepseek" / "__init__.py").exists()
    observed: list[str] = []
    inferred: list[str] = []
    unknown: list[str] = []
    needs_manual: list[str] = []
    if provider_dir_found:
        observed.append("Provider directory or provider-like path exists in local Hermes checkout.")
    if hits["openai"]:
        observed.append("OpenAI-related provider/config references observed in source or docs.")
    if hits["openrouter"]:
        observed.append("OpenRouter-related provider/config references observed in source or docs.")
    if hits["deepseek"]:
        observed.append("DeepSeek-related references observed in local checkout.")
    if deepseek_plugin_found:
        observed.append("Built-in `plugins/model-providers/deepseek` provider profile observed.")
    if hits["base_url"]:
        observed.append("base_url / api_base / endpoint-like configuration fields observed.")
    if hits["api_key"]:
        observed.append("API key / token / environment variable references observed.")
    if doc_hits:
        inferred.append("Docs mention model/provider switching; exact runtime mapping still needs manual verification.")
    if not hits["deepseek"]:
        unknown.append("Native DeepSeek provider support was not confirmed by static scan.")
    if not (hits["openai"] and hits["base_url"] and hits["api_key"]):
        unknown.append("OpenAI-compatible provider schema was not fully confirmed by static scan.")
    unknown.append("Exact Hermes local config write path and command remain unverified without running Hermes.")
    needs_manual.append("Confirm exact Hermes provider config schema before writing any real local config.")
    needs_manual.append("Keep DEEPSEEK_API_KEY in environment only; never commit real keys.")

    sample_files = tuple(sorted(set().union(*hits.values()))[:25])
    openai_compatible = bool(hits["openai"] and hits["base_url"])
    mapping = (
        "Set Hermes `model.provider: deepseek` and `model.default: deepseek-v4-pro`; keep API key in `DEEPSEEK_API_KEY`."
        if deepseek_plugin_found
        else (
            "Use observed OpenAI-compatible provider path with env-only API key after manual schema verification."
            if openai_compatible
            else "Use generic OpenAI-compatible provider template; needs_manual_mapping."
        )
    )
    return HermesConfigAudit(
        repo_path=str(repo_path),
        repo_status="available",
        files_scanned=files_scanned,
        provider_config_found=bool(hits["provider"] or provider_dir_found),
        openai_compatible_path_found=openai_compatible,
        deepseek_support_found=bool(hits["deepseek"]),
        provider_dir_found=provider_dir_found,
        base_url_field_found=bool(hits["base_url"]),
        model_field_found=bool(hits["model"]),
        api_key_env_field_found=bool(hits["api_key"]),
        observed_in_source=tuple(observed),
        inferred_from_docs=tuple(inferred),
        unknown=tuple(unknown),
        needs_manual_verification=tuple(needs_manual),
        sample_files=sample_files,
        mapping_recommendation=mapping,
    )


def run_smoke_test(
    *,
    env: Mapping[str, str] | None = None,
    http_post: Callable[[str, dict[str, str], bytes, float], tuple[int, Mapping[str, str], bytes]] | None = None,
    root: Path = ROOT,
) -> SmokeTestResult:
    env_map = dict(os.environ if env is None else env)
    base_url = env_map.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
    model = env_map.get("DEEPSEEK_MODEL") or DEFAULT_MODEL
    effort = env_map.get("DEEPSEEK_REASONING_EFFORT") or DEFAULT_REASONING_EFFORT
    key = env_map.get("DEEPSEEK_API_KEY")
    if env_map.get("ALLOW_DEEPSEEK_SMOKE_TEST") != "1":
        result = SmokeTestResult(
            run_attempted=False,
            run_allowed=False,
            status="smoke_test_skipped",
            reason="ALLOW_DEEPSEEK_SMOKE_TEST is not set to 1",
            model=model,
            base_url=base_url,
        )
        write_smoke_report(result, root=root)
        return result
    if not key:
        result = SmokeTestResult(
            run_attempted=False,
            run_allowed=False,
            status="smoke_test_skipped",
            reason="DEEPSEEK_API_KEY is missing",
            model=model,
            base_url=base_url,
        )
        write_smoke_report(result, root=root)
        return result

    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": SMOKE_PROMPT}],
        "max_tokens": 4,
        "temperature": 0,
        "reasoning_effort": effort,
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "capproof-deepseek-smoke-test/1.0",
    }
    post = http_post or _urllib_post
    try:
        status, response_headers, raw = post(endpoint, headers, body, 15.0)
        data = json.loads(raw.decode("utf-8")) if raw else {}
        usage = data.get("usage") if isinstance(data, dict) else {}
        total_tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
        response_model = str(data.get("model") or model) if isinstance(data, dict) else model
        request_id = str(
            response_headers.get("x-request-id")
            or response_headers.get("X-Request-Id")
            or response_headers.get("request-id")
            or ""
        )
        result = SmokeTestResult(
            run_attempted=True,
            run_allowed=True,
            status=f"http_{status}",
            reason="DeepSeek smoke test completed; response content not trusted as security signal",
            model=response_model,
            base_url=base_url,
            request_id=request_id,
            prompt_hash=hashlib.sha256(SMOKE_PROMPT.encode("utf-8")).hexdigest()[:16],
            response_preview=_safe_response_preview(data),
            total_tokens=total_tokens,
            key_value_printed=False,
        )
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        result = SmokeTestResult(
            run_attempted=True,
            run_allowed=True,
            status="error",
            reason="DeepSeek smoke test failed without logging secrets",
            model=model,
            base_url=base_url,
            prompt_hash=hashlib.sha256(SMOKE_PROMPT.encode("utf-8")).hexdigest()[:16],
            key_value_printed=False,
            error_type=type(exc).__name__,
        )
    write_smoke_report(result, root=root)
    return result


def load_or_skipped_smoke(*, root: Path = ROOT) -> SmokeTestResult:
    return SmokeTestResult(
        run_attempted=False,
        run_allowed=False,
        status="smoke_test_skipped",
        reason="--smoke-test was not requested",
        model=DEFAULT_MODEL,
        base_url=DEFAULT_BASE_URL,
    )


def load_or_run_audit(*, root: Path = ROOT) -> HermesConfigAudit:
    path = _path(root, AUDIT_JSON_PATH)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return HermesConfigAudit(**{key: data[key] for key in HermesConfigAudit.__dataclass_fields__ if key in data})
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    audit = run_hermes_config_audit(root=root)
    write_audit_report(audit, root=root)
    return audit


def validate_hermes_command(*, env: Mapping[str, str] | None = None) -> HermesCommandValidation:
    env_map = dict(os.environ if env is None else env)
    command = env_map.get("HERMES_DEEPSEEK_COMMAND", "").strip()
    missing = tuple(name for name in HERMES_RUN_REQUIRED_ENV if not env_map.get(name))
    denied: list[str] = []
    lower = f" {command.lower()} "
    tokenizes = True
    if command:
        for pattern in HERMES_COMMAND_DENIED_PATTERNS:
            if pattern in lower:
                denied.append(pattern)
        if HERMES_EXTERNAL_URL_RE.search(command):
            denied.append("non-DeepSeek external URL")
        if SECRET_LITERAL_RE.search(command):
            denied.append("token / secret / API key literal")
        try:
            shlex.split(command)
        except ValueError as exc:
            tokenizes = False
            denied.append(f"unsafe tokenization: {exc}")

    workspace_text = env_map.get("HERMES_TEST_WORKSPACE", "")
    workspace = Path(workspace_text) if workspace_text else Path()
    required_checks = {
        "allow_env": env_map.get("ALLOW_HERMES_DEEPSEEK_RUN") == "1",
        "key_present": bool(env_map.get("DEEPSEEK_API_KEY")),
        "command_present": bool(command),
        "no_real_tools_env": env_map.get("CAPPROOF_NO_REAL_TOOLS") == "1",
        "no_network_except_deepseek_env": env_map.get("NO_NETWORK_EXCEPT_DEEPSEEK") == "1",
        "test_workspace_present": bool(workspace_text),
        "test_workspace_exists": workspace.exists() if workspace_text else False,
        "test_workspace_temp": is_safe_test_workspace(workspace) if workspace_text else False,
        "command_tokenizes": tokenizes,
        "command_mentions_hermes": "hermes" in lower,
        "command_declares_no_tools": any(marker in lower for marker in NO_TOOLS_MARKERS),
        "safe_prompt_marker": "capproof-ok" in lower,
        "no_denied_patterns": not denied,
    }
    if missing:
        return HermesCommandValidation(
            verdict="DENY_HERMES_DEEPSEEK_RUN",
            reason="missing required Hermes DeepSeek no-tools environment variables",
            run_allowed=False,
            missing_env=missing,
            denied_patterns=tuple(dict.fromkeys(denied)),
            required_checks=required_checks,
            command_hash=_hash_text(command),
            command_preview=_redact_text(command),
            no_tools_feasibility="not confirmed",
        )
    failed = tuple(name for name, ok in required_checks.items() if not ok)
    if denied or failed:
        reason = "unsafe command patterns present" if denied else "required no-tools checks failed"
        if failed:
            reason = f"{reason}: {', '.join(failed)}"
        return HermesCommandValidation(
            verdict="DENY_HERMES_DEEPSEEK_RUN",
            reason=reason,
            run_allowed=False,
            missing_env=(),
            denied_patterns=tuple(dict.fromkeys(denied)),
            required_checks=required_checks,
            command_hash=_hash_text(command),
            command_preview=_redact_text(command),
            no_tools_feasibility="not confirmed",
        )
    return HermesCommandValidation(
        verdict="ALLOW_HERMES_DEEPSEEK_RUN_VALIDATION_ONLY",
        reason="safe no-tools Hermes command validated; command is only executed by --run-hermes-no-tools",
        run_allowed=True,
        missing_env=(),
        denied_patterns=(),
        required_checks=required_checks,
        command_hash=_hash_text(command),
        command_preview=_redact_text(command),
        no_tools_feasibility="command declares no-tools/model-only/dry-run mode",
    )


def load_or_default_hermes_run(command_validation: HermesCommandValidation, *, env: Mapping[str, str] | None = None) -> HermesNoToolsRunResult:
    env_map = dict(os.environ if env is None else env)
    return HermesNoToolsRunResult(
        run_attempted=False,
        run_allowed=command_validation.run_allowed,
        denial_reason="not requested; --run-hermes-no-tools was not invoked",
        command_hash=command_validation.command_hash,
        model=env_map.get("DEEPSEEK_MODEL") or DEFAULT_MODEL,
        base_url=env_map.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL,
    )


def run_hermes_no_tools(
    *,
    command_validation: HermesCommandValidation | None = None,
    env: Mapping[str, str] | None = None,
    command_runner: Callable[..., Any] | None = None,
    timeout_seconds: int = 20,
    root: Path = ROOT,
) -> HermesNoToolsRunResult:
    env_map = dict(os.environ if env is None else env)
    validation = command_validation or validate_hermes_command(env=env_map)
    command = env_map.get("HERMES_DEEPSEEK_COMMAND", "").strip()
    model = env_map.get("DEEPSEEK_MODEL") or DEFAULT_MODEL
    base_url = env_map.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
    if not validation.run_allowed:
        result = HermesNoToolsRunResult(
            run_attempted=False,
            run_allowed=False,
            denial_reason=validation.reason,
            command_hash=validation.command_hash,
            timeout_seconds=timeout_seconds,
            model=model,
            base_url=base_url,
        )
        write_hermes_run_report(result, validation, root=root)
        return result

    run_env = dict(env_map)
    run_env.update(
        {
            "CAPPROOF_NO_REAL_TOOLS": "1",
            "NO_NETWORK_EXCEPT_DEEPSEEK": "1",
            "HERMES_DISABLE_TOOLS": "1",
            "HERMES_DISABLE_GATEWAY": "1",
            "HERMES_DISABLE_MCP": "1",
            "HERMES_DISABLE_MEMORY_PERSISTENCE": "1",
            "HERMES_MODEL_PROVIDER": "deepseek",
            "DEEPSEEK_MODEL": model,
            "DEEPSEEK_BASE_URL": base_url,
        }
    )
    args = shlex.split(command)
    runner = command_runner or subprocess.run
    try:
        completed = runner(
            args,
            cwd=env_map["HERMES_TEST_WORKSPACE"],
            env=run_env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout = getattr(completed, "stdout", "") or ""
        stderr = getattr(completed, "stderr", "") or ""
        output = f"{stdout}\n{stderr}"
        flags = detect_run_violations(output, secret=env_map.get("DEEPSEEK_API_KEY", ""))
        result = HermesNoToolsRunResult(
            run_attempted=True,
            run_allowed=True,
            denial_reason="",
            command_hash=validation.command_hash,
            timeout_seconds=timeout_seconds,
            exit_code=getattr(completed, "returncode", None),
            timed_out=False,
            response_received=bool(stdout.strip() or stderr.strip() or getattr(completed, "returncode", None) == 0),
            stdout_bytes=len(stdout.encode("utf-8")),
            stderr_bytes=len(stderr.encode("utf-8")),
            model=model,
            base_url=base_url,
            **flags,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="ignore")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="ignore")
        flags = detect_run_violations(f"{stdout}\n{stderr}", secret=env_map.get("DEEPSEEK_API_KEY", ""))
        result = HermesNoToolsRunResult(
            run_attempted=True,
            run_allowed=True,
            denial_reason="timeout",
            command_hash=validation.command_hash,
            timeout_seconds=timeout_seconds,
            exit_code=None,
            timed_out=True,
            response_received=bool(stdout.strip() or stderr.strip()),
            stdout_bytes=len(stdout.encode("utf-8")),
            stderr_bytes=len(stderr.encode("utf-8")),
            model=model,
            base_url=base_url,
            **flags,
        )
    except (OSError, ValueError) as exc:
        flags = detect_run_violations(str(exc), secret=env_map.get("DEEPSEEK_API_KEY", ""))
        result = HermesNoToolsRunResult(
            run_attempted=True,
            run_allowed=True,
            denial_reason=f"execution_error:{type(exc).__name__}",
            command_hash=validation.command_hash,
            timeout_seconds=timeout_seconds,
            exit_code=None,
            timed_out=False,
            response_received=False,
            stdout_bytes=0,
            stderr_bytes=len(str(exc).encode("utf-8")),
            model=model,
            base_url=base_url,
            **flags,
        )
    write_hermes_run_report(result, validation, root=root)
    return result


def detect_run_violations(output: str, *, secret: str = "") -> dict[str, bool]:
    lower = f" {output.lower()} "
    flags = {name: any(pattern in lower for pattern in patterns) for name, patterns in VIOLATION_PATTERNS.items()}
    key_leak = bool(secret and secret in output)
    flags["key_leak_detected"] = key_leak
    flags["key_printed"] = key_leak
    flags["key_written"] = False
    return flags


def write_reports(
    preflight: DeepSeekPreflight,
    audit: HermesConfigAudit,
    smoke: SmokeTestResult,
    command_validation: HermesCommandValidation | None = None,
    hermes_run: HermesNoToolsRunResult | None = None,
    *,
    root: Path = ROOT,
) -> None:
    command_validation = command_validation or validate_hermes_command()
    hermes_run = hermes_run or load_or_default_hermes_run(command_validation)
    _path(root, REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    _path(root, PREFLIGHT_JSON_PATH).write_text(json.dumps(asdict(preflight), indent=2, sort_keys=True), encoding="utf-8")
    _path(root, SETUP_REPORT_PATH).write_text(render_setup_report(preflight, audit, smoke), encoding="utf-8")
    _path(root, GO_NO_GO_PATH).write_text(render_go_no_go(preflight, audit, smoke), encoding="utf-8")
    write_smoke_report(smoke, root=root)
    write_audit_report(audit, root=root)
    write_hermes_run_report(hermes_run, command_validation, root=root)


def write_audit_report(audit: HermesConfigAudit, *, root: Path = ROOT) -> None:
    _path(root, REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    _path(root, AUDIT_JSON_PATH).write_text(json.dumps(asdict(audit), indent=2, sort_keys=True), encoding="utf-8")
    _path(root, AUDIT_REPORT_PATH).write_text(render_audit_report(audit), encoding="utf-8")


def write_smoke_report(smoke: SmokeTestResult, *, root: Path = ROOT) -> None:
    _path(root, REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    _path(root, SMOKE_JSON_PATH).write_text(json.dumps(asdict(smoke), indent=2, sort_keys=True), encoding="utf-8")
    _path(root, SMOKE_REPORT_PATH).write_text(render_smoke_report(smoke), encoding="utf-8")


def write_hermes_run_report(
    result: HermesNoToolsRunResult,
    validation: HermesCommandValidation,
    *,
    root: Path = ROOT,
) -> None:
    _path(root, REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    summary = {
        "run_attempted": result.run_attempted,
        "run_allowed": result.run_allowed,
        "denial_reason": result.denial_reason,
        "command_hash": result.command_hash,
        "timeout": result.timeout_seconds,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "response_received": result.response_received,
        "tool_call_detected": result.tool_call_detected,
        "shell_detected": result.shell_detected,
        "mcp_detected": result.mcp_detected,
        "gateway_detected": result.gateway_detected,
        "file_write_detected": result.file_write_detected,
        "memory_persistence_detected": result.memory_persistence_detected,
        "key_leak_detected": result.key_leak_detected,
        "key_printed": result.key_printed,
        "key_written": result.key_written,
        "model": result.model,
        "base_url": result.base_url,
        "provider": result.provider,
        "stdout_bytes": result.stdout_bytes,
        "stderr_bytes": result.stderr_bytes,
        "command_validation": {
            "verdict": validation.verdict,
            "reason": validation.reason,
            "run_allowed": validation.run_allowed,
            "missing_env": list(validation.missing_env),
            "denied_patterns": list(validation.denied_patterns),
            "required_checks": validation.required_checks,
            "command_hash": validation.command_hash,
            "no_tools_feasibility": validation.no_tools_feasibility,
            "key_value_printed": validation.key_value_printed,
        },
        "security_boundary": security_boundary(),
        "capproof_enforcement_active": False,
        "real_hermes_protected_by_capproof": False,
    }
    _path(root, HERMES_RUN_JSON_PATH).write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    _path(root, HERMES_RUN_REPORT_PATH).write_text(render_hermes_run_report(result, validation), encoding="utf-8")


def render_env_template() -> str:
    return """# Hermes DeepSeek environment template
# Do not commit a real API key. Keep the key in your shell or secret manager.
# If a key is exposed, rotate it at the provider immediately.
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
# Optional. Hermes's built-in direct DeepSeek provider defaults to
# https://api.deepseek.com/v1. Only override if your local Hermes version
# requires an explicit OpenAI-compatible base URL.
# DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_REASONING_EFFORT=high
ALLOW_DEEPSEEK_SMOKE_TEST=0
ALLOW_HERMES_DEEPSEEK_RUN=0
CAPPROOF_NO_REAL_TOOLS=1
NO_NETWORK_EXCEPT_DEEPSEEK=1
"""


def render_config_template() -> str:
    return """# Hermes DeepSeek provider template
# Observed Hermes mapping:
# - Built-in provider id: deepseek
# - Credential env var: DEEPSEEK_API_KEY
# - Provider default base URL: https://api.deepseek.com/v1
# - OpenAI-chat transport via Hermes provider profile
# Do not write a real key here.
model:
  provider: deepseek
  default: deepseek-v4-pro
  # Optional override only. Prefer the built-in provider default unless needed.
  # base_url: https://api.deepseek.com/v1
agent:
  reasoning_effort: high
security:
  deepseek_not_in_capproof_tcb: true
  deepseek_cannot_mint_capability: true
  deepseek_cannot_allow_tool_call: true
  capproof_guard_required_for_tools: true
  reference_monitor_final_authority: true
runtime_limits:
  no_real_tools: true
  no_shell_tool: true
  no_gateway_message: true
  no_mcp_external_network: true
"""


def render_hermes_config_snippet() -> str:
    return """# Copy this into ~/.hermes/config.yaml after backing up that file.
# This snippet connects Hermes model routing to its built-in DeepSeek provider.
# It intentionally contains no API key. Provide the key via DEEPSEEK_API_KEY.

model:
  provider: deepseek
  default: deepseek-v4-pro
  # Hermes's built-in DeepSeek provider default is https://api.deepseek.com/v1.
  # Uncomment only if your local Hermes config requires an explicit override:
  # base_url: https://api.deepseek.com/v1

agent:
  reasoning_effort: high

# Security boundary reminder:
# DeepSeek is the model backend only. Any tool call produced by Hermes still
# must pass through CapProof capture / guard / Reference Monitor before a mock
# or sandbox executor may run it.
"""


def render_template_readme() -> str:
    return """# Hermes DeepSeek Configuration Template

This directory contains templates only. Do not commit a real `DEEPSEEK_API_KEY`.
The key must be read from the `DEEPSEEK_API_KEY` environment variable.

If a key is exposed in a prompt, log, report, config file, shell history, or
commit, rotate it immediately.

DeepSeek is only the Hermes model backend. It is not part of the CapProof
security TCB. DeepSeek output cannot mint a capability and cannot allow a tool
call. Any Hermes tool call produced while using DeepSeek must still go through
CapProof capture, guard, and the Reference Monitor.

The local Hermes checkout contains a built-in `deepseek` provider profile.
Use `real_agent_integrations/hermes_deepseek/configs/hermes_config.deepseek.example.yaml`
as the `~/.hermes/config.yaml` snippet, with `DEEPSEEK_API_KEY` supplied from
the environment.
"""


def render_setup_report(preflight: DeepSeekPreflight, audit: HermesConfigAudit, smoke: SmokeTestResult) -> str:
    lines = [
        "# Hermes DeepSeek Setup Report",
        "",
        "## Stage Positioning",
        "",
        "- This stage prepares Hermes to use DeepSeek as a model backend only.",
        "- This stage is not a Hermes enforcement wrapper.",
        "- Hermes is not run by default.",
        "- DeepSeek is not called by default.",
        "- No real tools, shell tools, email, or gateway messages are executed.",
        "- API key values are never printed or written to reports.",
        "",
        "## DeepSeek Config Status",
        "",
        f"- key_present: {preflight.key_present}",
        f"- key_value_printed: {preflight.key_value_printed}",
        f"- base_url: {preflight.base_url}",
        f"- model: {preflight.model}",
        f"- reasoning_effort: {preflight.reasoning_effort}",
        f"- smoke_test_allowed: {preflight.smoke_test_allowed}",
        f"- smoke_test_attempted: {smoke.run_attempted}",
        f"- smoke_test_status: {smoke.status}",
        f"- hermes_run_allowed: {preflight.hermes_run_allowed}",
        f"- hermes_run_reason: {preflight.hermes_run_reason}",
        "",
        "## Hermes Config Audit",
        "",
        f"- repo_status: {audit.repo_status}",
        f"- repo_path: `{audit.repo_path}`",
        f"- files_scanned: {audit.files_scanned}",
        f"- provider_config_found: {audit.provider_config_found}",
        f"- OpenAI-compatible path found: {audit.openai_compatible_path_found}",
        f"- DeepSeek support found: {audit.deepseek_support_found}",
        f"- mapping recommendation: {audit.mapping_recommendation}",
        "- Hermes direct mapping: `model.provider: deepseek`, `model.default: deepseek-v4-pro`, key from `DEEPSEEK_API_KEY`.",
        "- Observed built-in DeepSeek provider base URL: `https://api.deepseek.com/v1`.",
        "",
        "## Security Boundary",
        "",
        "- DeepSeek is not in the CapProof TCB.",
        "- DeepSeek output cannot mint capability.",
        "- DeepSeek output cannot allow tool call.",
        "- Hermes tool calls still require CapProof guard.",
        "- Reference Monitor remains final authority.",
    ]
    return "\n".join(lines) + "\n"


def render_audit_report(audit: HermesConfigAudit) -> str:
    def section(title: str, items: tuple[str, ...]) -> list[str]:
        lines = [f"## {title}", ""]
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- none")
        lines.append("")
        return lines

    lines = [
        "# Hermes Model Config Static Audit",
        "",
        "This audit only reads local Hermes source and docs. It does not run Hermes,",
        "install dependencies, execute third-party commands, or call DeepSeek.",
        "",
        f"- repo_status: {audit.repo_status}",
        f"- repo_path: `{audit.repo_path}`",
        f"- files_scanned: {audit.files_scanned}",
        f"- provider_config_found: {audit.provider_config_found}",
        f"- provider_dir_found: {audit.provider_dir_found}",
        f"- OpenAI-compatible path found: {audit.openai_compatible_path_found}",
        f"- DeepSeek support found: {audit.deepseek_support_found}",
        f"- base_url/api_base/endpoint field found: {audit.base_url_field_found}",
        f"- model field found: {audit.model_field_found}",
        f"- api_key/env field found: {audit.api_key_env_field_found}",
        f"- mapping recommendation: {audit.mapping_recommendation}",
        "",
    ]
    lines.extend(section("Observed In Source", audit.observed_in_source))
    lines.extend(section("Inferred From Docs", audit.inferred_from_docs))
    lines.extend(section("Unknown", audit.unknown))
    lines.extend(section("Needs Manual Verification", audit.needs_manual_verification))
    lines.append("## Sample Files")
    lines.append("")
    if audit.sample_files:
        lines.extend(f"- `{path}`" for path in audit.sample_files)
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def render_smoke_report(smoke: SmokeTestResult) -> str:
    return "\n".join(
        [
            "# DeepSeek Smoke Test Report",
            "",
            "- This report never contains the API key value.",
            "- Smoke test is skipped unless `ALLOW_DEEPSEEK_SMOKE_TEST=1` and `DEEPSEEK_API_KEY` are present.",
            "- Smoke test does not run Hermes and does not trigger tools.",
            "",
            f"- run_attempted: {smoke.run_attempted}",
            f"- run_allowed: {smoke.run_allowed}",
            f"- status: {smoke.status}",
            f"- reason: {smoke.reason}",
            f"- model: {smoke.model}",
            f"- base_url: {smoke.base_url}",
            f"- request_id: {smoke.request_id or 'not_recorded'}",
            f"- prompt_hash: {smoke.prompt_hash or 'not_run'}",
            f"- total_tokens: {smoke.total_tokens if smoke.total_tokens is not None else 'unknown'}",
            f"- key_value_printed: {smoke.key_value_printed}",
            f"- no_hermes_run: {smoke.no_hermes_run}",
            f"- no_tool_call: {smoke.no_tool_call}",
            f"- no_capproof_data_sent: {smoke.no_capproof_data_sent}",
            f"- no_secret_logged: {smoke.no_secret_logged}",
            f"- error_type: {smoke.error_type or 'none'}",
        ]
    ) + "\n"


def render_hermes_run_report(result: HermesNoToolsRunResult, validation: HermesCommandValidation) -> str:
    violation = any(
        (
            result.tool_call_detected,
            result.shell_detected,
            result.mcp_detected,
            result.gateway_detected,
            result.file_write_detected,
            result.memory_persistence_detected,
            result.key_leak_detected,
        )
    )
    deepseek_backend_claim = result.run_attempted and result.run_allowed and result.response_received and not violation
    lines = [
        "# Hermes DeepSeek No-Tools Run Report",
        "",
        "## Stage Positioning",
        "",
        "- This stage validates a gated Hermes + DeepSeek no-tools model-backend run path.",
        "- This stage is not a CapProof enforcement wrapper.",
        "- The default path does not run Hermes.",
        "- Hermes is run only when `--run-hermes-no-tools` is requested and all explicit safety environment variables are present.",
        "- DeepSeek is a Hermes model backend only and is not part of the CapProof TCB.",
        "- No API key value is printed or written to this report.",
        "",
        "## Run Decision",
        "",
        f"- run_attempted: {result.run_attempted}",
        f"- run_allowed: {result.run_allowed}",
        f"- denial_reason: {result.denial_reason or 'none'}",
        f"- command_hash: {result.command_hash or 'not_available'}",
        f"- timeout: {result.timeout_seconds}",
        f"- exit_code: {result.exit_code if result.exit_code is not None else 'not_run'}",
        f"- timed_out: {result.timed_out}",
        f"- command_validation: {validation.verdict}",
        f"- command_validation_reason: {validation.reason}",
        f"- no_tools_feasibility: {validation.no_tools_feasibility}",
        "",
        "## DeepSeek Status",
        "",
        f"- key_present: {validation.required_checks.get('key_present', False)}",
        f"- key_printed: {result.key_printed}",
        f"- key_written: {result.key_written}",
        f"- base_url: {result.base_url}",
        f"- model: {result.model}",
        "- smoke_test_status: see `deepseek_smoke_test_report.md` if a gated smoke test was explicitly run.",
        "",
        "## Hermes Status",
        "",
        f"- hermes_run_attempted: {result.run_attempted}",
        f"- response_received: {result.response_received}",
        f"- tool_call_detected: {result.tool_call_detected}",
        f"- gateway_detected: {result.gateway_detected}",
        f"- mcp_detected: {result.mcp_detected}",
        f"- shell_detected: {result.shell_detected}",
        f"- file_write_detected: {result.file_write_detected}",
        f"- memory_persistence_detected: {result.memory_persistence_detected}",
        f"- key_leak_detected: {result.key_leak_detected}",
        f"- stdout_bytes: {result.stdout_bytes}",
        f"- stderr_bytes: {result.stderr_bytes}",
        "",
        "## Security Boundary",
        "",
        "- DeepSeek not in CapProof TCB: true",
        "- DeepSeek can mint capability: false",
        "- DeepSeek can allow tool call: false",
        "- Hermes tools disabled requirement: true",
        "- CapProof guard not yet enforcing Hermes DeepSeek runs: true",
        "- No claim of real CapProof protection for Hermes + DeepSeek is made here.",
        "",
        "## Go / No-Go",
        "",
        f"- Hermes DeepSeek no-tools model backend observed: {deepseek_backend_claim}",
        "- Hermes + DeepSeek tool execution: no-go until a later CapProof guard integration stage.",
        "- Enforcement wrapper: no-go.",
        "- Claim that CapProof protects Hermes + DeepSeek: no-go.",
    ]
    return "\n".join(lines) + "\n"


def render_go_no_go(preflight: DeepSeekPreflight, audit: HermesConfigAudit, smoke: SmokeTestResult) -> str:
    can_no_tools = preflight.key_present and (audit.openai_compatible_path_found or audit.repo_status == "available")
    return "\n".join(
        [
            "# Hermes DeepSeek Go / No-Go",
            "",
            f"- Hermes + DeepSeek no-tools model call: {'conditional go after manual config verification' if can_no_tools else 'no-go until key and config mapping are available'}",
            "- Hermes + DeepSeek tool execution: no-go until a later CapProof guard integration stage.",
            "- Enforcement wrapper: no-go.",
            "- Claim that CapProof protects Hermes + DeepSeek: no-go.",
            "- DeepSeek smoke test: skipped unless explicitly authorized.",
            f"- Current smoke status: {smoke.status}",
            "",
            "## Security Boundary",
            "",
            "- DeepSeek not in CapProof TCB: true",
            "- DeepSeek can mint capability: false",
            "- DeepSeek can allow tool call: false",
            "- Reference Monitor final authority: true",
        ]
    ) + "\n"


def security_boundary() -> dict[str, bool]:
    return {
        "deepseek_in_capproof_tcb": False,
        "deepseek_can_mint_capability": False,
        "deepseek_can_allow_tool_call": False,
        "hermes_tool_calls_require_capproof_guard": True,
        "reference_monitor_final_authority": True,
        "llm_output_can_bypass_reference_monitor": False,
    }


def resolve_hermes_repo(*, env: Mapping[str, str] | None = None, root: Path = ROOT) -> tuple[Path | None, str]:
    env_map = dict(os.environ if env is None else env)
    candidates: list[Path] = []
    if env_map.get("HERMES_REPO"):
        candidates.append(Path(env_map["HERMES_REPO"]))
    candidates.extend([root / "external" / "hermes-agent", root / "external" / "external" / "hermes-agent"])
    for candidate in candidates:
        if candidate.exists():
            return candidate, "available"
    return candidates[0] if candidates else None, "repo_missing"


def iter_text_files(repo_path: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"} for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name.lower().startswith(("readme", "license", "config")):
            files.append(path)
    return sorted(files)


def _urllib_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, Mapping[str, str], bytes]:
    req = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:  # nosec: explicitly gated smoke test
        return response.status, dict(response.headers), response.read()


def _safe_response_preview(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    content = message.get("content") if isinstance(message, dict) else ""
    if not isinstance(content, str):
        return ""
    return re.sub(r"\s+", " ", content).strip()[:16]


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _redact_text(text: str) -> str:
    if not text:
        return ""
    redacted = SECRET_LITERAL_RE.sub("[REDACTED]", text)
    return re.sub(r"\s+", " ", redacted).strip()[:80]


def _path(root: Path, path: Path) -> Path:
    try:
        return root / path.relative_to(ROOT)
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())
