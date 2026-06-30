# OpenClaw CapProof MCP Commands

Stage 34O does not run OpenClaw. These commands document the outbound MCP
server configuration path that should be used in a later explicitly authorized
real OpenClaw run.

Important distinction:

- `openclaw mcp serve` means OpenClaw acting as an MCP server.
- `openclaw mcp add/status/doctor/probe/tools` manages outbound MCP servers
  available to OpenClaw as a client.

CapProof should be registered as an outbound MCP server:

```bash
openclaw mcp add capproof --command python --arg run_capproof_mcp_server.py --arg --stdio --arg --sandboxed-real-execution
openclaw mcp doctor capproof --probe
openclaw mcp tools capproof
```

Security notes:

- This reuses the standard CapProof MCP server.
- It does not fork CapProof guard or Reference Monitor logic.
- MCP metadata, tool metadata, plugin metadata, and LLM output cannot mint capability.
- DENY/ASK must not execute an executor.
- This is not a production-level protection claim.
