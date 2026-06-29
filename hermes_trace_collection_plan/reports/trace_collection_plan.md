# Hermes Trace Collection Plan

## Current Status

- No Hermes run.
- No dependency install.
- No third-party command execution.
- No real tool execution.
- No enforcement wrapper.
- No real integration claim.

## Capture Readiness Checklist

- Repo status: available
- Repo path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/external/hermes-agent`
- Trace schema ready: True
- Command validator ready: True
- Safe task templates ready: True
- Replay validator ready: True
- Missing real runtime traces: True

## Hook-specific Required Fields

| Hook | Required fields |
| --- | --- |
| tool_dispatcher_pre_call | tool_name, original_args, effective_args, session_id, task_id, agent_id, source_component |
| terminal_backend_pre_exec | command, cwd, env, stdin, terminal_backend, pre_execution_observed |
| mcp_pre_transport | server, tool_name, arguments, transport.endpoint, headers, pre_execution_observed |
| memory_pre_write | content, origin, persistent, target, authority_claims, pre_execution_observed |
| gateway_pre_send | platform, recipient_or_target_or_channel, body_or_body_ref_or_message, attachments_or_headers_if_present, pre_execution_observed |
| delegation_pre_dispatch | parent_agent, child_agent, goal_or_delegated_scope, cert_ref_if_present, toolsets, pre_execution_observed |
| scheduler_pre_register_or_fire | schedule_id, schedule, action, target_fields, recurrence, pre_execution_observed |
| skill_middleware_rewrite | original_args, effective_args, source_component, middleware_id, pre_execution_observed |

## Command Safety Policy

- Capture-run no-go unless explicitly authorized by env.
- Enforcement wrapper no-go.
- Real Hermes integration claim no-go.
- Current command validation verdict: DENY_CAPTURE_RUN
- Current command validation reason: missing required capture-run environment variables
