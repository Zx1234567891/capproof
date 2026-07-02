# CapProof Project Handoff: Stage 0 to Stage 42EVAL

Last updated: 2026-07-03

Repository: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7`

Current effective checkpoint:

```text
d80e92e
checkpoint: freeze real agent parity evaluator artifact
```

This handoff upgrades the Stage 41AP agent parity handoff with the Stage 42EVAL evaluator artifact. It is intended to let a new GPT/Codex session continue from the current release-candidate evaluation state without re-inferring prior project history.

No API key or secret is included in this document. DeepSeek credentials must come only from `DEEPSEEK_API_KEY` in the environment. Do not write API keys, tokens, runtime caches, third-party source, `node_modules/`, local auth queue state, clean-room worktrees, or generated runtime homes into commits.

## 1. Current Project State

CapProof is a capability-grounded enforcement prototype for AI agent tool use. The narrow security claim remains: authority-bearing tool actions are canonicalized and checked by CapProof's deterministic guard / Reference Monitor before a side effect can occur.

The project now includes:

- Core capability model, in-memory capability store, receipts, delegation checks, and deterministic Reference Monitor.
- Tool contracts and canonicalization for authority-bearing arguments.
- A productized standard CapProof MCP server with stdio transport, `initialize`, `tools/list`, `tools/call`, structured content, seven v1 tools, trace output, and limited sandboxed real execution.
- Hermes, OpenCode, and OpenClaw controlled local parity with DeepSeek and the same CapProof MCP server.
- Trusted ASK authorization queue and local approval CLI.
- Trace viewer, doctor UX, reviewer runbooks, MCP compatibility profile, and claims/non-claims documentation.
- A Stage 42EVAL real-agent parity evaluator artifact for fresh-run reproduction.

Stage 38REAL remains active as project policy: dry-run and preflight are safety readiness only, not completion evidence. Reusing existing reports is labeled as reuse and cannot be counted as a fresh run. Future stages must include real-environment scenarios before they can be marked complete.

## 2. Stage 41AP.1 Archive Checkpoint

Stage 41AP.1 docs checkpoint:

```text
185c20b docs: archive Stage 41AP agent parity matrix
```

Stage 41AP recorded:

- Hermes parity: true.
- OpenCode parity: true.
- OpenClaw parity: true.
- `aggregate_agent_parity_passed: true`.
- All three agents used DeepSeek through `DEEPSEEK_API_KEY`.
- All three observed `tools/list` and `tools/call`.
- All three demonstrated ALLOW, DENY, and ASK -> trusted approve -> rerun ALLOW on the tested local CapProof MCP path.
- All three reused the same CapProof MCP server and did not fork CapProof guard/security logic.

## 3. Stage 42EVAL Completed

Stage 42EVAL checkpoint:

```text
d80e92e checkpoint: freeze real agent parity evaluator artifact
```

Stage 42EVAL added or updated:

- `EVALUATOR_README.md`
- `REAL_AGENT_PARITY_EVALUATOR.md`
- `run_real_agent_parity_evaluator.py`
- `tests/test_real_agent_parity_evaluator.py`
- `artifact_reports/real_agent_parity_evaluator_report.md`
- `artifact_reports/real_agent_parity_evaluator_summary.json`
- `artifact_reports/real_agent_parity_evaluator_matrix.md`
- `artifact_reports/real_agent_parity_evaluator_matrix.json`
- `artifact_reports/final_claims_evidence_index.md`
- `artifact_reports/final_claims_evidence_index.json`
- `docs/REVIEWER_REAL_ENVIRONMENT_RUNBOOK.md`
- `docs/SECRET_HANDLING_AND_REDACTION.md`
- `docs/AGENT_PARITY_LIMITATIONS.md`

## 4. Evaluator Result

Stage 42EVAL real evaluator result:

- Evaluator mode: fresh-run.
- `evaluator_passed: true`.
- `aggregate_agent_parity_passed: true`.
- Hermes parity: true.
- OpenCode parity: true.
- OpenClaw parity: true.
- Three agents used DeepSeek: true.
- Three agents `key_source=DEEPSEEK_API_KEY`: true.
- Three agents `key_written=false`: true.
- Three agents `tools/list observed`: true.
- Three agents `tools/call observed`: true.
- Three agents ALLOW/DENY/ASK approval rerun observed: true.
- `final_claims_evidence_index` generated: true.
- Real key scan: `REAL_KEY_NOT_FOUND`.
- Forbidden tracked paths count: 0.
- Git status after Stage 42EVAL: clean.

The evaluator fresh-run called the existing real parity harnesses:

- Hermes real environment validation.
- OpenCode DeepSeek MCP parity.
- OpenClaw DeepSeek MCP parity.
- Aggregate agent parity matrix.
- Secret scan and forbidden tracked path scan.
- Claims/non-claims evidence index generation.

## 5. Validation

Recorded Stage 42EVAL validation:

- Stage 42 evaluator tests: 10 passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest`: 610 passed, 3 skipped.
- Kill tests: 24/24.
- Adapter bypass unexpected allow: 0.
- AuthSpec dangerous over-broadening: 0.
- Compileall: passed.
- Real key scan: `REAL_KEY_NOT_FOUND`.
- Forbidden tracked paths count: 0.
- Git status: clean.

## 6. Allowed Claims

It is safe to state:

- Hermes, OpenCode, and OpenClaw each exercised the same standard CapProof MCP server under controlled local real-environment conditions.
- All three used DeepSeek as the real model backend through `DEEPSEEK_API_KEY`.
- All three observed `tools/list` and `tools/call`.
- All three demonstrated ALLOW, DENY, and ASK -> trusted approve -> rerun ALLOW on the tested local CapProof MCP path.
- The artifact includes a fresh-run evaluator, trace/log/report evidence, and explicit claims/non-claims documentation.

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
Stage 43RC: clean-room release candidate reproduction
```

The goal should be to reproduce Stage 42EVAL from a clean worktree / clean-room workspace and verify that the artifact does not depend on current working-directory residue, untracked auth queues, stale traces, sandbox outputs, or runtime cache state.
