# Foreground Hermes CapProof MCP UX Report

## Stage Positioning

- Stage 35UX improves foreground usability; it does not change CapProof core verifier or Reference Monitor semantics.
- Doctor and trace viewer do not run Hermes or call DeepSeek by default.
- DeepSeek remains model-backend-only and outside the CapProof safety TCB.
- CapProof guard remains the tool execution gate.
- No production-level Hermes protection is claimed.

## Doctor Summary

- passed: True
- DeepSeek key present: True (value redacted)
- MCP server command exists: True
- tools/list returns 7 tools: True
- tools count: 7
- trace directory writable: True
- live log directory writable: True
- sandbox workspace exists: True
- external/.venv/node_modules not tracked: True
- API key scan ok: True
- MCP stdio stdout pollution check passes: True

## Paths

- trace: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/real_agent_integrations/hermes_mcp_server/traces/foreground_hermes_mcp_trace.jsonl`
- live log: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/real_agent_integrations/hermes_mcp_server/reports/foreground_hermes_mcp_live.log`
- sandbox workspace: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/real_agent_integrations/hermes_mcp_server/sandbox_workspace`
