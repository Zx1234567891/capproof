# Agent Adapter Report

## Scope

Stage 16 adds a mock Agent Adapter abstraction layer. It does not connect to
real LangGraph, OpenCode, Claude Code, Codex, OpenAI APIs, MCP servers, email,
network services, or shell execution. All tool execution is represented by a
mock executor.

The Reference Monitor remains the final allow/deny boundary. The adapter layer
parses framework-shaped tool-call events, preserves authority-bearing fields,
canonicalizes arguments with trusted tool contracts, asks the Proof Synthesizer
for a proof, and then verifies that proof with the Reference Monitor.

## New Components

- `AgentAction`: parsed candidate action from an agent runtime.
- `CanonicalToolCall`: canonical tool call summary, including `action_hash`,
  authority-bearing fields, and contract id.
- `ToolCallAdapter`: protocol with `supports`, `parse`, and `canonicalize`.
- `CapProofMiddleware`: guard flow from raw event to proof synthesis and
  Reference Monitor verification.
- `GuardedExecutor`: executes only when the guard decision is `ALLOW`.
- `MockExecutor`: records mock execution events only.
- `LangGraphLikeAdapter`: parses `{"tool": ..., "args": ...}` events.
- `OpenAIToolCallingLikeAdapter`: parses function-call-like events with JSON
  `arguments`.
- `CodingAgentLikeAdapter`: parses coding-agent-like `tool_use` events.

## Supported Mock Formats

LangGraph-like:

```json
{
  "agent_id": "agent_main",
  "task_id": "task_1",
  "tool": "send_email",
  "args": {"to": "alice@example.com", "body": "val_summary"}
}
```

OpenAI tool-calling-like:

```json
{
  "type": "function_call",
  "name": "send_email",
  "arguments": "{\"to\":\"alice@example.com\",\"body\":\"val_summary\"}",
  "call_id": "call_123"
}
```

Coding-agent-like:

```json
{
  "kind": "tool_use",
  "tool_name": "run_shell",
  "input": {"command_template": "pytest", "args": ["tests/"]},
  "agent": "opencode_mock"
}
```

## Guard Flow

1. Select the first adapter whose `supports(raw_event)` returns true.
2. Parse the raw event into `AgentAction`.
3. Canonicalize the action into `CanonicalToolCall`.
4. Build the CapProof `Action`, including receipt-backed content bindings.
5. Call `synthesize_proof(action, state)`.
6. Re-verify synthesized proof with `ReferenceMonitor.verify`.
7. Return `ALLOW`, `DENY`, or `ASK`.

`ASK` is returned only when proof synthesis reports
`EndorsementRequired`. The mock executor does not run on `ASK`.

## Behavior Examples

- Authorized `send_email` to `alice@example.com`: `ALLOW`, then mock executor
  records a `send_email` event.
- Unauthorized `send_email` to `attacker@example.com`: `DENY NoCap`, executor
  is not called.
- Unauthorized `bcc` recipient: `DENY NoCap`, executor is not called.
- Malformed OpenAI-style JSON arguments: fail-closed `DENY`.
- Coding-agent `pytest` template with matching command/cwd capabilities:
  `ALLOW`, then mock executor records `run_shell_template`.
- `sh -c`, pipes, redirects, base64 reconstruction, unsafe env, and stdin:
  `DENY`, no real shell execution.

## Safety Notes

- No real email is sent.
- No real network request is made.
- No real shell command is executed.
- No LLM is used as a security boundary.
- Adapter metadata and fake proof injection are ignored as authorization
  evidence; the verifier remains the final boundary.
- `run_shell` remains template-only and does not accept arbitrary shell strings.

## Future Real-Agent Mapping

- OpenCode: map CLI/tool-use events or an MCP proxy event stream into
  `CodingAgentLikeAdapter` semantics, then pass every proposed tool call through
  `CapProofMiddleware` before the executor.
- Claude Code: map tool-use blocks and filesystem/shell tool requests into a
  coding-agent adapter or MCP proxy. The shell wrapper must remain template-only
  for paper-grade experiments.
- Codex: map local tool calls or command proposals into `AgentAction` before any
  execution. Direct shell execution should stay outside the safety claim unless
  mediated by a template adapter.
- OpenAI tool-calling: parse function-call events with a production adapter that
  preserves all authority-bearing fields and rejects malformed argument JSON.
- LangGraph: install the middleware as a pre-tool node or tool executor wrapper
  so graph nodes cannot bypass Reference Monitor verification.

CLI wrappers, shell wrappers, and MCP proxy integrations are appropriate for
demo artifacts. They should not enter paper main experiments unless their
adapter coverage and canonicalization guarantees are independently audited.
