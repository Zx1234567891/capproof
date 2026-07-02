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