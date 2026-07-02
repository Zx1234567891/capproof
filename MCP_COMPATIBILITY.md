# CapProof MCP Compatibility Profile

This document defines the MCP subset supported by the local CapProof MCP
server artifact for Hermes. It is intentionally narrow and evidence-based.

## Supported Protocol / Profile

CapProof supports a local stdio MCP server profile:

- Local stdio MCP server.
- JSON-RPC `initialize`.
- JSON-RPC `tools/list`.
- JSON-RPC `tools/call`.
- Tool responses with `content` and `structuredContent`.
- JSON-RPC stdio cleanliness: stdout is reserved for MCP JSON-RPC.
- Human-readable diagnostics go to stderr, live log, reports, or trace files.

## Supported CapProof Tools

The server exposes 7 tools:

- `capproof.echo_summary`
- `capproof.send_message_mock`
- `capproof.read_workspace_file`
- `capproof.write_workspace_file`
- `capproof.run_command_template`
- `capproof.get_trace`
- `capproof.request_authorization`

Authority-bearing `tools/call` requests are routed through:

```text
canonicalizer -> CapProofMiddleware.guard(...) -> Reference Monitor -> executor gate
```

ALLOW can enter MockExecutor or the Stage 33S no-side-effect/workspace-limited
sandboxed executor. DENY and ASK do not execute.

## Not Claimed

The current artifact does not claim support for:

- MCP resources.
- MCP prompts.
- MCP sampling.
- MCP elicitation.
- Streamable HTTP transport.
- OAuth or remote MCP authorization.
- External MCP server protection.
- All MCP transports.
- All future or draft MCP versions.
- Production-level Hermes protection.
- All Hermes tool paths.

## Safety Notes

- MCP metadata, tool descriptions, annotations, `_meta`, clientInfo,
  clientCapabilities, Hermes output, DeepSeek output, and natural language
  cannot mint capability.
- DeepSeek is a model backend only. It is not in the CapProof safety TCB.
- The sandbox is not an authorization root. Authorization remains with
  CapProof guard and the Reference Monitor.
- No OS-level network denial is claimed.
