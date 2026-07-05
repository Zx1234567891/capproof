# CapProof MCP npm Package

The npm package is a thin installation and launch layer for the existing
CapProof artifact. It does not reimplement CapProof guard logic and does not
mint capabilities. All security decisions still flow through the standard
Python CapProof MCP server and Reference Monitor path already used by the local
wrappers.

## Local package build

From the repository root:

```bash
npm pack
npm install -g ./capproof-mcp-0.1.0.tgz
```

After installation, these commands are available:

```bash
capproof-mcp
capproof-mcp setup
capproof-mcp doctor
capproof-mcp list-tools
capproof-mcp serve
capproof-mcp trace
capproof-mcp auth-queue doctor

hermes
opencode
openclaw
codewhale
```

`capproof-mcp serve` starts the same standard MCP stdio server:

```bash
python tools/run_capproof_mcp_server.py --stdio --sandboxed-real-execution
```

## Model key handling

The DeepSeek key remains environment-only:

```bash
export DEEPSEEK_API_KEY="<your key>"
```

The npm package must not write the key into package files, agent config, traces,
logs, reports, or commits. The `setup` output only prints whether the key is
present.

## Runtime bootstrap boundary

The npm package installs CapProof launch commands. It does not silently install
third-party agent runtimes during `npm install`. Runtime installation remains an
explicit action:

```bash
capproof-mcp bootstrap-runtimes --preflight
ALLOW_AGENT_RUNTIME_BOOTSTRAP=1 capproof-mcp bootstrap-runtimes --bootstrap all --verify --report
```

If dependency download is required, keep the existing second gate:

```bash
ALLOW_AGENT_RUNTIME_BOOTSTRAP=1 \
ALLOW_AGENT_RUNTIME_NETWORK=1 \
capproof-mcp bootstrap-runtimes --bootstrap all --verify --report
```

## Non-claims

This package does not claim production-level protection, all built-in tool path
coverage, real email support, raw shell support, arbitrary filesystem access,
external MCP protection, or OS-level network denial. It packages the tested
local CapProof MCP path and foreground agent wrappers.
