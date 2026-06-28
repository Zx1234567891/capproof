# OpenClaw Audit

- Repo status: `repo_missing`
- Repo path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/openclaw`
- Files scanned: 0
- Notes: repo not available; audit requires local checkout

## Required Questions

- Watcher, skill, plugin, shell, file, and network surfaces need interception. Repo is missing, so this is a placeholder based on the Stage 17 mock profile.
- Watcher observations may trigger deny/ask but must not mint authority.
- Skill/plugin metadata can introduce endpoint, shell, or file-write laundering risks.
- Current gaps: legacy payload variants, plugin workflow step schema, hidden endpoint/header fields.
- Compatibility and migration scenarios likely need an independent wrapper.
- Required tests: watcher no-mint, skill endpoint cap, plugin shell denial, legacy unknown surface fail-closed.

## Surfaces

### legacy tool invocation

- Source file: `repo_missing`
- Action kind: `unknown`
- Possible tool: `tool_call`
- Evidence status: `repo_missing`
- Authority-bearing fields: raw_event, metadata, tool_name
- Current profile coverage: `partial`
- Missing fields: raw_event, metadata, tool_name
- Adapter coverage gap: yes
- Likely hook point: compatibility wrapper
- Residual risk: legacy payload may hide tool-specific authority fields
- Recommended adapter update: Add/verify real adapter coverage for raw_event, metadata, tool_name.
- Recommended test case: unknown OpenClaw tool surface is denied until modeled
- Confidence: `low`

### watcher observed action

- Source file: `repo_missing`
- Action kind: `skill_plugin`
- Possible tool: `watcher_event`
- Evidence status: `repo_missing`
- Authority-bearing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Current profile coverage: `partial`
- Missing fields: skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint
- Adapter coverage gap: yes
- Likely hook point: watcher wrapper
- Residual risk: watcher observations must not become authorization roots
- Recommended adapter update: Add/verify real adapter coverage for skill_id, plugin_id, tool_invoked, metadata, workflow_step, external_endpoint.
- Recommended test case: watcher can deny or ask but cannot mint capability
- Confidence: `low`

### skill/plugin external endpoint action

- Source file: `repo_missing`
- Action kind: `network`
- Possible tool: `http_post`
- Evidence status: `repo_missing`
- Authority-bearing fields: url, host, method, headers, body, follow_redirects, mcp_server, tool_name
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: skill/plugin tool wrapper
- Residual risk: metadata-driven endpoint exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: skill http_post unauthorized endpoint denies NoCap
- Confidence: `low`

### skill/plugin shell proposal

- Source file: `repo_missing`
- Action kind: `shell`
- Possible tool: `run_shell`
- Evidence status: `repo_missing`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Missing fields: none
- Adapter coverage gap: no
- Likely hook point: shell wrapper
- Residual risk: plugin workflow can hide shell exfiltration
- Recommended adapter update: No profile contract update required before dry-run; keep audit tests.
- Recommended test case: plugin run_shell sh-c denied
- Confidence: `low`
