# Final Reproduction Commands

## No-Secret Readiness

```bash
python run_final_release_check.py --preflight
python run_final_release_check.py --require-real --fail-if-gate-missing
python run_capproof_mcp_doctor.py --all
python run_capproof_trace_viewer.py --latest --last 5
```

## Final Evaluator Fresh Run

This command calls DeepSeek. Keep `DEEPSEEK_API_KEY` in the environment only. Do not paste or write the key into files.

```bash
ALLOW_AGENT_RUNTIME_REAL_SMOKE=1 ALLOW_CAPROOF_AGENT_PARITY=1 ALLOW_CAPROOF_REAL_ENV_VALIDATION=1 ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1 ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1 ALLOW_HERMES_DEEPSEEK_RUN=1 ALLOW_CAPROOF_MCP_REAL_HERMES=1 ALLOW_CAPROOF_REAL_OPENCODE_SMOKE=1 ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE=1 DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" python run_real_agent_parity_evaluator.py --all --fresh-run --require-real --fail-if-gate-missing --report
```

## Clean-Room RC Fresh Run

```bash
ALLOW_CAPROOF_CLEANROOM_RC=1 ALLOW_AGENT_RUNTIME_REAL_SMOKE=1 ALLOW_CAPROOF_AGENT_PARITY=1 ALLOW_CAPROOF_REAL_ENV_VALIDATION=1 ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1 ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1 ALLOW_HERMES_DEEPSEEK_RUN=1 ALLOW_CAPROOF_MCP_REAL_HERMES=1 ALLOW_CAPROOF_REAL_OPENCODE_SMOKE=1 ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE=1 DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" python run_cleanroom_release_candidate.py --fresh-run --require-real --fail-if-gate-missing --clean-before-run --report
```

## Final Release Check

```bash
ALLOW_CAPROOF_FINAL_RELEASE_CHECK=1 ALLOW_CAPROOF_CLEANROOM_RC=1 ALLOW_AGENT_RUNTIME_REAL_SMOKE=1 ALLOW_CAPROOF_AGENT_PARITY=1 ALLOW_CAPROOF_REAL_ENV_VALIDATION=1 ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1 ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1 ALLOW_HERMES_DEEPSEEK_RUN=1 ALLOW_CAPROOF_MCP_REAL_HERMES=1 ALLOW_CAPROOF_REAL_OPENCODE_SMOKE=1 ALLOW_CAPROOF_REAL_OPENCLAW_SMOKE=1 DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" python run_final_release_check.py --fresh-run --require-real --fail-if-gate-missing --check-claims --check-secrets --check-forbidden-paths --check-checksums --report
```
