# Agent CapProof Foreground Wrappers

This repository provides local foreground wrappers for Hermes, OpenCode, and
OpenClaw. Each wrapper launches the real agent runtime and attaches the same
standard CapProof MCP stdio server with `--sandboxed-real-execution`.

## Install

From the repository root:

```bash
make install-local-agent-wrappers
```

Ensure `~/.local/bin` is on `PATH`, then open a new terminal.

## Environment

The model key is environment-only:

```bash
export DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY"
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-v4-pro
```

Do not write the key into config files, reports, traces, logs, or commits.

## Foreground Commands

```bash
hermes
opencode
openclaw
```

The wrappers print a short startup banner to stderr showing:

- CapProof MCP attached
- agent runtime path
- DeepSeek model
- stdio MCP mode
- sandboxed real execution status
- trace path
- live log path
- auth queue path

## Status Commands

```bash
opencode --doctor
opencode --where-trace
opencode --capproof-status
opencode --trace-follow

openclaw --doctor
openclaw --where-trace
openclaw --capproof-status
openclaw --trace-follow
```

`--doctor`, `--where-trace`, and `--capproof-status` do not call DeepSeek.
`--trace-follow` only follows the local CapProof trace file.

## Real Parity Validation

These commands run the real agent parity harnesses:

```bash
opencode --parity-demo
openclaw --parity-demo
```

They require `DEEPSEEK_API_KEY` and run real OpenCode/OpenClaw processes,
DeepSeek calls, CapProof MCP `tools/list`, CapProof MCP `tools/call`, sandbox
ALLOW paths, DENY gates, and ASK approval reruns.

## Boundaries

These wrappers prove the tested local CapProof MCP path only. They do not claim
production-level protection, all built-in tool path coverage, external MCP
protection, raw shell support, arbitrary filesystem access, real email support,
or OS-level network denial.
