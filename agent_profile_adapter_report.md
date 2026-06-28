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
| `terminal` | observed Hermes terminal tool shape | Maps allowlisted raw pytest forms to `run_shell`; arbitrary raw commands deny. |
| `memory_write` | memory backend write | Authority claims are stripped before mock memory write. |
| `memory_action` | observed Hermes built-in memory shape | Maps to `memory_write`; persistent authority claims are stripped. |
| provider memory `tool_call` | `retaindb_remember` / `supermemory_store`-style shape | Routes through `memory_write`; provider metadata cannot mint caps. |
| `delegation` | subagent delegation | Requires delegation certificate evidence and attenuation. |
| `delegate_task` | observed Hermes subagent tool shape | Maps concrete requested child action to delegation evidence; natural-language goal cannot mint caps. |
| `gateway_message` | messaging/gateway action | Recipient is authority-bearing. |
| `tool_call` with `send_message` | observed Hermes target/message shape | Canonicalizes `target` into platform/channel/recipient; target requires recipient cap. |
| `scheduled_action` | cron/scheduled automation | Must match task/schedule/capability scope; old caps cannot replay. |
| `cronjob` | observed Hermes scheduled tool shape | Prompt-only authority denies; modeled targets/scripts must match scoped caps/templates. |
| `tool_call` with `edit_file` | observed Hermes file edit/patch shape | Maps path/resolved_path/patch ref to `write_file`; cross-profile or path mismatch fails closed. |
| `dispatcher_tool_call` | observed middleware effective args shape | Uses `effective_args`; records original/effective mismatch as middleware rewrite metadata. |

This profile is a mock event profile only. Real Hermes CLI, gateway, tools,
skills, MCP, memory, subagent, and terminal integrations require a separate
adapter coverage audit before they can support evaluation claims.

### Hermes Observed-Shape Coverage Update

Stage 20 adds mock coverage for the local static Hermes observed-source shapes
from Stage 19. This is still not a real Hermes integration. Hermes is not run,
dependencies are not installed, no third-party commands execute, and all
effects remain mock-only.

Current observed-source coverage is full 0, partial 11, uncovered 0. The partial
status is intentional: runtime event capture is still needed for terminal
process-control fields, non-http MCP tools, permission response/control
surfaces, media/reaction messaging variants, full patch semantics, and cron job
lifecycle events. CapProof must not claim it protects real Hermes until those
fields are audited against real runtime payloads.

## Stage 21 Hermes Supported-Subset Dry-Run

Stage 21 defines a supported subset for mock/replay Hermes JSON events, plus
separate sanitized/stripped allow, explicit-deny, and unknown/runtime-capture-
needed subsets. The dry-run runner is `run_hermes_dry_run.py`; it feeds events through
`HermesAgentLikeAdapter`, `AgentAdapterRegistry`, `CapProofMiddleware`, and
`MockExecutor`.

Supported dry-run shapes include allowlisted terminal pytest templates, exact
authorized `send_message` targets, content-only memory writes, delegated email
with a valid Delegation Certificate, dynamic MCP `http_post` to authorized
endpoints, authorized `edit_file`, and schedule-bound cron email. Sanitized
memory cases may `ALLOW` a content-only mock memory write after
`authority_claims` are stripped and no capability is minted. Explicit-deny
shapes include raw shell, unauthorized recipients/endpoints, MCP metadata
authority claims, delegation without certificate, delegation amplification,
stale cron capability replay, dangerous `edit_file`, and dispatcher
`effective_args` rewrites to unauthorized targets. Unknown shapes such as pty
terminal sessions, stdio MCP transport, gateway media attachments, and cronjob
lifecycle updates fail closed with `AdapterCoverageGap`.

This remains mock-profile / static-audit based. It does not run Hermes, install
dependencies, execute third-party commands, call real tools, use real network,
send email, or execute shell. Runtime event capture is still required before any
real Hermes wrapper or integration claim.

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
