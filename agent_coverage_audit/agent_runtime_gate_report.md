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

- command: `python tools/run_capproof_mcp_server.py --stdio --sandboxed-real-execution`
- uses_shared_capproof_mcp_server: True
- forked_guard_logic: False

## OpenCode

- command_name: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/bin/opencode`
- command_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/npm-prefix/opencode/node_modules/opencode-ai/bin/opencode.exe`
- source_repo_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/opencode`
- source_repo_present: True
- source_repo_commit: `f52424e05fab0edddb4462112ceb02044085f903`
- source_repo_remote: `https://github.com/anomalyco/opencode`
- runtime_present: True
- version_detected: `1.17.13`
- config_template_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/real_agent_integrations/opencode_mcp_server/configs/opencode.capproof.mcp.example.jsonc`
- capproof_mcp_config_template_exists: True
- capproof_mcp_command_referenced: True
- config_load_supported: True
- mcp_status_available: False
- mcp_doctor_probe_available: False
- mcp_tools_available: True
- real_smoke_eligible: True
- reason: ok
- blocked_runtime_missing: False
- real_agent_process_run: False
- tools_list_observed_from_real_agent: False
- tools_call_observed_from_real_agent: False
- real_integration_claim: False

### Real Runtime Probes

- which_opencode: `which /home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/bin/opencode` attempted=True, available=True, exit_code=0, error=``
- opencode_version_dash: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/npm-prefix/opencode/node_modules/opencode-ai/bin/opencode.exe --version` attempted=True, available=True, exit_code=0, error=``
- opencode_help: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/npm-prefix/opencode/node_modules/opencode-ai/bin/opencode.exe --help` attempted=True, available=True, exit_code=0, error=``

- OpenCode real smoke eligible for a later stage; smoke was not run in Stage 39RT.

## OpenClaw

- command_name: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/bin/openclaw`
- command_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/npm-prefix/node_modules/openclaw/openclaw.mjs`
- source_repo_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/openclaw`
- source_repo_present: True
- source_repo_commit: `5bcd25f0fb6de3cc2ba6b6a7688a9361eb355143`
- source_repo_remote: `https://github.com/openclaw/openclaw`
- runtime_present: True
- version_detected: `OpenClaw 2026.6.11 (e085fa1)`
- config_template_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/real_agent_integrations/openclaw_mcp_server/configs/openclaw.capproof.mcp.commands.md`
- capproof_mcp_config_template_exists: True
- capproof_mcp_command_referenced: True
- config_load_supported: True
- mcp_status_available: True
- mcp_doctor_probe_available: True
- mcp_tools_available: True
- real_smoke_eligible: True
- reason: ok
- blocked_runtime_missing: False
- real_agent_process_run: False
- tools_list_observed_from_real_agent: False
- tools_call_observed_from_real_agent: False
- real_integration_claim: False

### Real Runtime Probes

- which_openclaw: `which /home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/bin/openclaw` attempted=True, available=True, exit_code=0, error=``
- openclaw_version_dash: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/npm-prefix/node_modules/openclaw/openclaw.mjs --version` attempted=True, available=True, exit_code=0, error=``
- openclaw_mcp_status: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/npm-prefix/node_modules/openclaw/openclaw.mjs mcp status` attempted=True, available=True, exit_code=0, error=``
- openclaw_mcp_doctor_probe: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/npm-prefix/node_modules/openclaw/openclaw.mjs mcp doctor --probe` attempted=True, available=True, exit_code=0, error=``
- openclaw_mcp_tools: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/npm-prefix/node_modules/openclaw/openclaw.mjs mcp tools --help` attempted=True, available=True, exit_code=0, error=``

- OpenClaw real smoke eligible for a later stage; smoke was not run in Stage 39RT.

## Next Stage Recommendation

- Stage 40O real OpenCode MCP smoke
- Stage 40C real OpenClaw MCP smoke

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
