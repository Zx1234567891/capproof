# OpenCode Audit

- Repo status: `repo_missing`
- Repo path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/opencode`
- Files scanned: 0
- Notes: repo not available; audit requires local checkout

## Required Questions

- Shell, file write/edit, and config/policy write surfaces are high-impact. Repo is missing, so this is a placeholder based on the Stage 17 mock profile.
- CLI wrapper, terminal wrapper, filesystem hook, MCP proxy, and tool-use event streams are candidate hook points.
- AGENTS.md / config modifications can change future agent behavior and should be high-impact writes.
- Plan mode should produce proposed actions only; build mode may enter guard.
- Current gaps: real diff/patch metadata, symlink policy, config taxonomy, and exact plan/build event semantics.
- Required tests: raw shell denial, config write cap, path traversal/symlink, diff/patch field coverage.

## Surfaces

### terminal shell command proposal

- Source file: `repo_missing`
- Action kind: `shell`
- Possible tool: `run_shell`
- Authority-bearing fields: command, args, cwd, env, stdin, terminal_backend
- Current profile coverage: `yes`
- Adapter coverage gap: no
- Likely hook point: terminal wrapper / tool-use event
- Residual risk: arbitrary shell if raw command bypasses template adapter
- Recommended test case: OpenCode build mode pytest allow; sh-c pipe redirect deny
- Confidence: `low`

### file write/edit proposal

- Source file: `repo_missing`
- Action kind: `file_write`
- Possible tool: `write_file`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `partial`
- Adapter coverage gap: yes
- Likely hook point: filesystem hook / tool-use event
- Residual risk: diff/patch/symlink metadata may be missing from mock profile
- Recommended test case: write_file path/overwrite/diff/symlink policy coverage
- Confidence: `low`

### AGENTS.md / config / policy modification

- Source file: `repo_missing`
- Action kind: `file_write`
- Possible tool: `write_file`
- Authority-bearing fields: path, mode, overwrite, diff, patch, symlink_policy, workspace_root
- Current profile coverage: `partial`
- Adapter coverage gap: yes
- Likely hook point: filesystem hook before write
- Residual risk: future agent behavior can be changed by config/policy writes
- Recommended test case: AGENTS.md write requires explicit high-impact file capability
- Confidence: `low`

### plan mode proposed action

- Source file: `repo_missing`
- Action kind: `unknown`
- Possible tool: `proposed_action`
- Authority-bearing fields: raw_event, metadata, tool_name
- Current profile coverage: `partial`
- Adapter coverage gap: yes
- Likely hook point: agent event stream
- Residual risk: plan/build boundary may be framework-specific
- Recommended test case: plan mode never executes and produces proposed action only
- Confidence: `low`
