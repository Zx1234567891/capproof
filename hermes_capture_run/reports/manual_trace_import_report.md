# Manual Hermes Trace Import Report

Stage 29A imports hand-written Hermes runtime JSONL traces for offline validation only.
This stage does not run Hermes, does not execute capture-run, does not install dependencies,
does not execute third-party commands, does not execute real tools, does not use network,
and does not modify Hermes source. It cannot support a real Hermes integration claim or a
claim that true runtime capture has completed.

This is not an enforcement wrapper. `observer_only` events cannot produce enforcement ALLOW,
`side_effect_already_happened=true` events cannot support an enforcement claim, missing-field
events must fail closed with `AdapterCoverageGap`, and DENY / ASK decisions must not execute
the mock executor.

## Trace Files Imported

- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/denied_trace.jsonl`
- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/mixed_trace.jsonl`
- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/supported_trace.jsonl`

## Aggregate Summary

- Trace files: 3
- Total events: 12
- Valid events: 12
- Schema-valid events: 12
- Pre-execution-gate events: 11
- Observer-only events: 1
- Missing-field events: 1
- Side-effect-already-happened events: 1
- Allowed / denied / ask: 4 / 8 / 0
- Allowed: 4
- Denied: 8
- Ask: 0
- AdapterCoverageGap: 3
- Observer-only blocked: 1
- Side-effect posthoc blocked: 1
- Executor called on deny: 0
- Executor called on ask: 0

## Per-trace Summary

| Trace | Events | Valid | Pre-exec | Observer-only | Missing-field | Side-effect posthoc | Allow | Deny | Ask | AdapterCoverageGap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| denied_trace.jsonl | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| mixed_trace.jsonl | 5 | 5 | 4 | 1 | 1 | 1 | 1 | 4 | 0 | 3 |
| supported_trace.jsonl | 3 | 3 | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |

## Per-trace Results

- denied: 4 events, 0 ALLOW, 4 DENY, 0 AdapterCoverageGap
- mixed: 5 events, 1 ALLOW, 4 DENY, 3 AdapterCoverageGap
- supported: 3 events, 3 ALLOW, 0 DENY, 0 AdapterCoverageGap


## Hook Readiness Summary

| Hook | Observed in manual trace | Complete fields | Pre-execution observed | Side effect already happened | Enforcement-ready |
| --- | --- | --- | --- | --- | --- |
| tool_dispatcher | no | unknown | unknown | unknown | no |
| terminal | yes | partial | no | yes | no |
| MCP | yes | yes | yes | no | yes |
| memory | yes | yes | yes | no | yes |
| gateway | yes | yes | yes | no | yes |
| delegation | yes | yes | yes | no | yes |
| scheduler | no | unknown | unknown | unknown | no |
| middleware_rewrite | no | unknown | unknown | unknown | no |

## Scope

- Trace source: hand-written JSONL files.
- Capture-run: not executed.
- Real Hermes runtime: not run.
- Dependency install: not performed.
- Third-party commands: not executed.
- Real tool execution: not performed.
- External network calls: not performed.
- Real captured events: none in this stage.
- Enforcement wrapper: no-go.
- Real Hermes integration claim: no.
- More runtime samples are still required before any enforcement wrapper discussion.
