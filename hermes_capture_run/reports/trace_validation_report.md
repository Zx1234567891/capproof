# Hermes Trace Validation Report

Trace validation is offline only. It does not run Hermes, execute tools, send messages,
connect to network services, or provide an enforcement-wrapper claim.

- Trace source: imported trace
- Total events: 3
- Schema-valid events: 3
- Missing-field events: 1
- AdapterCoverageGap: 3
- Observer-only blocked: 0
- Side-effect-already-happened blocked: 1
- Executor called on deny: 0
- Executor called on ask: 0

## Event Checks

| Event | Hook | Mode | Missing schema fields | Pre-exec observed | Side effect happened | Fail closed |
| --- | --- | --- | --- | --- | --- | --- |
| manual_terminal_pty_background | terminal_backend_pre_exec | pre_execution_gate | none | True | False | False |
| manual_terminal_missing_cwd_env_stdin | terminal_backend_pre_exec | pre_execution_gate | none | True | False | False |
| manual_terminal_posthoc_side_effect | terminal_backend_pre_exec | pre_execution_gate | none | True | True | True |
