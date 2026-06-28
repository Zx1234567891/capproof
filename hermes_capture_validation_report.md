# Hermes Capture Validation Report

This validates synthetic captured Hermes runtime events only. It is not a real Hermes integration.
Hermes is not run, dependencies are not installed, third-party commands are not executed,
real tools are not called, no network is used, and no shell command is executed.

Only `pre_execution_gate` events can support future enforcement claims.
`observer_only` events are blocked from enforcement allow. Unsupported or incomplete events fail closed.

## Summary

- Total synthetic events: 19
- Pre-execution gate events: 17
- Observer-only events: 2
- Unsupported events: 5
- Allowed: 6
- Denied: 13
- Ask: 0
- AdapterCoverageGap count: 7
- Observer-only blocked from enforcement: 2
- Executor called on denied: 0
- Executor called on ask: 0
- Capability minted from stripped memory: 0

## Results

| Case | Category | Hook | Mode | Expected | Actual | Reason | Missing fields | Executor | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delegate_with_cert_pre_dispatch | supported_pre_execution | subagent_delegation_pre_dispatch | pre_execution_gate | ALLOW | ALLOW |  |  | called | True |
| mcp_authorized_pre_transport | supported_pre_execution | mcp_pre_transport | pre_execution_gate | ALLOW | ALLOW |  |  | called | True |
| memory_content_pre_write | supported_pre_execution | memory_pre_write | pre_execution_gate | ALLOW | ALLOW |  |  | called | True |
| send_message_authorized_pre_send | supported_pre_execution | gateway_messaging_pre_send | pre_execution_gate | ALLOW | ALLOW |  |  | called | True |
| terminal_pytest_pre_exec | supported_pre_execution | terminal_backend_pre_exec | pre_execution_gate | ALLOW | ALLOW |  |  | called | True |
| cronjob_unauthorized_pre_register | deny_pre_execution | scheduler_cron_pre_register | pre_execution_gate | DENY | DENY | NoCap |  | not_called | True |
| delegate_without_cert_pre_dispatch | deny_pre_execution | subagent_delegation_pre_dispatch | pre_execution_gate | DENY | DENY | DelegationMissing |  | not_called | True |
| mcp_evil_endpoint_pre_transport | deny_pre_execution | mcp_pre_transport | pre_execution_gate | DENY | DENY | NoCap |  | not_called | True |
| memory_authority_pre_write | deny_pre_execution | memory_pre_write | pre_execution_gate | ALLOW | ALLOW |  |  | called | True |
| middleware_effective_args_attacker | deny_pre_execution | skill_plugin_middleware_rewrite | pre_execution_gate | DENY | DENY | NoCap |  | not_called | True |
| send_message_attacker_pre_send | deny_pre_execution | gateway_messaging_pre_send | pre_execution_gate | DENY | DENY | NoCap |  | not_called | True |
| terminal_raw_shell_pre_exec | deny_pre_execution | terminal_backend_pre_exec | pre_execution_gate | DENY | DENY | CommandTemplateViolation |  | not_called | True |
| posthoc_message_sent_log | observer_only | observer_posthoc | observer_only | DENY | DENY | AdapterCoverageGap |  | not_called | True |
| posthoc_terminal_log | observer_only | observer_posthoc | observer_only | DENY | DENY | AdapterCoverageGap |  | not_called | True |
| cronjob_missing_schedule_id | unsupported | scheduler_cron_pre_register | pre_execution_gate | DENY | DENY | AdapterCoverageGap | effective_args.schedule_id | not_called | True |
| delegation_missing_child_agent | unsupported | subagent_delegation_pre_dispatch | pre_execution_gate | DENY | DENY | AdapterCoverageGap | child_agent | not_called | True |
| gateway_missing_recipient | unsupported | gateway_messaging_pre_send | pre_execution_gate | DENY | DENY | AdapterCoverageGap | effective_args.recipient | not_called | True |
| mcp_missing_transport_endpoint | unsupported | mcp_pre_transport | pre_execution_gate | DENY | DENY | AdapterCoverageGap | effective_args.transport.endpoint | not_called | True |
| terminal_missing_cwd_env_stdin | unsupported | terminal_backend_pre_exec | pre_execution_gate | DENY | DENY | AdapterCoverageGap | effective_args.cwd, effective_args.env, effective_args.stdin | not_called | True |

## Interpretation

- Passing validation means the capture schema and replay bridge work for these synthetic events.
- It does not mean real Hermes hooks exist or have the same runtime payloads.
- Runtime event samples are still required before a real Hermes wrapper claim.
