# CapProof Harness Audit

- Repo status: `available`
- Repo path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7`
- Files scanned: 170
- Notes: static read-only scan completed

## Required Questions

- Current kill_tests and run_kill_tests.py can be expressed as HarnessAdapter events for send/write/http scenarios.
- Benign and attack modes should continue to share one guard flow.
- Oracles are observable side-effect checks and should not depend on proof language.
- HarnessAdapter does not bypass Reference Monitor; fake proof metadata remains ignored.
- Future AuthLaunderBench inputs should use the HarnessAdapter event schema.

## Surfaces

### kill-test action event

- Source file: `expected_profile_surface`
- Action kind: `unknown`
- Possible tool: `kill_test_action`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: raw_event, metadata, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: HarnessAdapter before guard
- Residual risk: future AuthLaunderBench schema drift
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: attack and benign harness events use same guard flow
- Confidence: `high`

### observable oracle side-effect log

- Source file: `expected_profile_surface`
- Action kind: `unknown`
- Possible tool: `oracle`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: raw_event, metadata, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: task-local oracle
- Residual risk: oracle must not depend on CapProof proof language
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: oracle checks observable unsafe/safe side effects only
- Confidence: `high`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/attack_payload.txt`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/benign_environment.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/benign_expected_authspec.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/benign_expected_capabilities.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k10_argument_endpoint_lookalike/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/benign_expected_safe_behavior.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/benign_oracle.py`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/benign_user_request.txt`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/expected_capabilities.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k10_argument_endpoint_lookalike/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/oracle.py`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_write

- Source file: `kill_tests/k10_argument_endpoint_lookalike/tool_catalog.json`
- Action kind: `file_write`
- Possible tool: `write_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: path traversal, symlink escape, config/policy/credential writes
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness file_write profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_read

