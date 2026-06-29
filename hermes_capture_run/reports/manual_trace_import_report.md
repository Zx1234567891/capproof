# Manual Hermes Trace Import Report

Stages 29A and 29B import hand-written Hermes runtime JSONL traces for offline validation only.
This report covers manual JSONL trace-import validation only.
This stage does not run Hermes, does not execute capture-run, does not install dependencies,
does not execute third-party commands, does not execute real tools, does not use network,
and does not modify Hermes source. It cannot support a real Hermes integration claim or a
claim that true runtime capture has completed.

This is not an enforcement wrapper. `observer_only` events cannot produce enforcement ALLOW,
`side_effect_already_happened=true` events cannot support an enforcement claim, missing-field
events must fail closed with `AdapterCoverageGap`, unsupported events must fail closed, and
DENY / ASK decisions must not execute the mock executor.

## Trace Files Imported

- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/denied_trace.jsonl`
- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/dispatcher_rewrite_trace.jsonl`
- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/gateway_attachment_trace.jsonl`
- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/mcp_unsupported_trace.jsonl`
- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/mixed_trace.jsonl`
- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/scheduler_trace.jsonl`
- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/supported_trace.jsonl`
- `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/imported_traces/manual/terminal_edge_trace.jsonl`

## Aggregate Summary

- Trace files: 8
- Total events: 24
- Valid events: 24
- Schema-valid events: 24
- Pre-execution-gate events: 22
- Observer-only events: 1
- Unsupported events: 3
- Missing-field events: 4
- Side-effect-already-happened events: 2
- Allowed / denied / ask: 5 / 19 / 0
- Allowed: 5
- Denied: 19
- Ask: 0
- AdapterCoverageGap: 11
- Observer-only blocked: 1
- Side-effect posthoc blocked: 2
- Executor called on deny: 0
- Executor called on ask: 0

## Original vs Expanded Trace Sets

| Set | Trace files | Events | Valid | Pre-exec | Observer-only | Unsupported | Missing-field | Side-effect posthoc | Allow | Deny | Ask | AdapterCoverageGap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original | 3 | 12 | 12 | 11 | 1 | 1 | 1 | 1 | 4 | 8 | 0 | 3 |
| expanded | 5 | 12 | 12 | 11 | 0 | 2 | 3 | 1 | 1 | 11 | 0 | 8 |

## Per-trace Summary

| Trace | Events | Valid | Pre-exec | Observer-only | Missing-field | Side-effect posthoc | Allow | Deny | Ask | AdapterCoverageGap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| denied_trace.jsonl | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| dispatcher_rewrite_trace.jsonl | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| gateway_attachment_trace.jsonl | 2 | 2 | 2 | 0 | 1 | 0 | 0 | 2 | 0 | 2 |
| mcp_unsupported_trace.jsonl | 3 | 3 | 2 | 0 | 1 | 0 | 0 | 3 | 0 | 3 |
| mixed_trace.jsonl | 5 | 5 | 4 | 1 | 1 | 1 | 1 | 4 | 0 | 3 |
| scheduler_trace.jsonl | 3 | 3 | 3 | 0 | 0 | 0 | 1 | 2 | 0 | 0 |
| supported_trace.jsonl | 3 | 3 | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| terminal_edge_trace.jsonl | 3 | 3 | 3 | 0 | 1 | 1 | 0 | 3 | 0 | 3 |

## Per-trace Results

- denied: 4 events, 0 ALLOW, 4 DENY, 0 AdapterCoverageGap
- dispatcher_rewrite_trace: 1 events, 0 ALLOW, 1 DENY, 0 AdapterCoverageGap
- gateway_attachment_trace: 2 events, 0 ALLOW, 2 DENY, 2 AdapterCoverageGap
- mcp_unsupported_trace: 3 events, 0 ALLOW, 3 DENY, 3 AdapterCoverageGap
- mixed: 5 events, 1 ALLOW, 4 DENY, 3 AdapterCoverageGap
- scheduler_trace: 3 events, 1 ALLOW, 2 DENY, 0 AdapterCoverageGap
- supported: 3 events, 3 ALLOW, 0 DENY, 0 AdapterCoverageGap
- terminal_edge_trace: 3 events, 0 ALLOW, 3 DENY, 3 AdapterCoverageGap

## Key Scenario Results

- dispatcher rewrite: effective attacker target -> DENY NoCap.
- scheduler replay: authorized register ALLOW; unauthorized replay / mismatch DENY.
- MCP unsupported: stdio, missing endpoint, resource/prompt -> DENY AdapterCoverageGap.
- gateway attachment: attachment/thread and missing recipient -> DENY AdapterCoverageGap.
- terminal edge cases: pty/background, missing fields, post-effect -> DENY AdapterCoverageGap.


## Hook Readiness Summary

| Hook | Observed in manual trace | Complete fields | Pre-execution observed | Side effect already happened | Enforcement-ready |
| --- | --- | --- | --- | --- | --- |
| tool_dispatcher | no | unknown | unknown | unknown | no |
| terminal | yes | partial | no | yes | no |
| MCP | yes | partial | yes | no | no |
| memory | yes | yes | yes | no | yes |
| gateway | yes | partial | yes | no | no |
| delegation | yes | yes | yes | no | yes |
| scheduler | yes | yes | yes | no | yes |
| middleware_rewrite | yes | yes | yes | no | yes |

## Scope

- Trace source: hand-written JSONL files from the original Stage 29A set and expanded Stage 29B set.
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
