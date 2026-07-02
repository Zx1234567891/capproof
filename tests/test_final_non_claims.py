from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_final_release_check as final


def test_final_non_claims_document_lists_boundaries() -> None:
    text = final.render_non_claims()

    assert "production-level protection" in text
    assert "all Hermes/OpenCode/OpenClaw built-in tool paths covered" in text
    assert "OS-level network denial" in text
    assert "DeepSeek as safety TCB" in text


def test_final_status_keeps_non_claims() -> None:
    summary = {
        "cleanroom_passed": True,
        "evaluator_passed": True,
        "aggregate_agent_parity_passed": True,
        "hermes_parity": True,
        "opencode_parity": True,
        "openclaw_parity": True,
        "all_agents_deepseek": True,
        "all_key_source_env": True,
        "key_written": False,
        "real_key_scan": "REAL_KEY_NOT_FOUND",
        "forbidden_tracked_paths_count": 0,
    }
    text = final.render_final_status(summary)

    assert "no production-level protection" in text
    assert "DeepSeek is not safety TCB" in text
