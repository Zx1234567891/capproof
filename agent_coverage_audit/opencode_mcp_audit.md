# OpenCode MCP Reuse Audit

## Scope

Stage 34O audits whether OpenCode can reuse the standard CapProof MCP
server as an outbound MCP server. It does not run OpenCode; it only checks
repo/runtime presence, generates config guidance, and validates CapProof locally
through JSON-RPC.

## Status

- repo_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/opencode`
- repo_exists: False
- runtime_available: False
- files_scanned: 0
- observed_config_path: ``
- real_agent_run: False
- tools_list_observed_from_real_agent: False
- tools_call_observed_from_real_agent: False
- status: repo_missing

## Notes

- No real agent process was run.
- No real agent tools/list or tools/call observation is claimed.
- CapProof MCP config points to the shared standard server.
- opencode repo is missing; source-specific config schema still needs manual verification.
- opencode runtime command is not on PATH; runtime integration remains unverified.

## Boundary

- Reuse the same `tools/run_capproof_mcp_server.py --stdio --sandboxed-real-execution` server.
- Do not fork CapProof guard or Reference Monitor logic.
- Tool metadata, skill/plugin metadata, MCP metadata, and LLM output cannot mint capability.
- DENY/ASK executor_called must remain false.
- No production-level protection claim.