- Source file: `kill_tests/k10_argument_endpoint_lookalike/tool_catalog.json`
- Action kind: `file_read`
- Possible tool: `read_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, symlink_policy, workspace_root
- Current profile coverage: `unknown`
- Missing fields: path, symlink_policy, workspace_root
- Adapter coverage gap: yes
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: secret file read, traversal, symlink escape
- Recommended adapter update: Add/verify real adapter coverage for path, symlink_policy, workspace_root.
- Recommended test case: harness file_read profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/tool_catalog.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k10_argument_endpoint_lookalike/user_request.txt`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k11_memory_persistent_endorsement/attack_payload.txt`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k11_memory_persistent_endorsement/benign_environment.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k11_memory_persistent_endorsement/benign_environment.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k11_memory_persistent_endorsement/benign_expected_authspec.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k11_memory_persistent_endorsement/benign_expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k11_memory_persistent_endorsement/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k11_memory_persistent_endorsement/benign_expected_safe_behavior.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k11_memory_persistent_endorsement/benign_oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k11_memory_persistent_endorsement/benign_user_request.txt`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k11_memory_persistent_endorsement/expected_authspec.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k11_memory_persistent_endorsement/expected_failure_reason.txt`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k11_memory_persistent_endorsement/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k11_memory_persistent_endorsement/expected_safe_behavior.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k11_memory_persistent_endorsement/oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k11_memory_persistent_endorsement/oracle.py`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k11_memory_persistent_endorsement/tool_catalog.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k11_memory_persistent_endorsement/tool_catalog.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k11_memory_persistent_endorsement/user_request.txt`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: unknown

- Source file: `kill_tests/k12_delegated_prior_endorsement/attack_payload.txt`
- Action kind: `unknown`
- Possible tool: `unknown`
- Evidence status: `observed in source`
- Authority-bearing fields: raw_event, metadata, tool_name
- Current profile coverage: `no`
- Missing fields: raw_event, metadata, tool_name
- Adapter coverage gap: yes
- Likely hook point: harness adapter coverage audit
- Residual risk: unmodeled authority-bearing fields may be missed
- Recommended adapter update: Add/verify real adapter coverage for raw_event, metadata, tool_name.
- Recommended test case: harness unknown profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_environment.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_environment.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_expected_authspec.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_expected_capabilities.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_expected_safe_behavior.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_user_request.txt`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k12_delegated_prior_endorsement/benign_user_request.txt`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k12_delegated_prior_endorsement/expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k12_delegated_prior_endorsement/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k12_delegated_prior_endorsement/oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k12_delegated_prior_endorsement/tool_catalog.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/attack_payload.txt`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k1_memory_recipient/attack_payload.txt`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/benign_environment.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k1_memory_recipient/benign_environment.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/benign_expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k1_memory_recipient/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/benign_expected_safe_behavior.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/benign_oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k1_memory_recipient/benign_user_request.txt`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/expected_authspec.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k1_memory_recipient/expected_authspec.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k1_memory_recipient/expected_failure_reason.txt`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k1_memory_recipient/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k1_memory_recipient/expected_safe_behavior.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_read

- Source file: `kill_tests/k1_memory_recipient/tool_catalog.json`
- Action kind: `file_read`
- Possible tool: `read_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, symlink_policy, workspace_root
- Current profile coverage: `unknown`
- Missing fields: path, symlink_policy, workspace_root
- Adapter coverage gap: yes
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: secret file read, traversal, symlink escape
- Recommended adapter update: Add/verify real adapter coverage for path, symlink_policy, workspace_root.
- Recommended test case: harness file_read profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/tool_catalog.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k1_memory_recipient/user_request.txt`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k2_memory_export_path/attack_payload.txt`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k2_memory_export_path/benign_environment.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k2_memory_export_path/benign_expected_capabilities.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k2_memory_export_path/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k2_memory_export_path/benign_user_request.txt`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_write

- Source file: `kill_tests/k2_memory_export_path/expected_authspec.json`
- Action kind: `file_write`
- Possible tool: `write_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: path traversal, symlink escape, config/policy/credential writes
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness file_write profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k2_memory_export_path/expected_authspec.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k2_memory_export_path/expected_failure_reason.txt`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k2_memory_export_path/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `kill_tests/k2_memory_export_path/expected_safe_behavior.json`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_write

- Source file: `kill_tests/k2_memory_export_path/tool_catalog.json`
- Action kind: `file_write`
- Possible tool: `write_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: path traversal, symlink escape, config/policy/credential writes
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness file_write profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k3_delegation_relay/benign_environment.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k3_delegation_relay/benign_environment.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k3_delegation_relay/benign_expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k3_delegation_relay/benign_expected_capabilities.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k3_delegation_relay/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k3_delegation_relay/benign_expected_safe_behavior.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k3_delegation_relay/benign_oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k3_delegation_relay/benign_user_request.txt`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k3_delegation_relay/benign_user_request.txt`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k3_delegation_relay/expected_authspec.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k3_delegation_relay/expected_authspec.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k3_delegation_relay/expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k3_delegation_relay/expected_failure_reason.txt`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k3_delegation_relay/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k3_delegation_relay/expected_safe_behavior.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k3_delegation_relay/oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_write

- Source file: `kill_tests/k3_delegation_relay/tool_catalog.json`
- Action kind: `file_write`
- Possible tool: `write_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: path traversal, symlink escape, config/policy/credential writes
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness file_write profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_read

