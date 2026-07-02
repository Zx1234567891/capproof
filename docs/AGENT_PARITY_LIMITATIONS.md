# Agent Parity Limitations

The Hermes / OpenCode / OpenClaw parity result applies only to the tested local CapProof MCP path:

```text
agent -> DeepSeek -> standard CapProof MCP stdio server -> CapProof guard -> sandbox/mock executor
```

## Scope

The tested path covers:

- real local agent process;
- DeepSeek model backend via `DEEPSEEK_API_KEY`;
- standard MCP `tools/list` and `tools/call`;
- the seven CapProof MCP tools;
- workspace-only read/write sandbox subset;
- allowlisted command-template subset;
- DENY/ASK executor gate;
- ASK -> trusted local approve -> rerun ALLOW;
- LLM and MCP metadata rejection for authorization.

## Non-Claims

The artifact does not claim:

- production-level protection;
- all Hermes/OpenCode/OpenClaw built-in tool paths covered;
- all MCP clients or transports covered;
- external MCP server protection;
- real email support;
- raw shell support;
- arbitrary filesystem access;
- OS-level network denial;
- DeepSeek as safety TCB;
- LLM output authorization;
- MCP `_meta` authorization.

The model output remains untrusted. Authority still comes from CapProof capabilities and trusted local approval, not from natural language or metadata.
