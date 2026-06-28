# Hermes Unknown / Needs Runtime Capture Subset

These shapes are not reliably supported by the current mock profile. They must
fail closed with `AdapterCoverageGap` or equivalent structured denial until
real runtime event capture is available.

- Terminal background, pty, streaming sessions, timeout, and long-running
  process semantics.
- Gateway media, attachments, reactions, message IDs, and thread fields.
- Non-http MCP tools, resources, prompts, and stdio transport with command
  based servers.
- Provider memory remote container metadata.
- `delegate_task` ACP fields not visible in the mock event.
- Cronjob lifecycle update, disable, fire, `no_agent`, and `context_from`
  fields.
- Full file patch semantic conflicts.
- Runtime dispatcher `tool_request` variants not captured by static audit.
