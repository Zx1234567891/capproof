# Hermes Capture-run Report

## Stage Position

Stage 27 is a controlled capture-only run attempt. It is not an enforcement wrapper,
does not claim that CapProof is integrated with or protects real Hermes, and does not
trust natural-language logs as authorization evidence. If explicit capture-run
authorization is absent, the run fails closed with `DENY_CAPTURE_RUN` and no Hermes
process is started.

The default no-run report means `ALLOW_HERMES_CAPTURE_RUN=1` and
`HERMES_CAPTURE_COMMAND` were not both provided, so capture-run was not executed.

## Capture-run Status

- Run attempted: False
- Run allowed: False
- State: DENY_CAPTURE_RUN
- Denial reason: default no-run preflight: explicit capture-run authorization not provided
- Command hash: n/a
- Timeout seconds: 20
- Trace path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/traces/captured_events.jsonl`
- Events captured: 0

## Safety Status

- no_real_email: True
- no_real_external_network: True
- no_real_shell_high_risk_execution: True
- no_real_mcp_external_server: True
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
- Executor called on deny: 0
- Executor called on ask: 0

## Hook Readiness

| Hook | Observed | Complete fields | Pre-execution | Enforcement-ready | Missing fields |
| --- | --- | --- | --- | --- | --- |
| tool_dispatcher | unknown | unknown | unknown | no | none |
| terminal | unknown | unknown | unknown | no | none |
| mcp | unknown | unknown | unknown | no | none |
| memory | unknown | unknown | unknown | no | none |
| gateway | unknown | unknown | unknown | no | none |
| delegation | unknown | unknown | unknown | no | none |
| scheduler | unknown | unknown | unknown | no | none |
| middleware_rewrite | unknown | unknown | unknown | no | none |

## Go / No-Go

- Enforcement wrapper: no-go.
- Real Hermes integration claim: no.
- Real Hermes integration: False.
- Real capture trace collected: False.
- More runtime samples needed: True.
