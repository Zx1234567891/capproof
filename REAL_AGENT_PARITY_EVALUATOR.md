# Real Agent Parity Evaluator Specification

## Purpose

The Stage 42EVAL evaluator is a reviewer-facing artifact that reruns or summarizes controlled local real-environment parity for:

- Hermes
- OpenCode
- OpenClaw

Each agent must use DeepSeek through `DEEPSEEK_API_KEY`, connect to the same standard CapProof MCP stdio server, observe `tools/list` and `tools/call`, demonstrate sandbox ALLOW behavior, DENY gate behavior, and ASK -> trusted approve -> rerun ALLOW.

## Modes

- `--preflight`: readiness only; never completion evidence.
- `--list-agents`: prints supported agents.
- `--reuse-existing-reports`: reads existing reports and marks `evaluator_mode=reuse_existing`; not a fresh real run.
- `--fresh-run`: runs real agent parity harnesses.
- `--require-real --fail-if-gate-missing`: returns nonzero when required gates are absent.

## Completion Rule

`evaluator_passed=true` requires all of the following:

- `--fresh-run`.
- All explicit real-environment gates are present.
- Hermes, OpenCode, and OpenClaw real parity commands return zero.
- Aggregate parity matrix passes.
- Secret scan reports `REAL_KEY_NOT_FOUND`.
- No forbidden runtime or third-party paths are tracked.

## Required Gates

- `ALLOW_AGENT_RUNTIME_REAL_SMOKE=1`
- `ALLOW_CAPROOF_AGENT_PARITY=1`
- `ALLOW_CAPROOF_REAL_ENV_VALIDATION=1`
- `ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1`
- `ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1`
- `ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO=1`
- `ALLOW_HERMES_DEEPSEEK_RUN=1`
- `ALLOW_CAPROOF_MCP_REAL_HERMES=1`
- `ALLOW_CAPROOF_REAL_OPENCODE_SMOKE=1`
- `ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE=1`
- `DEEPSEEK_API_KEY` present in the environment

## Evidence

The evaluator matrix includes:

- agent
- real agent process status
- agent binary and version
- DeepSeek call status
- DeepSeek key source and write status
- standard CapProof MCP server status
- `tools/list`
- `tools/call`
- ALLOW read/write/command observation
- DENY outside path/raw shell/attacker observation
- ASK pending request
- trusted approval
- approval receipt
- rerun ALLOW
- LLM/MCP metadata rejection
- executor-called-on-DENY/ASK count
- trace/live-log/report generation
- parity result and reason
