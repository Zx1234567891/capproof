# CapProof Project Handoff: Stage 0 to Stage 41AP

Last updated: 2026-07-03

Repository: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7`

Current effective checkpoint:

```text
47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c
checkpoint: aggregate Hermes OpenCode OpenClaw CapProof MCP parity matrix
```

This handoff upgrades the Stage 40RB runtime-bootstrap handoff to the completed Stage 41AP agent parity state. It is intended to let a new GPT/Codex session continue from the current project state without re-inferring prior work.

No API key or secret is included in this document. DeepSeek credentials must come only from `DEEPSEEK_API_KEY` in the environment. Do not write API keys, tokens, runtime caches, third-party source, `node_modules/`, local auth queue state, or generated runtime homes into commits.

## 1. Current Project State

CapProof is a capability-grounded enforcement prototype for AI agent tool use. The narrow security claim remains: authority-bearing tool actions are canonicalized and checked by CapProof's deterministic guard / Reference Monitor before a side effect can occur.

The project now includes:

- Core capability model, in-memory capability store, receipts, delegation checks, and deterministic Reference Monitor.
- Tool contracts and canonicalization for authority-bearing arguments.
- Kill-test, adapter-bypass, AuthSpec faithfulness, and replay/baseline harnesses.
- A productized standard CapProof MCP server with stdio transport, `initialize`, `tools/list`, `tools/call`, structured content, seven v1 tools, trace output, and limited sandboxed real execution.
- Hermes foreground workflow with DeepSeek, standard CapProof MCP server, sandboxed real execution, trace UX, and trusted ASK approval flow.
- OpenCode and OpenClaw local real runtimes under ignored `external/.agent-runtimes/`.
- Real parity evidence for Hermes, OpenCode, and OpenClaw using DeepSeek and the same standard CapProof MCP server.
- Artifact packaging, MCP compatibility profile, claims/non-claims matrix, and reviewer-oriented reproduction commands.

Stage 38REAL remains active as project policy: dry-run and preflight are safety readiness only, not completion evidence. Future stages must include real-environment scenarios before they can be marked complete. Missing gates must be reported as blocked states such as `blocked_missing_real_env_gate`, `blocked_runtime_missing`, or equivalent.

## 2. Stage 40O-D Completed: OpenCode Parity

Stage 40O-D commit:

```text
b949d71bc7d5ac3fe29be7a75d104c3338a71b72
checkpoint: validate OpenCode DeepSeek CapProof MCP parity
```

OpenCode reached Hermes-level local controlled parity for the tested CapProof MCP path:

- Real OpenCode process ran.
- OpenCode binary: `external/.agent-runtimes/bin/opencode`.
- OpenCode version: `1.17.13`.
- Real DeepSeek call observed.
- DeepSeek key source: `DEEPSEEK_API_KEY`.
- DeepSeek key written: false.
- Standard CapProof MCP server used.
- Old Hermes proxy used: false.
- `tools/list` observed.
- `tools/call` observed.
- ALLOW read/write/command behavior observed through the sandbox subset.
- DENY outside path, raw shell, and attacker recipient behavior observed.
- ASK pending request created.
- Trusted local CLI approved exact scope.
- Rerun ALLOW observed.
- LLM / MCP metadata approval rejected.
- Trace, live log, and report generated.

Allowed claim: OpenCode real MCP parity passed for the tested local CapProof MCP path. Do not claim all OpenCode built-in tools or production OpenCode protection.

## 3. Stage 40C-D Completed: OpenClaw Parity

Stage 40C-D commit:

```text
7d967ebe053e0a7b9e199e7540dbc30547c33411
checkpoint: validate OpenClaw DeepSeek CapProof MCP parity
```

OpenClaw reached Hermes-level local controlled parity for the tested CapProof MCP path:

- Real OpenClaw process ran.
- OpenClaw binary: `external/.agent-runtimes/bin/openclaw`.
- OpenClaw version: `OpenClaw 2026.6.11 (e085fa1)`.
- Real DeepSeek call observed.
- DeepSeek key source: `DEEPSEEK_API_KEY`.
- DeepSeek key written: false.
- Standard CapProof MCP server used.
- Old Hermes proxy used: false.
- `tools/list` observed.
- `tools/call` observed.
- ALLOW read/write/command behavior observed through the sandbox subset.
- DENY outside path, raw shell, and attacker recipient behavior observed.
- ASK pending request created.
- Trusted local CLI approved exact scope.
- Rerun ALLOW observed.
- LLM / MCP metadata approval rejected.
- Trace, live log, and report generated.

Allowed claim: OpenClaw real MCP parity passed for the tested local CapProof MCP path. Do not claim all OpenClaw built-in tools or production OpenClaw protection.

## 4. Stage 41AP Completed: Aggregate Agent Parity

Stage 41AP commit:

```text
47e66f0877aec0bf06b45f930ca0cb36fcb1ef9c
checkpoint: aggregate Hermes OpenCode OpenClaw CapProof MCP parity matrix
```

Final parity matrix:

| Agent | DeepSeek | MCP tools/list | MCP tools/call | Sandbox ALLOW | DENY gate | ASK approve rerun | Parity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hermes | yes | yes | yes | yes | yes | yes | true |
| OpenCode | yes | yes | yes | yes | yes | yes | true |
| OpenClaw | yes | yes | yes | yes | yes | yes | true |

Aggregate result:

```text
aggregate_agent_parity_passed: true
Hermes parity: true
OpenCode parity: true
OpenClaw parity: true
```

All three agents satisfy the tested local parity criteria:

- Real agent process ran.
- Real DeepSeek call observed.
- Key source = `DEEPSEEK_API_KEY`.
- Key written = false.
- Same standard CapProof MCP server used.
- No fork of CapProof guard/security logic.
- `tools/list` observed.
- `tools/call` observed.
- ALLOW read/write/command through sandbox.
- DENY outside path, raw shell, and attacker recipient.
- ASK pending request created.
- Trusted local CLI approved exact scope.
- Rerun ALLOW observed.
- LLM / MCP metadata approval rejected.
- Trace, live log, and report generated.

## 5. Validation

Recorded validation for Stage 41AP:

- Parity tests passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest`: 600 passed, 3 skipped.
- Kill tests: 24/24.
- Adapter bypass unexpected allow: 0.
- AuthSpec dangerous over-broadening: 0.
- Compileall: passed.
- Real key scan: `REAL_KEY_NOT_FOUND`.
- Forbidden tracked paths count: 0.
- Git status after Stage 41AP: clean.

