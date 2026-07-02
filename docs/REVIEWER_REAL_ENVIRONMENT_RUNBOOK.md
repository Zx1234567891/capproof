# Reviewer Real Environment Runbook

This runbook reproduces the controlled local real-environment evaluator artifact. It assumes the repository is checked out locally and that the ignored local runtimes already exist under `external/.agent-runtimes/`.

## Safety Defaults

Readiness commands do not start agents or call DeepSeek:

```bash
python tools/run_real_agent_parity_evaluator.py --preflight
python tools/run_real_agent_parity_evaluator.py --list-agents
python tools/run_real_agent_parity_evaluator.py --require-real --fail-if-gate-missing
```

The third command should fail when gates are missing. That failure is expected and verifies Stage 38REAL policy.

## Fresh Real Evaluation

Set the gates and keep the key in the environment only:

```bash
export DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY"

ALLOW_AGENT_RUNTIME_REAL_SMOKE=1 \
ALLOW_CAPROOF_AGENT_PARITY=1 \
ALLOW_CAPROOF_REAL_ENV_VALIDATION=1 \
ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1 \
ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1 \
ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO=1 \
ALLOW_HERMES_DEEPSEEK_RUN=1 \
ALLOW_CAPROOF_MCP_REAL_HERMES=1 \
ALLOW_CAPROOF_REAL_OPENCODE_SMOKE=1 \
ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE=1 \
DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
python tools/run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report
```

Expected result: `evaluator_passed=true`.

## Inspect Evidence

```bash
less artifact_reports/real_agent_parity_evaluator_report.md
cat artifact_reports/real_agent_parity_evaluator_matrix.json
less artifact_reports/final_claims_evidence_index.md
```

## What This Proves

The evaluator proves local controlled parity for the tested CapProof MCP path across Hermes, OpenCode, and OpenClaw.

## What This Does Not Prove

It does not prove production-level protection, all built-in tool path coverage, external MCP protection, real email, raw shell support, arbitrary filesystem access, or OS-level network denial.