- Source file: `kill_tests/k3_delegation_relay/tool_catalog.json`
- Action kind: `file_read`
- Possible tool: `read_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, symlink_policy, workspace_root
- Current profile coverage: `unknown`
- Missing fields: path, symlink_policy, workspace_root
- Adapter coverage gap: yes
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: secret file read, traversal, symlink escape
- Recommended adapter update: Add/verify real adapter coverage for path, symlink_policy, workspace_root.
- Recommended test case: harness file_read profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k3_delegation_relay/tool_catalog.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/attack_payload.txt`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k4_delegation_amplification/attack_payload.txt`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/benign_environment.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k4_delegation_amplification/benign_environment.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/benign_expected_authspec.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/benign_expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k4_delegation_amplification/benign_expected_capabilities.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k4_delegation_amplification/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/benign_expected_safe_behavior.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/benign_oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/benign_user_request.txt`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k4_delegation_amplification/benign_user_request.txt`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/expected_authspec.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k4_delegation_amplification/expected_authspec.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k4_delegation_amplification/expected_failure_reason.txt`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k4_delegation_amplification/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `kill_tests/k4_delegation_amplification/expected_safe_behavior.json`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k4_delegation_amplification/tool_catalog.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: unknown

- Source file: `kill_tests/k5_endorsement_replay/attack_payload.txt`
- Action kind: `unknown`
- Possible tool: `unknown`
- Evidence status: `observed in source`
- Authority-bearing fields: raw_event, metadata, tool_name
- Current profile coverage: `no`
- Missing fields: raw_event, metadata, tool_name
- Adapter coverage gap: yes
- Likely hook point: harness adapter coverage audit
- Residual risk: unmodeled authority-bearing fields may be missed
- Recommended adapter update: Add/verify real adapter coverage for raw_event, metadata, tool_name.
- Recommended test case: harness unknown profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k5_endorsement_replay/benign_environment.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k5_endorsement_replay/benign_expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k5_endorsement_replay/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k5_endorsement_replay/benign_expected_safe_behavior.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k5_endorsement_replay/benign_oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: unknown

- Source file: `kill_tests/k5_endorsement_replay/expected_authspec.json`
- Action kind: `unknown`
- Possible tool: `unknown`
- Evidence status: `observed in source`
- Authority-bearing fields: raw_event, metadata, tool_name
- Current profile coverage: `no`
- Missing fields: raw_event, metadata, tool_name
- Adapter coverage gap: yes
- Likely hook point: harness adapter coverage audit
- Residual risk: unmodeled authority-bearing fields may be missed
- Recommended adapter update: Add/verify real adapter coverage for raw_event, metadata, tool_name.
- Recommended test case: harness unknown profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k5_endorsement_replay/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k5_endorsement_replay/oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k5_endorsement_replay/tool_catalog.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k6_endorsement_raw_widening/benign_environment.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k6_endorsement_raw_widening/benign_expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k6_endorsement_raw_widening/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k6_endorsement_raw_widening/benign_expected_safe_behavior.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k6_endorsement_raw_widening/benign_oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k6_endorsement_raw_widening/expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k6_endorsement_raw_widening/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k6_endorsement_raw_widening/oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k6_endorsement_raw_widening/tool_catalog.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/attack_payload.txt`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k7_mcp_metadata_endpoint/attack_payload.txt`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/benign_environment.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k7_mcp_metadata_endpoint/benign_environment.json`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/benign_expected_authspec.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k7_mcp_metadata_endpoint/benign_expected_authspec.json`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/benign_expected_capabilities.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k7_mcp_metadata_endpoint/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/benign_user_request.txt`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/expected_authspec.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k7_mcp_metadata_endpoint/expected_authspec.json`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/expected_capabilities.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k7_mcp_metadata_endpoint/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/oracle.py`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_write

- Source file: `kill_tests/k7_mcp_metadata_endpoint/tool_catalog.json`
- Action kind: `file_write`
- Possible tool: `write_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: path traversal, symlink escape, config/policy/credential writes
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness file_write profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_read

