# Agent Profile Adapter Report

## Scope

Stage 17 adds mock adapter profiles for OpenCode-like, OpenClaw-like,
Hermes-agent-like, and harness-native events. This is not a real integration
with OpenCode, OpenClaw, Hermes, their CLIs, their gateways, their tools, their
skills, or their MCP servers.

All execution remains mock-only through `MockExecutor`. No email is sent, no
network request is made, and no shell command is executed. The adapters do not
mint capabilities and do not treat workflow, skill, watcher, MCP, gateway,
memory, delegation, or cron metadata as authorization.

The profile adapters only parse raw events into `AgentAction`, canonicalize
them into `CanonicalToolCall`, and hand them to `CapProofMiddleware`.
`OpenCodeLikeAdapter`, `OpenClawLikeAdapter`, and `HermesAgentLikeAdapter`
do not execute tools.
`CapProofMiddleware` still calls the Proof Synthesizer and then the Reference
Monitor. The Reference Monitor remains the final allow/deny boundary.

## OpenCodeLikeAdapter

| Event | Tool surface | Behavior |
| --- | --- | --- |
| `tool_call` with `run_shell` | terminal/build command proposal | Build mode enters guard; plan mode returns proposed action and does not execute. |
| `tool_call` with `write_file` | IDE/file write proposal | Path/content/overwrite become canonical `write_file` args. |
| `tool_call` writing `AGENTS.md` or config/policy file | high-impact file write | Requires scoped `write_file` capabilities like any other high-impact path. |

`run_shell` remains template-only. Raw shell forms such as `sh-c`, pipes,
redirects, and base64 reconstruction fail closed through canonicalization.

## OpenClawLikeAdapter

| Event | Tool surface | Behavior |
| --- | --- | --- |
| `tool_call` | legacy tool invocation | Enters the normal guard flow. |
| `watcher_event` | observed action | Can be denied or routed to ask, but cannot create authorization. |
| `skill_action` | skill/plugin action | Skill metadata cannot mint caps; `http_post` needs endpoint authority. |
| `tool_call` with `run_shell` | legacy shell proposal | Must satisfy the shell template policy. |

This profile is a compatibility mock profile only. It is not a claim that
CapProof protects a real OpenClaw implementation.

## HermesAgentLikeAdapter

| Event | Tool surface | Behavior |
| --- | --- | --- |
| `tool_call` | ordinary tool invocation | Enters the normal guard flow. |
| `skill_action` | skill/tool workflow | Skill metadata cannot mint caps; endpoints require endpoint caps. |
| `mcp_tool_call` | MCP server tool call | External endpoints require endpoint caps. |
| `terminal_action` | terminal backend command | Must satisfy the shell template policy. |
| `memory_write` | memory backend write | Authority claims are stripped before mock memory write. |
| `delegation` | subagent delegation | Requires delegation certificate evidence and attenuation. |
| `gateway_message` | messaging/gateway action | Recipient is authority-bearing. |
| `scheduled_action` | cron/scheduled automation | Must match task/schedule/capability scope; old caps cannot replay. |

This profile is a mock event profile only. Real Hermes CLI, gateway, tools,
skills, MCP, memory, subagent, and terminal integrations require a separate
adapter coverage audit before they can support evaluation claims.

## HarnessAdapter

| Event | Tool surface | Behavior |
| --- | --- | --- |
| `kill_test_action` | attack/benign kill-test action | Parses into the same `AgentAction` and guard flow as other adapters. |
| `tool_call` | harness-native tool proposal | Intended future input format for AuthLaunderBench-style tasks. |

Attack and benign events use the same `CapProofMiddleware` path. The adapter
does not accept fake proof metadata as authorization evidence.

## AgentAdapterRegistry

- `register(adapter)` appends an adapter profile.
- `select(raw_event)` fails closed when no adapter supports the event.
- `select(raw_event)` fails closed on ambiguous adapter match when multiple
  adapters support the same event.
- `parse_and_canonicalize(raw_event)` returns parsed action plus canonical call;
  it does not execute tools.
- Unknown source and unknown `event_type` are denied with
  `CanonicalizationMismatch`.

## Safety Position

- No real OpenCode integration.
- No real OpenClaw integration.
- No real Hermes integration.
- No real email, network, shell, gateway, MCP, or tool execution.
- No LLM is part of the security boundary.
- All high-impact profile actions still enter Reference Monitor verification.
- Real product integrations still require adapter field coverage and
  canonicalization audits.
