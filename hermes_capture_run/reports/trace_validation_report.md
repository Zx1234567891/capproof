# Hermes Trace Validation Report

Trace validation is offline only. It does not run Hermes, execute tools, send messages,
connect to network services, or provide an enforcement-wrapper claim.

- Trace source: imported trace
- Total events: 5
- Schema-valid events: 5
- Missing-field events: 1
- AdapterCoverageGap: 3
- Observer-only blocked: 1
- Side-effect-already-happened blocked: 1
- Executor called on deny: 0
- Executor called on ask: 0

## Event Checks

| Event | Hook | Mode | Missing schema fields | Pre-exec observed | Side effect happened | Fail closed |
| --- | --- | --- | --- | --- | --- | --- |
| manual_mixed_allowed_terminal_pytest | terminal_backend_pre_exec | pre_execution_gate | none | True | False | False |
| manual_mixed_denied_send_message_attacker | gateway_messaging_pre_send | pre_execution_gate | none | True | False | False |
| manual_mixed_observer_only_terminal_log | terminal_backend_pre_exec | observer_only | none | False | False | False |
| manual_mixed_missing_terminal_cwd | terminal_backend_pre_exec | pre_execution_gate | none | True | False | False |
| manual_mixed_post_effect_terminal | terminal_backend_pre_exec | pre_execution_gate | none | True | True | True |
