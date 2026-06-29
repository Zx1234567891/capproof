# Hermes Trace Collection Safety Policy

This plan is capture-only. It is not an enforcement wrapper and not a claim that
CapProof is integrated with or protects real Hermes.

## Allowed

- capture-only mode
- mock tools
- local fixture tasks
- no-network mode
- no-real-shell mode
- no-real-email mode
- no-real-file-side-effect mode
- timeout-limited process
- trace-only output

## Prohibited

- install dependencies
- run production Hermes agent
- run arbitrary shell
- run network tools
- run real MCP servers
- send real messages
- write outside temp workspace
- read secrets
- use real tokens
- execute user-provided shell strings

## Required Capture-run Environment

- `ALLOW_HERMES_CAPTURE_RUN=1`
- `HERMES_CAPTURE_COMMAND` is set
- `HERMES_CAPTURE_TRACE_PATH` is set
- `CAPPROOF_CAPTURE_ONLY=1`
- `CAPPROOF_NO_REAL_TOOLS=1`
- `NO_NETWORK=1`
- `HERMES_TEST_WORKSPACE` points to temp workspace
