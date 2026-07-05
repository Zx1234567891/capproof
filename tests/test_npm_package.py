from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_package_json_exposes_expected_bins_and_files() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["name"] == "capproof-mcp"
    assert package["license"] == "MIT"
    assert package["publishConfig"]["access"] == "public"
    assert package["publishConfig"]["registry"] == "https://registry.npmjs.org/"
    assert package["bin"]["capproof-mcp"] == "npm/bin/capproof-mcp.js"
    assert package["bin"]["hermes"] == "npm/bin/capproof-agent.js"
    assert package["bin"]["opencode"] == "npm/bin/capproof-agent.js"
    assert package["bin"]["openclaw"] == "npm/bin/capproof-agent.js"
    assert package["bin"]["codewhale"] == "npm/bin/capproof-agent.js"

    files = set(package["files"])
    assert "src/**/*.py" in files
    assert "src/**/*.pyi" in files
    assert "tools/*.py" in files
    assert "npm/" in files
    forbidden = {"external/", "external/.agent-runtimes/", ".venv-hermes/", "node_modules/", "artifact_cleanroom/"}
    assert not files.intersection(forbidden)


def test_npm_cli_help_is_redaction_safe() -> None:
    result = subprocess.run(
        ["node", "npm/bin/capproof-mcp.js", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
        check=False,
    )

    assert result.returncode == 0
    assert "CapProof MCP" in result.stdout
    assert "DEEPSEEK_API_KEY is read from the environment only" in result.stdout
    assert "sk-" not in result.stdout


def test_npm_cli_lists_real_capproof_tools() -> None:
    result = subprocess.run(
        ["node", "npm/bin/capproof-mcp.js", "list-tools"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    tools = payload["tools"]
    names = {item["name"] for item in tools}
    assert len(tools) == 7
    assert "capproof.read_workspace_file" in names
    assert "capproof.write_workspace_file" in names
    assert "capproof.run_command_template" in names
    assert "capproof.request_authorization" in names


def test_npm_pack_dry_run_excludes_runtime_and_secret_paths() -> None:
    result = subprocess.run(
        ["npm", "pack", "--dry-run", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)[0]
    files = {item["path"] for item in payload["files"]}
    assert "package.json" in files
    assert "npm/bin/capproof-mcp.js" in files
    assert "npm/bin/capproof-agent.js" in files
    assert "src/capproof/__init__.py" in files
    assert "tools/run_capproof_mcp_server.py" in files

    forbidden_fragments = (
        "external/",
        ".agent-runtimes/",
        ".venv-hermes/",
        "node_modules/",
        "artifact_cleanroom/",
        "auth_queue/",
        "runtime/",
        "__pycache__/",
        ".pyc",
        "DEEPSEEK_API_KEY=",
    )
    for path in files:
        assert not any(fragment in path for fragment in forbidden_fragments), path
