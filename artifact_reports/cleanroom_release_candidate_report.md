# Clean-Room Release Candidate Report

## Positioning

- Stage 43RC validates the release candidate from a clean-room worktree.
- Preflight is readiness only, not completion evidence.
- Reuse-existing reports cannot pass clean-room reproduction.
- This report does not claim production-level protection.

## Summary

- cleanroom_mode: fresh-run
- cleanroom_passed: True
- source_commit: e90d71c7d5d7ed54a649c109ea239c1a32951d13
- cleanroom_git_status_before: clean
- cleanroom_git_status_after: clean
- evaluator_passed: True
- aggregate_agent_parity_passed: True
- hermes_parity: True
- opencode_parity: True
- openclaw_parity: True
- all_agents_deepseek: True
- all_key_source_env: True
- key_written: False
- real_key_scan: REAL_KEY_NOT_FOUND
- tools_list_all_agents: True
- tools_call_all_agents: True
- allow_deny_ask_all_agents: True
- forbidden_tracked_paths_count: 0
- production_level_overclaim: False
- raw_logs_copied: False
- redaction_safe: True

## Non-Claims

- no production-level protection
- no all built-in tool paths covered
- no external MCP protection
- no real email
- no raw shell support
- no arbitrary filesystem access
- no OS-level network denial
