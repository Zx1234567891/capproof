# CapProof Project Handoff: Stage 0 to Stage 43RC

Last updated: 2026-07-03

Repository: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7`

Current effective checkpoint:

```text
0ab6e29
checkpoint: validate clean-room release candidate reproduction
```

This handoff upgrades the Stage 42EVAL evaluator handoff with the Stage 43RC clean-room release-candidate reproduction result. It is intended to let a new GPT/Codex session continue from the release-candidate state without re-inferring prior project history.

No API key or secret is included in this document. DeepSeek credentials must come only from `DEEPSEEK_API_KEY` in the environment. Do not write API keys, tokens, runtime caches, third-party source, `node_modules/`, local auth queue state, clean-room worktrees, or generated runtime homes into commits.

## 1. Active Policy

Stage 38REAL remains active as project policy:

- Real environment runs are required for completion evidence.
- Dry-run and preflight are safety readiness only.
- Reusing existing reports cannot count as a fresh-run pass.
- Missing real gates must block rather than pass.
- CapProof core verifier / Reference Monitor semantics must not be modified unless separately scoped and tested.

## 2. Stage 42EVAL.1 Archive Checkpoint

Stage 42EVAL.1 docs checkpoint:

```text
9176771 docs: archive Stage 42EVAL real agent parity evaluator artifact
```

Stage 42EVAL recorded:

- Real evaluator mode: fresh-run.
- `evaluator_passed: true`.
- `aggregate_agent_parity_passed: true`.
- Hermes parity: true.
- OpenCode parity: true.
- OpenClaw parity: true.
- Three agents used DeepSeek through `DEEPSEEK_API_KEY`.
- Three agents observed `tools/list` and `tools/call`.
- Three agents demonstrated ALLOW, DENY, and ASK -> trusted approve -> rerun ALLOW.
- `final_claims_evidence_index` generated.
- Real key scan: `REAL_KEY_NOT_FOUND`.
- Forbidden tracked paths count: 0.

## 3. Stage 43RC Completed

Stage 43RC checkpoint:

```text
0ab6e29 checkpoint: validate clean-room release candidate reproduction
```

Stage 43RC added:

- `CLEANROOM_REPRODUCTION.md`
- `run_cleanroom_release_candidate.py`
- `tests/test_cleanroom_release_candidate.py`
- `artifact_reports/cleanroom_release_candidate_report.md`
- `artifact_reports/cleanroom_release_candidate_summary.json`
- `artifact_reports/cleanroom_release_candidate_matrix.md`
- `artifact_reports/cleanroom_release_candidate_matrix.json`
- `docs/REVIEWER_CLEANROOM_REPRODUCTION.md`
- `.gitignore` entry for `artifact_cleanroom/`

Clean-room runtime/worktree hygiene:

- `artifact_cleanroom/` ignored.
- Clean-room worktree/runtime/cache/raw logs not committed.
- `external/` not committed.
- `external/.agent-runtimes/` not committed.
- `.venv-hermes/` not committed.
- `node_modules/` not committed.
- Local auth queue runtime state not committed.

## 4. Clean-Room Result

Stage 43RC clean-room fresh-run result:

- `cleanroom_passed: true`.
- `cleanroom_mode: fresh-run`.
- `evaluator_passed: true`.
- `aggregate_agent_parity_passed: true`.
- Hermes/OpenCode/OpenClaw parity: true/true/true.
- Three agents DeepSeek: true.
- Three agents `key_source=DEEPSEEK_API_KEY`: true.
- `key_written: false`.
- `REAL_KEY_NOT_FOUND: true`.
- `tools/list` + `tools/call` observed for all three agents: true.
- ALLOW/DENY/ASK approval rerun observed for all three agents: true.
- Forbidden tracked paths count: 0.
- `production_level_overclaim: false`.
- `raw_logs_copied: false`.
- `redaction_safe: true`.

The clean-room harness created an ignored clean worktree under `artifact_cleanroom/`, prepared ignored local runtimes, executed the Stage 42 real-agent parity evaluator as a fresh run, scanned for the real key, and copied only redaction-safe summary/report/matrix artifacts back into tracked `artifact_reports/`.

## 5. Validation

Recorded Stage 43RC validation:

- Cleanroom tests: 9 passed.
- Real evaluator tests: 10 passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest`: 619 passed, 3 skipped.
- Kill tests: 24/24.
- Adapter bypass unexpected allow: 0.
- AuthSpec dangerous over-broadening: 0.
- Compileall: passed.
- Real key scan: `REAL_KEY_NOT_FOUND`.
- Forbidden tracked paths count: 0.
- Git status after Stage 43RC: clean.

## 6. Allowed Claims

It is safe to state:

- The Stage 42 evaluator artifact was reproduced from a clean-room worktree with a real fresh run.
- Hermes, OpenCode, and OpenClaw each exercised the same standard CapProof MCP server under controlled local real-environment conditions.
- All three used DeepSeek as the real model backend through `DEEPSEEK_API_KEY`.
- All three observed `tools/list` and `tools/call`.
- All three demonstrated ALLOW, DENY, and ASK -> trusted approve -> rerun ALLOW on the tested local CapProof MCP path.
- The release-candidate artifact includes clean-room reproduction evidence and explicit claims/non-claims documentation.

## 7. Non-Claims That Must Remain

Do not claim:

- Production-level protection.
- All Hermes/OpenCode/OpenClaw built-in tool paths covered.
- All MCP clients covered.
- External MCP protection.
- Real email support.
- Raw shell support.
- Arbitrary filesystem access.
- OS-level network denial.
- DeepSeek as part of the safety TCB.
- LLM output can authorize execution.
- MCP metadata, `_meta`, tool descriptions, annotations, or client metadata can authorize execution.

The current result is local controlled parity on the tested CapProof MCP path, not comprehensive production coverage of all agent transports, built-in tools, plugins, or deployment modes.

## 8. Recommended Next Stage

Recommended next stage:

```text
Stage 44FINAL: final artifact freeze and release manifest
```

The goal should be to freeze the final artifact: release manifest, claims evidence table, commit index, reproduction commands, limitations, secret hygiene report, checksums, and final release check.
