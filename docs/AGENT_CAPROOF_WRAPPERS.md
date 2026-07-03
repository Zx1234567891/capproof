# Agent CapProof Foreground Wrappers

This repository provides local foreground wrappers for Hermes, OpenCode,
OpenClaw, and CodeWhale. Each wrapper launches the real agent runtime and
attaches the same standard CapProof MCP stdio server with
`--sandboxed-real-execution`.

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
codewhale
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

## OpenClaw Browser UI

The OpenClaw wrapper avoids the official dashboard path that may try to install
a system service. Use the local foreground Gateway instead:

```bash
openclaw --web
```

This starts the OpenClaw Control UI on loopback only:

```text
http://127.0.0.1:18789/
```

The local auth token is printed by the wrapper. `openclaw dashboard` is also
mapped to this foreground loopback Gateway path, so it does not call systemd,
install a daemon, or write a global service.

To print the URL without starting the Gateway:

```bash
openclaw --web-url
```

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

codewhale --doctor
codewhale --where-trace
codewhale --capproof-status
codewhale --trace-follow
codewhale --mcp-tools
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

## CodeWhale MCP

CodeWhale's in-TUI MCP manager is available inside the CodeWhale session:

```text
/mcp validate
/mcp
```

The wrapper configures the MCP server under the `capproof` server name. CodeWhale
will expose discovered MCP tools with its own `mcp_<server>_<tool>` naming
convention.

## Boundaries

These wrappers prove the tested local CapProof MCP path only. They do not claim
production-level protection, all built-in tool path coverage, external MCP
protection, raw shell support, arbitrary filesystem access, real email support,
or OS-level network denial.
