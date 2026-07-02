# Agent Runtime Gate Report

## Stage Positioning

- Stage 39RT performs real local runtime discovery/version/probe commands.
- Dry-run and preflight are not completion evidence under Stage 38REAL.
- Runtime-missing results are blocked runtime states, not integration completion.
- This stage does not run real OpenCode/OpenClaw agent smoke.
- Third-party source may be cloned under ignored `external/` when explicitly requested, but it is not submitted and does not by itself prove runtime availability.
- It does not install dependencies or submit third-party source.
- It does not claim real OpenCode/OpenClaw integration.

## Policy

- real_environment_policy_active: True
- dry_run_counts_as_completion: False
- blocked_if_missing: True

## Shared CapProof MCP Server

- command: `python run_capproof_mcp_server.py --stdio --sandboxed-real-execution`
- uses_shared_capproof_mcp_server: True
- forked_guard_logic: False

## OpenCode

- command_name: `opencode`
- command_path: `None`
- source_repo_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/opencode`
- source_repo_present: True
- source_repo_commit: `f52424e05fab0edddb4462112ceb02044085f903`
- source_repo_remote: `https://github.com/anomalyco/opencode`
- runtime_present: False
- version_detected: `None`
- config_template_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/real_agent_integrations/opencode_mcp_server/configs/opencode.capproof.mcp.example.jsonc`
- capproof_mcp_config_template_exists: True
- capproof_mcp_command_referenced: True
- config_load_supported: False
- mcp_status_available: False
- mcp_doctor_probe_available: False
- mcp_tools_available: False
- real_smoke_eligible: False
- reason: blocked_runtime_missing
- blocked_runtime_missing: True
- real_agent_process_run: False
- tools_list_observed_from_real_agent: False
- tools_call_observed_from_real_agent: False
- real_integration_claim: False

### Real Runtime Probes

- which_opencode: `which opencode` attempted=True, available=False, exit_code=1, error=``

- OpenCode real smoke blocked_runtime_missing.
- OpenCode integration not complete.

## OpenClaw

- command_name: `openclaw`
- command_path: `None`
- source_repo_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/openclaw`
- source_repo_present: True
- source_repo_commit: `5bcd25f0fb6de3cc2ba6b6a7688a9361eb355143`
- source_repo_remote: `https://github.com/openclaw/openclaw`
- runtime_present: False
- version_detected: `None`
- config_template_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/real_agent_integrations/openclaw_mcp_server/configs/openclaw.capproof.mcp.commands.md`
- capproof_mcp_config_template_exists: True
- capproof_mcp_command_referenced: True
- config_load_supported: False
- mcp_status_available: False
- mcp_doctor_probe_available: False
- mcp_tools_available: False
- real_smoke_eligible: False
- reason: blocked_runtime_missing
- blocked_runtime_missing: True
- real_agent_process_run: False
- tools_list_observed_from_real_agent: False
- tools_call_observed_from_real_agent: False
- real_integration_claim: False

### Real Runtime Probes

- which_openclaw: `which openclaw` attempted=True, available=False, exit_code=1, error=``

- OpenClaw real smoke blocked_runtime_missing.
- OpenClaw integration not complete.

## Next Stage Recommendation

- Install or expose a real OpenCode/OpenClaw runtime before real agent smoke

## Non-Claims

- integration_claim_made: False
- real_opencode_integration_claim: False
- real_openclaw_integration_claim: False
- production_level_protection_claim: False
- api_key_written: False
- external_venv_node_modules_runtime_cache_committed: False
- No real agent `tools/list` or `tools/call` observation is claimed in Stage 39RT.
- OpenCode/OpenClaw metadata cannot mint capability.
- The same standard CapProof MCP server is reused; CapProof guard logic is not forked.
