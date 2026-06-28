# Hermes Agent Audit

- Repo status: `available`
- Repo path: `external/external/hermes-agent`
- Files scanned: 2500
- Notes: static read-only scan completed

## Required Questions

- Tools, skills, MCP, memory, gateway, subagent, terminal backend, and scheduled actions are high-impact surfaces.
- Local Stage 19 rows distinguish `observed in source`, `inferred from naming/docs`, `not found`, and `unknown`; inferred rows are not treated as confirmed execution paths.
- Observed tool dispatch flows through `model_tools.handle_function_call`, `agent/tool_executor.py`, and `tools/registry.py`; middleware can rewrite effective args before dispatch.
- Observed real tool names include `terminal`, `send_message`, `memory`, `delegate_task`, `cronjob`, file tools, dynamic `mcp_*` tools, and MCP-server `messages_send`; these do not all match the Stage 17 synthetic Hermes event profile.
- Memory has persistent authority laundering risk and must be stripped by default.
- Subagent delegation requires Delegation Certificate evidence and attenuation.
- Gateway recipients map to recipient authority; platform/chat_id semantics need explicit canonicalization.
- MCP calls must map server/tool/url/method/headers/body into endpoint and content authority.
- Terminal backend should be intercepted by a template-only wrapper.
- Current gaps: real `terminal` command mapping, `send_message.target` parsing, provider memory tools, dynamic MCP schemas, cron persistence/schedule scope, and `delegate_task` certificate fields.
- Required tests: real Hermes terminal shape fail-closed, MCP field coverage, gateway target parsing, memory persistence stripping, delegation certificate denial, cron schedule binding.

## Surfaces

## Stage 19 Local Static Coverage Summary

- This is a Hermes local static coverage audit, not a real Hermes integration.
- Hermes was not run; dependencies were not installed; no third-party commands, real tools, network calls, email, or shell actions were executed.
- Actual local checkout used: `external/external/hermes-agent`.
- The requested path is normally `external/hermes-agent`; pass `--hermes-repo <path>` to point at another local checkout.
- Observed-source rows are confirmed by static source reads; inferred rows are not treated as confirmed execution paths.
- HermesAgentLikeAdapter observed-source full coverage: 0; partial coverage: 8; uncovered: 3.
- CapProof cannot claim it protects real Hermes or that coverage is complete from this audit.
- Current findings are adapter coverage gaps and integration risks, not runtime vulnerability proofs.
- Do not enter a real Hermes dry-run wrapper claim until terminal, send_message, dynamic MCP, memory, delegate_task, and cronjob real shapes are modeled and tested.

### tool invocation

- Source file: `expected_profile_surface`
- Action kind: `email_messaging`
- Possible tool: `send_email`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: tool wrapper
- Residual risk: unauthorized recipient or attachment egress
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: Hermes send_email Alice allow, attacker deny
- Confidence: `medium`

### skill action external endpoint

- Source file: `expected_profile_surface`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: skill tool wrapper
- Residual risk: skill metadata exfiltration endpoint
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: Hermes skill http_post unauthorized endpoint deny
- Confidence: `medium`

### MCP tool call

- Source file: `expected_profile_surface`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `partial`
- Missing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Adapter coverage gap: yes
- Likely hook point: MCP proxy
- Residual risk: server/tool metadata can select endpoint or hidden action
- Recommended adapter update: Add/verify real adapter coverage for url, host, method, headers, body, follow_redirects, mcp_server, tool_name.
- Recommended test case: MCP server/tool/url/method/header field coverage
- Confidence: `medium`

### terminal backend shell action

- Source file: `expected_profile_surface`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: terminal backend wrapper
- Residual risk: backend may accept arbitrary shell strings
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: terminal sh-c and stdin injection deny
- Confidence: `medium`

### memory write

- Source file: `expected_profile_surface`
- Action kind: `memory`
- Possible tool: `memory_write`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `partial`
- Missing fields: content, origin, persistence, authority_claims, scope
- Adapter coverage gap: yes
- Likely hook point: memory backend wrapper
- Residual risk: persistent authority laundering through memory
- Recommended adapter update: Add/verify real adapter coverage for content, origin, persistence, authority_claims, scope.
- Recommended test case: authority_claims stripped and persistence scoped
- Confidence: `medium`

### subagent delegation

