# Agent MCP Client Matrix

## Stage Positioning

- Stage 34O is OpenCode/OpenClaw MCP reuse audit/config/dry-run only.
- It does not run real OpenCode/OpenClaw.
- It does not claim real OpenCode/OpenClaw integration.
- It reuses the standard CapProof MCP server and does not fork guard logic.

## Client Matrix

| client | repo_exists | runtime_available | files_scanned | real_agent_run | real tools/list | real tools/call | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opencode | False | False | 0 | False | False | False | repo_missing |
| openclaw | False | False | 0 | False | False | False | repo_missing |

## Local JSON-RPC CapProof MCP Dry-Run

- tools_list_passed: True
- tools_call_passed: True
- tools_count: 7
- allow_verdict: ALLOW
- allow_executor_called: True
- deny_verdict: DENY
- deny_reason: NoCap
- deny_executor_called: False
- metadata_cannot_mint_capability: True
- llm_output_cannot_allow_tool_call: True

## Non-Claims

- production_level_protection_claim: False
- real_opencode_integration_claim: False
- real_openclaw_integration_claim: False
- external_mcp_claim: False
- raw_shell_supported: False
- arbitrary_filesystem_access_supported: False