- Source file: `kill_tests/k7_mcp_metadata_endpoint/tool_catalog.json`
- Action kind: `file_read`
- Possible tool: `read_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, symlink_policy, workspace_root
- Current profile coverage: `unknown`
- Missing fields: path, symlink_policy, workspace_root
- Adapter coverage gap: yes
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: secret file read, traversal, symlink escape
- Recommended adapter update: Add/verify real adapter coverage for path, symlink_policy, workspace_root.
- Recommended test case: harness file_read profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/tool_catalog.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k7_mcp_metadata_endpoint/user_request.txt`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k8_skill_metadata_upload/attack_payload.txt`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k8_skill_metadata_upload/attack_payload.txt`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k8_skill_metadata_upload/benign_environment.json`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k8_skill_metadata_upload/benign_expected_authspec.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k8_skill_metadata_upload/benign_expected_authspec.json`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k8_skill_metadata_upload/benign_expected_capabilities.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k8_skill_metadata_upload/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k8_skill_metadata_upload/benign_user_request.txt`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k8_skill_metadata_upload/expected_authspec.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k8_skill_metadata_upload/expected_authspec.json`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k8_skill_metadata_upload/expected_capabilities.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k8_skill_metadata_upload/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k8_skill_metadata_upload/oracle.py`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k8_skill_metadata_upload/tool_catalog.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_read

- Source file: `kill_tests/k8_skill_metadata_upload/tool_catalog.json`
- Action kind: `file_read`
- Possible tool: `read_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, symlink_policy, workspace_root
- Current profile coverage: `unknown`
- Missing fields: path, symlink_policy, workspace_root
- Adapter coverage gap: yes
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: secret file read, traversal, symlink escape
- Recommended adapter update: Add/verify real adapter coverage for path, symlink_policy, workspace_root.
- Recommended test case: harness file_read profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `kill_tests/k8_skill_metadata_upload/tool_catalog.json`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `kill_tests/k8_skill_metadata_upload/user_request.txt`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/benign_environment.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/benign_expected_authspec.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/benign_expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k9_argument_bcc/benign_expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/benign_expected_safe_behavior.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/benign_oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/benign_user_request.txt`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/expected_authspec.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/expected_capabilities.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `kill_tests/k9_argument_bcc/expected_safe_behavior.json`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/oracle.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_read

- Source file: `kill_tests/k9_argument_bcc/tool_catalog.json`
- Action kind: `file_read`
- Possible tool: `read_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, symlink_policy, workspace_root
- Current profile coverage: `unknown`
- Missing fields: path, symlink_policy, workspace_root
- Adapter coverage gap: yes
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: secret file read, traversal, symlink escape
- Recommended adapter update: Add/verify real adapter coverage for path, symlink_policy, workspace_root.
- Recommended test case: harness file_read profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/tool_catalog.json`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `kill_tests/k9_argument_bcc/user_request.txt`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `run_kill_tests.py`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_write

- Source file: `run_kill_tests.py`
- Action kind: `file_write`
- Possible tool: `write_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: path traversal, symlink escape, config/policy/credential writes
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness file_write profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_read

- Source file: `run_kill_tests.py`
- Action kind: `file_read`
- Possible tool: `read_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, symlink_policy, workspace_root
- Current profile coverage: `unknown`
- Missing fields: path, symlink_policy, workspace_root
- Adapter coverage gap: yes
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: secret file read, traversal, symlink escape
- Recommended adapter update: Add/verify real adapter coverage for path, symlink_policy, workspace_root.
- Recommended test case: harness file_read profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `run_kill_tests.py`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `run_kill_tests.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `run_kill_tests.py`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `run_kill_tests.py`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `run_kill_tests.py`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: scheduled

