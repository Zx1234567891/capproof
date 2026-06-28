# Hermes Agent Audit

- Repo status: `repo_missing`
- Repo path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/hermes-agent`
- Files scanned: 0
- Notes: repo not available; audit requires local checkout

## Required Questions

- Tools, skills, MCP, memory, gateway, subagent, terminal backend, and scheduled actions are high-impact surfaces. Repo is missing, so this is a placeholder based on the Stage 17 mock profile.
- Memory has persistent authority laundering risk and must be stripped by default.
- Subagent delegation requires Delegation Certificate evidence and attenuation.
- Gateway recipients map to recipient authority; platform/chat_id semantics need explicit canonicalization.
- MCP calls must map server/tool/url/method/headers/body into endpoint and content authority.
- Terminal backend should be intercepted by a template-only wrapper.
- Current gaps: gateway recipient taxonomy, MCP header/method/follow_redirects, schedule recurrence and replay scope.
- Required tests: MCP field coverage, gateway chat_id, memory persistence, delegation amplification, scheduled replay.

## Surfaces

### tool invocation

- Source file: `repo_missing`
- Action kind: `email_messaging`
- Possible tool: `send_email`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Adapter coverage gap: no
- Likely hook point: tool wrapper
- Residual risk: unauthorized recipient or attachment egress
- Recommended test case: Hermes send_email Alice allow, attacker deny
- Confidence: `low`

### skill action external endpoint

- Source file: `repo_missing`
- Action kind: `network`
- Possible tool: `http_post`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Adapter coverage gap: no
- Likely hook point: skill tool wrapper
- Residual risk: skill metadata exfiltration endpoint
- Recommended test case: Hermes skill http_post unauthorized endpoint deny
- Confidence: `low`

### MCP tool call

- Source file: `repo_missing`
- Action kind: `network`
- Possible tool: `http_post`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `partial`
- Adapter coverage gap: yes
- Likely hook point: MCP proxy
- Residual risk: server/tool metadata can select endpoint or hidden action
- Recommended test case: MCP server/tool/url/method/header field coverage
- Confidence: `low`

### terminal backend shell action

- Source file: `repo_missing`
- Action kind: `shell`
- Possible tool: `run_shell`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Adapter coverage gap: no
- Likely hook point: terminal backend wrapper
- Residual risk: backend may accept arbitrary shell strings
- Recommended test case: terminal sh-c and stdin injection deny
- Confidence: `low`

### memory write

- Source file: `repo_missing`
- Action kind: `memory`
- Possible tool: `memory_write`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `partial`
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering through memory
- Recommended test case: authority_claims stripped and persistence scoped
- Confidence: `low`

### subagent delegation

- Source file: `repo_missing`
- Action kind: `delegation`
- Possible tool: `send_email`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `partial`
- Adapter coverage gap: yes
- Likely hook point: subagent/delegation gateway
- Residual risk: delegation amplification or missing certificate
- Recommended test case: delegation missing and amplification denied
- Confidence: `low`

### gateway messaging action

- Source file: `repo_missing`
- Action kind: `email_messaging`
- Possible tool: `send_message`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `partial`
- Adapter coverage gap: yes
- Likely hook point: gateway proxy
- Residual risk: platform/chat_id recipient ambiguity
- Recommended test case: gateway recipient/chat_id/channel field coverage
- Confidence: `low`

### scheduled automation action

- Source file: `repo_missing`
- Action kind: `scheduled`
- Possible tool: `send_email`
- Authority-bearing fields: schedule_id, action, recipient, endpoint, command, recurrence, task_binding
- Current profile coverage: `partial`
- Adapter coverage gap: yes
- Likely hook point: scheduler wrapper
- Residual risk: stale capability replay or persistent task authority
- Recommended test case: scheduled action bound to schedule_id/task_id/cap scope
- Confidence: `low`