- Source file: `expected_profile_surface`
- Action kind: `delegation`
- Possible tool: `send_email`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `partial`
- Missing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Adapter coverage gap: yes
- Likely hook point: subagent/delegation gateway
- Residual risk: delegation amplification or missing certificate
- Recommended adapter update: Add/verify real adapter coverage for parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag.
- Recommended test case: delegation missing and amplification denied
- Confidence: `medium`

### gateway messaging action

- Source file: `expected_profile_surface`
- Action kind: `email_messaging`
- Possible tool: `send_message`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `partial`
- Missing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Adapter coverage gap: yes
- Likely hook point: gateway proxy
- Residual risk: platform/chat_id recipient ambiguity
- Recommended adapter update: Add/verify real adapter coverage for recipient, channel, platform, chat_id, body, attachment, headers.
- Recommended test case: gateway recipient/chat_id/channel field coverage
- Confidence: `medium`

### scheduled automation action

- Source file: `expected_profile_surface`
- Action kind: `scheduled`
- Possible tool: `send_email`
- Evidence status: `inferred from Stage 17 mock profile`
- Authority-bearing fields: schedule_id, action, recipient, endpoint, command, recurrence, task_binding
- Current profile coverage: `partial`
- Missing fields: schedule_id, action, recipient, endpoint, command, recurrence, task_binding
- Adapter coverage gap: yes
- Likely hook point: scheduler wrapper
- Residual risk: stale capability replay or persistent task authority
- Recommended adapter update: Add/verify real adapter coverage for schedule_id, action, recipient, endpoint, command, recurrence, task_binding.
- Recommended test case: scheduled action bound to schedule_id/task_id/cap scope
- Confidence: `medium`

### model tool-call dispatcher and middleware boundary

- Source file: `model_tools.py, agent/tool_executor.py, docs/middleware/README.md`
- Action kind: `tool_invocation`
- Possible tool: `handle_function_call`
- Evidence status: `observed in source`
- Authority-bearing fields: function_name, function_args, task_id, session_id, tool_call_id, enabled_toolsets, middleware_trace
- Current profile coverage: `partial`
- Missing fields: original_args, effective_args, enabled_toolsets, session_id, turn_id, api_request_id
- Adapter coverage gap: yes
- Likely hook point: tool_request middleware or pre-dispatch wrapper before registry.dispatch
- Residual risk: middleware can rewrite authority-bearing args before execution; bridge tools can unwrap to real tools
- Recommended adapter update: Add a Hermes real-tool-call event shape carrying original/effective args, tool_call_id, session_id, turn_id, and enabled_toolsets.
- Recommended test case: Hermes observed tool invocation shape is parsed into canonical tool-specific action or fails closed.
- Confidence: `high`

### core file read/write/patch tools

- Source file: `tools/file_tools.py, agent/tool_dispatch_helpers.py`
- Action kind: `file_write`
- Possible tool: `read_file/write_file/patch`
- Evidence status: `observed in source`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `partial`
- Missing fields: patch, old_string, new_string, replace_all, cross_profile, resolved_path, session_id
- Adapter coverage gap: yes
- Likely hook point: file tool wrapper before file_tools handlers
- Residual risk: patch mode, cross_profile, staleness state, and resolved_path need explicit adapter coverage
- Recommended adapter update: Map real Hermes read_file/write_file/patch schemas into separate CapProof contracts or deny patch until modeled.
- Recommended test case: Real Hermes write_file path/content and patch path headers are represented or denied fail-closed.
- Confidence: `high`

### terminal tool shell command

- Source file: `tools/terminal_tool.py, tools/process_registry.py, tools/environments/base.py, tools/environments/docker.py`
- Action kind: `shell`
- Possible tool: `terminal`
- Evidence status: `observed in source`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `no`
- Missing fields: terminal tool name mapping, command, background, timeout, workdir, pty, notify_on_complete, watch_patterns
- Adapter coverage gap: yes
- Likely hook point: terminal tool wrapper before terminal_tool(command=...)
- Residual risk: real Hermes uses tool name terminal with raw command string, background, workdir, pty, notification, and process controls
- Recommended adapter update: Add a dry-run-only Hermes terminal adapter that maps terminal.command to an allowlisted run_shell template or denies arbitrary commands.
- Recommended test case: Real Hermes terminal command shape fails closed until template mapping exists.
- Confidence: `high`

### cross-channel send_message gateway tool

