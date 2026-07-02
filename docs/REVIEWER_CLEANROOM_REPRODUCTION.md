# Reviewer Clean-Room Reproduction

Use this runbook after Stage 42EVAL has passed.

## Readiness

```bash
python tools/run_cleanroom_release_candidate.py --preflight
python tools/run_cleanroom_release_candidate.py --require-real --fail-if-gate-missing
```

Preflight is not completion evidence. Missing gates must block.

## Fresh Reproduction

Keep the DeepSeek key in the environment only:

```bash
ALLOW_CAPROOF_CLEANROOM_RC=1 \
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
python tools/run_cleanroom_release_candidate.py --fresh-run --require-real --fail-if-gate-missing --clean-before-run --report
```

Expected result: `cleanroom_passed=true`.

## Inspect

```bash
less artifact_reports/cleanroom_release_candidate_report.md
cat artifact_reports/cleanroom_release_candidate_summary.json
cat artifact_reports/cleanroom_release_candidate_matrix.json
```

## Hygiene

`artifact_cleanroom/` is ignored and must not be committed. The harness copies only redaction-safe summaries back to `artifact_reports/`; raw clean-room logs are not copied.
