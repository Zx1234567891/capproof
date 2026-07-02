# Artifact Release Manifest

- artifact name: CapProof Hermes OpenCode OpenClaw MCP parity artifact
- release candidate stage: 43RC
- current commit: 955b1b19e4893ac9368c97f2856b1b9384ac4b1c
- final checkpoint note: Stage 44FINAL commit is the git HEAD after final artifact commit.

## Important Scripts

- `tools/run_real_agent_parity_evaluator.py`
- `tools/run_cleanroom_release_candidate.py`
- `tools/run_agent_parity_matrix.py`
- `tools/run_real_environment_validation.py`
- `tools/run_capproof_mcp_server.py`
- `tools/run_capproof_trace_viewer.py`
- `tools/run_capproof_auth_queue.py`

## Important Docs

- `MCP_COMPATIBILITY.md`
- `CLAIMS_AND_NON_CLAIMS.md`
- `REAL_ENVIRONMENT_VALIDATION.md`
- `EVALUATOR_README.md`
- `REAL_AGENT_PARITY_EVALUATOR.md`
- `CLEANROOM_REPRODUCTION.md`
- `docs/REVIEWER_REAL_ENVIRONMENT_RUNBOOK.md`
- `docs/REVIEWER_CLEANROOM_REPRODUCTION.md`
- `docs/SECRET_HANDLING_AND_REDACTION.md`
- `docs/AGENT_PARITY_LIMITATIONS.md`

## Important Reports

- `artifact_reports/agent_parity_matrix.json`
- `artifact_reports/real_agent_parity_evaluator_summary.json`
- `artifact_reports/cleanroom_release_candidate_summary.json`
- `artifact_reports/final_claims_evidence_index.json`

## Ignored Runtime Paths

- `external/`
- `external/.agent-runtimes/`
- `artifact_cleanroom/`
- `.venv-hermes/`
- `node_modules/`
- `real_agent_integrations/hermes_mcp_server/auth_queue/`