- Source file: `run_kill_tests.py`
- Action kind: `scheduled`
- Possible tool: `scheduled_action`
- Evidence status: `observed in source`
- Authority-bearing fields: schedule_id, action, recipient, endpoint, command, recurrence, task_binding
- Current profile coverage: `unknown`
- Missing fields: schedule_id, action, recipient, endpoint, command, recurrence, task_binding
- Adapter coverage gap: yes
- Likely hook point: scheduler wrapper
- Residual risk: stale capability replay and persistent scheduled exfiltration
- Recommended adapter update: Add/verify real adapter coverage for schedule_id, action, recipient, endpoint, command, recurrence, task_binding.
- Recommended test case: harness scheduled profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: tool_invocation

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `tool_invocation`
- Possible tool: `handle_function_call`
- Evidence status: `observed in source`
- Authority-bearing fields: function_name, function_args, task_id, session_id, tool_call_id, enabled_toolsets, middleware_trace
- Current profile coverage: `unknown`
- Missing fields: function_name, function_args, task_id, session_id, tool_call_id, enabled_toolsets, middleware_trace
- Adapter coverage gap: yes
- Likely hook point: tool-call dispatcher / middleware boundary
- Residual risk: tool-name bridge, middleware rewrite, or dynamic dispatch can hide authority-bearing args
- Recommended adapter update: Add/verify real adapter coverage for function_name, function_args, task_id, session_id, tool_call_id, enabled_toolsets, middleware_trace.
- Recommended test case: harness tool_invocation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: shell

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal/shell wrapper
- Residual risk: arbitrary shell string, sh-c, pipes, redirects, env/cwd/stdin injection
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness shell profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_write

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `file_write`
- Possible tool: `write_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: path traversal, symlink escape, config/policy/credential writes
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness file_write profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: file_read

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `file_read`
- Possible tool: `read_file`
- Evidence status: `observed in source`
- Authority-bearing fields: path, symlink_policy, workspace_root
- Current profile coverage: `unknown`
- Missing fields: path, symlink_policy, workspace_root
- Adapter coverage gap: yes
- Likely hook point: filesystem hook / tool wrapper
- Residual risk: secret file read, traversal, symlink escape
- Recommended adapter update: Add/verify real adapter coverage for path, symlink_policy, workspace_root.
- Recommended test case: harness file_read profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: network

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: unauthorized endpoint, redirect, punycode/encoded host, metadata-driven endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness network profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: email_messaging

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `email_messaging`
- Possible tool: `send_email/send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: gateway/email tool wrapper
- Residual risk: unauthorized recipient, hidden route, gateway exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: harness email_messaging profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: memory

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `unknown`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering and policy memory poisoning
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: harness memory profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: skill_plugin

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `skill_plugin`
- Possible tool: `skill_action`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `unknown`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: tool wrapper / MCP proxy
- Residual risk: workflow laundering and plugin metadata authority injection
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: harness skill_plugin profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: delegation

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `delegation`
- Possible tool: `delegation`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `unknown`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent delegation gateway
- Residual risk: delegation amplification and cross-agent replay
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: harness delegation profile adapter field coverage and fail-closed test
- Confidence: `low`

### static keyword surface: scheduled

- Source file: `tests/test_agent_profile_adapters.py`
- Action kind: `scheduled`
- Possible tool: `scheduled_action`
- Evidence status: `observed in source`
- Authority-bearing fields: schedule_id, action, recipient, endpoint, command, recurrence, task_binding
- Current profile coverage: `unknown`
- Missing fields: schedule_id, action, recipient, endpoint, command, recurrence, task_binding
- Adapter coverage gap: yes
- Likely hook point: scheduler wrapper
- Residual risk: stale capability replay and persistent scheduled exfiltration
- Recommended adapter update: Add/verify real adapter coverage for schedule_id, action, recipient, endpoint, command, recurrence, task_binding.
- Recommended test case: harness scheduled profile adapter field coverage and fail-closed test
- Confidence: `low`

### 12 kill tasks with benign/attack counterparts

- Source file: `kill_tests/`
- Action kind: `unknown`
- Possible tool: `HarnessAdapter`
- Evidence status: `unknown`
- Authority-bearing fields: raw_event, metadata, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: run_kill_tests.py action construction
- Residual risk: future tasks may introduce new tool surfaces
- Recommended adapter update: Use HarnessAdapter event schema for future AuthLaunderBench inputs
- Recommended test case: all kill_tests can be emitted as HarnessAdapter events
- Confidence: `high`
