# Hermes DeepSeek No-Tools Run Report

## Stage Positioning

- This stage validates a gated Hermes + DeepSeek no-tools model-backend run path.
- This stage is not a CapProof enforcement wrapper.
- The default path does not run Hermes.
- Hermes is run only when `--run-hermes-no-tools` is requested and all explicit safety environment variables are present.
- DeepSeek is a Hermes model backend only and is not part of the CapProof TCB.
- No API key value is printed or written to this report.

## Run Decision

- run_attempted: False
- run_allowed: False
- denial_reason: not requested; --run-hermes-no-tools was not invoked
- command_hash: not_available
- timeout: 20
- exit_code: not_run
- timed_out: False
- command_validation: DENY_HERMES_DEEPSEEK_RUN
- command_validation_reason: missing required Hermes DeepSeek no-tools environment variables
- no_tools_feasibility: not confirmed

## DeepSeek Status

- key_present: True
- key_printed: False
- key_written: False
- base_url: https://api.deepseek.com
- model: deepseek-v4-pro
- smoke_test_status: see `deepseek_smoke_test_report.md` if a gated smoke test was explicitly run.

## Hermes Status

- hermes_run_attempted: False
- response_received: False
- tool_call_detected: False
- gateway_detected: False
- mcp_detected: False
- shell_detected: False
- file_write_detected: False
- memory_persistence_detected: False
- key_leak_detected: False
- stdout_bytes: 0
- stderr_bytes: 0

## Security Boundary

- DeepSeek not in CapProof TCB: true
- DeepSeek can mint capability: false
- DeepSeek can allow tool call: false
- Hermes tools disabled requirement: true
- CapProof guard not yet enforcing Hermes DeepSeek runs: true
- No claim of real CapProof protection for Hermes + DeepSeek is made here.

## Go / No-Go

- Hermes DeepSeek no-tools model backend observed: False
- Hermes + DeepSeek tool execution: no-go until a later CapProof guard integration stage.
- Enforcement wrapper: no-go.
- Claim that CapProof protects Hermes + DeepSeek: no-go.
