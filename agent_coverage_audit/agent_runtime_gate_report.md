# Agent Runtime Gate Report

## Stage Positioning

- Stage 34R-G only detects local OpenCode/OpenClaw runtime readiness.
- It does not run a real OpenCode/OpenClaw agent smoke.
- It does not install dependencies or third-party source.
- It does not claim real OpenCode/OpenClaw integration.
- It reuses the same standard CapProof MCP server command.

## Shared CapProof MCP Server

- command: `python run_capproof_mcp_server.py --stdio --sandboxed-real-execution`
- uses_shared_capproof_mcp_server: True
- forked_guard_logic: False

## OpenCode

- command_name: `opencode`
- command_path: ``
- runtime_present: False
- version_detected: False
- version: ``
- config_path_detected: False
- config_path: ``
- mcp_status_available: False
- mcp_doctor_probe_available: False
- mcp_tools_available: False
- can_load_capproof_mcp_config: False
- real_smoke_eligible: False
- reason: runtime_missing: opencode command is not on PATH
- real_agent_process_run: False
- tools_list_observed_from_real_agent: False
- tools_call_observed_from_real_agent: False

### Probes

- No metadata commands were run because the runtime command was missing.

## OpenClaw

- command_name: `openclaw`
- command_path: ``
- runtime_present: False
- version_detected: False
- version: ``
- config_path_detected: False
- config_path: ``
- mcp_status_available: False
- mcp_doctor_probe_available: False
- mcp_tools_available: False
- can_load_capproof_mcp_config: False
- real_smoke_eligible: False
- reason: runtime_missing: openclaw command is not on PATH
- real_agent_process_run: False
- tools_list_observed_from_real_agent: False
- tools_call_observed_from_real_agent: False

### Probes

- No metadata commands were run because the runtime command was missing.

## Non-Claims

- real_opencode_integration_claim: False
- real_openclaw_integration_claim: False
- production_level_protection_claim: False
- api_key_written: False
- external_or_venv_committed: False
- No real agent `tools/list` or `tools/call` observation is claimed.
- OpenCode/OpenClaw metadata cannot mint capability.
