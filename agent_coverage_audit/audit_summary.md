# Agent Coverage Audit Summary

Stage 18 is a static, read-only adapter coverage audit, not a real Agent integration stage.
It does not run OpenCode, OpenClaw, Hermes, third-party project commands, agents, tools, email, network clients, or shell commands.
It does not clone, build, install, or test third-party projects.
When OpenCode, OpenClaw, or Hermes source checkouts are missing, their sections are placeholder / planned audits, not complete real-source audits.
Coverage gaps in this report are a pre-integration risk inventory, not final vulnerability conclusions.

## Repo Availability

- opencode: `repo_missing` at `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/opencode`; files scanned: 0
- openclaw: `repo_missing` at `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/openclaw`; files scanned: 0
- hermes: `repo_missing` at `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/hermes-agent`; files scanned: 0
- harness: `available` at `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7`; files scanned: 170

## Static Scan Scope

- File types: `.py`, `.ts`, `.js`, `.json`, `.yaml`, `.yml`, `.toml`, README/docs/config text.
- Keywords: tool, command, shell, exec, terminal, write_file, read_file, memory, mcp, skill, plugin, gateway, message, delegate, subagent, schedule, cron, hook, watcher, approval, permission, allow, deny.
- Missing third-party repos are reported as `repo_missing`; no clone or network fetch is attempted.

## Coverage Summary

- Total surfaces scanned: 222
- High-impact surfaces found: 214
- Covered by current profile: 145
- Partial coverage: 10
- Uncovered surfaces: 67
- Coverage gap count: 77

## Top Adapter Coverage Gaps

- opencode / file write/edit proposal: diff/patch/symlink metadata may be missing from mock profile -> write_file path/overwrite/diff/symlink policy coverage
- opencode / AGENTS.md / config / policy modification: future agent behavior can be changed by config/policy writes -> AGENTS.md write requires explicit high-impact file capability
- opencode / plan mode proposed action: plan/build boundary may be framework-specific -> plan mode never executes and produces proposed action only
- openclaw / legacy tool invocation: legacy payload may hide tool-specific authority fields -> unknown OpenClaw tool surface is denied until modeled
- openclaw / watcher observed action: watcher observations must not become authorization roots -> watcher can deny or ask but cannot mint capability
- hermes / MCP tool call: server/tool metadata can select endpoint or hidden action -> MCP server/tool/url/method/header field coverage
- hermes / memory write: persistent authority laundering through memory -> authority_claims stripped and persistence scoped
- hermes / subagent delegation: delegation amplification or missing certificate -> delegation missing and amplification denied
- hermes / gateway messaging action: platform/chat_id recipient ambiguity -> gateway recipient/chat_id/channel field coverage
- hermes / scheduled automation action: stale capability replay or persistent task authority -> scheduled action bound to schedule_id/task_id/cap scope

## Recommended Integration Order

1. HarnessAdapter schema hardening for future AuthLaunderBench inputs.
2. OpenCode dry-run shell/file wrapper, because shell and filesystem surfaces are already modeled.
3. Hermes MCP/gateway/memory/delegation dry-run wrappers after field coverage tests are expanded.
4. OpenClaw compatibility wrapper once local source or event logs are available.

## Go / No-Go

- OpenCode dry-run wrapper: go only for mock/dry-run; no real execution until diff/patch/config field coverage is audited.
- Hermes dry-run wrapper: partial go; MCP/gateway/schedule fields need more tests first.
- OpenClaw compatibility wrapper: no-go for claims if repo is missing; go for placeholder compatibility tests only.
- Blocking coverage gap: no single blocker for mock dry-run wrappers; real integration needs local source audits and adapter coverage tests.
