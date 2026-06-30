# CapProof MCP Server Self-Test Report

## Stage Positioning

- This is Stage 31M product-layer MCP server validation.
- It does not modify Reference Monitor, Capability Store, or Proof Model semantics.
- It does not claim production-level Hermes protection.
- ALLOW uses MockExecutor/no-side-effect local executor only.
- DENY/ASK do not execute executor.
- MCP metadata, tool descriptions, annotations, and LLM output cannot mint capability.

## Summary

- workspace: `/tmp/capproof_mcp_zwxo4loc`
- trace path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/real_agent_integrations/hermes_mcp_server/traces/capproof_mcp_trace.jsonl`
- tools count: 7
- tools: capproof.echo_summary, capproof.send_message_mock, capproof.read_workspace_file, capproof.write_workspace_file, capproof.run_command_template, capproof.get_trace, capproof.request_authorization
- allow verdict: ALLOW
- allow executor called: True
- deny verdict: DENY
- deny reason: NoCap
- deny executor called: False
- shell verdict: DENY
- shell reason: CommandTemplateViolation
- trace entries visible: 3
- unexpected allow count: 0
- executor called on deny count: 0
