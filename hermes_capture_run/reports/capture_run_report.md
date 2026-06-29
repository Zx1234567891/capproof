# Hermes Capture-run Report

Stage 28 is a capture-run safety gate, no-run preflight, and optional trace-import
validation harness. It is not a real Hermes integration, not an enforcement wrapper,
and not a claim that CapProof protects real Hermes.

By default Hermes is not run. `--capture-run` is denied unless all explicit
capture-only safety environment variables are present and the command passes safety checks.

## Capture-run Decision

- Run attempted: False
- Run allowed: False
- State: DENY_CAPTURE_RUN
- Denial reason: default no-run preflight: explicit capture-run authorization not provided
- Command hash: n/a
- Timeout seconds: 20
- Trace path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/traces/captured_events.jsonl`
- Events captured: 0

## Trace Source

- Source: no-run

## Safety Status

- no_real_email: True
- no_real_network: True
- no_real_shell_high_risk_execution: True
- no_real_mcp_external_server: True
- no_dependency_install: True
- no_third_party_project_command: True
- no_real_tool_execution: True
- no_secrets_used: True
- no_hermes_source_modification: True
- not_enforcement_wrapper: True

## Trace Validation Summary

- Total events: 0
- Schema-valid events: 0
- Pre-execution-gate events: 0
- Observer-only events: 0
- Unsupported events: 0
- Missing-field events: 0
- Allowed: 0
- Denied: 0
- Ask: 0
- AdapterCoverageGap: 0
- Observer-only blocked: 0
- Executor called on deny: 0
- Executor called on ask: 0
- Side-effect-already-happened blocked: 0

## Hook Readiness

| Hook | Observed | Complete fields | Pre-execution observed | Side effect already happened | Enforcement-ready |
| --- | --- | --- | --- | --- | --- |
| tool_dispatcher | no | unknown | unknown | unknown | no |
| terminal | no | unknown | unknown | unknown | no |
| MCP | no | unknown | unknown | unknown | no |
| memory | no | unknown | unknown | unknown | no |
| gateway | no | unknown | unknown | unknown | no |
| delegation | no | unknown | unknown | unknown | no |
| scheduler | no | unknown | unknown | unknown | no |
| middleware_rewrite | no | unknown | unknown | unknown | no |

## Go / No-Go

- Enforcement wrapper: no-go.
- Real Hermes integration: False.
- Real Hermes integration claim: no.
- Real capture trace collected: False.
- More runtime samples needed: True.
- Blocking hook points: tool_dispatcher, terminal, MCP, memory, gateway, delegation, scheduler, middleware_rewrite.
