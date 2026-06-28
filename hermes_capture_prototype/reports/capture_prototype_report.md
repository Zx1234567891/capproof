# Hermes Capture Prototype Report

This stage is not a real Hermes integration. Hermes is not run, dependencies are not installed,
third-party project commands are not executed, real tools are not called, no network is used,
and no shell command is executed. The prototype processes JSON / JSONL captured-event examples only.

`pre_execution_gate` events can enter CapProof guard dry-run. `observer_only` events are recorded
only and cannot produce enforcement ALLOW. Unsupported or missing-field events fail closed.
DENY and ASK decisions do not call `MockExecutor`; ALLOW decisions use only `MockExecutor`.

Future real integration must first verify that these hook points are available in Hermes runtime.

## Summary

- Total events processed: 15
- Valid pre_execution_gate events: 10
- Observer-only events: 1
- Unsupported / missing-field events: 4
- Allowed: 6
- Denied: 9
- Ask: 0
- AdapterCoverageGap count: 5
- Observer-only blocked count: 1
- Executor called on deny: 0
- Executor called on ask: 0
- Trace path: /home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_prototype/traces/capture_trace.jsonl
- Ready for real capture-only instrumentation: True
- Ready for enforcement wrapper: False

## Hook Readiness

| Hook | Required fields | Prototype support | Runtime verification needed |
| --- | --- | --- | --- |
| tool dispatcher | tool_name, original_args, effective_args, source_component | supported for synthetic send_message | yes |
| terminal backend | command, cwd, env, stdin | supported for allowlisted templates; raw shell denied | yes |
| MCP | server, tool_name, arguments, transport endpoint | supported for synthetic http_post | yes |
| memory | content, origin, persistent | supported with authority stripping | yes |
| gateway | platform/target, recipient/target, body/body_ref/message | supported for synthetic send_message | yes |
| delegation | parent_agent, child_agent, goal/scope, cert ref or explicit missing cert | supported for synthetic delegate_task | yes |
| scheduler | schedule_id plus action target | supported for synthetic cron registration | yes |
| middleware rewrite | original_args, effective_args, source_component | supported; effective_args authorize | yes |

## Results

| Case | Hook | Mode | Verdict | Reason | Missing fields | Executor |
| --- | --- | --- | --- | --- | --- | --- |
| proto_tool_dispatcher_send_message | tool_dispatcher_pre_call | pre_execution_gate | ALLOW |  |  | called |
| proto_terminal_pytest | terminal_backend_pre_exec | pre_execution_gate | ALLOW |  |  | called |
| proto_terminal_raw_shell | terminal_backend_pre_exec | pre_execution_gate | DENY | CommandTemplateViolation |  | not_called |
| proto_terminal_missing_fields | terminal_backend_pre_exec | pre_execution_gate | DENY | AdapterCoverageGap | effective_args.cwd, effective_args.env, effective_args.stdin | not_called |
| proto_gateway_authorized | gateway_messaging_pre_send | pre_execution_gate | ALLOW |  |  | called |
| proto_gateway_missing_recipient | gateway_messaging_pre_send | pre_execution_gate | DENY | AdapterCoverageGap | effective_args.recipient | not_called |
| proto_mcp_authorized | mcp_pre_transport | pre_execution_gate | ALLOW |  |  | called |
| proto_mcp_evil_endpoint | mcp_pre_transport | pre_execution_gate | DENY | NoCap |  | not_called |
| proto_mcp_missing_endpoint | mcp_pre_transport | pre_execution_gate | DENY | AdapterCoverageGap | effective_args.transport.endpoint | not_called |
| proto_memory_authority_claim | memory_pre_write | pre_execution_gate | ALLOW |  |  | called |
| proto_delegation_without_cert | subagent_delegation_pre_dispatch | pre_execution_gate | DENY | DelegationMissing |  | not_called |
| proto_scheduler_authorized | scheduler_cron_pre_register | pre_execution_gate | ALLOW |  |  | called |
| proto_middleware_effective_attacker | skill_plugin_middleware_rewrite | pre_execution_gate | DENY | NoCap |  | not_called |
| proto_observer_posthoc_terminal | observer_posthoc | observer_only | DENY | AdapterCoverageGap |  | not_called |
| proto_unsupported_capture_mode | terminal_backend_pre_exec | unsupported | DENY | AdapterCoverageGap |  | not_called |

## Remaining Missing Hook Fields

- effective_args.cwd
- effective_args.env
- effective_args.recipient
- effective_args.stdin
- effective_args.transport.endpoint

## Go / No-Go

- Capture-only instrumentation prototype: go.
- Enforcement wrapper: no-go until real Hermes runtime hook availability and payload samples are verified.
- Real Hermes integration claim: no.
