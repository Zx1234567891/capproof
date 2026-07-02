# Agent Parity Matrix

Stage 41AP aggregates controlled local real-environment evidence for Hermes, OpenCode, and OpenClaw.

- aggregate_agent_parity_passed: True
- dry-run/preflight counts as completion: false
- DeepSeek key source: DEEPSEEK_API_KEY only

| agent | real_agent_process_ran | deepseek_real_call | deepseek_key_source | deepseek_key_written | standard_capproof_mcp_server_used | tools_list_observed | tools_call_observed | allow_read_write_command_observed | deny_outside_path_raw_shell_attacker_observed | ask_pending_request_created | trusted_approval_executed | rerun_allow_observed | llm_metadata_approval_rejected | trace_live_log_report_generated | parity_passed | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hermes | True | True | DEEPSEEK_API_KEY | False | True | True | True | True | True | True | True | True | True | True | True | ok |
| opencode | True | True | DEEPSEEK_API_KEY | False | True | True | True | True | True | True | True | True | True | True | True | ok |
| openclaw | True | True | DEEPSEEK_API_KEY | False | True | True | True | True | True | True | True | True | True | True | True | ok |

## Non-Claims

- no production-level protection
- no all Hermes/OpenCode/OpenClaw tool paths covered
- no built-in tools fully protected claim
- no external MCP protection claim
- no real email support
- no raw shell support
- no OS-level network denial claim
