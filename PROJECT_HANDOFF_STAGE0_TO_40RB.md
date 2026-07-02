# CapProof Project Handoff: Stage 0 to Stage 40RB

Last updated: 2026-07-02

Repository: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7`

Current effective checkpoint:

```text
c164da571e25b50e4b445d7b723473804de8d5c9
checkpoint: bootstrap OpenCode OpenClaw local runtimes for CapProof MCP
```

This handoff upgrades `PROJECT_HANDOFF_STAGE0_TO_39RT.md` with the Stage 40RB runtime bootstrap result. It is intended to let a new GPT/Codex session continue from the current state without re-inferring the project history.

Important secret-handling note: no API key is included in this file. DeepSeek or model credentials must come only from environment variables such as `DEEPSEEK_API_KEY`. Do not write API keys, tokens, secrets, runtime caches, third-party source, `node_modules/`, or local auth queue state into commits.

## 1. Current Project State

CapProof is a capability-grounded enforcement prototype for AI agent tool use. The core security claim remains narrow: authority-bearing tool actions must be converted into canonical actions and checked by CapProof's deterministic guard / Reference Monitor before any side effect occurs.

The project now includes:

- Core capability model and in-memory capability store.
- Tool contracts and canonicalization for authority-bearing arguments.
- Receipt/provenance tracking.
- Deterministic Reference Monitor.
- Memory Authority Stripping.
- Delegation and endorsement verification.
- Proof synthesis and proof replay checks.
- Kill-test and baseline evaluation harnesses.
- Agent adapter abstractions for OpenCode, OpenClaw, Hermes-like events, and harness events.
- Productized standard CapProof MCP server with stdio transport, standard `tools/list` and `tools/call`, seven v1 CapProof tools, observable trace rows, and sandboxed real execution for the limited tested subset.
- Hermes + DeepSeek real foreground validation, sandbox validation, trusted ASK approval UX, and real-environment policy.
- Artifact packaging, compatibility profile, claims/non-claims matrix, Makefile targets, and reviewer-safe reproduction checks.
- OpenCode/OpenClaw source repos under ignored `external/`.
- OpenCode/OpenClaw real CLI runtimes bootstrapped under ignored `external/.agent-runtimes/`.

Stage 38REAL remains active as project policy: dry-run and preflight are safety readiness only, not completion evidence. Future stages must run a real-environment scenario before they can be marked complete. Missing real gates must produce a blocked result such as `blocked_missing_real_env_gate`, `blocked_runtime_missing`, `blocked_bootstrap_failed`, or `blocked_prereq_missing`.

## 2. Stage 40RB Completed

Stage 40RB commit:

```text
c164da571e25b50e4b445d7b723473804de8d5c9
checkpoint: bootstrap OpenCode OpenClaw local runtimes for CapProof MCP
```

Stage 40RB advanced the project from:

```text
OpenCode/OpenClaw source repo present, runtime missing
```

to:

```text
OpenCode/OpenClaw source repo present
OpenCode/OpenClaw real CLI runtime present
OpenCode/OpenClaw real_smoke_eligible=true
```

### OpenCode

- OpenCode source: `external/opencode`
- OpenCode source commit: `f52424e05fab0edddb4462112ceb02044085f903`
- OpenCode remote: `https://github.com/anomalyco/opencode`
- OpenCode runtime bootstrap: success
- OpenCode binary: `external/.agent-runtimes/bin/opencode`
- OpenCode version: `1.17.13`
- OpenCode runtime_present: true
- OpenCode real_smoke_eligible: true
- OpenCode real integration claim: false
- OpenCode real agent smoke: not run in Stage 40RB
- OpenCode `tools/list` observed from real agent: false
- OpenCode `tools/call` observed from real agent: false

### OpenClaw

- OpenClaw source: `external/openclaw`
- OpenClaw source commit: `5bcd25f0fb6de3cc2ba6b6a7688a9361eb355143`
- OpenClaw remote: `https://github.com/openclaw/openclaw`
- OpenClaw runtime bootstrap: success
- OpenClaw binary: `external/.agent-runtimes/bin/openclaw`
- OpenClaw version: `OpenClaw 2026.6.11 (e085fa1)`
- OpenClaw MCP probes/status/help callable:
  - `openclaw mcp status`
  - `openclaw mcp doctor --probe`
  - `openclaw mcp tools --help`
