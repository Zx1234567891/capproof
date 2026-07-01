from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_capproof_trace_viewer as viewer


def test_trace_viewer_pretty_filters_and_skips_malformed(tmp_path: Path, capsys) -> None:
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": 1,
                        "user_task": "read",
                        "mcp_method": "tools/call",
                        "tool_name": "capproof.read_workspace_file",
                        "capproof_verdict": "ALLOW",
                        "reason": "",
                        "proof_id": "proof_1",
                        "executor_called": True,
                        "canonical_action_hash": "hash_1",
                        "mock_event": {"executed": True},
                    }
                ),
                "{not-json",
                json.dumps(
                    {
                        "timestamp": 2,
                        "user_task": "deny",
                        "mcp_method": "tools/call",
                        "tool_name": "capproof.send_message_mock",
                        "capproof_verdict": "DENY",
                        "reason": "NoCap",
                        "proof_id": None,
                        "executor_called": False,
                        "canonical_action_hash": "hash_2",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rc = viewer.main(["--file", str(trace), "--filter-verdict", "DENY", "--last", "10"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "skipped_malformed_count=1" in out
    assert "tool_name=capproof.send_message_mock" in out
    assert "verdict=DENY" in out
    assert "reason=NoCap" in out
    assert "executor_called=False" in out
    assert "capproof.read_workspace_file" not in out


def test_trace_viewer_json_redacts_secret_like_values(tmp_path: Path, capsys) -> None:
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        json.dumps(
            {
                "timestamp": 1,
                "mcp_method": "tools/call",
                "tool_name": "capproof.echo_summary",
                "capproof_verdict": "ALLOW",
                "reason": "",
                "executor_called": False,
                "original_arguments": {"api_key": "test-secret-token-value"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rc = viewer.main(["--file", str(trace), "--format", "json", "--last", "5"])

    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["entry_count"] == 1
    assert payload["skipped_malformed_count"] == 0
    assert "test-secret-token-value" not in out
    assert "[REDACTED]" in out