- Source file: `tools/send_message_tool.py, gateway/stream_events.py, gateway/platforms/ADDING_A_PLATFORM.md, gateway/platforms/__init__.py, gateway/platforms/_http_client_limits.py`
- Action kind: `email_messaging`
- Possible tool: `send_message`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `partial`
- Missing fields: target, action, message, emoji, message_id, media local_path, thread_id
- Adapter coverage gap: yes
- Likely hook point: send_message tool wrapper / gateway proxy
- Residual risk: real Hermes target encodes platform, chat_id, thread_id, media attachments, and reaction message_id in one string
- Recommended adapter update: Canonicalize target into platform/channel/chat_id/thread_id recipient fields and map message to body/content.
- Recommended test case: Real Hermes send_message target/message shape is denied or mapped to recipient authority.
- Confidence: `high`

### external MCP client dynamic tools

- Source file: `tools/mcp_tool.py, optional-mcps/linear/manifest.yaml, optional-mcps/n8n/manifest.yaml, optional-mcps/unreal-engine/manifest.yaml, docs/design/profile-builder.md`
- Action kind: `network`
- Possible tool: `mcp_*`
- Evidence status: `observed in source`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `partial`
- Missing fields: server_name, tool_name, inputSchema, arguments, transport.command, transport.url, headers, resources/prompts
- Adapter coverage gap: yes
- Likely hook point: MCP proxy before dynamic registry.register handler dispatch
- Residual risk: MCP server/tool metadata can define arbitrary inputSchema, transport command/url, resources, prompts, and mutating tools
- Recommended adapter update: Add MCP-specific adapter rows for server name, prefixed tool name, transport endpoint/command, and raw arguments.
- Recommended test case: Real Hermes mcp_* tool event preserves server/tool/arguments and unauthorized endpoint denies.
- Confidence: `high`

### Hermes messaging MCP server tools

- Source file: `mcp_serve.py`
- Action kind: `email_messaging`
- Possible tool: `messages_send`
- Evidence status: `observed in source`
- Authority-bearing fields: recipient, channel, platform, chat_id, body, attachment, headers
- Current profile coverage: `no`
- Missing fields: session_key, target, message, permission id, decision
- Adapter coverage gap: yes
- Likely hook point: MCP server tool wrapper before messages_send dispatch
- Residual risk: external MCP clients can drive Hermes message send and approval response surfaces
- Recommended adapter update: Model Hermes MCP server tools separately from Hermes internal MCP client tools.
- Recommended test case: messages_send target/message requires recipient capability; permissions_respond requires endorsement/control capability.
- Confidence: `high`

### built-in memory tool

- Source file: `tools/memory_tool.py, agent/memory_manager.py, agent/memory_provider.py`
- Action kind: `memory`
- Possible tool: `memory`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `partial`
- Missing fields: action, target, old_text, operations, provider metadata, session_id
- Adapter coverage gap: yes
- Likely hook point: memory tool wrapper before memory_tool and provider mirror
- Residual risk: persistent user/profile memories can encode future authority claims unless stripped
- Recommended adapter update: Map real memory(action,target,content,operations) to memory_write with origin/persistence/scope and authority stripping.
- Recommended test case: Real Hermes memory add with authority-like content is stripped or denied fail-closed.
- Confidence: `high`

### external memory provider tools

- Source file: `plugins/memory/retaindb/__init__.py, plugins/memory/supermemory/__init__.py, plugins/memory/openviking/__init__.py`
- Action kind: `memory`
- Possible tool: `retaindb_remember/supermemory_store/openviking_remember`
- Evidence status: `observed in source`
- Authority-bearing fields: content, origin, persistence, authority_claims, scope
- Current profile coverage: `no`
- Missing fields: provider tool name, memory_type/category, importance, metadata, remote container, scope
- Adapter coverage gap: yes
- Likely hook point: provider handle_tool_call wrapper
- Residual risk: provider-specific persistent memory tools can store preferences/instructions outside the built-in memory tool path
- Recommended adapter update: Route provider memory tool calls through the same Memory Authority Stripping contract.
- Recommended test case: Provider-specific memory save event cannot mint recipient or policy authority.
- Confidence: `high`

### delegate_task subagent tool

