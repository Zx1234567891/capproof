from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_agent_parity_matrix as matrix


def test_matrix_rows_require_key_source_and_no_key_write() -> None:
    row = {
        "real_agent_process_ran": True,
        "deepseek_real_call": True,
        "deepseek_key_source": "DEEPSEEK_API_KEY",
        "deepseek_key_written": False,
        "standard_capproof_mcp_server_used": True,
        "tools_list_observed": True,
        "tools_call_observed": True,
        "allow_read_write_command_observed": True,
        "deny_outside_path_raw_shell_attacker_observed": True,
        "ask_pending_request_created": True,
        "trusted_approval_executed": True,
        "rerun_allow_observed": True,
        "llm_metadata_approval_rejected": True,
        "trace_live_log_report_generated": True,
        "production_level_overclaim": False,
    }

    assert matrix.row_passed(row) is True
    row["deepseek_key_written"] = True
    assert matrix.row_passed(row) is False


def test_agent_row_maps_parity_summary() -> None:
    summary = {
        "real_agent_process_ran": True,
        "deepseek_real_call": True,
        "deepseek_key_source": "DEEPSEEK_API_KEY",
        "deepseek_key_written": False,
        "standard_capproof_mcp_server_used": True,
        "tools_list_observed": True,
        "tools_call_observed": True,
        "allow_read_write_command_observed": True,
        "deny_outside_path_raw_shell_attacker_observed": True,
        "ask_pending_request_created": True,
        "trusted_approval_executed": True,
        "rerun_allow_observed": True,
        "llm_metadata_approval_rejected": True,
        "trace_live_log_report_generated": True,
        "production_level_overclaim": False,
    }

    row = matrix.agent_row("opencode", summary)

    assert row["parity_passed"] is True
    assert row["reason"] == "ok"


def test_render_markdown_contains_non_claims() -> None:
    payload = {
        "aggregate_agent_parity_passed": False,
        "agents": [
            {
                "agent": "hermes",
                "parity_passed": False,
                "reason": "blocked_test",
            }
        ],
    }

    text = matrix.render_markdown(payload)

    assert "no production-level protection" in text
    assert "no all Hermes/OpenCode/OpenClaw tool paths covered" in text
