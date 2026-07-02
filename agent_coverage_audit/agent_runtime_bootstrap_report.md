# Agent Runtime Bootstrap Report

## Stage Positioning

- Stage 40RB bootstraps local OpenCode/OpenClaw CLI runtimes only.
- It does not run OpenCode/OpenClaw MCP smoke.
- It does not claim OpenCode/OpenClaw real integration.
- Dry-run/preflight is not completion evidence under Stage 38REAL.

## Summary

- status: passed
- runtime_bootstrap_passed: True
- real_environment_policy_active: True
- bootstrap_gate_present: True
- network_gate_present: True
- install_prefix: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes`
- integration_claim_made: False
- api_key_written: False

## OpenCode

- source_repo_present: True
- source_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/opencode`
- source_commit: `f52424e05fab0edddb4462112ceb02044085f903`
- bootstrap_attempted: True
- bootstrap_mode: none
- runtime_present: True
- binary_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/bin/opencode`
- version_detected: `1.17.13`
- real_smoke_eligible: True
- reason: ok

## OpenClaw

- source_repo_present: True
- source_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/openclaw`
- source_commit: `5bcd25f0fb6de3cc2ba6b6a7688a9361eb355143`
- bootstrap_attempted: True
- bootstrap_mode: none
- runtime_present: True
- binary_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/.agent-runtimes/bin/openclaw`
- version_detected: `OpenClaw 2026.6.11 (e085fa1)`
- real_smoke_eligible: True
- reason: ok
- node_version: `v24.12.0`
- package_manager: `npm`
- mcp_cli_help_available: True
- mcp_status_available: True
- mcp_doctor_help_available: True
- mcp_tools_help_available: True

## Non-Claims

- No OpenCode/OpenClaw real integration claim.
- No OpenCode/OpenClaw MCP smoke passed claim.
- No production-level protection claim.
- No system install, sudo, onboarding, daemon, gateway, real message, or external MCP.