## 6. Allowed Claims

It is safe to state:

- Hermes, OpenCode, and OpenClaw each exercised the same standard CapProof MCP server under controlled local real-environment conditions.
- All three used DeepSeek as the real model backend through `DEEPSEEK_API_KEY`.
- All three observed `tools/list` and `tools/call`.
- All three demonstrated ALLOW, DENY, and ASK -> trusted approve -> rerun ALLOW on the tested local CapProof MCP path.
- All three reused the same CapProof MCP server and did not fork CapProof guard/security logic.

## 7. Non-Claims That Must Remain

Do not claim:

- Production-level protection.
- All Hermes/OpenCode/OpenClaw built-in tool paths covered.
- All MCP clients covered.
- External MCP protection.
- Real email support.
- Raw shell support.
- Arbitrary filesystem access.
- OS-level network denial.
- DeepSeek as part of the safety TCB.
- LLM output can authorize execution.
- MCP metadata, `_meta`, tool descriptions, annotations, or client metadata can authorize execution.

The current result is local controlled parity on the tested CapProof MCP path, not comprehensive production coverage of all agent transports, built-in tools, plugins, or deployment modes.

## 8. Recommended Next Stage

Recommended next stage:

```text
Stage 42EVAL: real-environment evaluator suite and artifact freeze
```

The goal should be to freeze the current Hermes / OpenCode / OpenClaw parity evidence into a reviewer-safe evaluator artifact, not to expand feature scope.
