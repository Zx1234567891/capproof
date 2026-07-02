# CapProof Real Agent Parity Evaluator

Stage 42EVAL freezes the controlled local real-environment evaluator artifact for Hermes, OpenCode, and OpenClaw. It does not add new security semantics and does not expand the production claim.

The evaluator command is:

```bash
python run_real_agent_parity_evaluator.py --preflight
python run_real_agent_parity_evaluator.py --list-agents
```

Those commands are readiness checks only. They do not call DeepSeek, do not start real agents, and cannot be completion evidence.

Fresh real evaluation requires explicit gates:

```bash
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
python run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report
```

The evaluator runs the existing Hermes, OpenCode, and OpenClaw real parity harnesses, regenerates `artifact_reports/agent_parity_matrix.*`, scans for key leaks and forbidden tracked paths, and writes:

- `artifact_reports/real_agent_parity_evaluator_report.md`
- `artifact_reports/real_agent_parity_evaluator_summary.json`
- `artifact_reports/real_agent_parity_evaluator_matrix.md`
- `artifact_reports/real_agent_parity_evaluator_matrix.json`
- `artifact_reports/final_claims_evidence_index.md`
- `artifact_reports/final_claims_evidence_index.json`

Allowed claim after a passing fresh run: Hermes, OpenCode, and OpenClaw each exercised the same standard CapProof MCP server with DeepSeek via `DEEPSEEK_API_KEY` on the tested local MCP path.

Non-claims remain: no production-level protection, no all built-in tool path coverage, no external MCP protection, no real email, no raw shell support, no arbitrary filesystem access, and no OS-level network-denial claim.