- OpenClaw runtime_present: true
- OpenClaw real_smoke_eligible: true
- OpenClaw real integration claim: false
- OpenClaw real agent smoke: not run in Stage 40RB
- OpenClaw `tools/list` observed from real agent: false
- OpenClaw `tools/call` observed from real agent: false

## 3. Stage 40RB Security and Hygiene

- `external/` not committed.
- `external/.agent-runtimes/` not committed.
- `.venv-hermes/` not committed.
- `node_modules/` not committed.
- Runtime cache not committed.
- Local auth queue runtime state not committed.
- No API key written.
- No sudo/system install.
- No OpenClaw onboarding/daemon/gateway.
- No OpenCode/OpenClaw agent smoke yet.
- No OpenCode/OpenClaw real integration claim.
- No production-level overclaim.
- No fork of CapProof guard/security logic.
- CapProof MCP server reused:

```text
python run_capproof_mcp_server.py --stdio --sandboxed-real-execution
```

## 4. Stage 40RB Validation

- Runtime bootstrap tests: 7 passed.
- Runtime gate tests: 7 passed.
- Agent MCP audit tests: 5 passed.
- OpenCode MCP config tests: 3 passed.
- OpenClaw MCP config tests: 3 passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest`: 574 passed, 3 skipped.
- Kill tests: 24/24.
- Adapter bypass unexpected allow: 0.
- AuthSpec dangerous over-broadening: 0.
- Compileall: passed.
- Secret scan for Stage 40RB tracked files: no key-like pattern found.
- Forbidden tracked paths check: no `external/`, `external/.agent-runtimes/`, `.venv-hermes/`, `node_modules/`, runtime cache, or local auth queue tracked.

## 5. Current Claims Allowed

It is safe to state:

- OpenCode source is present under ignored `external/opencode`.
- OpenCode real CLI runtime was bootstrapped locally under ignored `external/.agent-runtimes/`.
- OpenCode binary exists at `external/.agent-runtimes/bin/opencode`.
- OpenCode `--version` succeeded: `1.17.13`.
- OpenCode `real_smoke_eligible=true`.
- OpenClaw source is present under ignored `external/openclaw`.
- OpenClaw real CLI runtime was bootstrapped locally under ignored `external/.agent-runtimes/`.
- OpenClaw binary exists at `external/.agent-runtimes/bin/openclaw`.
- OpenClaw `--version` succeeded: `OpenClaw 2026.6.11 (e085fa1)`.
- OpenClaw `mcp status`, `mcp doctor --probe`, and `mcp tools --help` surfaces are callable.
- OpenClaw `real_smoke_eligible=true`.
- No OpenCode/OpenClaw real integration claim has been made yet.

## 6. Claims Not Yet Allowed

Do not claim:

- OpenCode MCP integration complete.
- OpenCode `tools/list` observed from a real OpenCode agent process.
- OpenCode `tools/call` observed from a real OpenCode agent process.
- OpenClaw MCP integration complete.
- OpenClaw live tools proof complete unless a later Stage 40C-P run proves it.
- OpenClaw agent `tools/call` observed unless a later Stage 40C-A run proves it.
- OpenCode/OpenClaw built-in tool paths covered.
- OpenCode/OpenClaw protected by CapProof in production.
- All MCP clients covered.
- All agent tool paths covered.
- OS-level network denial.
- Production-level protection.

## 7. Next Recommended Stages

Recommended order:

1. Stage 40O: real OpenCode CapProof MCP smoke.
2. Stage 40C-P: real OpenClaw CapProof MCP live probe.
3. Stage 40C-A: real OpenClaw agent `tools/call` smoke, only if OpenClaw runtime path supports it.

Stage 40O completion must be based on a real OpenCode process observing and invoking the standard CapProof MCP server. Config files, dry-run, version probes, or local JSON-RPC clients are not enough.

