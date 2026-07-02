from pathlib import Path
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_agent_runtime_bootstrap as bootstrap


def _args(tmp_path: Path):
    return type(
        "Args",
        (),
        {
            "install_prefix": str(tmp_path / "prefix"),
            "source_root": str(tmp_path / "external"),
            "allow_network_install": False,
            "from_source": False,
            "from_package": False,
        },
    )()


def _make_source(root: Path, agent: str) -> None:
    source = root / "external" / agent
    source.mkdir(parents=True)
    (source / ".git").mkdir()
    (source / "package.json").write_text("{}", encoding="utf-8")


def _write_executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_require_real_gate_missing_returns_nonzero(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ALLOW_AGENT_RUNTIME_BOOTSTRAP", raising=False)
    monkeypatch.setattr(bootstrap, "SUMMARY_PATH", tmp_path / "summary.json")
    monkeypatch.setattr(bootstrap, "REPORT_PATH", tmp_path / "report.md")
    monkeypatch.setattr(bootstrap, "MATRIX_JSON_PATH", tmp_path / "matrix.json")
    monkeypatch.setattr(bootstrap, "MATRIX_MD_PATH", tmp_path / "matrix.md")
    monkeypatch.setattr(bootstrap, "OPENCODE_REPORT", tmp_path / "opencode.md")
    monkeypatch.setattr(bootstrap, "OPENCLAW_REPORT", tmp_path / "openclaw.md")

    code = bootstrap.main(["--require-real", "--fail-if-bootstrap-missing", "--install-prefix", str(tmp_path / "prefix")])

    assert code == 2
    assert bootstrap.SUMMARY_PATH.exists()
    assert "blocked_bootstrap_gate_missing" in bootstrap.SUMMARY_PATH.read_text(encoding="utf-8")


def test_preflight_does_not_mark_bootstrap_passed(tmp_path: Path) -> None:
    args = _args(tmp_path)

    summary = bootstrap.build_summary(args, bootstrap_requested=False)

    assert summary["stage"] == "40RB"
    assert summary["runtime_bootstrap_passed"] is False
    assert summary["dry_run_preflight_completion_evidence"] is False
    assert summary["integration_claim_made"] is False


def test_bootstrap_without_network_gate_blocks_prereq(monkeypatch, tmp_path: Path) -> None:
    _make_source(tmp_path, "opencode")
    monkeypatch.setenv("ALLOW_AGENT_RUNTIME_BOOTSTRAP", "1")
    monkeypatch.delenv("ALLOW_AGENT_RUNTIME_NETWORK", raising=False)
    args = _args(tmp_path)

    result = bootstrap.bootstrap_agent("opencode", args)

    assert result["bootstrap_attempted"] is True
    assert result["runtime_present"] is False
    assert result["reason"] == "blocked_prereq_missing"
    assert "ALLOW_AGENT_RUNTIME_NETWORK=1" in result["failure_detail"]


def test_verify_fake_opencode_binary_marks_runtime_present(tmp_path: Path) -> None:
    args = _args(tmp_path)
    _write_executable(
        Path(args.install_prefix) / "bin" / "opencode",
        "#!/usr/bin/env python3\nprint('opencode 1.17.13')\n",
    )

    result = bootstrap.verify_agent("opencode", args, attempted=True, mode="from_package")

    assert result["runtime_present"] is True
    assert result["version_detected"] == "opencode 1.17.13"
    assert result["real_smoke_eligible"] is True
    assert result["reason"] == "ok"


def test_verify_fake_openclaw_binary_checks_mcp_help(tmp_path: Path) -> None:
    args = _args(tmp_path)
    _write_executable(
        Path(args.install_prefix) / "bin" / "openclaw",
        """#!/usr/bin/env python3
import sys
if '--version' in sys.argv:
    print('OpenClaw 2026.6.11')
elif sys.argv[1:3] == ['mcp', 'doctor']:
    print('doctor help')
elif sys.argv[1:3] == ['mcp', 'tools']:
    print('tools help')
elif sys.argv[1:3] == ['mcp', 'status']:
    print('status ok')
else:
    print('ok')
""",
    )

    result = bootstrap.verify_agent("openclaw", args, attempted=True, mode="from_package")

    assert result["runtime_present"] is True
    assert result["version_detected"] == "OpenClaw 2026.6.11"
    assert result["mcp_cli_help_available"] is True
    assert result["real_smoke_eligible"] is True
    assert result["reason"] == "ok"


def test_package_bootstrap_uses_local_npm_prefix(monkeypatch, tmp_path: Path) -> None:
    _make_source(tmp_path, "opencode")
    monkeypatch.setenv("ALLOW_AGENT_RUNTIME_BOOTSTRAP", "1")
    monkeypatch.setenv("ALLOW_AGENT_RUNTIME_NETWORK", "1")
    args = _args(tmp_path)
    commands = []

    def fake_run_cmd(command, *, timeout):
        commands.append(command)
        return {"command": list(command), "returncode": 0, "stdout_tail": "", "stderr_tail": "", "timed_out": False}

    monkeypatch.setattr(bootstrap, "run_cmd", fake_run_cmd)
    monkeypatch.setattr(bootstrap, "link_binary", lambda agent, prefix: (True, str(prefix / "bin" / agent)))
    verify_calls = {"count": 0}

    def fake_verify(agent, args, attempted, mode):
        verify_calls["count"] += 1
        return {
            **bootstrap.source_info(agent, Path(args.source_root)),
            "bootstrap_attempted": attempted,
            "bootstrap_mode": mode,
            "runtime_present": verify_calls["count"] > 1,
            "binary_path": str(Path(args.install_prefix) / "bin" / agent),
            "version_detected": "fake" if verify_calls["count"] > 1 else None,
            "real_smoke_eligible": verify_calls["count"] > 1,
            "reason": "ok" if verify_calls["count"] > 1 else "blocked_runtime_missing",
        }

    monkeypatch.setattr(
        bootstrap,
        "verify_agent",
        fake_verify,
    )

    result = bootstrap.bootstrap_agent("opencode", args)

    assert result["runtime_present"] is True
    install = commands[0]
    assert install[:2] == ["npm", "install"]
    assert "--prefix" in install
    assert str(Path(args.install_prefix) / "npm-prefix" / "opencode") in install
    assert "sudo" not in install
    assert "opencode-ai@latest" in install


def test_write_artifacts_are_redaction_safe(monkeypatch, tmp_path: Path) -> None:
    fake_secret = "fake-deepseek-secret-for-redaction-test"
    monkeypatch.setenv("DEEPSEEK_API_KEY", fake_secret)
    monkeypatch.setattr(bootstrap, "SUMMARY_PATH", tmp_path / "summary.json")
    monkeypatch.setattr(bootstrap, "REPORT_PATH", tmp_path / "report.md")
    monkeypatch.setattr(bootstrap, "MATRIX_JSON_PATH", tmp_path / "matrix.json")
    monkeypatch.setattr(bootstrap, "MATRIX_MD_PATH", tmp_path / "matrix.md")
    monkeypatch.setattr(bootstrap, "OPENCODE_REPORT", tmp_path / "opencode.md")
    monkeypatch.setattr(bootstrap, "OPENCLAW_REPORT", tmp_path / "openclaw.md")
    args = _args(tmp_path)

    summary = bootstrap.build_summary(args, bootstrap_requested=False)
    summary["opencode"]["failure_detail"] = fake_secret
    bootstrap.write_artifacts(summary)

    combined = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.iterdir())
    assert fake_secret not in combined
    assert "No OpenCode/OpenClaw real integration claim" in combined