- Source file: `tools/delegate_tool.py, tools/async_delegation.py, docs/observability/README.md`
- Action kind: `delegation`
- Possible tool: `delegate_task`
- Evidence status: `observed in source`
- Authority-bearing fields: parent_agent, child_agent, delegated_scope, requested_action, task_id, redelegation_flag
- Current profile coverage: `partial`
- Missing fields: goal, context, toolsets, tasks, role, acp_command, acp_args, parent_agent_id, child_task_id
- Adapter coverage gap: yes
- Likely hook point: delegate_task wrapper before child agent spawn
- Residual risk: child toolsets, model/provider/base_url, ACP command, role, and context can amplify or relay authority
- Recommended adapter update: Map delegate_task to Delegation Certificate inputs and deny child scope not attenuated by parent caps.
- Recommended test case: Real delegate_task shape without Delegation Certificate denies DelegationMissing.
- Confidence: `high`

### skills and plugin managed workflows

- Source file: `tools/skill_manager_tool.py, tools/skills_tool.py, agent/skill_preprocessing.py, skills/autonomous-ai-agents/hermes-agent/SKILL.md, skills/computer-use/SKILL.md`
- Action kind: `skill_plugin`
- Possible tool: `skill_manage/skills/*/plugins/*`
- Evidence status: `observed in source`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `partial`
- Missing fields: skill_id, plugin_id, workflow_step, blueprint, middleware payload, declared endpoint
- Adapter coverage gap: yes
- Likely hook point: skill manager / plugin middleware wrapper
- Residual risk: skill metadata, blueprints, plugin hooks, and middleware can rewrite tool args or propose scheduled/MCP actions
- Recommended adapter update: Treat skill/plugin metadata as non-authority and require downstream tool-specific CapProof checks after middleware rewrites.
- Recommended test case: Skill/plugin metadata cannot mint endpoint, recipient, command, or file capability.
- Confidence: `medium`

### cronjob scheduled automation tool

- Source file: `tools/cronjob_tools.py, cron/jobs.py, cron/scheduler.py, cron/suggestions.py, docs/chronos-managed-cron-contract.md`
- Action kind: `scheduled`
- Possible tool: `cronjob`
- Evidence status: `observed in source`
- Authority-bearing fields: schedule_id, action, recipient, endpoint, command, recurrence, task_binding
- Current profile coverage: `partial`
- Missing fields: action, job_id, prompt, schedule, deliver, script, enabled_toolsets, workdir, no_agent, context_from
- Adapter coverage gap: yes
- Likely hook point: cronjob tool wrapper before job create/update/fire
- Residual risk: scheduled prompt/script/deliver/workdir/toolsets can preserve authority beyond one task and replay stale caps
- Recommended adapter update: Bind scheduled capabilities to schedule_id/task scope and model script/workdir/deliver as high-impact fields.
- Recommended test case: Real cronjob create/update shape without schedule-bound caps denies or asks.
- Confidence: `high`

### optional MCP catalog transport endpoints

- Source file: `optional-mcps/linear/manifest.yaml, optional-mcps/n8n/manifest.yaml, optional-mcps/unreal-engine/manifest.yaml`
- Action kind: `network`
- Possible tool: `optional-mcps/*/manifest.yaml`
- Evidence status: `inferred from naming/docs`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `partial`
- Missing fields: manifest transport.url, manifest transport.command, tools.default_enabled
- Adapter coverage gap: yes
- Likely hook point: catalog/skill installer plus downstream tool wrapper
- Residual risk: catalog metadata can introduce remote endpoint or local command transport during MCP install/configuration
- Recommended adapter update: Keep metadata non-authoritative; require downstream canonical tool call proof for any proposed action.
- Recommended test case: MCP catalog manifest fields are treated as non-authority until user confirms endpoint/command.
- Confidence: `medium`

### skill docs with messaging/file/shell instructions

- Source file: `skills/apple/apple-notes/SKILL.md, skills/apple/apple-reminders/SKILL.md, skills/apple/findmy/SKILL.md, skills/apple/imessage/SKILL.md, skills/autonomous-ai-agents/claude-code/SKILL.md`
- Action kind: `skill_plugin`
- Possible tool: `skills/*/SKILL.md`
- Evidence status: `inferred from naming/docs`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `partial`
- Missing fields: skill path, workflow step, tool mention, endpoint mention
- Adapter coverage gap: yes
- Likely hook point: catalog/skill installer plus downstream tool wrapper
- Residual risk: skill instructions can launder endpoints, paths, commands, or recipients if treated as authority
- Recommended adapter update: Keep metadata non-authoritative; require downstream canonical tool call proof for any proposed action.
- Recommended test case: Skill instructions never mint capability without explicit user AuthSpec or endorsement.
- Confidence: `medium`
