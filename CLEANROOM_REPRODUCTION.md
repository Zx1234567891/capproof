# Clean-Room Release Candidate Reproduction

Stage 43RC verifies that the Stage 42EVAL artifact can be reproduced from a clean worktree. It does not add new security semantics, does not modify the Reference Monitor, and does not expand sandbox capability.

## Default Safety

These commands do not call DeepSeek and do not start real agents:

```bash
python tools/run_cleanroom_release_candidate.py --preflight
python tools/run_cleanroom_release_candidate.py --require-real --fail-if-gate-missing
```

The second command must fail when gates are missing. That is expected and confirms Stage 38REAL behavior.

## Fresh Clean-Room Run

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

The harness creates an ignored linked worktree under `artifact_cleanroom/worktrees/capproof-rc`, prepares ignored runtimes under that worktree, runs the Stage 42 evaluator as a fresh run, scans for the real key, and copies only redaction-safe summary/report/matrix artifacts back to root `artifact_reports/`.

## Expected Tracked Artifacts

- `artifact_reports/cleanroom_release_candidate_report.md`
- `artifact_reports/cleanroom_release_candidate_summary.json`
- `artifact_reports/cleanroom_release_candidate_matrix.md`
- `artifact_reports/cleanroom_release_candidate_matrix.json`

## Non-Claims

No production-level protection, all built-in tool coverage, external MCP protection, real email, raw shell support, arbitrary filesystem access, or OS-level network denial is claimed.
