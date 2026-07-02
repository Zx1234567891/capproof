# Claims and Non-Claims Matrix

This artifact records only claims that have been exercised in controlled local
workflows. It does not claim production-level protection.

## Proven / Supported in Controlled Local Workflows

- Hermes foreground MCP path.
- DeepSeek as Hermes model backend.
- standard CapProof MCP `tools/list` and `tools/call`.
- Foreground user-visible workflow.
- Trace viewer and doctor UX.
- Sandboxed local file read/write subset.
- Allowlisted command-template subset.
- DENY/ASK executor gate.
- trusted ASK approval queue.
- Foreground ASK -> trusted approve -> rerun ALLOW flow.
- Metadata and LLM output cannot mint capability.
- Raw shell denied.
- Attacker recipient denied.
- Path traversal and outside-workspace access denied or refused in tested paths.

## Explicitly Not Claimed

- Production-level Hermes protection.
- All Hermes tool paths covered.
- All MCP clients covered.
- Real email.
- External MCP.
- Raw shell support.
- Arbitrary filesystem access.
- OS-level network denial.
- OpenCode/OpenClaw real integration.
- DeepSeek as safety TCB.
- LLM output authorization.
- MCP `_meta` authorization.

## Boundary Summary

CapProof guard and the Reference Monitor remain the authority for execution
decisions. DeepSeek can propose text or tool calls through Hermes, but it cannot
mint capability or approve a tool call. The trusted authorization queue only
accepts local CLI approval for exact or narrower requested scopes.
